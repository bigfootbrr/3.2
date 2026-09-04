"""Leitor visual experimental de velas da IQ Option.

Transforma pixels do grafico em OHLC relativo. Nao controla mouse, teclado ou
qualquer botao da corretora. A escala vertical permanece em pixels: valores
menores representam precos visualmente mais altos.
"""

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class VelaVisual:
    x: int
    abertura_y: int
    maxima_y: int
    minima_y: int
    fechamento_y: int
    direcao: str


@dataclass(frozen=True)
class ResultadoVelas:
    sucesso: bool
    velas: tuple[VelaVisual, ...]
    mensagem: str
    linha_expiracao_x: int | None = None


def ler_velas(caminho, minimo_velas=20):
    """Le velas fechadas visiveis e ignora a vela junto a linha de expiracao."""
    try:
        rgb = np.asarray(Image.open(caminho).convert("RGB"))
    except (OSError, ValueError) as erro:
        return ResultadoVelas(False, (), f"imagem indisponivel: {erro}")

    altura, largura = rgb.shape[:2]
    linha = _detectar_linha_expiracao(rgb)
    if linha is None:
        return ResultadoVelas(False, (), "linha de expiracao nao reconhecida")

    x_inicio = max(250, int(largura * 0.09))
    x_fim = linha - max(12, int(largura * 0.004))
    y_inicio = int(altura * 0.17)
    y_fim = int(altura * 0.84)
    if x_fim <= x_inicio or y_fim <= y_inicio:
        return ResultadoVelas(False, (), "area util do grafico invalida", linha)

    recorte = rgb[y_inicio:y_fim, x_inicio:x_fim]
    verdes, vermelhas = _mascaras_cores(recorte)
    mascara = verdes | vermelhas
    pontuacao_x = mascara.sum(axis=0).astype(float)
    passo = _estimar_passo(pontuacao_x)
    if passo is None:
        return ResultadoVelas(False, (), "espacamento das velas nao reconhecido", linha)

    fase = max(range(passo), key=lambda valor: float(pontuacao_x[valor::passo].sum()))
    velas = []
    meia_largura = max(3, int(round(passo * 0.36)))
    for centro in range(fase, recorte.shape[1], passo):
        esquerda = max(0, centro - meia_largura)
        direita = min(recorte.shape[1], centro + meia_largura + 1)
        verde = verdes[:, esquerda:direita]
        vermelha = vermelhas[:, esquerda:direita]
        cor, direcao = (verde, "ALTA") if verde.sum() >= vermelha.sum() else (vermelha, "BAIXA")
        vela = _extrair_vela(cor, x_inicio + centro, y_inicio, direcao)
        if vela is not None:
            velas.append(vela)

    # A ultima posicao pode conter a vela que ainda esta formando.
    limite_fechadas = linha - max(18, passo)
    velas = tuple(vela for vela in velas if vela.x <= limite_fechadas)
    if len(velas) < minimo_velas:
        return ResultadoVelas(
            False,
            velas,
            f"somente {len(velas)} velas fechadas reconhecidas",
            linha,
        )
    return ResultadoVelas(
        True,
        velas,
        f"{len(velas)} velas fechadas reconhecidas; vela atual ignorada",
        linha,
    )


def _mascaras_cores(rgb):
    canais = rgb.astype(np.int16)
    vermelho, verde, azul = (canais[:, :, indice] for indice in range(3))
    mascara_verde = (
        (verde > 65)
        & ((verde - vermelho) > 22)
        & (verde > azul * 1.08)
    )
    mascara_vermelha = (
        (vermelho > 100)
        & ((vermelho - verde) > 28)
        & (vermelho > azul * 1.08)
    )
    return mascara_verde, mascara_vermelha


def _detectar_linha_expiracao(rgb):
    altura, largura = rgb.shape[:2]
    canais = rgb.astype(np.int16)
    vermelho, verde, azul = (canais[:, :, indice] for indice in range(3))
    mascara = (
        (vermelho > 150)
        & ((vermelho - verde) > 50)
        & (vermelho > azul * 1.25)
    )
    inicio_y, fim_y = int(altura * 0.12), int(altura * 0.88)
    inicio_x, fim_x = int(largura * 0.55), int(largura * 0.90)
    contagens = mascara[inicio_y:fim_y, inicio_x:fim_x].sum(axis=0)
    indice = int(np.argmax(contagens))
    if contagens[indice] < (fim_y - inicio_y) * 0.45:
        return None
    return inicio_x + indice


def _estimar_passo(pontuacao):
    if pontuacao.size < 100 or pontuacao.max(initial=0) < 4:
        return None
    serie = np.minimum(pontuacao, 100)
    serie = serie - serie.mean()
    candidatos = range(9, 23)
    return max(candidatos, key=lambda passo: float(np.dot(serie[:-passo], serie[passo:])))


def _extrair_vela(mascara_cor, x, deslocamento_y, direcao):
    if int(mascara_cor.sum()) < 8:
        return None
    linhas_corpo = np.where(mascara_cor.sum(axis=1) >= 2)[0]
    if not linhas_corpo.size:
        return None
    grupos = _grupos_contiguos(linhas_corpo, tolerancia=2)
    corpo = max(grupos, key=lambda grupo: int(mascara_cor[grupo[0]:grupo[-1] + 1].sum()))
    topo_corpo, base_corpo = int(corpo[0]), int(corpo[-1])
    if base_corpo - topo_corpo > 180:
        return None

    colunas = mascara_cor[:, max(0, mascara_cor.shape[1] // 2 - 1):mascara_cor.shape[1] // 2 + 2]
    linhas_pavio = np.where(colunas.any(axis=1))[0]
    if linhas_pavio.size:
        proximas = linhas_pavio[
            (linhas_pavio >= topo_corpo - 100) & (linhas_pavio <= base_corpo + 100)
        ]
        if proximas.size:
            topo, base = int(proximas.min()), int(proximas.max())
        else:
            topo, base = topo_corpo, base_corpo
    else:
        topo, base = topo_corpo, base_corpo

    topo = min(topo, topo_corpo)
    base = max(base, base_corpo)
    if direcao == "ALTA":
        abertura, fechamento = base_corpo, topo_corpo
    else:
        abertura, fechamento = topo_corpo, base_corpo
    return VelaVisual(
        x=x,
        abertura_y=deslocamento_y + abertura,
        maxima_y=deslocamento_y + topo,
        minima_y=deslocamento_y + base,
        fechamento_y=deslocamento_y + fechamento,
        direcao=direcao,
    )


def _grupos_contiguos(valores, tolerancia=1):
    grupos = []
    inicio = anterior = int(valores[0])
    for valor_bruto in valores[1:]:
        valor = int(valor_bruto)
        if valor - anterior > tolerancia:
            grupos.append(range(inicio, anterior + 1))
            inicio = valor
        anterior = valor
    grupos.append(range(inicio, anterior + 1))
    return grupos
