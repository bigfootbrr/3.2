"""Simulador de Forex OTC com dados realistas para as 4 plataformas."""

import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TipoForex:
    """Definição de um par de forex."""
    
    codigo: str
    nome: str
    preco_inicial: float
    volatilidade: float  # % de movimento
    

# Pares de Forex disponíveis — TODOS os pares nas 4 plataformas
PARES_FOREX = {
    # ===== EUR PAIRS =====
    # EUR Principais
    "EURUSD": TipoForex("EURUSD", "EUR/USD", 1.160320, 0.0008),
    "EURGBP": TipoForex("EURGBP", "EUR/GBP", 0.840000, 0.0008),
    "EURJPY": TipoForex("EURJPY", "EUR/JPY", 185.4855, 0.15),
    "EURAUD": TipoForex("EURAUD", "EUR/AUD", 1.618945, 0.0009),
    "EURCHF": TipoForex("EURCHF", "EUR/CHF", 0.939840, 0.0007),
    "EURNZD": TipoForex("EURNZD", "EUR/NZD", 1.964435, 0.0010),
    "EURCAD": TipoForex("EURCAD", "EUR/CAD", 1.450000, 0.0008),
    "EURPLN": TipoForex("EURPLN", "EUR/PLN", 4.250000, 0.0015),
    "EURCEK": TipoForex("EURCEK", "EUR/CZK", 25.300000, 0.02),
    "EURHUF": TipoForex("EURHUF", "EUR/HUF", 410.500000, 0.10),
    "EURRON": TipoForex("EURRON", "EUR/RON", 4.975000, 0.0015),
    "EURSEK": TipoForex("EURSEK", "EUR/SEK", 11.800000, 0.015),
    "EURNOK": TipoForex("EURNOK", "EUR/NOK", 11.950000, 0.015),
    "EURDKK": TipoForex("EURDKK", "EUR/DKK", 7.450000, 0.01),
    "EURBGN": TipoForex("EURBGN", "EUR/BGN", 1.956000, 0.001),
    "EURHRK": TipoForex("EURHRK", "EUR/HRK", 7.535000, 0.010),
    "EURTRY": TipoForex("EURTRY", "EUR/TRY", 39.950000, 0.25),
    "EURINR": TipoForex("EURINR", "EUR/INR", 98.500000, 0.30),
    "EURMXN": TipoForex("EURMXN", "EUR/MXN", 19.850000, 0.10),
    "EURSGD": TipoForex("EURSGD", "EUR/SGD", 1.580000, 0.008),
    "EURHKD": TipoForex("EURHKD", "EUR/HKD", 9.050000, 0.030),
    "EURTHB": TipoForex("EURTHB", "EUR/THB", 40.500000, 0.20),
    "EURZAR": TipoForex("EURZAR", "EUR/ZAR", 20.750000, 0.15),
    "EURKRW": TipoForex("EURKRW", "EUR/KRW", 1580.000000, 5.00),
    "EURMYR": TipoForex("EURMYR", "EUR/MYR", 5.150000, 0.020),
    "EURPHP": TipoForex("EURPHP", "EUR/PHP", 65.850000, 0.20),
    "EURIDR": TipoForex("EURIDR", "EUR/IDR", 18500.000000, 50.00),
    
    # ===== EUR OTC =====
    "EURAUD_OTC": TipoForex("EURAUD_OTC", "EUR/AUD (OTC)", 1.680565, 0.0009),
    "EURCAD_OTC": TipoForex("EURCAD_OTC", "EUR/CAD (OTC)", 1.613655, 0.0008),
    "EURCHF_OTC": TipoForex("EURCHF_OTC", "EUR/CHF (OTC)", 0.940355, 0.0007),
    "EURNZD_OTC": TipoForex("EURNZD_OTC", "EUR/NZD (OTC)", 1.985415, 0.0010),
    "EURTHB_OTC": TipoForex("EURTHB_OTC", "EUR/THB (OTC)", 38.47987, 0.25),
    "EURSGD_OTC": TipoForex("EURSGD_OTC", "EUR/SGD (OTC)", 1.600000, 0.008),
    "EURPLN_OTC": TipoForex("EURPLN_OTC", "EUR/PLN (OTC)", 4.280000, 0.0015),
    "EURCZK_OTC": TipoForex("EURCZK_OTC", "EUR/CZK (OTC)", 25.500000, 0.02),
    
    # ===== USD PAIRS (para completude) =====
    "USDJPY": TipoForex("USDJPY", "USD/JPY", 159.850000, 0.15),
    "USDCHF": TipoForex("USDCHF", "USD/CHF", 0.810000, 0.0007),
    "USDCAD": TipoForex("USDCAD", "USD/CAD", 1.250000, 0.0008),
    "USDMXN": TipoForex("USDMXN", "USD/MXN", 17.100000, 0.10),
    "USDTRY": TipoForex("USDTRY", "USD/TRY", 34.450000, 0.20),
    "USDINR": TipoForex("USDINR", "USD/INR", 84.850000, 0.25),
    "USDPHP": TipoForex("USDPHP", "USD/PHP", 56.750000, 0.20),
    "USDZAR": TipoForex("USDZAR", "USD/ZAR", 17.900000, 0.15),
    "USDSGD": TipoForex("USDSGD", "USD/SGD", 1.360000, 0.008),
    "USDHKD": TipoForex("USDHKD", "USD/HKD", 7.800000, 0.020),
    "USDTHB": TipoForex("USDTHB", "USD/THB", 34.850000, 0.20),
    
    # ===== GBP PAIRS =====
    "GBPUSD": TipoForex("GBPUSD", "GBP/USD", 1.270000, 0.0010),
    "GBPJPY": TipoForex("GBPJPY", "GBP/JPY", 201.500000, 0.20),
    "GBPCHF": TipoForex("GBPCHF", "GBP/CHF", 1.020000, 0.0008),
    "GBPCAD": TipoForex("GBPCAD", "GBP/CAD", 1.575000, 0.0010),
    "GBPAUD": TipoForex("GBPAUD", "GBP/AUD", 1.930000, 0.0010),
    "GBPNZD": TipoForex("GBPNZD", "GBP/NZD", 2.345000, 0.0012),
    
    # ===== AUD PAIRS =====
    "AUDUSD": TipoForex("AUDUSD", "AUD/USD", 0.668000, 0.0009),
    "AUDJPY": TipoForex("AUDJPY", "AUD/JPY", 106.850000, 0.15),
    "AUDNZD": TipoForex("AUDNZD", "AUD/NZD", 1.215000, 0.0010),
    "AUDCAD": TipoForex("AUDCAD", "AUD/CAD", 0.910000, 0.0008),
    "AUDCHF": TipoForex("AUDCHF", "AUD/CHF", 0.582000, 0.0007),
    
    # ===== NZD PAIRS =====
    "NZDUSD": TipoForex("NZDUSD", "NZD/USD", 0.550000, 0.0010),
    "NZDJPY": TipoForex("NZDJPY", "NZD/JPY", 87.950000, 0.15),
    "NZDCAD": TipoForex("NZDCAD", "NZD/CAD", 0.750000, 0.0008),
    "NZDCHF": TipoForex("NZDCHF", "NZD/CHF", 0.479000, 0.0007),
    
    # ===== CAD PAIRS =====
    "CADJPY": TipoForex("CADJPY", "CAD/JPY", 118.500000, 0.15),
    "CADCHF": TipoForex("CADCHF", "CAD/CHF", 0.650000, 0.0007),
    
    # ===== CHF PAIRS =====
    "CHFJPY": TipoForex("CHFJPY", "CHF/JPY", 182.350000, 0.20),
}

# Pares populares nas 4 plataformas (em ordem de preferência - aparecem nas abas)
PARES_POPULARES = [
    "EURUSD", 
    "EURAUD_OTC", 
    "EURJPY", 
    "EURCHF_OTC", 
    "EURNZD_OTC", 
    "EURTHB_OTC",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "NZDUSD",
]


@dataclass
class VelaForex:
    """Vela de forex com dados OHLC."""
    
    par: str
    abertura: float
    maxima: float
    minima: float
    fechamento: float
    volume: float
    timestamp: datetime


class SimuladorForexOTC:
    """Simula dados realistas de Forex OTC."""
    
    def __init__(self, par_inicial: str = "EURUSD", semente: int = None):
        if par_inicial not in PARES_FOREX:
            raise ValueError(f"Par {par_inicial} não disponível")
        
        self.par_atual = par_inicial
        self.tipo_par = PARES_FOREX[par_inicial]
        self.preco_atual = self.tipo_par.preco_inicial
        self.semente = semente
        self.rng = random.Random(semente)
        self.historico_velas: List[VelaForex] = []
        self.timestamp_inicio = datetime.now()
        self.vela_atual_inicio = datetime.now()
        self.precos_tick = [self.preco_atual]
    
    def mudar_par(self, novo_par: str) -> None:
        """Muda para outro par de forex."""
        if novo_par not in PARES_FOREX:
            raise ValueError(f"Par {novo_par} não disponível")
        
        self.par_atual = novo_par
        self.tipo_par = PARES_FOREX[novo_par]
        self.preco_atual = self.tipo_par.preco_inicial
        self.precos_tick = [self.preco_atual]
        self.historico_velas = []
        self.vela_atual_inicio = datetime.now()
    
    def gerar_tick(self) -> float:
        """Gera um tick realista seguindo movimento browniano."""
        # Movimento browniano com drift
        mudanca_pct = self.rng.normalvariate(0, self.tipo_par.volatilidade)
        self.preco_atual = max(0.0001, self.preco_atual * (1 + mudanca_pct / 100))
        self.precos_tick.append(self.preco_atual)
        return self.preco_atual
    
    def obter_vela_m1(self) -> VelaForex:
        """Gera vela M1 com base nos ticks atuais."""
        if len(self.precos_tick) < 2:
            self.gerar_tick()
            self.gerar_tick()
        
        abertura = self.precos_tick[0]
        fechamento = self.precos_tick[-1]
        maxima = max(self.precos_tick)
        minima = min(self.precos_tick)
        volume = len(self.precos_tick) * self.rng.uniform(1000, 5000)
        
        vela = VelaForex(
            par=self.par_atual,
            abertura=abertura,
            maxima=maxima,
            minima=minima,
            fechamento=fechamento,
            volume=volume,
            timestamp=datetime.now(),
        )
        
        self.historico_velas.append(vela)
        if len(self.historico_velas) > 1000:
            self.historico_velas = self.historico_velas[-1000:]
        
        # Reseta para próxima vela
        self.precos_tick = [fechamento]
        self.vela_atual_inicio = datetime.now()
        
        return vela
    
    def obter_historico_velas(self, quantidade: int = 50) -> List[VelaForex]:
        """Retorna histórico de velas."""
        return self.historico_velas[-quantidade:]
    
    def obter_preco_bid_ask(self) -> Tuple[float, float]:
        """Retorna bid e ask realistas."""
        spread = self.tipo_par.volatilidade * self.preco_atual * 10  # Spread proporcional
        bid = self.preco_atual - spread / 2
        ask = self.preco_atual + spread / 2
        return round(bid, 5), round(ask, 5)
    
    def obter_variacao_24h(self) -> float:
        """Retorna variação percentual nas últimas 24h."""
        if len(self.historico_velas) < 10:
            return self.rng.uniform(-2, 2)
        
        preco_24h_atras = self.historico_velas[0].abertura
        variacao_pct = ((self.preco_atual - preco_24h_atras) / preco_24h_atras) * 100
        return round(variacao_pct, 2)


class GerenciadorForexPlataformas:
    """Gerencia simuladores de forex para as 4 plataformas."""
    
    PLATAFORMAS = ["IQ Option", "Quotex", "Casa Trader", "Avallon"]
    
    def __init__(self):
        self.simuladores: Dict[str, SimuladorForexOTC] = {
            plataforma: SimuladorForexOTC() for plataforma in self.PLATAFORMAS
        }
        self.pares_disponiveis = list(PARES_FOREX.keys())
    
    def obter_simulador(self, plataforma: str) -> SimuladorForexOTC:
        """Obtém simulador para plataforma."""
        if plataforma not in self.PLATAFORMAS:
            raise ValueError(f"Plataforma {plataforma} não suportada")
        return self.simuladores[plataforma]
    
    def mudar_par_plataforma(self, plataforma: str, novo_par: str) -> None:
        """Muda par em uma plataforma."""
        sim = self.obter_simulador(plataforma)
        sim.mudar_par(novo_par)
    
    def gerar_tick_todas_plataformas(self) -> Dict[str, float]:
        """Gera tick para todas as plataformas."""
        resultado = {}
        for plataforma in self.PLATAFORMAS:
            sim = self.simuladores[plataforma]
            resultado[plataforma] = sim.gerar_tick()
        return resultado
    
    def obter_snapshot_todas(self) -> Dict[str, Dict]:
        """Snapshot completo de todas as plataformas."""
        snapshot = {}
        for plataforma in self.PLATAFORMAS:
            sim = self.simuladores[plataforma]
            bid, ask = sim.obter_preco_bid_ask()
            snapshot[plataforma] = {
                "par": sim.par_atual,
                "preco_bid": bid,
                "preco_ask": ask,
                "preco_mid": (bid + ask) / 2,
                "variacao_24h": sim.obter_variacao_24h(),
                "timestamp": datetime.now().isoformat(),
            }
        return snapshot


def criar_gerenciador_forex() -> GerenciadorForexPlataformas:
    """Factory para criar gerenciador."""
    return GerenciadorForexPlataformas()


if __name__ == "__main__":
    gerenciador = criar_gerenciador_forex()
    
    print("\n" + "="*100)
    print("🌍 SIMULADOR DE FOREX OTC — INTEGRAÇÃO COM 4 PLATAFORMAS")
    print("="*100)
    
    print("\n📊 Pares disponíveis:")
    for par_code, par_tipo in PARES_FOREX.items():
        print(f"  {par_code:12} → {par_tipo.nome:15} Volatilidade: {par_tipo.volatilidade*100:.3f}%")
    
    print("\n🏢 Plataformas:")
    for plataforma in gerenciador.PLATAFORMAS:
        print(f"  ✓ {plataforma}")
    
    print("\n⚡ Gerando 5 ticks para cada plataforma...")
    for i in range(5):
        precos = gerenciador.gerar_tick_todas_plataformas()
        print(f"\nTick {i+1}:")
        for plataforma, preco in precos.items():
            print(f"  {plataforma:20} → {preco:.5f}")
    
    print("\n📸 Snapshot atual:")
    snapshot = gerenciador.obter_snapshot_todas()
    for plataforma, dados in snapshot.items():
        print(f"\n  {plataforma}:")
        print(f"    Par: {dados['par']}")
        print(f"    Bid: {dados['preco_bid']:.5f} | Ask: {dados['preco_ask']:.5f}")
        print(f"    Variação 24h: {dados['variacao_24h']:+.2f}%")
    
    print("\n" + "="*100)
