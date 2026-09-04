"""Ciclo pós-clique para entradas reais do Mercado Aberto.

Quando o robô dispara (clique autorizado), registra a entrada com o
preço REAL do par (Yahoo Finance) e a expiração de 1 vela. No próximo
ciclo, avalia VITÓRIA/DERROTA comparando o movimento do preço real com
a direção da entrada. Mantém o placar da sessão.
"""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class EntradaReal:
    ativo: str
    direcao: str
    preco_entrada: float
    gerada_em: object
    expira_em: object
    valor: float = 0.0
    payout: float | None = None


@dataclass(frozen=True)
class ResultadoReal:
    entrada: EntradaReal
    resultado: str
    preco_entrada: float
    preco_saida: float
    lucro: float


class RegistroEntradasReais:
    """Uma entrada pendente por vez (mesma política do SimuladorDemo)."""

    def __init__(self):
        self.pendente: EntradaReal | None = None
        self.vitorias = 0
        self.derrotas = 0
        self.empates = 0

    def registrar(self, ativo, direcao, preco, agora, minutos=1, valor=0.0, payout=None):
        """Registra entrada no disparo. Retorna EntradaReal ou None."""
        if direcao not in {"ALTA", "BAIXA"} or self.pendente is not None:
            return None
        if preco is None or preco <= 0:
            return None
        self.pendente = EntradaReal(
            ativo=ativo,
            direcao=direcao,
            preco_entrada=float(preco),
            gerada_em=agora,
            expira_em=agora + timedelta(minutes=minutos),
            valor=float(valor or 0.0),
            payout=payout,
        )
        return self.pendente

    def avaliar(self, preco_atual, agora):
        """Avalia a entrada pendente quando a expiração chegou.

        Movimento real: preço_atual vs preco_entrada. ALTA vence se subiu,
        BAIXA vence se caiu, EMPATE se igual. Retorna ResultadoReal ou None.
        """
        entrada = self.pendente
        if entrada is None or agora < entrada.expira_em:
            return None
        self.pendente = None
        movimento = preco_atual - entrada.preco_entrada
        if abs(movimento) < 1e-12:
            resultado = "EMPATE"
        elif movimento > 0:
            resultado = "VITÓRIA" if entrada.direcao == "ALTA" else "DERROTA"
        else:
            resultado = "VITÓRIA" if entrada.direcao == "BAIXA" else "DERROTA"

        if entrada.payout is not None and entrada.valor > 0:
            if resultado == "VITÓRIA":
                lucro = entrada.valor * entrada.payout
            elif resultado == "DERROTA":
                lucro = -entrada.valor
            else:
                lucro = 0.0
        else:
            # Sem valor/payout informados: lucro relativo (% do movimento).
            lucro = (
                movimento / entrada.preco_entrada * 100.0
                if entrada.preco_entrada
                else 0.0
            )

        if resultado == "VITÓRIA":
            self.vitorias += 1
        elif resultado == "DERROTA":
            self.derrotas += 1
        else:
            self.empates += 1

        return ResultadoReal(
            entrada=entrada,
            resultado=resultado,
            preco_entrada=entrada.preco_entrada,
            preco_saida=float(preco_atual),
            lucro=lucro,
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
            "pendente_info": (
                None
                if self.pendente is None
                else {
                    "ativo": self.pendente.ativo,
                    "direcao": self.pendente.direcao,
                    "preco_entrada": self.pendente.preco_entrada,
                    "expira_em": self.pendente.expira_em.strftime("%H:%M"),
                }
            ),
        }