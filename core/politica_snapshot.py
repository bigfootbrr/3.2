"""Regras de segurança para entregar capturas visuais ao motor BFT."""

from dataclasses import dataclass

from modo_operacao import AUTOMATICO_DEMO, AUTOMATICO_REAL, SOMENTE_SINAIS


@dataclass(frozen=True)
class ValidacaoSnapshot:
    permitido: bool
    motivo: str


def validar_snapshot_visual(modo, corretora="IQ OPTION"):
    """Autoriza o snapshot; a conta e o clique são validados separadamente."""
    corretora = corretora.strip().upper()
    if corretora != "IQ OPTION":
        return ValidacaoSnapshot(
            False,
            f"conector visual de {corretora or 'corretora desconhecida'} ainda não instalado",
        )
    if modo in {SOMENTE_SINAIS, AUTOMATICO_DEMO}:
        return ValidacaoSnapshot(True, "snapshot liberado para análise")
    if modo == AUTOMATICO_REAL:
        return ValidacaoSnapshot(
            True,
            "snapshot liberado; plataforma confirmada e trava armada serão exigidas no clique",
        )
    return ValidacaoSnapshot(False, "modo de operação desconhecido")
