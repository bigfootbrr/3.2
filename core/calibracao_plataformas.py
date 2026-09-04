"""Registro de perfis visuais por plataforma (IQ, Quotex, Casa Trader, Avallon).

Cada plataforma declara suas regiões relativas de observação usando a mesma
`RegiaoRelativa` da IQ. Os leitores genéricos (`leitor_visual`) consomem o
perfil e produzem os mesmos resultados dos leitores `_iq`, sem duplicar a
lógica de OCR/recorte.

Regras (planta mental do projeto):
- Regiões são áreas de OBSERVAÇÃO, nunca coordenadas de clique.
- Perfis só são válidos se a proporção da janela estiver dentro da tolerância.
- Falha fechado: leitura ambígua nunca vira sinal.
"""

from dataclasses import dataclass, field

from calibracao_iq import PERFIL_IQ_2026_08_30, RegiaoRelativa, perfil_compativel


# ---------------------------------------------------------------------------
# Perfil genérico
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerfilVisualPlataforma:
    """Regiões relativas de uma plataforma, independentes da resolução."""

    plataforma: str
    nome: str
    proporcao_referencia: float
    ativo_selecionado: RegiaoRelativa | None = None
    payout: RegiaoRelativa | None = None
    timeframe: RegiaoRelativa | None = None
    botao_compra: RegiaoRelativa | None = None
    botao_venda: RegiaoRelativa | None = None

    def geometria_ok(self, largura, altura, tolerancia=0.08):
        """True se a proporção da janela está dentro da tolerância do perfil."""
        return perfil_compativel(self, largura, altura, tolerancia)

    def recorte(self, regiao, largura, altura):
        """Converte uma região relativa em caixa de pixels da captura."""
        if regiao is None:
            raise ValueError(f"perfil {self.plataforma} não define essa região")
        return regiao.converter(largura, altura)


# ---------------------------------------------------------------------------
# Perfis por plataforma
# ---------------------------------------------------------------------------

# A IQ reaproveita o perfil já calibrado (fonte única da verdade).
PERFIL_IQ = PerfilVisualPlataforma(
    plataforma="iq",
    nome=PERFIL_IQ_2026_08_30.nome,
    proporcao_referencia=PERFIL_IQ_2026_08_30.proporcao_referencia,
    ativo_selecionado=PERFIL_IQ_2026_08_30.ativo_selecionado,
    payout=PERFIL_IQ_2026_08_30.payout,
    timeframe=PERFIL_IQ_2026_08_30.timeframe,
    botao_compra=PERFIL_IQ_2026_08_30.botao_higher,
    botao_venda=PERFIL_IQ_2026_08_30.botao_lower,
)

# Quotex web: layout de proporção próxima (barra lateral direita de trade).
# Calibração inicial estimada a partir de capturas 2x2 do Trading Desk;
# precisa ser confirmada visualmente antes de liberar disparos reais.
PERFIL_QUOTEX = PerfilVisualPlataforma(
    plataforma="quotex",
    nome="Quotex web - estimativa inicial 2026-09-04",
    proporcao_referencia=16 / 9,
    ativo_selecionado=RegiaoRelativa(0.010, 0.055, 0.200, 0.140),
    payout=RegiaoRelativa(0.845, 0.240, 0.995, 0.360),
    botao_compra=RegiaoRelativa(0.845, 0.360, 0.995, 0.560),
    botao_venda=RegiaoRelativa(0.845, 0.560, 0.995, 0.760),
)

# Casa Trader: mesmo esqueleto de botões por cor, payout à direita.
PERFIL_CASA_TRADER = PerfilVisualPlataforma(
    plataforma="casa_trader",
    nome="Casa Trader - estimativa inicial 2026-09-04",
    proporcao_referencia=16 / 9,
    ativo_selecionado=RegiaoRelativa(0.008, 0.040, 0.230, 0.150),
    payout=RegiaoRelativa(0.830, 0.220, 0.995, 0.380),
    botao_compra=RegiaoRelativa(0.830, 0.380, 0.995, 0.580),
    botao_venda=RegiaoRelativa(0.830, 0.580, 0.995, 0.780),
)

# Avallon: proporção desktop clássica, botões empilhados à direita.
PERFIL_AVALLON = PerfilVisualPlataforma(
    plataforma="avallon",
    nome="Avallon - estimativa inicial 2026-09-04",
    proporcao_referencia=16 / 9,
    ativo_selecionado=RegiaoRelativa(0.008, 0.050, 0.220, 0.150),
    payout=RegiaoRelativa(0.840, 0.230, 0.995, 0.370),
    botao_compra=RegiaoRelativa(0.840, 0.370, 0.995, 0.565),
    botao_venda=RegiaoRelativa(0.840, 0.565, 0.995, 0.760),
)

PERFIS_POR_PLATAFORMA = {
    PERFIL_IQ.plataforma: PERFIL_IQ,
    PERFIL_QUOTEX.plataforma: PERFIL_QUOTEX,
    PERFIL_CASA_TRADER.plataforma: PERFIL_CASA_TRADER,
    PERFIL_AVALLON.plataforma: PERFIL_AVALLON,
}

PLATAFORMAS = tuple(PERFIS_POR_PLATAFORMA)

_PERFIS_DE_ESTIMATIVA = frozenset({"quotex", "casa_trader", "avallon"})


def obter_perfil(plataforma):
    """Retorna o perfil da plataforma ou levanta erro claro."""
    chave = (plataforma or "").strip().lower()
    if chave not in PERFIS_POR_PLATAFORMA:
        raise ValueError(
            f"plataforma desconhecida: {plataforma!r}; válidas: {', '.join(PLATAFORMAS)}"
        )
    return PERFIS_POR_PLATAFORMA[chave]


def perfil_confirmado(plataforma):
    """True somente quando o perfil da plataforma já foi calibrado visualmente.

    Quotex/Casa Trader/Avallon ainda são ESTIMATIVAS: nunca liberar disparos
    reais com elas até confirmar a geometria com capturas de referência.
    """
    return (plataforma or "").strip().lower() not in _PERFIS_DE_ESTIMATIVA