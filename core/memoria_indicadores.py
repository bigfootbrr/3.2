"""Memória adaptativa: placar por indicador × timeframe (só velas fechadas).

Cada diagnóstico com direção (ALTA/BAIXA) e peso vira uma aposta pendente;
a PRÓXIMA vela fechada do mesmo timeframe decide o resultado comparando o
movimento real da vela (fechamento vs abertura) com a direção apontada.

Regras (constituição do projeto):
- Nada é avaliado com a mesma vela que gerou o sinal (anti-repaint).
- EMPATE não conta no placar (mercado não confirmou nada).
- A taxa RECENTE (janela deslizante) tem prioridade sobre a histórica:
  o bot enxerga o momento, não só o passado distante.
- Falha fechado: sem amostras mínimas, o indicador não recebe bônus.
"""

from collections import deque
from dataclasses import dataclass, field


JANELA_RECENTE = 20
MINIMO_AVALIACOES = 4


@dataclass
class PlacarIndicador:
    acertos: int = 0
    total: int = 0
    recentes: deque = field(default_factory=lambda: deque(maxlen=JANELA_RECENTE))

    @property
    def taxa(self) -> float:
        return self.acertos / self.total if self.total else 0.0

    @property
    def taxa_recente(self) -> float:
        if not self.recentes:
            return self.taxa
        return sum(self.recentes) / len(self.recentes)


class MemoriaIndicadores:
    """Junta o placar por (timeframe, indicador) e ranqueia os melhores."""

    def __init__(self, minimo_amostras: int = MINIMO_AVALIACOES):
        self.minimo_amostras = int(minimo_amostras)
        self._placares: dict = {}
        self._pendentes: dict = {}

    # ------------------------------------------------------------------
    # Registro de sinais e avaliação
    # ------------------------------------------------------------------

    @staticmethod
    def _chave(timeframe: str, codigo: str) -> tuple:
        return (str(timeframe).upper(), str(codigo).upper())

    def _placar_de(self, timeframe: str, codigo: str) -> PlacarIndicador:
        return self._placares.setdefault(
            self._chave(timeframe, codigo), PlacarIndicador()
        )

    def registrar_diagnosticos(self, timeframe, diagnosticos, vela) -> int:
        """Guarda apostas pendentes a partir dos diagnósticos da confluência.

        Só entram diagnósticos com direção ALTA/BAIXA e peso > 0 (neutro não
        é aposta). Um novo sinal do mesmo indicador substitui o anterior.
        """
        tf = str(timeframe).upper()
        apostas = 0
        for diagnostico in diagnosticos or ():
            direcao = getattr(diagnostico, "direcao", None)
            codigo = (
                getattr(diagnostico, "codigo", None)
                or (getattr(diagnostico, "nome", "") or "").upper()
            )
            if direcao not in ("ALTA", "BAIXA") or not codigo:
                continue
            if float(getattr(diagnostico, "peso", 0) or 0) <= 0:
                continue
            self._pendentes[self._chave(tf, codigo)] = {
                "direcao": direcao,
                "fim_sinal": vela.fim,
            }
            apostas += 1
        return apostas

    def avaliar_pendentes(self, vela) -> tuple:
        """Fecha as apostas pendentes do timeframe desta vela.

        A vela de avaliação precisa ser POSTERIOR à vela do sinal
        (anti-repaint). EMPATE não entra no placar. Retorna os resultados
        avaliados: (timeframe, codigo, resultado, venceu).
        """
        tf = str(getattr(vela, "timeframe", "") or "").upper()
        movimento = float(vela.fechamento) - float(vela.abertura)
        resultados = []
        for chave, aposta in list(self._pendentes.items()):
            chave_tf, codigo = chave
            if chave_tf != tf or vela.fim <= aposta["fim_sinal"]:
                continue
            del self._pendentes[chave]

            if movimento > 0:
                resultado = "VITÓRIA" if aposta["direcao"] == "ALTA" else "DERROTA"
            elif movimento < 0:
                resultado = "VITÓRIA" if aposta["direcao"] == "BAIXA" else "DERROTA"
            else:
                resultado = "EMPATE"

            if resultado != "EMPATE":
                placar = self._placar_de(tf, codigo)
                venceu = resultado == "VITÓRIA"
                placar.total += 1
                placar.recentes.append(venceu)
                if venceu:
                    placar.acertos += 1
                resultados.append((tf, codigo, resultado, venceu))
        return tuple(resultados)

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------

    def melhores(self, timeframe, limite: int = 2) -> tuple:
        """Top indicadores por taxa recente (exige amostras mínimas)."""
        tf = str(timeframe).upper()
        candidatos = []
        for (chave_tf, codigo), placar in self._placares.items():
            if chave_tf != tf or placar.total < self.minimo_amostras:
                continue
            candidatos.append({
                "codigo": codigo,
                "taxa": round(placar.taxa_recente, 3),
                "total": placar.total,
            })
        candidatos.sort(key=lambda item: (-item["taxa"], -item["total"]))
        return tuple(candidatos[: max(0, int(limite))])

    def taxa(self, timeframe, codigo) -> float | None:
        placar = self._placares.get(self._chave(timeframe, codigo))
        if placar is None or placar.total < self.minimo_amostras:
            return None
        return round(placar.taxa_recente, 3)

    def resumo(self) -> dict:
        """Resumo completo para a API: por timeframe, ordenado pelo melhor."""
        resumo: dict = {}
        for (tf, _), _ in self._placares.items():
            resumo[tf] = [dict(item) for item in self.melhores(tf, limite=8)]
        return resumo