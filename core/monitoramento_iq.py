"""Temporização do monitor visual; não executa operações financeiras."""


def segundos_ate_proxima_leitura(agora, margem_segundos=0.0, periodo=30.0):
    """Agenda capturas visuais nos marcos de 30 segundos."""
    if periodo <= 0:
        raise ValueError("período deve ser positivo")
    restante = periodo - (agora % periodo)
    return restante + margem_segundos
