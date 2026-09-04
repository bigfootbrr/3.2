"""Gestão automática de conta com as 4 operações básicas.

O motor controla a banca por meio de SOMA, SUBTRAÇÃO, MULTIPLICAÇÃO e
DIVISÃO e decide os disparos automaticamente via Stop Gain / Stop Loss:

- MULTIPLICAÇÃO: valor da entrada = banca × risco% (padrão 1.5%)
- DIVISÃO:      retorno da vitória = valor ÷ (1 ÷ payout) = valor × payout
- SOMA:         vitória soma o retorno na banca
- SUBTRAÇÃO:    derrota subtrai o valor da banca
- STOP GAIN:    banca ≥ meta → PARA os disparos (lucro alcançado)
- STOP LOSS:    banca ≤ piso → PARA os disparos (proteção do capital)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisaoConta:
    """Resultado da avaliação da conta antes de um disparo."""
    permitido: bool
    motivo: str
    valor_entrada: float
    banca_atual: float
    lucro_total: float
    atingiu_stop: str | None  # "GAIN", "LOSS" ou None


class GestaoConta:
    """Controle automático de banca e stops (modo AUTO)."""

    def __init__(self, banca_inicial=0.0, valor_entrada=25.0,
                 stop_gain_pct=None, stop_loss_pct=None, risco_pct=1.5):
        self.banca_inicial = float(banca_inicial)
        self.banca = float(banca_inicial)
        self.valor_entrada_fixo = float(valor_entrada)
        self.risco_pct = float(risco_pct)
        # Stops em % da banca inicial (None = sem stop nesse lado).
        self.stop_gain_pct = stop_gain_pct
        self.stop_loss_pct = stop_loss_pct
        self.lucro_total = 0.0
        self.operacoes = 0
        self.stops_disparados = []
        # SOROS/GALE inteligente (estudo do mercado, com freios BFT):
        # após DERROTA, próxima entrada multiplica por k para recuperar a
        # perda + lucro alvo. Cadeia limitada a N gales + confluência extra.
        self.max_gales = 2          # nunca mais que 2 gales (kushaln3 quebrou com 8)
        self.gales_ativos = 0       # gales consecutivos em andamento
        self.perda_acumulada = 0.0  # perdas da cadeia atual

    # --- Soros/Gale inteligente ---

    def multiplicador_gale(self, payout):
        """DIVISÃO: k = (perda + lucro alvo) ÷ (valor × payout).

        k exato para a vitória seguinte recuperar a perda acumulada da
        cadeia e ainda dar o lucro da entrada base, considerando o payout
        real (payout baixo exige k maior).
        """
        payout = float(payout if payout is not None else 0.85)
        if payout <= 0:
            return None
        alvo = self.perda_acumulada + self.calcular_entrada()
        valor_base = max(self.calcular_entrada(), 1.0)
        k = (alvo / valor_base) / payout
        return round(k, 2)

    def proxima_entrada(self, confluencia=None, payout=None):
        """Valor da próxima entrada considerando cadeia Soros/Gale.

        Sem cadeia ativa → entrada base (banca × risco).
        Em cadeia (perdeu) → entrada base × k (recuperação), SE:
        - gales < max_gales (cadeia limitada);
        - confluência ≥ 85% (exigência extra pra gale, +10%);
        - nova entrada ≤ banca (nunca apostar mais do que existe).
        Se não aprovar, cadeia encerra (aceita a perda e recomeça).
        """
        base = self.calcular_entrada()
        if self.perda_acumulada <= 0 or self.gales_ativos >= self.max_gales:
            self.perda_acumulada = 0.0
            self.gales_ativos = 0
            return base, False
        # Gale exige confluência maior (85%) — qualidade acima de teimosia.
        if confluencia is not None and confluencia < 0.85:
            return base, False
        k = self.multiplicador_gale(payout)
        valor_gale = round(base * k, 2)
        if self.banca > 0 and valor_gale > self.banca:
            return base, False  # sem banca pra gale — cadeia encerra
        return valor_gale, True

    # --- As 4 operações ---

    def calcular_entrada(self):
        """MULTIPLICAÇÃO: valor da entrada = banca × risco%.

        RISCO DINÂMICO (protege os dois lados da meta do operador):
        - Banca saudável (≥ 50% da inicial): risco base (1.5%) — cresce
          com calma rumo ao STOP GAIN.
        - Banca sofrendo (< 50%): o risco DOBRA progressivamente (2×, 3×…)
          conforme a banca desce — recuperação mais eficiente que entradas
          minúsculas que nunca alcançam o piso (dezenas de derrotas seguidas
          deixariam a banca eternamente em $28 com entradas de $0.45).
        Nunca acima do teto de segurança: 8% da banca atual.
        """
        if self.banca <= 0:
            return self.valor_entrada_fixo
        if self.banca_inicial > 0:
            proporcao = self.banca / self.banca_inicial
            if proporcao < 0.5:
                multiplicador = min(4.0, 1.0 + (0.5 - proporcao) * 4.0)
            else:
                multiplicador = 1.0
            risco_efetivo = min(8.0, self.risco_pct * multiplicador)
        return round(self.banca * (risco_efetivo / 100.0), 2)

    def registrar_resultado(self, resultado, valor, payout):
        """SOMA/SUBTRAÇÃO/DIVISÃO do resultado na banca.

        VITÓRIA:  banca += valor × payout (DIVISÃO do retorno)
        DERROTA:  banca -= valor (SUBTRAÇÃO da perda)
        EMPATE:   banca inalterada
        """
        self.operacoes += 1
        if resultado == "VITÓRIA":
            retorno = valor * float(payout if payout is not None else 0.85)
            self.banca += retorno            # SOMA
            self.lucro_total += retorno
            # Vitória encerra a cadeia Soros/Gale.
            self.perda_acumulada = 0.0
            self.gales_ativos = 0
            return retorno
        if resultado == "DERROTA":
            self.banca -= valor              # SUBTRAÇÃO
            self.lucro_total -= valor
            # Inicia/estende a cadeia Soros/Gale (com limite de gales).
            self.perda_acumulada += valor
            if self.gales_ativos < self.max_gales:
                self.gales_ativos += 1
            return -valor
        return 0.0

    def _stop_gain(self):
        if self.stop_gain_pct is None or self.banca_inicial <= 0:
            return False
        meta = self.banca_inicial * (1.0 + self.stop_gain_pct / 100.0)
        return self.banca >= meta

    def _stop_loss(self):
        if self.stop_loss_pct is None or self.banca_inicial <= 0:
            return False
        piso = self.banca_inicial * (1.0 - self.stop_loss_pct / 100.0)
        return self.banca <= piso

    def avaliar_disparo(self, valor=None, confluencia=None, payout=None):
        """Decide se um novo disparo é permitido (stops + Soros/Gale)."""
        stop = None
        if self._stop_gain():
            stop = "GAIN"
        elif self._stop_loss():
            stop = "LOSS"
        if stop is not None:
            if stop not in self.stops_disparados:
                self.stops_disparados.append(stop)
            return DecisaoConta(
                permitido=False,
                motivo=f"STOP {stop} atingido — operações pausadas",
                valor_entrada=0.0,
                banca_atual=self.banca,
                lucro_total=self.lucro_total,
                atingiu_stop=stop,
            )
        valor_final = valor if valor is not None else self.proxima_entrada(
            confluencia=confluencia, payout=payout
        )[0]
        if self.banca > 0 and valor_final > self.banca:
            return DecisaoConta(
                permitido=False,
                motivo=f"entrada ${valor_final:.2f} > banca ${self.banca:.2f}",
                valor_entrada=0.0,
                banca_atual=self.banca,
                lucro_total=self.lucro_total,
                atingiu_stop=None,
            )
        return DecisaoConta(
            permitido=True,
            motivo="banca liberada",
            valor_entrada=valor_final,
            banca_atual=self.banca,
            lucro_total=self.lucro_total,
            atingiu_stop=None,
        )

    def resumo(self):
        return {
            "banca": round(self.banca, 2),
            "banca_inicial": round(self.banca_inicial, 2),
            "lucro_total": round(self.lucro_total, 2),
            "operacoes": self.operacoes,
            "proximo_valor_entrada": self.calcular_entrada(),
            "stop_gain_pct": self.stop_gain_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "stops_disparados": list(self.stops_disparados),
            "soros": {
                "cadeia_ativa": self.perda_acumulada > 0,
                "gales": self.gales_ativos,
                "max_gales": self.max_gales,
                "perda_cadeia": round(self.perda_acumulada, 2),
            },
        }