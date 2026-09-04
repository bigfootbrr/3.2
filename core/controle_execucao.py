"""Trava de execução simulada baseada em probabilidade calibrada."""

from dataclasses import dataclass


LIMIAR_PROBABILIDADE = 0.75
PAYOUT_MINIMO = 0.80


@dataclass(frozen=True)
class DecisaoExecucao:
    autorizada: bool
    modo: str
    motivo: str


def avaliar_execucao_simulada(sinal, probabilidade_calibrada, payout):
    """Autoriza apenas simulação e somente acima de 75%.

    None significa que ainda não existe modelo calibrado. Pontuação de
    confluência não pode ser passada como se fosse probabilidade.
    """
    if sinal not in {"ALTA", "BAIXA", "AGUARDAR"}:
        raise ValueError("sinal precisa ser ALTA, BAIXA ou AGUARDAR")

    if sinal == "AGUARDAR":
        return DecisaoExecucao(False, "SIMULAÇÃO", "sem direção válida")

    if payout is None:
        return DecisaoExecucao(
            False, "SIMULAÇÃO", "payout não informado; execução bloqueada"
        )
    if not 0.0 <= payout <= 1.0:
        raise ValueError("payout precisa estar entre 0 e 1")
    if payout <= PAYOUT_MINIMO:
        return DecisaoExecucao(
            False, "SIMULAÇÃO", f"payout {payout:.1%} abaixo do mínimo de 80%"
        )

    if probabilidade_calibrada is None:
        return DecisaoExecucao(
            False, "SIMULAÇÃO",
            "probabilidade ainda não calibrada; execução bloqueada",
        )

    if not 0.0 <= probabilidade_calibrada <= 1.0:
        raise ValueError("probabilidade precisa estar entre 0 e 1")

    if probabilidade_calibrada <= LIMIAR_PROBABILIDADE:
        return DecisaoExecucao(
            False, "SIMULAÇÃO",
            f"probabilidade {probabilidade_calibrada:.1%} não supera 75%",
        )

    return DecisaoExecucao(
        True, "SIMULAÇÃO",
        f"entrada simulada autorizada com probabilidade "
        f"{probabilidade_calibrada:.1%} e payout {payout:.1%}",
    )
