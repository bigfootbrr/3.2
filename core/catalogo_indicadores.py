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
    IndicadorCatalogo("EMA_TENDENCIA", "BFTWIN TENDENCIA", "Tendência", True, "Alinhamento EMA 9/21/100"),
    IndicadorCatalogo("RSI", "BFTWIN FORCA", "Momentum", True, "Força compradora ou vendedora (RSI 14)"),
    IndicadorCatalogo("MACD", "BFTWIN IMPULSO", "Momentum", True, "Cruzamento MACD 12/26 com sinal 9"),
    IndicadorCatalogo("ATR", "BFTWIN VOLATIL", "Volatilidade", True, "Filtro de volatilidade anormal (ATR)"),
    IndicadorCatalogo("BOLLINGER", "BFTWIN EXTREMOS", "Volatilidade", True, "Extremos das bandas e retorno à média"),
    IndicadorCatalogo("ESTOCASTICO", "BFTWIN REVERSAO", "Momentum", True, "Estocástico saturado em regiões extremas"),
    IndicadorCatalogo("PRICE_ACTION", "BFTWIN PRECO", "Preço", True, "Direção e corpo da última vela fechada"),
    IndicadorCatalogo("PADROES_CANDLE", "BFTWIN VELAS", "Preço", True, "Engolfo, martelo, estrela e marubozu"),
    IndicadorCatalogo("BOMBRIL", "BFTWIN BOMBRIL", "OTC", True, "Retorno às bandas curtas do preço (OTC)"),
    IndicadorCatalogo("BIGFOOT", "BFTWIN BIGFOOT", "BFT", True, "Gatilho raiz SMA 1/34 + WMA 5"),
    IndicadorCatalogo("BFT_PANO", "BFTWIN PANO 26", "BFT", True, "Confluência opcional EMA 2/8 + WMA 6"),
    IndicadorCatalogo("BFT_GAP", "BFTWIN GAP 26", "BFT", True, "Gap de abertura fechado com escala de 5 casas"),
    IndicadorCatalogo("BFT_OB", "BFTWIN OB 26", "BFT", True, "Cruzamento EMA 3 com SMA 6 em velas fechadas"),
    IndicadorCatalogo("BFT_SUP_REST", "BFTWIN SUP REST", "BFT referência", False, "Referência recebida; fórmula ainda não validada"),
    IndicadorCatalogo("BFT_WIN26", "BFTWIN 26", "BFT", True, "SMA 1/34 com sinal WMA 4 em velas fechadas"),
    IndicadorCatalogo("BFT_WIN26K", "BFTWIN 26K", "BFT referência", False, "Exige filtro M15 da fórmula original; ainda não reproduzido"),
    IndicadorCatalogo("BFT_WIN07_M5", "BFTWIN 07 M5", "BFT referência M5", False, "Setup M5 recebido; executável fechado"),
    IndicadorCatalogo("KILL_ARROWS", "BFTWIN KILL ARROWS", "BFT referência M5", False, "Parâmetros recebidos; fórmula fechada"),
    IndicadorCatalogo("DON_FOREX_OTC", "BFTWIN DON OTC", "Referência", False, "Executável fechado recebido"),
    IndicadorCatalogo("FILTER_RATIO_OTC", "BFTWIN FILTER OTC", "Referência", False, "Executável fechado recebido"),
    IndicadorCatalogo("SNIPER_OTC", "BFTWIN SNIPER OTC", "Referência", False, "Executável fechado recebido"),
    IndicadorCatalogo("BOB05_OTC", "BFTWIN BOB05 OTC", "Referência", False, "Executável fechado recebido"),
    IndicadorCatalogo("ULTRA_TREND_OTC", "BFTWIN ULTRA OTC", "Referência", False, "Executável fechado recebido"),
)

POR_CODIGO = {indicador.codigo: indicador for indicador in INDICADORES}

PADRAO_MANUAL = {"BIGFOOT", "BFT_WIN26"}

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


# ---------------------------------------------------------------------------
# Aba Estratégias — catálogo curado por mercado, com a lógica de cada uma.
# Mercado Aberto = Forex real (Yahoo); OTC = leitura visual da corretora.
# Cada entrada: (nome, indicadores, lógica em traderês, melhor momento).
# ---------------------------------------------------------------------------

ESTRATEGIAS_MERCADO_ABERTO = (
    {
        "nome": "Tendência Puxada (Pullback)",
        "indicadores": ("EMA_TENDENCIA", "RSI", "BIGFOOT"),
        "logica": "EMA 9>21>100 alinhada; entra no pullback quando o RSI recua "
                  "para 40-55 e o BigFoot dispara o cruzamento a favor.",
        "melhor_momento": "M5/M15 em tendência clara — evita lateral",
    },
    {
        "nome": "Confluência Macro",
        "indicadores": ("EMA_TENDENCIA", "MACD", "BIGFOOT"),
        "logica": "Só opera a favor da EMA 100; o MACD confirma o impulso e o "
                  "BigFoot marca o gatilho na vela fechada.",
        "melhor_momento": "M15 — filtragem forte, menos sinais e mais limpos",
    },
    {
        "nome": "Impulso Puro",
        "indicadores": ("EMA_TENDENCIA", "PRICE_ACTION", "RSI"),
        "logica": "Corpo forte (≥35%) na direção da tendência com RSI "
                  "acompanhando — continuidade do movimento.",
        "melhor_momento": "M1/M5 na abertura de sessão (Londres/NY)",
    },
    {
        "nome": "Romper Extremos com Vela",
        "indicadores": ("BOLLINGER", "PADROES_CANDLE", "RSI"),
        "logica": "Preço toca a banda com RSI extremo e um padrão de reversão "
                  "(engolfo/martelo) fecha confirmando o retorno.",
        "melhor_momento": "M5 em mercado sem notícia — lateral definida",
    },
    {
        "nome": "BFT Raiz (BigFoot + força)",
        "indicadores": ("BIGFOOT", "RSI", "BOLLINGER"),
        "logica": "A original: gatilho BigFoot fechado, RSI a favor e preço "
                  "fora do meio das bandas. A base de 2020.",
        "melhor_momento": "M1 — os 3 confluindo na mesma vela",
    },
)

ESTRATEGIAS_OTC = (
    {
        "nome": "BFT PANO OTC — Reversão",
        "indicadores": ("BFT_PANO", "BOMBRIL", "ESTOCASTICO"),
        "logica": "PANO gira, Bombril marca o retorno à banda curta e o "
                  "Estocástico satura no extremo oposto — reversão limpa.",
        "melhor_momento": "M1 OTC após 3+ velas na mesma direção",
    },
    {
        "nome": "BFT PANO OTC — Continuidade",
        "indicadores": ("BFT_PANO", "PRICE_ACTION", "RSI"),
        "logica": "PANO mantém a direção, corpo forte fecha a favor e o RSI "
                  "ainda tem espaço até o extremo — segue o movimento.",
        "melhor_momento": "M1/M5 OTC em fluxo constante (payday alto)",
    },
    {
        "nome": "MHI OTC (3 velas)",
        "indicadores": ("PADROES_CANDLE", "EMA_TENDENCIA", "RSI"),
        "logica": "Após 3 velas da mesma cor, a 4ª entra contra com padrão de "
                  "reversão confirmado e EMA 100 como filtro estrutural.",
        "melhor_momento": "M1 OTC — o clássico das salas de sinal",
    },
    {
        "nome": "BFT WIN 26 OTC",
        "indicadores": ("BFT_WIN26", "BFT_OB", "PADROES_CANDLE"),
        "logica": "Cruzamento WIN 26 fechado + OB confirmando + padrão de "
                  "vela na direção — tríade BFT completa.",
        "melhor_momento": "M1/M5 OTC em qualquer sessão",
    },
    {
        "nome": "Torres Gêmeas (Gale 1)",
        "indicadores": ("BFT_OB", "ESTOCASTICO", "PRICE_ACTION"),
        "logica": "Duas velas de força seguidas satura o Estocástico; a OB "
                  "gira e entra contra na 2ª vela com Gale 1 na gestão.",
        "melhor_momento": "M1 OTC — pares de payout alto (≥85%)",
    },
)

ESTRATEGIAS_POR_MERCADO = {
    "MERCADO ABERTO": ESTRATEGIAS_MERCADO_ABERTO,
    "OTC": ESTRATEGIAS_OTC,
}


def codigos_implementados():
    return {item.codigo for item in INDICADORES if item.implementado}


def validar_selecao(codigos):
    desconhecidos = set(codigos) - set(POR_CODIGO)
    if desconhecidos:
        raise ValueError(f"indicadores desconhecidos: {', '.join(sorted(desconhecidos))}")
    selecionados = set(codigos) & codigos_implementados()
    if len(selecionados) < 2:
        raise ValueError("selecione pelo menos 2 indicadores para confluirem entre si")
    if len(selecionados) > 8:
        raise ValueError("selecione no máximo 8 indicadores por estratégia")
    return selecionados


def selecionar_para_regime(regime):
    nome = getattr(regime, "value", str(regime)).upper()
    if "TENDENCIA" in nome:
        return set(PERFIS_AUTOMATICOS["TENDENCIA"])
    if "LATERAL" in nome:
        return set(PERFIS_AUTOMATICOS["LATERAL"])
    return set(PERFIS_AUTOMATICOS["INDEFINIDO"])
