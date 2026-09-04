"""Política explícita dos modos disponíveis no laboratório BFT."""

from dataclasses import dataclass


SOMENTE_SINAIS = "SOMENTE SINAIS"
AUTOMATICO_DEMO = "AUTOMÁTICO DEMO"
AUTOMATICO_REAL = "AUTOMÁTICO REAL"
MODOS = {SOMENTE_SINAIS, AUTOMATICO_DEMO, AUTOMATICO_REAL}


@dataclass(frozen=True)
class PermissaoModo:
    permitido: bool
    motivo: str


def validar_modo(modo):
    if modo not in MODOS:
        raise ValueError("modo de operação desconhecido")
    if modo == SOMENTE_SINAIS:
        return PermissaoModo(True, "apenas exibição e registro de sinais")
    if modo == AUTOMATICO_DEMO:
        return PermissaoModo(True, "execução permitida somente no simulador")
    return PermissaoModo(
        True,
        "modo real disponível com plataforma confirmada e trava armada",
    )
