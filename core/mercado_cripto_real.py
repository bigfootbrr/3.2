"""Velas reais de criptomoedas via Binance (fonte pública, sem chave).

Nova fase BFT WIN 3.3: dados reais para análise quando o mercado das
corretoras está fechado. Cripto opera 24/7, então é o par de teste ideal
para validar confluências, regime e sinais em tempo real.

Mesmo contrato de `mercado_aberto_real.py`:
- vela em formação é DESCARTADA (no-repaint);
- vela repetida não reanalisa (no-repeat);
- fonte é injetável para testes sem internet;
- nada é inventado: sem fonte real, levanta erro.
"""

from datetime import datetime, timezone

from dados_mercado import Vela


URL_KLINES = "https://api.binance.com/api/v3/klines"

PARES_BINANCE = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "SOL": "SOLUSDT",
    "DOGE": "DOGEUSDT",
    "LTC": "LTCUSDT",
}

INTERVALOS = {
    # Binance aceita "1m"/"5m"/"15m" — o mesmo significado de M1/M5/M15.
    "M1": ("1m", 300),
    "M5": ("5m", 300),
    "M15": ("15m", 300),
}

MS_POR_MINUTO = 60_000


class ErroMercadoCripto(RuntimeError):
    pass


def _converter_klines_em_velas(klines, ativo, timeframe):
    """Converte o formato de kline da Binance em velas internas.

    Descarta a última vela (em formação) para garantir no-repaint.
    """
    velas = []
    for numero, k in enumerate(klines[:-1] if len(klines) > 1 else klines, start=1):
        try:
            abertura = float(k[1])
            maxima = float(k[2])
            minima = float(k[3])
            fechamento = float(k[4])
            volume = float(k[5])
            inicio_ms = int(k[0])
        except (TypeError, ValueError, IndexError):
            continue
        fim = datetime.fromtimestamp(inicio_ms / 1000.0, tz=timezone.utc)
        inicio = fim
        velas.append(Vela(
            ativo=ativo,
            timeframe=timeframe,
            numero=numero,
            abertura=abertura,
            maxima=maxima,
            minima=minima,
            fechamento=fechamento,
            inicio=inicio,
            fim=fim,
            volume=volume,
        ))
    return tuple(velas)


class MercadoCriptoReal:
    """Busca velas reais de cripto na Binance e mantém o snapshot válido."""

    def __init__(self, ativo, timeframe="M1", downloader=None, limite=300):
        ativo = ativo.upper()
        if ativo not in PARES_BINANCE:
            raise ValueError(f"par cripto não mapeado: {ativo}")
        timeframe = timeframe.upper()
        if timeframe not in INTERVALOS:
            raise ValueError("timeframe precisa ser M1, M5 ou M15")
        self.ativo = ativo
        self.timeframe = timeframe
        self.limite = limite
        self._downloader = downloader
        self._historico = ()

    def _baixar(self, simbolo, intervalo, quantidade):
        if self._downloader is not None:
            return self._downloader(simbolo=simbolo, intervalo=intervalo, quantidade=quantidade)
        try:
            import requests
        except ImportError as erro:
            raise ErroMercadoCripto("requests não está instalado") from erro
        url = (
            f"{URL_KLINES}?symbol={simbolo}&interval={intervalo}"
            f"&limit={quantidade}"
        )
        resposta = requests.get(url, timeout=10)
        if resposta.status_code != 200:
            raise ErroMercadoCripto(
                f"binance retornou status {resposta.status_code}"
            )
        return resposta.json()

    def atualizar(self):
        # DADOS REAIS E AO VIVO — SEM REPAINT E SEM VELA REPETIDA.
        # A vela em formação (última do kline) é descartada antes da análise.
        intervalo, quantidade = INTERVALOS[self.timeframe]
        simbolo = PARES_BINANCE[self.ativo]
        try:
            klines = self._baixar(simbolo, intervalo, quantidade)
        except ErroMercadoCripto:
            if self._historico:
                return self._historico
            raise
        except Exception as erro:
            if self._historico:
                return self._historico
            raise ErroMercadoCripto(f"falha na Binance: {erro}") from erro
        velas = _converter_klines_em_velas(klines, self.ativo, self.timeframe)
        if len(velas) < 3:
            if self._historico:
                return self._historico
            raise ErroMercadoCripto("fonte real retornou poucas velas")
        # NO-REPEAT: vela mais nova igual à que já está no histórico —
        # não reanalisa.
        if self._historico and velas and velas[-1].fim <= self._historico[-1].fim:
            return self._historico
        self._historico = velas[-self.limite:]
        return self._historico

    def obter_historico(self):
        return tuple(self._historico)

    def resumo(self):
        if not self._historico:
            raise ErroMercadoCripto("ativo ainda não foi atualizado")
        ultima = self._historico[-1]
        anterior = self._historico[-2] if len(self._historico) > 1 else None
        variacao = (
            (ultima.fechamento / anterior.fechamento - 1.0) * 100.0
            if anterior and anterior.fechamento else 0.0
        )
        return {
            "ativo": self.ativo,
            "preco": ultima.fechamento,
            "variacao": variacao,
            "horario": ultima.fim,
            "velas": len(self._historico),
        }