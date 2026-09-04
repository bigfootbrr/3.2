"""Testes da validação de captura e calibração da Quotex."""

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from validacao_captura import (  # noqa: E402
    CAMINHO_PADRAO_CALIBRACAO_QUOTEX,
    CHAVES_OBRIGATORIAS,
    listar_capturas_inutilizaveis,
    validar_calibracao_quotex,
    validar_captura,
)


# ---------------------------------------------------------------------------
# validar_captura
# ---------------------------------------------------------------------------

def test_captura_corrompida_2x2_recusada(tmp_path):
    """A captura real que causou o problema (2x2 px) deve ser recusada."""
    captura = tmp_path / "corrompida.png"
    Image.new("RGB", (2, 2)).save(captura)
    resultado = validar_captura(str(captura))
    assert resultado.sucesso is False
    assert "inutilizável" in resultado.mensagem
    assert "2x2" in resultado.mensagem
    assert "recapturar" in resultado.mensagem


def test_captura_inexistente_recusada(tmp_path):
    resultado = validar_captura(str(tmp_path / "nao_existe.png"))
    assert resultado.sucesso is False
    assert "não encontrada" in resultado.mensagem


def test_captura_pequena_demais_recusada(tmp_path):
    """Recorte acidental de 50x40 não serve para calibrar."""
    captura = tmp_path / "pequena.png"
    Image.new("RGB", (50, 40), color=(40, 40, 60)).save(captura)
    resultado = validar_captura(str(captura))
    assert resultado.sucesso is False


def test_captura_monocromatica_recusada(tmp_path):
    """Tela travada (cor única) deve ser recusada mesmo grande."""
    captura = tmp_path / "travada.png"
    Image.new("RGB", (1920, 1080), color=(30, 30, 30)).save(captura)
    resultado = validar_captura(str(captura))
    assert resultado.sucesso is False
    assert "cor única" in resultado.mensagem


def test_captura_proporcao_implausivel_recusada(tmp_path):
    """Fatia 3000x400 (proporção 7.5) tem tamanho ok mas formato absurdo."""
    captura = _captura_com_conteudo(tmp_path / "fatia.png", 3000, 400)
    resultado = validar_captura(captura)
    assert resultado.sucesso is False
    assert "proporção" in resultado.mensagem


def _captura_com_conteudo(caminho, largura=1920, altura=1080):
    """Gera captura sintética com variação contínua (como uma tela real).

    Usa bandas horizontais coloridas (simula gráfico + painéis) em vez de
    pontos isolados: putpixel esparso pinta <1% da imagem e o resize dilui
    o desvio a zero — falso 'tela travada'.
    """
    imagem = Image.new("RGB", (largura, altura))
    banda = max(1, altura // 24)
    for y in range(altura):
        base = (y // banda) * 37
        for x in range(0, largura, max(1, largura // 128)):
            imagem.putpixel((x, y), ((base + x) % 255, (base * 2 + y) % 255, (x ^ y) % 255))
    imagem.save(caminho)
    return str(caminho)


def test_captura_utilizada_aceita(tmp_path):
    """Captura real de trading (16/9 com ruído) passa na validação."""
    captura = _captura_com_conteudo(tmp_path / "ok.png")
    resultado = validar_captura(captura)
    assert resultado.sucesso is True
    assert resultado.largura == 1920 and resultado.altura == 1080


def test_captura_vertical_utilizada_aceita(tmp_path):
    """Janela vertical plausível (ex.: mobile) também passa."""
    captura = _captura_com_conteudo(tmp_path / "vertical.png", 720, 1400)
    assert validar_captura(captura).sucesso is True


# ---------------------------------------------------------------------------
# Auditoria de assets
# ---------------------------------------------------------------------------

def test_auditoria_encontra_a_corrompida(tmp_path):
    """A varredura deve apontar exatamente as capturas ruins como inutilizáveis."""
    boa = _captura_com_conteudo(tmp_path / "boa.png", 1600, 900)
    (tmp_path / "corrompida.png").write_bytes(b"")  # inválida
    Image.new("RGB", (2, 2)).save(tmp_path / "degenerada.png")

    inutilizaveis = listar_capturas_inutilizaveis(tmp_path)
    assert "degenerada.png" in inutilizaveis
    assert "corrompida.png" in inutilizaveis
    assert "boa.png" not in inutilizaveis


def test_pasta_vazia_sem_auditoria_erro(tmp_path):
    assert listar_capturas_inutilizaveis(tmp_path) == []
    assert listar_capturas_inutilizaveis(tmp_path / "nao_existe") == []


# ---------------------------------------------------------------------------
# validar_calibracao_quotex
# ---------------------------------------------------------------------------

def _calibracao_valida(tela=(1920, 1080)):
    return {
        "compra": [1500, 700],
        "venda": [1500, 800],
        "tela": list(tela),
    }


def test_calibracao_inexistente_falha_claro(tmp_path):
    """Estado atual do projeto: calibracao_quotex.json não existe ainda."""
    resultado = validar_calibracao_quotex(caminho=str(tmp_path / "ausente.json"))
    assert resultado.sucesso is False
    assert "inexistente" in resultado.mensagem
    assert resultado.coordenadas is None


def test_calibracao_completa_aceita(tmp_path):
    caminho = tmp_path / "calibracao_quotex.json"
    caminho.write_text(json.dumps(_calibracao_valida()), encoding="utf-8")
    resultado = validar_calibracao_quotex(caminho=str(caminho))
    assert resultado.sucesso is True
    assert resultado.coordenadas["compra"] == [1500, 700]


def test_calibracao_incompleta_falha(tmp_path):
    caminho = tmp_path / "calibracao.json"
    dados = _calibracao_valida()
    del dados["venda"]  # só um botão calibrado
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    resultado = validar_calibracao_quotex(caminho=str(caminho))
    assert resultado.sucesso is False
    assert "venda" in resultado.mensagem


def test_calibracao_valores_invalidos_falha(tmp_path):
    caminho = tmp_path / "calibracao.json"
    dados = _calibracao_valida()
    dados["compra"] = [-10, 700]  # coordenada negativa
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    assert validar_calibracao_quotex(caminho=str(caminho)).sucesso is False

    dados["compra"] = "centro"  # tipo errado
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    assert validar_calibracao_quotex(caminho=str(caminho)).sucesso is False


def test_calibracao_tela_diferente_exige_recalibrar(tmp_path):
    """Mudou a resolução desde a calibração → recusar cliques."""
    caminho = tmp_path / "calibracao.json"
    caminho.write_text(json.dumps(_calibracao_valida(tela=(1920, 1080))))
    resultado = validar_calibracao_quotex(
        caminho=str(caminho), tela_atual=(2560, 1440)
    )
    assert resultado.sucesso is False
    assert "tela mudou" in resultado.mensagem


def test_calibracao_tela_igual_aceita(tmp_path):
    caminho = tmp_path / "calibracao.json"
    caminho.write_text(json.dumps(_calibracao_valida(tela=(2560, 1440))))
    resultado = validar_calibracao_quotex(
        caminho=str(caminho), tela_atual=(2560, 1440)
    )
    assert resultado.sucesso is True


def test_calibracao_ilegivel_falha(tmp_path):
    caminho = tmp_path / "calibracao.json"
    caminho.write_text("{ isso não é json", encoding="utf-8")
    resultado = validar_calibracao_quotex(caminho=str(caminho))
    assert resultado.sucesso is False
    assert "ilegível" in resultado.mensagem


def test_chaves_obrigatorias_definem_cadeia_completa():
    """compra + venda + tela: sem isso não há clique seguro."""
    assert CHAVES_OBRIGATORIAS == ("compra", "venda", "tela")


def test_caminho_padrao_aponta_para_app_support():
    """O caminho padrão deve casar com o usado pela interface (pc/interface.py)."""
    assert "BFT Winbot" in CAMINHO_PADRAO_CALIBRACAO_QUOTEX
    assert CAMINHO_PADRAO_CALIBRACAO_QUOTEX.endswith("calibracao_quotex.json")