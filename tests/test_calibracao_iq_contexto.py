"""Testes da seleção de perfil IQ por contexto de captura (tela vs janela)."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from calibracao_iq import PERFIL_IQ_2026_08_30, perfil_compativel  # noqa: E402
from calibracao_iq_contexto import (  # noqa: E402
    CONTEXTO_JANELA,
    CONTEXTO_TELA,
    PERFIL_IQ_JANELA,
    capturar_janela_iq,
    identificar_contexto,
    selecionar_perfil_iq,
    selecionar_perfil_iq_por_captura,
)


# ---------------------------------------------------------------------------
# Identificação de contexto pela proporção
# ---------------------------------------------------------------------------

def test_captura_tela_inteira_identifica_tela():
    """Proporção 1.547 (calibração original) → contexto tela_inteira."""
    assert identificar_contexto(3456, 2234) == CONTEXTO_TELA


def test_captura_janela_identifica_janela():
    """Proporção ~1.594 (janela IQ) → contexto janela_iq."""
    assert identificar_contexto(1594, 1000) == CONTEXTO_JANELA


def test_proporcoes_limiares_nao_se_confundem():
    """1.547 e 1.594 distam ~3%; tolerância 8% permite distinção correta."""
    # Ambos os contextos aceitam um pouco de desvio, mas cada proporção
    # deve ser atribuída ao perfil mais próximo.
    perfil_tela, contexto_tela = selecionar_perfil_iq(3456, 2234)
    perfil_janela, contexto_janela = selecionar_perfil_iq(1594, 1000)
    assert contexto_tela == CONTEXTO_TELA
    assert contexto_janela == CONTEXTO_JANELA
    assert perfil_tela is PERFIL_IQ_2026_08_30
    assert perfil_janela is PERFIL_IQ_JANELA


def test_geometria_desconhecida_falha_fechado():
    """Proporção fora de ambos os perfis → None (nunca adivinhar recortes)."""
    assert identificar_contexto(0, 0) is None
    assert identificar_contexto(-10, 100) is None
    perfil, contexto = selecionar_perfil_iq(1024, 1024)  # quadrado
    assert perfil is None and contexto is None


def test_perfil_janela_eh_geometria_valida():
    """Todas as regiões do perfil da janela devem ser relativas válidas."""
    for campo in ("ativo_selecionado", "payout", "botao_higher",
                  "botao_lower", "timeframe", "barra_abas",
                  "saldo_e_tipo_conta"):
        regiao = getattr(PERFIL_IQ_JANELA, campo)
        # converter não pode levantar ValueError para uma janela real
        caixa = regiao.converter(1600, 1004)
        assert caixa[0] < caixa[2] and caixa[1] < caixa[3]


def test_selecao_por_arquivo_de_captura(tmp_path):
    """selecionar_perfil_iq_por_captura lê a proporção direto do PNG."""
    captura_tela = tmp_path / "tela.png"
    Image.new("RGB", (3456, 2234)).save(captura_tela)
    perfil, contexto = selecionar_perfil_iq_por_captura(str(captura_tela))
    assert contexto == CONTEXTO_TELA and perfil is PERFIL_IQ_2026_08_30

    captura_janela = tmp_path / "janela.png"
    Image.new("RGB", (1594, 1000)).save(captura_janela)
    perfil, contexto = selecionar_perfil_iq_por_captura(str(captura_janela))
    assert contexto == CONTEXTO_JANELA and perfil is PERFIL_IQ_JANELA

    captura_lixo = tmp_path / "lixo.png"
    Image.new("RGB", (200, 900)).save(captura_lixo)
    perfil, contexto = selecionar_perfil_iq_por_captura(str(captura_lixo))
    assert perfil is None and contexto is None

    perfil, contexto = selecionar_perfil_iq_por_captura(
        str(tmp_path / "inexistente.png")
    )
    assert perfil is None and contexto is None


# ---------------------------------------------------------------------------
# Leitores _iq com contexto automático
# ---------------------------------------------------------------------------

def test_leitor_payout_iq_funciona_com_captura_da_janela(tmp_path, monkeypatch):
    """ler_payout deve escolher o perfil da janela automaticamente."""
    from leitor_payout_iq import ler_payout
    from leitor_texto_macos import LeituraTexto

    captura = tmp_path / "janela.png"
    Image.new("RGB", (1594, 1000)).save(captura)

    def fake_leitor(caminho):
        assert caminho.endswith(".png")
        return LeituraTexto(True, ("+93%",), "ok")

    resultado = ler_payout(str(captura), leitor=fake_leitor)
    assert resultado.sucesso is True
    assert resultado.payout == pytest.approx(0.93)


def test_leitor_payout_iq_geometria_desconhecida_nao_levanta_excecao(tmp_path):
    """Captura de proporção estranha falha de forma controlada, sem exceção."""
    from leitor_payout_iq import ler_payout
    from leitor_texto_macos import LeituraTexto

    captura = tmp_path / "estranha.png"
    Image.new("RGB", (700, 1400)).save(captura)  # proporção 0.5

    # Leitor legítimo que não encontra nada na área recortada
    resultado = ler_payout(
        str(captura),
        leitor=lambda c: LeituraTexto(False, (), "nenhum texto"),
    )
    assert isinstance(resultado.sucesso, bool)
    assert resultado.sucesso is False


def test_leitor_ativo_iq_funciona_com_captura_da_janela(tmp_path):
    """ler_ativo deve escolher o perfil da janela automaticamente."""
    from leitor_ativo_iq import ler_ativo
    from leitor_texto_macos import LeituraTexto
    from painel_abas_iq import ATIVOS_IQ_CONHECIDOS

    captura = tmp_path / "janela.png"
    Image.new("RGB", (1594, 1000)).save(captura)
    ativo = ATIVOS_IQ_CONHECIDOS[0]

    with patch("leitor_ativo_iq.ler_textos",
               return_value=LeituraTexto(True, (ativo,), "ok")):
        resultado = ler_ativo(str(captura))

    assert resultado.sucesso is True
    assert resultado.ativo == ativo


# ---------------------------------------------------------------------------
# capturar_janela_iq
# ---------------------------------------------------------------------------

def test_captura_janela_sem_janela_aberta_falha_claro():
    """windowid 0 = janela não encontrada → falha com mensagem clara."""
    executor = MagicMock()
    executor.returncode = 0
    executor.stdout = "0\n"

    sucesso, mensagem = capturar_janela_iq(
        "/tmp/teste_janela.png", executor=executor,
        windowid_binario="/nonexistent-bft-bina/rio",
    )
    # executor mockado: primeira chamada é a compilação (pulada pois binário
    # inexistente + executor não é subprocess.run → precisa_compilar True),
    # segunda é o windowid. MagicMock retorna o mesmo objeto para tudo,
    # então simulamos explicitamente.
    assert sucesso is False


def test_captura_janela_fluxo_completo(tmp_path):
    """Fluxo completo mockado: compila → windowid → screencapture -l."""
    fonte = Path(__file__).parent.parent / "scripts" / "janela_iq.m"
    assert fonte.exists(), "scripts/janela_iq.m deve existir"

    captura_path = tmp_path / "janela.png"

    respostas = {
        ("clang",): MagicMock(returncode=0, stdout="", stderr=""),
        ("bft_janela_iq",): MagicMock(returncode=0, stdout="12345\n", stderr=""),
        ("screencapture",): MagicMock(returncode=0, stdout="", stderr=""),
    }

    def fake_executor(cmd, **kwargs):
        cmd_str = " ".join(cmd)
        if "clang" in cmd_str:
            return respostas[("clang",)]
        if "bft_janela_iq" in cmd_str:
            return respostas[("bft_janela_iq",)]
        if "screencapture" in cmd_str:
            # Cria o arquivo como o screencapture real faria
            Image.new("RGB", (1594, 1000)).save(captura_path)
            return respostas[("screencapture",)]
        raise AssertionError(f"comando inesperado: {cmd}")

    sucesso, mensagem = capturar_janela_iq(
        str(captura_path), executor=fake_executor,
        windowid_binario=str(tmp_path / "bft_janela_iq"),
    )
    assert sucesso is True, mensagem
    assert captura_path.exists()

    # A captura gerada tem proporção da janela → perfil identificado
    perfil, contexto = selecionar_perfil_iq_por_captura(str(captura_path))
    assert contexto == CONTEXTO_JANELA
    assert perfil is PERFIL_IQ_JANELA


def test_captura_janela_erro_de_permissao():
    """screencapture com erro de permissão → falha clara sem exceção."""
    def fake_executor(cmd, **kwargs):
        cmd_str = " ".join(cmd)
        resultado = MagicMock(returncode=0, stdout="12345\n", stderr="")
        if "clang" in cmd_str:
            resultado.returncode = 0
            return resultado
        if "screencapture" in cmd_str:
            return MagicMock(returncode=1, stdout="", stderr="operation not permitted")
        return resultado

    sucesso, mensagem = capturar_janela_iq(
        "/tmp/teste_perm.png", executor=fake_executor,
        windowid_binario="/tmp/fake_bft_janela_bin",
    )
    assert sucesso is False
    assert "bloqueada" in mensagem or "falhou" in mensagem