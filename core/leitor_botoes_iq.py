"""Reconhece visualmente os botões de direção sem interagir com eles."""

from dataclasses import dataclass
import os

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ResultadoBotoes:
    sucesso: bool
    higher_visivel: bool
    lower_visivel: bool
    mensagem: str

    @property
    def prontos(self):
        return self.higher_visivel and self.lower_visivel


def ler_botoes(caminho_captura):
    """Detecta os dois grandes blocos coloridos na lateral direita da IQ."""
    if not os.path.isfile(caminho_captura):
        return ResultadoBotoes(False, False, False, "captura da IQ não encontrada")
    try:
        rgb = np.asarray(Image.open(caminho_captura).convert("RGB"))
    except (OSError, ValueError) as erro:
        return ResultadoBotoes(False, False, False, f"imagem indisponível: {erro}")

    altura, largura = rgb.shape[:2]
    regiao = rgb[int(altura * 0.25):int(altura * 0.68), int(largura * 0.89):]
    canais = regiao.astype(np.int16)
    vermelho, verde, azul = (canais[:, :, indice] for indice in range(3))
    pixels_higher = (
        (verde > 105)
        & ((verde - vermelho) > 22)
        & ((verde - azul) > 12)
    )
    pixels_lower = (
        (vermelho > 150)
        & ((vermelho - verde) > 35)
        & ((vermelho - azul) > 30)
    )
    area_minima = max(500, int(regiao.shape[0] * regiao.shape[1] * 0.025))
    higher = int(pixels_higher.sum()) >= area_minima
    lower = int(pixels_lower.sum()) >= area_minima
    if higher and lower:
        return ResultadoBotoes(True, True, True, "HIGHER e LOWER visíveis — confirmação manual")
    ausentes = []
    if not higher:
        ausentes.append("HIGHER")
    if not lower:
        ausentes.append("LOWER")
    return ResultadoBotoes(
        False,
        higher,
        lower,
        f"botões não confirmados: {', '.join(ausentes)}",
    )
