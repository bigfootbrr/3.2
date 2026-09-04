"""Travas para estudar uma única recuperação, exclusivamente em simulação."""

from dataclasses import dataclass


PROBABILIDADE_MINIMA = 0.89
PAYOUT_MINIMO = 0.80
MAXIMO_RECUPERACOES = 1
LIMITE_BANCA_POR_TENTATIVA = 0.02


@dataclass(frozen=True)
class DecisaoRecuperacao:
    autorizada: bool
    motivo: str
    modo: str = "SIMULAÇÃO"


def avaliar_recuperacao(
    ativada,
    houve_perda,
    probabilidade_calibrada,
    payout,
    regime_mantido,
    recuperacoes_realizadas,
    banca,
    valor_proposto,
):
    """Avalia travas sem calcular ou enviar uma ordem."""
    if not ativada:
        return DecisaoRecuperacao(False, "recuperação desativada")
    if not houve_perda:
        return DecisaoRecuperacao(False, "não existe perda simulada a recuperar")
    if recuperacoes_realizadas >= MAXIMO_RECUPERACOES:
        return DecisaoRecuperacao(False, "limite de uma recuperação atingido")
    if probabilidade_calibrada is None:
        return DecisaoRecuperacao(False, "probabilidade ainda não calibrada")
    if not 0 <= probabilidade_calibrada <= 1:
        raise ValueError("probabilidade precisa estar entre 0 e 1")
    if probabilidade_calibrada < PROBABILIDADE_MINIMA:
        return DecisaoRecuperacao(
            False,
            f"probabilidade {probabilidade_calibrada:.1%} abaixo de 89%",
        )
    if payout is None:
        return DecisaoRecuperacao(False, "payout não confirmado")
    if not 0 <= payout <= 1:
        raise ValueError("payout precisa estar entre 0 e 1")
    if payout < PAYOUT_MINIMO:
        return DecisaoRecuperacao(False, f"payout {payout:.1%} abaixo de 80%")
    if not regime_mantido:
        return DecisaoRecuperacao(False, "regime de mercado mudou após a perda")
    if banca <= 0 or valor_proposto <= 0:
        raise ValueError("banca e valor proposto precisam ser positivos")
    limite = banca * LIMITE_BANCA_POR_TENTATIVA
    if valor_proposto > limite:
        return DecisaoRecuperacao(
            False,
            f"valor proposto supera o limite de 2% da banca ({limite:.2f})",
        )
    return DecisaoRecuperacao(
        True,
        "recuperação simulada autorizada por todas as travas",
    )

