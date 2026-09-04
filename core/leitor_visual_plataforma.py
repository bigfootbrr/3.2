"""Leitores visuais genéricos para qualquer plataforma com perfil calibrado.

Reutiliza o OCR (`leitor_texto_macos`) e as mesmas validações dos leitores
`_iq` (falha fechado, sem ambiguidade), mas recebem o perfil da plataforma
via `calibracao_plataformas.obter_perfil()`.

APIs mantidas em paridade com os leitores `_iq`:
- ler_ativo_plataforma(...)  ~ leitor_ativo_iq.ler_ativo
- ler_payout_plataforma(...) ~ leitor_payout_iq.ler_payout
- ler_timeframe_plataforma() ~ leitor_timeframe_iq.ler_timeframe
"""

from dataclasses import dataclass
import os
import re

from PIL import Image

from calibracao_plataformas import obter_perfil
from leitor_texto_macos import extrair_payouts, ler_textos
from leitor_timeframe_iq import TIMEFRAMES_CONHECIDOS
from leitor_ativo_iq import _extrair_ativo_otc, _normalizar
from painel_abas_iq import ATIVOS_IQ_CONHECIDOS


@dataclass(frozen=True)
class ResultadoVisual:
    sucesso: bool
    valor: str | float | None
    mensagem: str


def _recortar_regiao(caminho_captura, perfil, campo, caminho_recorte, nome_regiao):
    """Abre a captura, valida geometria e recorta a região do perfil."""
    if not os.path.isfile(caminho_captura):
        return ResultadoVisual(False, None, f"captura da {perfil.plataforma} não encontrada")
    try:
        with Image.open(caminho_captura) as imagem:
            largura, altura = imagem.size
            if not perfil.geometria_ok(largura, altura):
                return ResultadoVisual(
                    False, None,
                    "geometria da janela mudou; recalibrar o perfil antes de ler",
                )
            caixa = perfil.recorte(getattr(perfil, campo), largura, altura)
            imagem.crop(caixa).save(caminho_recorte)
    except (OSError, ValueError) as erro:
        return ResultadoVisual(False, None, f"não foi possível recortar {nome_regiao}: {erro}")
    return None


def ler_ativo_plataforma(
    caminho_captura,
    plataforma,
    caminho_recorte="/private/tmp/bft_plataforma_ativo.png",
    leitor=None,
    ativos=ATIVOS_IQ_CONHECIDOS,
):
    """Reconhece o ativo selecionado na região do perfil da plataforma."""
    if leitor is None:
        leitor = ler_textos
    perfil = obter_perfil(plataforma)
    erro = _recortar_regiao(caminho_captura, perfil, "ativo_selecionado",
                            caminho_recorte, "o ativo")
    if erro:
        return erro

    leitura = leitor(caminho_recorte)
    if not leitura.sucesso:
        return ResultadoVisual(False, None, leitura.mensagem)

    reconhecido = _normalizar(" ".join(leitura.textos))
    encontrados = []
    for ativo in ativos:
        completo = _normalizar(ativo)
        base = completo.replace("OTC", "")
        if completo in reconhecido or (base and base in reconhecido):
            encontrados.append(ativo)
    if len(encontrados) == 1:
        return ResultadoVisual(True, encontrados[0], f"ativo observado: {encontrados[0]}")
    generico = _extrair_ativo_otc(leitura.textos)
    if generico is None:
        return ResultadoVisual(False, None, "ativo não reconhecido com segurança")
    return ResultadoVisual(True, generico, f"novo ativo observado: {generico}")


def ler_payout_plataforma(
    caminho_captura,
    plataforma,
    caminho_recorte="/private/tmp/bft_plataforma_payout.png",
    leitor=None,
):
    """Lê somente a região de payout do perfil; falha fechado em ambiguidade."""
    if leitor is None:
        leitor = ler_textos
    perfil = obter_perfil(plataforma)
    erro = _recortar_regiao(caminho_captura, perfil, "payout",
                            caminho_recorte, "payout")
    if erro:
        return erro

    leitura = leitor(caminho_recorte)
    if not leitura.sucesso:
        return ResultadoVisual(False, None, leitura.mensagem)

    percentuais = tuple(dict.fromkeys(extrair_payouts(leitura.textos)))
    if not percentuais:
        return ResultadoVisual(False, None, "payout está carregando ou não foi reconhecido")
    if len(percentuais) != 1:
        return ResultadoVisual(False, None, "leitura ambígua na região de payout")
    payout = percentuais[0]
    return ResultadoVisual(True, payout, f"payout observado: {payout:.0%}")


def ler_timeframe_plataforma(
    caminho_captura,
    plataforma,
    caminho_recorte="/private/tmp/bft_plataforma_timeframe.png",
    leitor=None,
    timeframes=TIMEFRAMES_CONHECIDOS,
):
    """Reconhece o timeframe na região do perfil; exige leitura única."""
    if leitor is None:
        leitor = ler_textos
    perfil = obter_perfil(plataforma)
    erro = _recortar_regiao(caminho_captura, perfil, "timeframe",
                            caminho_recorte, "o timeframe")
    if erro:
        return erro

    leitura = leitor(caminho_recorte)
    if not leitura.sucesso:
        return ResultadoVisual(False, None, leitura.mensagem)

    unido = " ".join(leitura.textos).upper()
    encontrados = [
        timeframe
        for timeframe in timeframes
        if re.search(rf"(?<![A-Z0-9]){timeframe}(?![A-Z0-9])", unido)
    ]
    unicos = tuple(dict.fromkeys(encontrados))
    if len(unicos) != 1:
        return ResultadoVisual(False, None, "timeframe não reconhecido com segurança")
    return ResultadoVisual(True, unicos[0], f"timeframe observado: {unicos[0]}")


def ler_botoes_plataforma(caminho_captura, plataforma):
    """Detecta os botões por COR dentro das regiões do perfil (compra/venda).

    Delega ao detector genérico por cor, mas restringindo a busca à área
    declarada pelos botões do perfil — muito mais preciso que varrer a
    metade direita inteira da tela.
    """
    from detector_botoes_cor import detectar_botoes_cor

    perfil = obter_perfil(plataforma)
    if not os.path.isfile(caminho_captura):
        return None, None
    try:
        with Image.open(caminho_captura) as imagem:
            largura, altura = imagem.size
        if not perfil.geometria_ok(largura, altura):
            return None, None

        def _limites(regiao):
            if regiao is None:
                return (0.85, 0.99), (0.10, 0.98)  # fallback: região clássica
            return (regiao.x1, regiao.x2), (regiao.y1, regiao.y2)

        faixa_x_c, faixa_y_c = _limites(perfil.botao_compra)
        compra, _ = detectar_botoes_cor(caminho_captura, faixa_x_c, faixa_y_c)
        faixa_x_v, faixa_y_v = _limites(perfil.botao_venda)
        _, venda = detectar_botoes_cor(caminho_captura, faixa_x_v, faixa_y_v)
        return compra, venda
    except (OSError, ValueError):
        return None, None