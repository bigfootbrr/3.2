"""Classificação observacional do regime usando apenas velas fechadas."""

from dataclasses import dataclass
from enum import Enum
from statistics import median

from configuracoes import obter_configuracao
from indicadores import atr, ema


class Regime(str, Enum):
    DADOS_INSUFICIENTES = "DADOS_INSUFICIENTES"
    TENDENCIA_ALTA = "TENDENCIA_ALTA"
    TENDENCIA_BAIXA = "TENDENCIA_BAIXA"
    LATERAL = "LATERAL"
    VOLATILIDADE_ANORMAL = "VOLATILIDADE_ANORMAL"
    INDEFINIDO = "INDEFINIDO"


@dataclass(frozen=True)
class DiagnosticoRegime:
    regime: Regime
    motivo: str
    separacao_medias_atr: float | None = None
    inclinacao_lenta_atr: float | None = None
    atr_relativo: float | None = None


def classificar_regime(velas, timeframe):
    config = obter_configuracao(timeframe)
    velas = list(velas)
    minimo = max(config.ema_estrutural, config.atr_periodo + 20)
    if len(velas) < minimo:
        return DiagnosticoRegime(
            Regime.DADOS_INSUFICIENTES,
            f"necessárias {minimo} velas fechadas; recebidas {len(velas)}",
        )

    fechamentos = [vela.fechamento for vela in velas]
    rapida = ema(fechamentos, config.ema_rapida)
    lenta = ema(fechamentos, config.ema_lenta)
    estrutural = ema(fechamentos, config.ema_estrutural)
    valores_atr = atr(velas, config.atr_periodo)

    atr_atual = valores_atr[-1]
    atr_recentes = [valor for valor in valores_atr[-50:] if valor is not None]
    atr_mediano = median(atr_recentes)
    atr_relativo = atr_atual / atr_mediano if atr_mediano else 1.0

    if atr_relativo >= 2.5:
        return DiagnosticoRegime(
            Regime.VOLATILIDADE_ANORMAL,
            "ATR atual muito acima da mediana recente",
            atr_relativo=atr_relativo,
        )

    separacao = abs(rapida[-1] - lenta[-1]) / atr_atual if atr_atual else 0.0
    atraso = 5
    inclinacao = (lenta[-1] - lenta[-1 - atraso]) / (atraso * atr_atual) if atr_atual else 0.0
    fechamento = fechamentos[-1]

    if separacao <= 0.35 and abs(inclinacao) <= 0.08:
        regime = Regime.LATERAL
        motivo = "médias próximas e EMA lenta com baixa inclinação"
    elif rapida[-1] > lenta[-1] and fechamento > estrutural[-1] and inclinacao > 0.03:
        regime = Regime.TENDENCIA_ALTA
        motivo = "médias alinhadas, preço acima da EMA estrutural e inclinação positiva"
    elif rapida[-1] < lenta[-1] and fechamento < estrutural[-1] and inclinacao < -0.03:
        regime = Regime.TENDENCIA_BAIXA
        motivo = "médias alinhadas, preço abaixo da EMA estrutural e inclinação negativa"
    else:
        regime = Regime.INDEFINIDO
        motivo = "condições de direção e lateralização não estão alinhadas"

    return DiagnosticoRegime(
        regime,
        motivo,
        separacao_medias_atr=separacao,
        inclinacao_lenta_atr=inclinacao,
        atr_relativo=atr_relativo,
    )

