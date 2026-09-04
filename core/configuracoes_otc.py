"""Hipóteses iniciais para backtest OTC, separadas do mercado aberto."""

from configuracoes import ConfiguracaoTimeframe


CONFIGURACOES_OTC = {
    "M1": ConfiguracaoTimeframe("M1", 9, 21, 100, 14, 14, 20, 2.5, 25, 5, 9),
    "M5": ConfiguracaoTimeframe("M5", 9, 34, 100, 14, 14, 20, 2.5, 20, 3, 9),
    "M15": ConfiguracaoTimeframe("M15", 9, 34, 100, 14, 14, 20, 2.5, 20, 2, 9),
}


def obter_configuracao_otc(timeframe):
    timeframe = timeframe.upper()
    try:
        return CONFIGURACOES_OTC[timeframe]
    except KeyError as erro:
        raise ValueError("timeframe OTC precisa ser M1, M5 ou M15") from erro

