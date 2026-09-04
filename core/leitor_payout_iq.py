"""Lê somente a região Profit para não confundir payout com HIGHER/LOWER."""

from dataclasses import dataclass
import os

from PIL import Image

from calibracao_iq import PERFIL_IQ_2026_08_30
from calibracao_iq_contexto import selecionar_perfil_iq_por_captura
from leitor_texto_macos import extrair_payouts, ler_textos


@dataclass(frozen=True)
class ResultadoPayout:
    sucesso: bool
    payout: float | None
    mensagem: str


def ler_payout(
    caminho_captura,
    caminho_recorte="/private/tmp/bft_iq_profit.png",
    leitor=ler_textos,
):
    if not os.path.isfile(caminho_captura):
        return ResultadoPayout(False, None, "captura da IQ não encontrada")
    try:
        with Image.open(caminho_captura) as imagem:
            perfil, _contexto = selecionar_perfil_iq_por_captura(caminho_captura)
            if perfil is None:
                perfil = PERFIL_IQ_2026_08_30
            caixa = perfil.payout.converter(*imagem.size)
            imagem.crop(caixa).save(caminho_recorte)
    except (OSError, ValueError) as erro:
        return ResultadoPayout(False, None, f"não foi possível recortar Profit: {erro}")

    leitura = leitor(caminho_recorte)
    if not leitura.sucesso:
        return ResultadoPayout(False, None, leitura.mensagem)
    percentuais = tuple(dict.fromkeys(extrair_payouts(leitura.textos)))
    if not percentuais:
        return ResultadoPayout(False, None, "Profit está carregando ou não foi reconhecido")
    if len(percentuais) != 1:
        return ResultadoPayout(False, None, "leitura ambígua na região Profit")
    payout = percentuais[0]
    return ResultadoPayout(True, payout, f"payout observado: {payout:.0%}")
