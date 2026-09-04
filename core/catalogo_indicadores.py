"""Catálogo dos módulos de análise exibidos na interface BFT."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndicadorCatalogo:
    codigo: str
    nome: str
    categoria: str
    implementado: bool
    descricao: str


INDICADORES = (
    IndicadorCatalogo("EMA_TENDENCIA", "BFT EMA — tendência", "Tendência", True, "Alinhamento EMA 9/21/100"),
    IndicadorCatalogo("RSI", "BFT RSI — força", "Momentum", True, "Força compradora ou vendedora"),
    IndicadorCatalogo("MACD", "BFT MACD — tendência e impulso", "Momentum", True, "Cruzamento MACD 12/26 com sinal 9"),
    IndicadorCatalogo("ATR", "BFT ATR — volatilidade", "Volatilidade", True, "Filtro de volatilidade anormal"),
    IndicadorCatalogo("BOLLINGER", "BFT Bollinger — extremos", "Volatilidade", True, "Extremos e retorno à média"),
    IndicadorCatalogo("ESTOCASTICO", "BFT Estocástico — reversão", "Momentum", True, "Cruzamentos em regiões extremas"),
    IndicadorCatalogo("PRICE_ACTION", "BFT Price Action — impulso", "Preço", True, "Direção e corpo da última vela fechada"),
    IndicadorCatalogo("PADROES_CANDLE", "BFT Candles — padrões", "Preço", True, "Engolfo, martelo, estrela e marubozu"),
    IndicadorCatalogo("BOMBRIL", "BFT Bombril — retorno OTC", "OTC", True, "Retorno às bandas curtas do preço"),
    IndicadorCatalogo("BIGFOOT", "BFT BigFoot — gatilho", "BFT", True, "Gatilho reconstruído SMA 1/34 + WMA 5"),
    IndicadorCatalogo("BFT_PANO", "BFT PANO 26", "BFT", True, "Confluência opcional EMA 2/8 + WMA 6"),
    IndicadorCatalogo("BFT_GAP", "BFT GAP 26", "BFT", True, "Gap de abertura fechado com escala de 5 casas"),
    IndicadorCatalogo("BFT_OB", "BFT OB 26", "BFT", True, "Cruzamento EMA 3 com SMA 6 em velas fechadas"),
    IndicadorCatalogo("BFT_SUP_REST", "BFT SUP/REST", "BFT referência", False, "Referência recebida; fórmula ainda não validada"),
    IndicadorCatalogo("BFT_WIN26", "BFT WIN 26", "BFT", True, "SMA 1/34 com sinal WMA 4 em velas fechadas"),
    IndicadorCatalogo("BFT_WIN26K", "BFT WIN 26K", "BFT referência", False, "Exige filtro M15 da fórmula original; ainda não reproduzido"),
    IndicadorCatalogo("BFT_WIN07_M5", "BFT WIN 07 M5", "BFT referência M5", False, "Setup M5 recebido; executável fechado"),
    IndicadorCatalogo("KILL_ARROWS", "BFT WIN Kill Arrows", "BFT referência M5", False, "Parâmetros recebidos; fórmula fechada"),
    IndicadorCatalogo("DON_FOREX_OTC", "BFT Don Forex OTC", "Referência", False, "Executável fechado recebido"),
    IndicadorCatalogo("FILTER_RATIO_OTC", "BFT Filter Ratio OTC", "Referência", False, "Executável fechado recebido"),
    IndicadorCatalogo("SNIPER_OTC", "BFT Sniper OTC", "Referência", False, "Executável fechado recebido"),
    IndicadorCatalogo("BOB05_OTC", "BFT Bob05 OTC", "Referência", False, "Executável fechado recebido"),
    IndicadorCatalogo("ULTRA_TREND_OTC", "BFT Ultra Trend OTC", "Referência", False, "Executável fechado recebido"),
)

POR_CODIGO = {indicador.codigo: indicador for indicador in INDICADORES}

PADRAO_MANUAL = {"EMA_TENDENCIA", "RSI", "PADROES_CANDLE"}

PERFIS_AUTOMATICOS = {
    "TENDENCIA": {"BIGFOOT", "BFT_WIN26", "BFT_OB"},
    "LATERAL": {"BFT_PANO", "BFT_GAP", "BFT_OB"},
    "INDEFINIDO": {"BIGFOOT", "BFT_PANO", "BFT_WIN26"},
}

ESTRATEGIAS_PRONTAS = {
    "BFT Raiz M1": ("BIGFOOT", "RSI", "BOLLINGER"),
    "Tendência M1": ("EMA_TENDENCIA", "RSI", "BIGFOOT"),
    "BFT Tendência Macro": ("EMA_TENDENCIA", "MACD", "BIGFOOT"),
    "Reversão M1": ("BOLLINGER", "ESTOCASTICO", "PADROES_CANDLE"),
    "Price Action M1": ("PRICE_ACTION", "PADROES_CANDLE", "BFT_PANO"),
    "Impulso M1": ("EMA_TENDENCIA", "PRICE_ACTION", "RSI"),
    "BFT PANO OTC — reversão": ("BFT_PANO", "BOMBRIL", "ESTOCASTICO"),
    "BFT PANO OTC — continuidade": ("BFT_PANO", "PRICE_ACTION", "RSI"),
    "BFT WIN 26 M1": ("BFT_WIN26", "BFT_OB", "PADROES_CANDLE"),
    "BFT Vini 3 — confluência": ("BIGFOOT", "BFT_OB", "RSI"),
    "BFT Velas M1 — estilo MHI": ("PADROES_CANDLE", "EMA_TENDENCIA", "RSI"),
}


def codigos_implementados():
    return {item.codigo for item in INDICADORES if item.implementado}


def validar_selecao(codigos):
    desconhecidos = set(codigos) - set(POR_CODIGO)
    if desconhecidos:
        raise ValueError(f"indicadores desconhecidos: {', '.join(sorted(desconhecidos))}")
    selecionados = set(codigos) & codigos_implementados()
    if len(selecionados) > 3:
        raise ValueError("selecione no máximo 3 indicadores por estratégia")
    return selecionados


def selecionar_para_regime(regime):
    nome = getattr(regime, "value", str(regime)).upper()
    if "TENDENCIA" in nome:
        return set(PERFIS_AUTOMATICOS["TENDENCIA"])
    if "LATERAL" in nome:
        return set(PERFIS_AUTOMATICOS["LATERAL"])
    return set(PERFIS_AUTOMATICOS["INDEFINIDO"])
