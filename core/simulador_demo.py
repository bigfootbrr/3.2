"""Placar de sinais em velas fechadas, sem integração com corretora."""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class EntradaDemo:
    ativo: str
    timeframe: str
    direcao: str
    gerada_em: object
    expira_em: object


@dataclass(frozen=True)
class ResultadoDemo:
    entrada: EntradaDemo
    resultado: str
    abertura: float
    fechamento: float


class SimuladorDemo:
    def __init__(self):
        self.pendente = None
        self.vitorias = 0
        self.derrotas = 0
        self.empates = 0

    def registrar(self, sinal, vela):
        if sinal not in {"ALTA", "BAIXA"} or self.pendente is not None:
            return None
        minutos = {"M1": 1, "M5": 5, "M15": 15}[vela.timeframe.upper()]
        self.pendente = EntradaDemo(
            ativo=vela.ativo,
            timeframe=vela.timeframe.upper(),
            direcao=sinal,
            gerada_em=vela.fim,
            expira_em=vela.fim + timedelta(minutes=minutos),
        )
        return self.pendente

    def avaliar(self, vela):
        entrada = self.pendente
        if entrada is None or vela.fim < entrada.expira_em:
            return None
        if vela.fim != entrada.expira_em:
            # Se faltou uma captura, não inventa o resultado de outra vela.
            self.pendente = None
            return None

        movimento = (
            "ALTA" if vela.fechamento > vela.abertura
            else "BAIXA" if vela.fechamento < vela.abertura
            else "EMPATE"
        )
        resultado = (
            "EMPATE" if movimento == "EMPATE"
            else "VITÓRIA" if movimento == entrada.direcao
            else "DERROTA"
        )
        if resultado == "VITÓRIA":
            self.vitorias += 1
        elif resultado == "DERROTA":
            self.derrotas += 1
        else:
            self.empates += 1
        self.pendente = None
        return ResultadoDemo(
            entrada=entrada,
            resultado=resultado,
            abertura=vela.abertura,
            fechamento=vela.fechamento,
        )

    @property
    def total_decidido(self):
        return self.vitorias + self.derrotas

    @property
    def taxa_acerto(self):
        if not self.total_decidido:
            return None
        return self.vitorias / self.total_decidido

    def resumo(self):
        return {
            "vitorias": self.vitorias,
            "derrotas": self.derrotas,
            "empates": self.empates,
            "taxa_acerto": self.taxa_acerto,
            "pendente": self.pendente is not None,
        }
