"""Seleção automática do perfil da IQ conforme o contexto da captura.

Problema resolvido: o perfil PERFIL_IQ_2026_08_30 foi calibrado para captura
de TELA INTEIRA (proporção 1.547), mas a captura da JANELA da IQ (via
`screencapture -l` com o window ID que `scripts/janela_iq.m` retorna) tem
proporção ~1.594 — os recortes relativos deslocam e leituras ficam erradas.

Solução: cada contexto de captura tem seu próprio perfil. `selecionar_perfil_iq()`
escolhe automaticamente pela proporção da captura real, e quem captura por
janela usa `capturar_janela_iq()` para gravar o PNG correto.

Regra de falha fechado: se a proporção não casa com nenhum perfil conhecido,
a leitura é recusada (nunca adivinhar recortes).
"""

from dataclasses import dataclass
import os
import subprocess

from PIL import Image

from calibracao_iq import (
    PERFIL_IQ_2026_08_30,
    PerfilVisualIq,
    RegiaoRelativa,
    perfil_compativel,
)


# ---------------------------------------------------------------------------
# Perfil da JANELA da IQ (derivado do perfil de tela inteira)
# ---------------------------------------------------------------------------

# A janela da IQ tem a mesma UI em proporção ~1.594. Os recortes relativos são
# recalibrados para esse enquadramento: a janela ocupa menos área vertical
# (barras do macOS somem) e os elementos ficam proporcionalmente maiores.
PERFIL_IQ_JANELA = PerfilVisualIq(
    nome="IQ Option desktop - captura da JANELA (screencapture -l)",
    proporcao_referencia=1.594,
    barra_abas=RegiaoRelativa(0.000, 0.020, 0.720, 0.100),
    ativo_selecionado=RegiaoRelativa(0.050, 0.095, 0.210, 0.180),
    saldo_e_tipo_conta=RegiaoRelativa(0.750, 0.015, 0.920, 0.095),
    payout=RegiaoRelativa(0.920, 0.195, 0.998, 0.320),
    botao_higher=RegiaoRelativa(0.920, 0.320, 0.998, 0.440),
    botao_lower=RegiaoRelativa(0.920, 0.440, 0.998, 0.560),
    timeframe=RegiaoRelativa(0.030, 0.730, 0.070, 0.820),
)

PERFIS_IQ_POR_CONTEXTO = (PERFIL_IQ_2026_08_30, PERFIL_IQ_JANELA)

CONTEXTO_TELA = "tela_inteira"
CONTEXTO_JANELA = "janela_iq"


def _desvio_proporcao(perfil, largura, altura):
    """Desvio relativo da proporção da captura em relação ao perfil."""
    if largura <= 0 or altura <= 0:
        return float("inf")
    proporcao_atual = largura / altura
    return abs(proporcao_atual - perfil.proporcao_referencia) / perfil.proporcao_referencia


def identificar_contexto(largura, altura, tolerancia=0.08):
    """Retorna o contexto da captura pela proporção (tela inteira ou janela).

    Escolhe o perfil MAIS PRÓXIMO dentro da tolerância: 1.547 (tela) e 1.594
    (janela) distam ~3%, então "primeiro que aceita" sempre escolheria tela.
    """
    if largura <= 0 or altura <= 0:
        return None
    melhor, melhor_desvio = None, float("inf")
    for contexto, perfil in (
        (CONTEXTO_TELA, PERFIL_IQ_2026_08_30),
        (CONTEXTO_JANELA, PERFIL_IQ_JANELA),
    ):
        desvio = _desvio_proporcao(perfil, largura, altura)
        if desvio <= tolerancia and desvio < melhor_desvio:
            melhor, melhor_desvio = contexto, desvio
    return melhor


def selecionar_perfil_iq(largura, altura, tolerancia=0.08):
    """Escolhe o perfil da IQ mais compatível com a proporção da captura.

    Retorna (perfil, contexto) ou (None, None) quando nenhuma geometria casa
    — o chamador deve recusar a leitura (falha fechado).
    """
    if largura <= 0 or altura <= 0:
        return None, None
    melhor = None
    melhor_desvio = float("inf")
    for contexto, perfil in (
        (CONTEXTO_TELA, PERFIL_IQ_2026_08_30),
        (CONTEXTO_JANELA, PERFIL_IQ_JANELA),
    ):
        desvio = _desvio_proporcao(perfil, largura, altura)
        if desvio <= tolerancia and desvio < melhor_desvio:
            melhor, melhor_desvio = (perfil, contexto), desvio
    return melhor if melhor else (None, None)


def selecionar_perfil_iq_por_captura(caminho_captura):
    """Abre a captura e seleciona o perfil compatível.

    Retorna (perfil, contexto) ou (None, None).
    """
    try:
        with Image.open(caminho_captura) as imagem:
            largura, altura = imagem.size
    except (OSError, ValueError):
        return None, None
    return selecionar_perfil_iq(largura, altura)


# ---------------------------------------------------------------------------
# Captura por janela
# ---------------------------------------------------------------------------

BINARIO_JANELA = "/private/tmp/bft_janela_iq"


def capturar_janela_iq(
    caminho="/private/tmp/bft_iq_janela.png",
    executor=subprocess.run,
    windowid_binario=BINARIO_JANELA,
):
    """Captura somente a JANELA da IQ via `screencapture -l <windowid>`.

    Compila `scripts/janela_iq.m` sob demanda. Retorna (sucesso, mensagem).
    Proporção da imagem resultante: ~1.594 (perfil PERFIL_IQ_JANELA).
    """
    fonte = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts", "janela_iq.m",
    )
    try:
        precisa_compilar = (
            executor is not subprocess.run
            or not os.path.isfile(windowid_binario)
            or os.path.getmtime(windowid_binario) < os.path.getmtime(fonte)
        )
        if precisa_compilar:
            compilacao = executor(
                ["/usr/bin/clang", "-framework", "CoreGraphics",
                 "-framework", "Foundation", fonte, "-o", windowid_binario],
                capture_output=True, text=True, timeout=30, check=False,
            )
            if compilacao.returncode != 0:
                return False, f"leitor de janela não compilou: {compilacao.stderr}"

        resultado = executor([windowid_binario], capture_output=True,
                             text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as erro:
        return False, f"leitor de janela não iniciou: {erro}"

    windowid = (resultado.stdout or "").strip()
    if not windowid or windowid == "0":
        return False, "janela da IQ não encontrada"

    try:
        captura = executor(
            ["/usr/sbin/screencapture", "-x", "-l", windowid, caminho],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError) as erro:
        return False, f"captura da janela falhou: {erro}"

    if captura.returncode != 0 or not os.path.isfile(caminho):
        detalhe = (captura.stderr or captura.stdout or "permissão negada").strip()
        return False, f"captura da janela bloqueada: {detalhe}"
    return True, f"janela {windowid} capturada em {caminho}"