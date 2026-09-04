"""Perfil visual inicial da IQ Option baseado em proporções da janela.

As regiões são apenas áreas de observação. Não representam coordenadas de
clique e precisam ser confirmadas novamente se tamanho/zoom da janela mudar.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegiaoRelativa:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self):
        if not (0 <= self.x1 < self.x2 <= 1 and 0 <= self.y1 < self.y2 <= 1):
            raise ValueError("região relativa deve permanecer dentro da janela")

    def converter(self, largura, altura):
        if largura <= 0 or altura <= 0:
            raise ValueError("dimensões da janela devem ser positivas")
        return (
            round(self.x1 * largura),
            round(self.y1 * altura),
            round(self.x2 * largura),
            round(self.y2 * altura),
        )


@dataclass(frozen=True)
class PerfilVisualIq:
    nome: str
    proporcao_referencia: float
    barra_abas: RegiaoRelativa
    ativo_selecionado: RegiaoRelativa
    saldo_e_tipo_conta: RegiaoRelativa
    payout: RegiaoRelativa
    botao_higher: RegiaoRelativa
    botao_lower: RegiaoRelativa
    timeframe: RegiaoRelativa


PERFIL_IQ_2026_08_30 = PerfilVisualIq(
    nome="IQ Option desktop - captura 2026-08-30 02:02",
    proporcao_referencia=3456 / 2234,
    barra_abas=RegiaoRelativa(0.125, 0.035, 0.735, 0.105),
    ativo_selecionado=RegiaoRelativa(0.070, 0.105, 0.215, 0.175),
    saldo_e_tipo_conta=RegiaoRelativa(0.765, 0.030, 0.915, 0.105),
    payout=RegiaoRelativa(0.925, 0.205, 0.995, 0.315),
    botao_higher=RegiaoRelativa(0.925, 0.315, 0.995, 0.430),
    botao_lower=RegiaoRelativa(0.925, 0.430, 0.995, 0.545),
    timeframe=RegiaoRelativa(0.045, 0.745, 0.075, 0.820),
)


def perfil_compativel(perfil, largura, altura, tolerancia=0.08):
    """Impede usar a calibração se a geometria da janela mudou demais."""
    if largura <= 0 or altura <= 0:
        return False
    proporcao_atual = largura / altura
    desvio = abs(proporcao_atual - perfil.proporcao_referencia)
    return desvio / perfil.proporcao_referencia <= tolerancia
