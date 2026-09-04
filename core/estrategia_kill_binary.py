"""Perfil Kill Binary reconstruído do zero e calculado em velas fechadas."""

from dataclasses import dataclass

from estrategia_otc_classica import Sinal
from indicadores import wma


@dataclass(frozen=True)
class ResultadoKillBinary:
    sinal: Sinal
    pontuacao: int
    motivo: str


def analisar_kill_binary(velas, periodo=3):
    """Compara WMA de fechamentos e aberturas sem usar a vela em formação.

    O perfil confirma que o cruzamento ocorreu na vela anterior e que a
    direção permaneceu válida na vela fechada mais recente. Nada é desenhado
    retrospectivamente.
    """
    velas = list(velas)
    if periodo < 1:
        raise ValueError("periodo precisa ser maior que zero")

    minimo = periodo + 2
    if len(velas) < minimo:
        return ResultadoKillBinary(
            Sinal.AGUARDAR,
            0,
            f"histórico insuficiente: {len(velas)}/{minimo} velas fechadas",
        )

    medias_fechamento = wma([vela.fechamento for vela in velas], periodo)
    medias_abertura = wma([vela.abertura for vela in velas], periodo)

    diferencas = [
        fechamento - abertura
        for fechamento, abertura in zip(
            medias_fechamento[-3:], medias_abertura[-3:]
        )
    ]
    anterior_2, anterior_1, atual = diferencas

    if anterior_2 < 0 and anterior_1 > 0 and atual > 0:
        return ResultadoKillBinary(
            Sinal.ALTA,
            8,
            "cruzamento de alta confirmado e mantido na vela fechada seguinte",
        )

    if anterior_2 > 0 and anterior_1 < 0 and atual < 0:
        return ResultadoKillBinary(
            Sinal.BAIXA,
            8,
            "cruzamento de baixa confirmado e mantido na vela fechada seguinte",
        )

    return ResultadoKillBinary(
        Sinal.AGUARDAR,
        4,
        "médias de abertura e fechamento sem cruzamento confirmado",
    )

