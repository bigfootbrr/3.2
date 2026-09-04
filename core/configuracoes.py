"""Configurações iniciais versionadas para M1, M5 e M15."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracaoTimeframe:
    timeframe: str
    ema_rapida: int
    ema_lenta: int
    ema_estrutural: int
    rsi_periodo: int
    atr_periodo: int
    bollinger_periodo: int
    bollinger_desvio: float
    estrutura_periodo: int
    espera_velas: int
    pontuacao_minima: int


CONFIGURACOES = {
    "M1": ConfiguracaoTimeframe(
        timeframe="M1",
        ema_rapida=9,
        ema_lenta=21,
        ema_estrutural=100,
        rsi_periodo=9,
        atr_periodo=14,
        bollinger_periodo=20,
        bollinger_desvio=2.2,
        estrutura_periodo=20,
        espera_velas=3,
        pontuacao_minima=8,
    ),
    "M5": ConfiguracaoTimeframe(
        timeframe="M5",
        ema_rapida=9,
        ema_lenta=21,
        ema_estrutural=200,
        rsi_periodo=14,
        atr_periodo=14,
        bollinger_periodo=20,
        bollinger_desvio=2.0,
        estrutura_periodo=20,
        espera_velas=2,
        pontuacao_minima=8,
    ),
    "M15": ConfiguracaoTimeframe(
        timeframe="M15",
        ema_rapida=9,
        ema_lenta=34,
        ema_estrutural=200,
        rsi_periodo=14,
        atr_periodo=14,
        bollinger_periodo=20,
        bollinger_desvio=2.0,
        estrutura_periodo=20,
        espera_velas=1,
        pontuacao_minima=8,
    ),
}


def obter_configuracao(timeframe):
    timeframe = timeframe.upper()
    try:
        return CONFIGURACOES[timeframe]
    except KeyError as erro:
        raise ValueError("timeframe precisa ser M1, M5 ou M15") from erro
