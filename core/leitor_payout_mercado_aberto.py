"""Lê o payout que a IQ Option está pagando AGORA (Mercado Aberto).

Captura a janela da IQ Option, roda OCR e procura percentuais válidos.
Se não conseguir ler um payout único e válido, retorna None — e o gate
de disparo (`avaliar_criterios_clique_automatico`) descarta o sinal,
pois exige payout > 80% para AMBOS os mercados.
"""

import os
import subprocess

from leitor_payout_iq import ResultadoPayout
from leitor_texto_macos import extrair_payouts, ler_textos

from captura_tela_macos import testar_captura

CAMINHO_CAPTURA_MA = "/private/tmp/bft_iq_payout_ma.png"


def ler_payout_mercado_aberto(
    caminho_captura=CAMINHO_CAPTURA_MA,
    leitor=ler_textos,
):
    """Lê o payout atual da tela da IQ Option (janela inteira).

    Retorna ResultadoPayout; payout=None quando a leitura falha ou é
    ambígua — nesse caso o sinal é descartado pelo gate de disparo.
    """
    captura = testar_captura(caminho=caminho_captura)
    if not captura.sucesso:
        return ResultadoPayout(False, None, f"captura falhou: {captura.mensagem}")

    leitura = leitor(caminho_captura)
    if not leitura.sucesso:
        return ResultadoPayout(False, None, f"OCR falhou: {leitura.mensagem}")

    # Percentuais únicos presentes na tela inteira (dedupe mantendo ordem).
    percentuais = tuple(dict.fromkeys(extrair_payouts(leitura.textos)))
    if not percentuais:
        return ResultadoPayout(
            False, None, "nenhum payout reconhecido na tela da IQ"
        )
    if len(percentuais) > 1:
        # Tela tem vários % (ex.: lista de ativos): usa o maior payout visível,
        # pois é o melhor payout disponível para o operador agora.
        payout = max(percentuais)
        return ResultadoPayout(
            True, payout, f"payout observado (maior da tela): {payout:.0%}"
        )
    payout = percentuais[0]
    return ResultadoPayout(True, payout, f"payout observado: {payout:.0%}")