"""Reconstrução sem repaint da confluência OTC mostrada no vídeo."""

from dataclasses import dataclass
from enum import Enum

from indicadores import ema, sma, wma


class Sinal(str, Enum):
    ALTA = "ALTA"
    BAIXA = "BAIXA"
    AGUARDAR = "AGUARDAR"


@dataclass(frozen=True)
class ResultadoOtc:
    sinal: Sinal
    pontuacao: int
    motivo: str
    gatilho_bigfoot: str | None = None
    confirmacao_panos: str | None = None


def analisar_otc_classico(velas, janela_confirmacao=3):
    """Analisa apenas velas recebidas como fechadas.

    O gatilho BigFoot.Trader usa SMA 1/34 com WMA 5. A confirmação PANOS
    usa EMA 2/8 e WMA 6 sobre o diferencial. O sinal é emitido na vela
    da confirmação, sem deslocamento retrospectivo.
    """
    velas = list(velas)
    if janela_confirmacao < 1:
        raise ValueError("janela_confirmacao precisa ser maior que zero")
    if len(velas) < 105:
        return ResultadoOtc(
            Sinal.AGUARDAR, 0,
            f"histórico insuficiente: {len(velas)}/105 velas fechadas",
        )

    fechamentos = [vela.fechamento for vela in velas]

    # BigFoot.Trader 2: diferencial SMA 1/34 contra WMA 5.
    rapida_bigfoot = sma(fechamentos, 1)
    lenta_bigfoot = sma(fechamentos, 34)
    diferencial_bigfoot = _subtrair_series(rapida_bigfoot, lenta_bigfoot)
    sinal_bigfoot = _media_sobre_validos(diferencial_bigfoot, wma, 5)
    eventos_bigfoot = _cruzamentos(diferencial_bigfoot, sinal_bigfoot)

    # BFT PANOS: reconstrução testável do diferencial 2/8 com sinal 6.
    rapida_panos = ema(fechamentos, 2)
    lenta_panos = ema(fechamentos, 8)
    diferencial_panos = _subtrair_series(rapida_panos, lenta_panos)
    sinal_panos = _media_sobre_validos(diferencial_panos, wma, 6)
    histograma = _subtrair_series(diferencial_panos, sinal_panos)
    eventos_panos = _cruzamentos_zero(histograma)

    confirmacao = eventos_panos[-1]
    if confirmacao is None:
        return ResultadoOtc(Sinal.AGUARDAR, 4, "BFT PANOS ainda não confirmou")

    inicio = max(0, len(velas) - janela_confirmacao)
    gatilhos_recentes = eventos_bigfoot[inicio:]
    gatilho_esperado = confirmacao
    if gatilho_esperado not in gatilhos_recentes:
        return ResultadoOtc(
            Sinal.AGUARDAR, 5,
            "seta PANOS sem gatilho BigFoot recente na mesma direção",
            confirmacao_panos=confirmacao,
        )

    ema_100 = ema(fechamentos, 100)[-1]
    direcao_estrutural = (
        "ALTA" if fechamentos[-1] > ema_100
        else "BAIXA" if fechamentos[-1] < ema_100
        else None
    )
    if direcao_estrutural != confirmacao:
        return ResultadoOtc(
            Sinal.ALTA if confirmacao == "ALTA" else Sinal.BAIXA,
            7,
            "gatilho e PANOS concordam; EMA 100 ainda não confirmou",
            gatilho_bigfoot=gatilho_esperado,
            confirmacao_panos=confirmacao,
        )

    sinal = Sinal.ALTA if confirmacao == "ALTA" else Sinal.BAIXA
    return ResultadoOtc(
        sinal, 9,
        "BigFoot.Trader + BFT PANOS + EMA 100 confirmados em velas fechadas",
        gatilho_bigfoot=gatilho_esperado,
        confirmacao_panos=confirmacao,
    )


def _subtrair_series(a, b):
    return [
        None if esquerda is None or direita is None else esquerda - direita
        for esquerda, direita in zip(a, b)
    ]


def _media_sobre_validos(serie, funcao, periodo):
    resultado = [None] * len(serie)
    inicio = next((i for i, valor in enumerate(serie) if valor is not None), None)
    if inicio is None:
        return resultado
    calculada = funcao(serie[inicio:], periodo)
    resultado[inicio:] = calculada
    return resultado


def _cruzamentos(serie, sinal):
    eventos = [None] * len(serie)
    for indice in range(1, len(serie)):
        valores = serie[indice], sinal[indice], serie[indice - 1], sinal[indice - 1]
        if any(valor is None for valor in valores):
            continue
        if serie[indice] > sinal[indice] and serie[indice - 1] <= sinal[indice - 1]:
            eventos[indice] = "ALTA"
        elif serie[indice] < sinal[indice] and serie[indice - 1] >= sinal[indice - 1]:
            eventos[indice] = "BAIXA"
    return eventos


def _cruzamentos_zero(histograma):
    eventos = [None] * len(histograma)
    for indice in range(1, len(histograma)):
        atual, anterior = histograma[indice], histograma[indice - 1]
        if atual is None or anterior is None:
            continue
        if atual > 0 and anterior <= 0:
            eventos[indice] = "ALTA"
        elif atual < 0 and anterior >= 0:
            eventos[indice] = "BAIXA"
    return eventos
