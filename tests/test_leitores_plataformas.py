"""Testes da camada genérica de leitura visual para as 4 plataformas."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from calibracao_plataformas import (  # noqa: E402
    PERFIS_POR_PLATAFORMA,
    PLATAFORMAS,
    obter_perfil,
    perfil_confirmado,
)
from leitor_visual_plataforma import (  # noqa: E402
    ResultadoVisual,
    ler_ativo_plataforma,
    ler_botoes_plataforma,
    ler_payout_plataforma,
    ler_timeframe_plataforma,
)
from leitor_texto_macos import LeituraTexto  # noqa: E402


# ---------------------------------------------------------------------------
# Registro de perfis
# ---------------------------------------------------------------------------

def test_quatro_plataformas_registradas():
    assert PLATAFORMAS == ("iq", "quotex", "casa_trader", "avallon")


def test_obter_perfil_valida_nome():
    for plataforma in PLATAFORMAS:
        perfil = obter_perfil(plataforma)
        assert perfil.plataforma == plataforma
    with pytest.raises(ValueError, match="plataforma desconhecida"):
        obter_perfil("binance")


def test_perfil_iq_reaproveita_calibracao_original():
    """O perfil IQ deve usar exatamente as regiões do PERFIL_IQ_2026_08_30."""
    from calibracao_iq import PERFIL_IQ_2026_08_30

    perfil = obter_perfil("iq")
    assert perfil.ativo_selecionado == PERFIL_IQ_2026_08_30.ativo_selecionado
    assert perfil.payout == PERFIL_IQ_2026_08_30.payout
    assert perfil.timeframe == PERFIL_IQ_2026_08_30.timeframe


def test_somente_iq_tem_perfil_confirmado():
    """Quotex/CasaTrader/Avallon são ESTIMATIVAS: nunca liberar disparos reais."""
    assert perfil_confirmado("iq") is True
    for plataforma in ("quotex", "casa_trader", "avallon"):
        assert perfil_confirmado(plataforma) is False


def test_perfis_tem_proporcao_valida():
    for perfil in PERFIS_POR_PLATAFORMA.values():
        assert perfil.proporcao_referencia > 1.0


def test_geometria_ok_valida_proporcao_da_janela():
    perfil = obter_perfil("quotex")  # referência 16/9
    assert perfil.geometria_ok(1920, 1080) is True    # exatamente 16/9
    assert perfil.geometria_ok(1600, 900) is True     # também 16/9
    assert perfil.geometria_ok(1024, 1024) is False   # quadrado, fora


def test_recorte_converte_regiao_para_pixels():
    perfil = obter_perfil("quotex")
    caixa = perfil.recorte(perfil.payout, 1000, 1000)
    assert caixa == (845, 240, 995, 360)
    with pytest.raises(ValueError, match="não define essa região"):
        perfil.recorte(perfil.timeframe, 1000, 1000)  # quotex não declara timeframe


# ---------------------------------------------------------------------------
# Leitores genéricos (OCR mockado, capturas reais pequenas)
# ---------------------------------------------------------------------------

def _captura_169(tmp_path, largura=1600, altura=900):
    """Gera uma captura pequena com a proporção 16/9 das plataformas web."""
    caminho = tmp_path / "captura.png"
    Image.new("RGB", (largura, altura), color=(20, 20, 30)).save(caminho)
    return str(caminho)


def _leitura_ok(textos):
    return LeituraTexto(True, tuple(textos), "ok")


def test_ler_ativo_plataforma_reconhece_ativo_conhecido(tmp_path):
    from painel_abas_iq import ATIVOS_IQ_CONHECIDOS
    ativo_esperado = ATIVOS_IQ_CONHECIDOS[0]
    captura = _captura_169(tmp_path)

    with patch("leitor_visual_plataforma.ler_textos",
               return_value=_leitura_ok([f"  {ativo_esperado}  "])):
        resultado = ler_ativo_plataforma(captura, "quotex")

    assert resultado.sucesso is True
    assert resultado.valor == ativo_esperado


def test_ler_payout_plataforma_valor_unico(tmp_path):
    captura = _captura_169(tmp_path)
    with patch("leitor_visual_plataforma.ler_textos",
               return_value=_leitura_ok(["+92%"])):
        resultado = ler_payout_plataforma(captura, "casa_trader")

    assert resultado.sucesso is True
    assert resultado.valor == pytest.approx(0.92)


def test_ler_payout_plataforma_ambiguo_falha_fechado(tmp_path):
    """Dois percentuais diferentes na região = falha (nunca sinal)."""
    captura = _captura_169(tmp_path)
    with patch("leitor_visual_plataforma.ler_textos",
               return_value=_leitura_ok(["+92%", "+85%"])):
        resultado = ler_payout_plataforma(captura, "casa_trader")

    assert resultado.sucesso is False
    assert "ambígua" in resultado.mensagem


def test_ler_timeframe_plataforma_reconhece_m1(tmp_path):
    """Apenas a IQ tem região de timeframe calibrada até agora."""
    captura = _captura_169(tmp_path, largura=3456, altura=2234)  # proporção da IQ
    with patch("leitor_visual_plataforma.ler_textos",
               return_value=_leitura_ok(["M1"])):
        resultado = ler_timeframe_plataforma(captura, "iq")

    assert resultado.sucesso is True
    assert resultado.valor == "M1"


def test_leitura_em_plataforma_sem_regiao_declarada_falha(tmp_path):
    """Quotex não declara região de timeframe; leitura deve falhar claro."""
    captura = _captura_169(tmp_path)
    resultado = ler_timeframe_plataforma(captura, "quotex")
    assert resultado.sucesso is False
    assert "não define essa região" in resultado.mensagem


def test_captura_inexistente_falha_sem_excecao(tmp_path):
    for leitor, plataforma in (
        (ler_ativo_plataforma, "quotex"),
        (ler_payout_plataforma, "avallon"),
        (ler_timeframe_plataforma, "casa_trader"),
    ):
        resultado = leitor(str(tmp_path / "nao_existe.png"), plataforma)
        assert resultado.sucesso is False
        assert "não encontrada" in resultado.mensagem


def test_geometria_fora_de_tolerancia_bloqueia_leitura(tmp_path):
    """Proporção muito diferente da referência impede OCR enganoso."""
    captura = _captura_169(tmp_path, largura=1024, altura=1024)  # quadrado vs 16/9

    resultado = ler_payout_plataforma(captura, "quotex")

    assert resultado.sucesso is False
    assert "recalibrar" in resultado.mensagem


def test_ler_botoes_plataforma_com_captura_inexistente(tmp_path):
    compra, venda = ler_botoes_plataforma(str(tmp_path / "nao_existe.png"), "quotex")
    assert compra is None and venda is None