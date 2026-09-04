"""Conexão com dados de mercado reais em tempo real.

Suporta múltiplas bolsas e ativos via APIs públicas.
"""

import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass


@dataclass
class CotacaoReal:
    ativo: str
    preco: float
    variacao: float
    variacao_percentual: float
    horario: datetime
    fonte: str  # "Yahoo", "Binance", "CoinGecko", etc


class ConectorMercadoReal:
    """Conecta a dados de mercado reais via APIs públicas."""

    # Ativos disponíveis em tempo real
    ATIVOS_DISPONIVEIS = {
        # Índices brasileiros
        "IBOV": {"fonte": "yahoofinance", "symbol": "^BVSP", "descricao": "Ibovespa"},
        "IBRX": {"fonte": "yahoofinance", "symbol": "^IBRX", "descricao": "IBrX 100"},
        
        # Pares de moeda (via API pública)
        "EURUSD": {"fonte": "yahoofinance", "symbol": "EURUSD=X", "descricao": "EUR/USD"},
        "GBPUSD": {"fonte": "yahoofinance", "symbol": "GBPUSD=X", "descricao": "GBP/USD"},
        "USDJPY": {"fonte": "yahoofinance", "symbol": "USDJPY=X", "descricao": "USD/JPY"},
        
        # Ações populares
        "PETR4": {"fonte": "yahoofinance", "symbol": "PETR4.SA", "descricao": "Petrobras"},
        "VALE3": {"fonte": "yahoofinance", "symbol": "VALE3.SA", "descricao": "Vale"},
        "ITUB4": {"fonte": "yahoofinance", "symbol": "ITUB4.SA", "descricao": "Itaú"},
        
        # Criptomoedas (Binance - sem autenticação)
        "BTC": {"fonte": "binance", "symbol": "BTCUSDT", "descricao": "Bitcoin"},
        "ETH": {"fonte": "binance", "symbol": "ETHUSDT", "descricao": "Ethereum"},
        "BNB": {"fonte": "binance", "symbol": "BNBUSDT", "descricao": "Binance Coin"},
        "XRP": {"fonte": "binance", "symbol": "XRPUSDT", "descricao": "Ripple"},
        "ADA": {"fonte": "binance", "symbol": "ADAUSDT", "descricao": "Cardano"},
    }

    def __init__(self, timeout=5, intervalo_minimo_consulta=15):
        self.timeout = timeout
        self.intervalo_minimo_consulta = intervalo_minimo_consulta
        self.historico_cotacoes = {}
        self.ultima_cotacao = {}
        self.ultima_consulta = {}

    def obter_ativos_disponiveis(self) -> Dict[str, Dict]:
        """Retorna lista de ativos disponíveis com suas informações."""
        return self.ATIVOS_DISPONIVEIS.copy()

    def obter_cotacao_yahoo(self, symbol: str) -> Optional[CotacaoReal]:
        """Obtém cotação de um ativo via Yahoo Finance (API indireta)."""
        try:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                "?interval=1m&range=1d"
            )
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0 (BFT-Winbot/3.1)"},
            )
            
            if response.status_code != 200:
                return None
            
            dados = response.json().get("chart", {}).get("result", [])
            if not dados:
                return None

            resultado = dados[0]
            meta = resultado.get("meta", {})
            preco = meta.get("regularMarketPrice")
            variacao = meta.get("regularMarketChange", 0)
            variacao_pct = meta.get("regularMarketChangePercent", 0)
            timestamps = resultado.get("timestamp", [])
            timestamp = meta.get("regularMarketTime") or (timestamps[-1] if timestamps else 0)
            
            if preco is None or preco == 0:
                return None
            
            ativo_nome = symbol.replace("=X", "").split(".")[0]
            
            return CotacaoReal(
                ativo=ativo_nome,
                preco=float(preco),
                variacao=float(variacao),
                variacao_percentual=float(variacao_pct),
                horario=datetime.fromtimestamp(timestamp) if timestamp else datetime.now(),
                fonte="Yahoo Finance",
            )
        except Exception as e:
            print(f"Erro ao obter cotação Yahoo para {symbol}: {e}")
            return None

    def obter_cotacao_binance(self, symbol: str) -> Optional[CotacaoReal]:
        """Obtém cotação de um par da Binance em tempo real."""
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code != 200:
                return None
            
            dados = response.json()
            
            preco_atual = float(dados.get("lastPrice", 0))
            variacao_24h = float(dados.get("priceChange", 0))
            variacao_pct = float(dados.get("priceChangePercent", 0))
            
            if preco_atual == 0:
                return None
            
            ativo_nome = symbol.replace("USDT", "")
            
            return CotacaoReal(
                ativo=ativo_nome,
                preco=preco_atual,
                variacao=variacao_24h,
                variacao_percentual=variacao_pct,
                horario=datetime.now(),
                fonte="Binance",
            )
        except Exception as e:
            print(f"Erro ao obter cotação Binance para {symbol}: {e}")
            return None

    def obter_cotacao(self, ativo: str) -> Optional[CotacaoReal]:
        """Obtém cotação em tempo real para um ativo."""
        if ativo not in self.ATIVOS_DISPONIVEIS:
            return None

        agora = time.monotonic()
        cotacao_cache = self.ultima_cotacao.get(ativo)
        if (
            cotacao_cache is not None
            and agora - self.ultima_consulta.get(ativo, 0)
            < self.intervalo_minimo_consulta
        ):
            return cotacao_cache
        
        info = self.ATIVOS_DISPONIVEIS[ativo]
        fonte = info.get("fonte")
        symbol = info.get("symbol")
        
        if fonte == "yahoofinance":
            cotacao = self.obter_cotacao_yahoo(symbol)
        elif fonte == "binance":
            cotacao = self.obter_cotacao_binance(symbol)
        else:
            return None
        
        if cotacao:
            self.ultima_consulta[ativo] = agora
            self.ultima_cotacao[ativo] = cotacao
            if ativo not in self.historico_cotacoes:
                self.historico_cotacoes[ativo] = []
            self.historico_cotacoes[ativo].append(cotacao)
            # Manter apenas últimas 100 cotações por ativo
            if len(self.historico_cotacoes[ativo]) > 100:
                self.historico_cotacoes[ativo] = self.historico_cotacoes[ativo][-100:]
        
        return cotacao

    def obter_multiplos_ativos(self, ativos: List[str]) -> Dict[str, Optional[CotacaoReal]]:
        """Obtém cotações de múltiplos ativos em paralelo."""
        resultado = {}
        for ativo in ativos:
            resultado[ativo] = self.obter_cotacao(ativo)
        return resultado

    def formatar_cotacao(self, cotacao: CotacaoReal) -> str:
        """Formata cotação para exibição."""
        sinal = "📈" if cotacao.variacao > 0 else "📉" if cotacao.variacao < 0 else "➡️"
        return (
            f"{sinal} {cotacao.ativo} | R$ {cotacao.preco:,.2f} | "
            f"{cotacao.variacao:+.2f} ({cotacao.variacao_percentual:+.2f}%) | "
            f"{cotacao.horario.strftime('%H:%M:%S')}"
        )


def criar_conector_padrao() -> ConectorMercadoReal:
    """Factory para criar conector padrão."""
    return ConectorMercadoReal()


def listar_ativos_em_tempo_real():
    """Exibe lista de ativos disponíveis em tempo real."""
    conector = criar_conector_padrao()
    ativos = conector.obter_ativos_disponiveis()
    
    print("\n" + "="*80)
    print("📊 ATIVOS DISPONÍVEIS EM TEMPO REAL")
    print("="*80)
    
    por_categoria = {}
    for codigo, info in ativos.items():
        categoria = info.get("fonte", "Outro")
        if categoria not in por_categoria:
            por_categoria[categoria] = []
        por_categoria[categoria].append((codigo, info.get("descricao")))
    
    for categoria, lista in por_categoria.items():
        print(f"\n🏢 {categoria.upper()}")
        print("-" * 80)
        for codigo, descricao in sorted(lista):
            print(f"  {codigo:15} → {descricao}")
    
    print("\n" + "="*80)


def testar_ativos_em_tempo_real():
    """Testa obtenção de cotações reais em tempo real."""
    conector = criar_conector_padrao()
    
    print("\n" + "="*80)
    print("🚀 TESTANDO COTAÇÕES EM TEMPO REAL")
    print("="*80)
    
    # Testa alguns ativos principais
    ativos_teste = ["BTC", "IBOV", "EURUSD", "PETR4"]
    
    for ativo in ativos_teste:
        print(f"\n⏳ Obtendo {ativo}...")
        cotacao = conector.obter_cotacao(ativo)
        if cotacao:
            print(f"   ✅ {conector.formatar_cotacao(cotacao)}")
        else:
            print(f"   ❌ Não foi possível obter {ativo}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    listar_ativos_em_tempo_real()
    testar_ativos_em_tempo_real()
