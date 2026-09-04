"""Reconhece o timeframe selecionado do gráfico OTC da corretora."""

from dataclasses import dataclass
import os
import re

from PIL import Image

from calibracao_iq import PERFIL_IQ_2026_08_30
from calibracao_iq_contexto import selecionar_perfil_iq_por_captura
from leitor_texto_macos import ler_textos


TIMEFRAMES_CONHECIDOS = ("M1", "M5", "M15", "M30", "H1", "H4")


@dataclass(frozen=True)
class ResultadoTimeframe:
    sucesso: bool
    timeframe: str | None
    mensagem: str


def ler_timeframe(
    caminho_captura,
    caminho_recorte="/private/tmp/bft_iq_timeframe.png",
    leitor=ler_textos,
    timeframes=TIMEFRAMES_CONHECIDOS,
):
    if not os.path.isfile(caminho_captura):
        return ResultadoTimeframe(False, None, "captura da IQ não encontrada")
    try:
        with Image.open(caminho_captura) as imagem:
            perfil, _contexto = selecionar_perfil_iq_por_captura(caminho_captura)
            if perfil is None:
                perfil = PERFIL_IQ_2026_08_30
            caixa = perfil.timeframe.converter(*imagem.size)
            imagem.crop(caixa).save(caminho_recorte)
    except (OSError, ValueError) as erro:
        return ResultadoTimeframe(
            False, None, f"não foi possível recortar o timeframe: {erro}"
        )

    leitura = leitor(caminho_recorte)
    if not leitura.sucesso:
        return ResultadoTimeframe(False, None, leitura.mensagem)

    unido = " ".join(leitura.textos).upper()
    encontrados = [
        timeframe
        for timeframe in timeframes
        if re.search(rf"(?<![A-Z0-9]){timeframe}(?![A-Z0-9])", unido)
    ]
    unicos = tuple(dict.fromkeys(encontrados))
    if len(unicos) != 1:
        return ResultadoTimeframe(False, None, "timeframe não reconhecido com segurança")
    return ResultadoTimeframe(True, unicos[0], f"timeframe observado: {unicos[0]}")
