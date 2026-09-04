"""Mercado fictício com formação de velas para testes seguros do BFT Winbot."""

from dataclasses import dataclass
from datetime import datetime
import random


@dataclass(frozen=True)
class Cotacao:
    ativo: str
    preco: float
    variacao: float
    horario: datetime


@dataclass(frozen=True)
class Vela:
    ativo: str
    timeframe: str
    numero: int
    abertura: float
    maxima: float
    minima: float
    fechamento: float
    inicio: datetime
    fim: datetime
    volume: float | None = None


class MercadoSimulado:
    """Gera preços e velas fictícias, sem conexão externa ou envio de ordens."""

    def __init__(
        self,
        ativo="WIN",
        preco_inicial=130_000.0,
        semente=None,
        ticks_por_vela=5,
        limite_historico=500,
        timeframe="M1",
    ):
        if ticks_por_vela < 1:
            raise ValueError("ticks_por_vela precisa ser maior que zero")
        if limite_historico < 1:
            raise ValueError("limite_historico precisa ser maior que zero")
        timeframe = timeframe.upper()
        if timeframe not in {"M1", "M5", "M15"}:
            raise ValueError("timeframe precisa ser M1, M5 ou M15")

        self.ativo = ativo
        self.timeframe = timeframe
        self._preco = float(preco_inicial)
        self._gerador = random.Random(semente)
        self._ticks_por_vela = ticks_por_vela
        self._limite_historico = limite_historico
        self._ticks_atuais = []
        self._inicio_vela = None
        self._numero_vela = 0
        self._historico = []

    def obter_cotacao(self):
        """Mantém compatibilidade com o loop antigo."""
        cotacao, _ = self.obter_evento()
        return cotacao

    def obter_evento(self):
        """Retorna a cotação atual e, quando completa, uma vela fechada."""
        variacao = self._gerador.uniform(-120.0, 120.0)
        self._preco = max(0.0, self._preco + variacao)
        agora = datetime.now()

        cotacao = Cotacao(
            ativo=self.ativo,
            preco=round(self._preco, 2),
            variacao=round(variacao, 2),
            horario=agora,
        )

        if not self._ticks_atuais:
            self._inicio_vela = agora
        self._ticks_atuais.append(cotacao.preco)

        vela_fechada = None
        if len(self._ticks_atuais) >= self._ticks_por_vela:
            self._numero_vela += 1
            vela_fechada = Vela(
                ativo=self.ativo,
                timeframe=self.timeframe,
                numero=self._numero_vela,
                abertura=self._ticks_atuais[0],
                maxima=max(self._ticks_atuais),
                minima=min(self._ticks_atuais),
                fechamento=self._ticks_atuais[-1],
                inicio=self._inicio_vela,
                fim=agora,
            )
            self._historico.append(vela_fechada)
            self._historico = self._historico[-self._limite_historico :]
            self._ticks_atuais = []
            self._inicio_vela = None

        return cotacao, vela_fechada

    def obter_historico(self):
        """Devolve uma cópia para impedir alteração acidental do histórico."""
        return tuple(self._historico)
