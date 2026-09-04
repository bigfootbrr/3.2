"""Velas reais de mercado aberto obtidas por uma fonte pública independente.

OTC nunca passa por este módulo: seus preços continuam vindo da tela da
corretora. O provedor é injetável para que toda a conversão seja testável sem
internet.
"""

from datetime import datetime

from dados_mercado import Vela


SIMBOLOS_YAHOO = {
    "AUD/CAD": "AUDCAD=X",
    "AUD/CHF": "AUDCHF=X",
    "AUD/JPY": "AUDJPY=X",
    "AUD/NZD": "AUDNZD=X",
    "AUD/USD": "AUDUSD=X",
    "CAD/CHF": "CADCHF=X",
    "CAD/JPY": "CADJPY=X",
    "CHF/JPY": "CHFJPY=X",
    "EUR/AUD": "EURAUD=X",
    "EUR/CAD": "EURCAD=X",
    "EUR/CHF": "EURCHF=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "EUR/NZD": "EURNZD=X",
    "EUR/USD": "EURUSD=X",
    "GBP/AUD": "GBPAUD=X",
    "GBP/CAD": "GBPCAD=X",
    "GBP/CHF": "GBPCHF=X",
    "GBP/JPY": "GBPJPY=X",
    "GBP/NZD": "GBPNZD=X",
    "GBP/USD": "GBPUSD=X",
    "NZD/CAD": "NZDCAD=X",
    "NZD/CHF": "NZDCHF=X",
    "NZD/JPY": "NZDJPY=X",
    "NZD/USD": "NZDUSD=X",
    "USD/CAD": "CAD=X",
    "USD/CHF": "CHF=X",
    "USD/DKK": "USDDKK=X",
    "USD/HKD": "USDHKD=X",
    "USD/JPY": "JPY=X",
    "USD/KRW": "USDKRW=X",
    "USD/NOK": "USDNOK=X",
    "USD/SEK": "USDSEK=X",
    "USD/SGD": "USDSGD=X",
}

INTERVALOS = {
    # Cinco dias evitam que a virada do dia deixe RSI/MACD sem histórico.
    # O limite interno continua preservando apenas as 300 velas mais recentes.
    "M1": ("1m", "5d"),
    "M5": ("5m", "5d"),
    "M15": ("15m", "5d"),
}


class ErroMercadoAberto(RuntimeError):
    pass


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def converter_dataframe_em_velas(quadro, ativo, timeframe):
    """Converte OHLC em velas internas e descarta linhas incompletas."""
    velas = []
    for numero, (indice, linha) in enumerate(quadro.iterrows(), start=1):
        abertura = _numero(linha.get("Open"))
        maxima = _numero(linha.get("High"))
        minima = _numero(linha.get("Low"))
        fechamento = _numero(linha.get("Close"))
        volume = _numero(linha.get("Volume"))
        if None in (abertura, maxima, minima, fechamento):
            continue
        if hasattr(indice, "to_pydatetime"):
            fim = indice.to_pydatetime()
        elif isinstance(indice, datetime):
            fim = indice
        else:
            continue
        if fim.tzinfo is not None:
            fim = fim.astimezone()
        velas.append(Vela(
            ativo=ativo,
            timeframe=timeframe,
            numero=numero,
            abertura=abertura,
            maxima=maxima,
            minima=minima,
            fechamento=fechamento,
            inicio=fim,
            fim=fim,
            volume=volume,
        ))
    return tuple(velas)


class MercadoAbertoReal:
    """Busca histórico real sob demanda e mantém o último snapshot válido."""

    def __init__(self, ativo, timeframe="M1", downloader=None, limite=300):
        timeframe = timeframe.upper()
        if ativo not in SIMBOLOS_YAHOO:
            raise ValueError(f"ativo de mercado aberto não mapeado: {ativo}")
        if timeframe not in INTERVALOS:
            raise ValueError("timeframe precisa ser M1, M5 ou M15")
        self.ativo = ativo
        self.timeframe = timeframe
        self.limite = limite
        self._downloader = downloader
        self._historico = ()

    def _baixar(self):
        if self._downloader is not None:
            return self._downloader
        try:
            import yfinance as yf
        except ImportError as erro:
            raise ErroMercadoAberto("yfinance não está instalado") from erro
        return yf.download

    def atualizar(self):
        intervalo, periodo = INTERVALOS[self.timeframe]
        try:
            quadro = self._baixar()(
                SIMBOLOS_YAHOO[self.ativo],
                period=periodo,
                interval=intervalo,
                progress=False,
                auto_adjust=False,
                threads=False,
            )
        except Exception as erro:
            raise ErroMercadoAberto(f"fonte real indisponível: {erro}") from erro
        # yfinance pode devolver colunas MultiIndex mesmo para um único ativo.
        if getattr(quadro.columns, "nlevels", 1) > 1:
            quadro.columns = quadro.columns.get_level_values(0)
        velas = converter_dataframe_em_velas(quadro, self.ativo, self.timeframe)
        if len(velas) < 3:
            raise ErroMercadoAberto("fonte real retornou poucas velas")
        self._historico = velas[-self.limite :]
        return self._historico

    def obter_historico(self):
        return tuple(self._historico)

    def resumo(self):
        if not self._historico:
            raise ErroMercadoAberto("ativo ainda não foi atualizado")
        ultima = self._historico[-1]
        anterior = self._historico[-2]
        variacao = (
            (ultima.fechamento / anterior.fechamento - 1.0) * 100.0
            if anterior.fechamento else 0.0
        )
        return {
            "ativo": self.ativo,
            "preco": ultima.fechamento,
            "variacao": variacao,
            "horario": ultima.fim,
            "velas": len(self._historico),
        }
