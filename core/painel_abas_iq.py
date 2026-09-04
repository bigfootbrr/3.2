"""Modelo da central dinâmica de ativos observados na IQ."""

from dataclasses import dataclass, replace


ATIVOS_MERCADO_ABERTO = (
    "AUD/CAD",
    "AUD/CHF",
    "AUD/JPY",
    "AUD/NZD",
    "AUD/USD",
    "CAD/CHF",
    "CAD/JPY",
    "CHF/JPY",
    "EUR/AUD",
    "EUR/CAD",
    "EUR/CHF",
    "EUR/GBP",
    "EUR/JPY",
    "EUR/NZD",
    "EUR/USD",
    "GBP/AUD",
    "GBP/CAD",
    "GBP/CHF",
    "GBP/JPY",
    "GBP/NZD",
    "GBP/USD",
    "NZD/CAD",
    "NZD/CHF",
    "NZD/JPY",
    "NZD/USD",
    "USD/CAD",
    "USD/CHF",
    "USD/DKK",
    "USD/HKD",
    "USD/JPY",
    "USD/KRW",
    "USD/NOK",
    "USD/SEK",
    "USD/SGD",
)


# Dez pares Forex OTC em ordem alfabética. A ordem não promete rentabilidade:
# o payout observado na tela continua sendo a trava que decide se o ativo pode
# ou não ser considerado naquele momento.
ATIVOS_OTC_PRIORITARIOS = (
    "AUD/NZD (OTC)",
    "CAD/JPY (OTC)",
    "EUR/AUD (OTC)",
    "EUR/CAD (OTC)",
    "EUR/CHF (OTC)",
    "EUR/GBP (OTC)",
    "EUR/JPY (OTC)",
    "EUR/NZD (OTC)",
    "EUR/THB (OTC)",
    "USD/ARS (OTC)",
)


ATIVOS_IQ_CONHECIDOS = ATIVOS_MERCADO_ABERTO + ATIVOS_OTC_PRIORITARIOS + (
    "SHIB/USD (OTC)",
    "TRUMP COIN (OTC)",
    "VAULTA (OTC)",
    "CARDANO (OTC)",
    "TRON/USD (OTC)",
    "PEN/USD (OTC)",
    "PEPE (OTC)",
    "ARBITRUM (OTC)",
    "NATURAL GAS (OTC)",
    "JUPITER (OTC)",
    "DYDX (OTC)",
    "PALANTIR TECHNOLOGIES (OTC)",
    "WORLDCOIN (OTC)",
    "KLARNA GROUP PLC (OTC)",
    "FORMULA ONE GROUP (OTC)",
    "SPACEX (OTC)",
    "DOGWIFHAT (OTC)",
    "FARTCOIN (OTC)",
    "SUGAR (OTC)",
    "GRAPH (OTC)",
    "IMMUTABLE (OTC)",
    "INJECTIVE (OTC)",
    "FET (OTC)",
    "INTEL/IBM (OTC)",
)

# A interface começa somente com os 10 prioritários. O leitor visual continua
# conhecendo a lista ampliada por ATIVOS_IQ_CONHECIDOS.
ATIVOS_INICIAIS_IQ = ATIVOS_OTC_PRIORITARIOS


# Organização dos OTC conhecidos por tipo de mercado (menu estilo IQ Option).
# Chave = rótulo da categoria; valor = tupla de ativos dessa categoria.
def _classificar_otc_por_tipo(ativos):
    forex, cripto, commodities, acoes = [], [], [], []
    for ativo in ativos:
        nome = ativo.replace(" (OTC)", "").upper()
        # Criptomoedas e tokens por nome conhecido.
        if nome in _CRIPTO_OTC_NOMES or "/" in nome and nome.split("/")[0] in _CRIPTO_OTC_NOMES:
            cripto.append(ativo)
        # Commodities por nome.
        elif nome in _COMMODITIES_OTC_NOMES:
            commodities.append(ativo)
        # Ações/empresas (nomes longos, sem "/") e os pares Intel/IBM.
        elif "/" not in nome or nome in ("INTEL/IBM",):
            acoes.append(ativo)
        else:
            forex.append(ativo)
    return forex, cripto, commodities, acoes


_CRIPTO_OTC_NOMES = {
    "SHIB/USD", "TRUMP COIN", "VAULTA", "CARDANO", "TRON/USD", "PEN/USD",
    "PEPE", "ARBITRUM", "JUPITER", "DYDX", "WORLDCOIN", "DOGWIFHAT",
    "FARTCOIN", "GRAPH", "IMMUTABLE", "INJECTIVE", "FET",
}
_COMMODITIES_OTC_NOMES = {"NATURAL GAS", "SUGAR"}


def categorias_otc(ativos=None):
    """Retorna listas nomeadas de OTC agrupados por tipo de mercado."""
    ativos = tuple(ativos) if ativos is not None else ATIVOS_IQ_CONHECIDOS
    forex, cripto, commodities, acoes = _classificar_otc_por_tipo(ativos)
    return {
        "Forex OTC": tuple(forex),
        "Cripto OTC": tuple(cripto),
        "Commodities OTC": tuple(commodities),
        "Ações OTC": tuple(acoes),
    }


def categorias_mercado_aberto(ativos=None):
    """Agrupa os pares de mercado aberto pela base (EUR, GBP, USD, AUD...)."""
    ativos = tuple(ativos) if ativos is not None else ATIVOS_MERCADO_ABERTO
    grupos = {}
    for ativo in ativos:
        base = ativo.split("/")[0]
        grupos.setdefault(f"{base} *", []).append(ativo)
    return {chave: tuple(v) for chave, v in grupos.items()}


@dataclass(frozen=True)
class LinhaAbaIq:
    numero: int
    ativo: str
    payout: float | None = None
    estado: str = "NÃO LIDA"
    sinal: str = "AGUARDAR"


class PainelAbasIq:
    def __init__(self, ativos=ATIVOS_OTC_PRIORITARIOS):
        if not ativos:
            raise ValueError("a central precisa de pelo menos um ativo")
        if len(set(ativos)) != len(ativos):
            raise ValueError("a central não aceita ativos duplicados")
        self._linhas = {
            numero: LinhaAbaIq(numero, ativo)
            for numero, ativo in enumerate(ativos, start=1)
        }

    def atualizar(self, numero, *, ativo=None, payout=None, estado=None, sinal=None):
        if numero not in self._linhas:
            raise ValueError("aba não cadastrada")
        linha = self._linhas[numero]
        if payout is not None and not 0 <= payout <= 1:
            raise ValueError("payout deve estar entre 0 e 1")
        if sinal is not None and sinal not in {"COMPRA", "VENDA", "AGUARDAR"}:
            raise ValueError("sinal inválido")
        self._linhas[numero] = replace(
            linha,
            ativo=linha.ativo if ativo is None else ativo,
            payout=linha.payout if payout is None else payout,
            estado=linha.estado if estado is None else estado,
            sinal=linha.sinal if sinal is None else sinal,
        )

    def adicionar(self, ativo):
        ativo = ativo.strip()
        if not ativo:
            raise ValueError("ativo não pode ser vazio")
        existente = next(
            (linha for linha in self._linhas.values() if linha.ativo == ativo), None
        )
        if existente is not None:
            return existente
        numero = max(self._linhas, default=0) + 1
        linha = LinhaAbaIq(numero, ativo)
        self._linhas[numero] = linha
        return linha

    def linhas(self):
        return tuple(self._linhas[numero] for numero in sorted(self._linhas))

    @staticmethod
    def payout_texto(linha):
        return "—" if linha.payout is None else f"{linha.payout:.0%}"
