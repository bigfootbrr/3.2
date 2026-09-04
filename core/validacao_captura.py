"""Validação de capturas e calibrações da Quotex (e demais plataformas web).

Problema resolvido: uma captura da Quotex em assets/ veio com 2x2 pixels
(Bildschirmfoto ... 01.57.12.png) e coordenadas foram estimadas "a olho" a
partir dela — calibração sem valor. Este módulo:

1. `validar_captura()` — recusa capturas inutilizáveis (2x2, cor única,
   proporção absurda) ANTES de qualquer OCR/calibração;
2. `validar_calibracao_quotex()` — checa se o JSON de calibração salvo pela
   interface está completo e coerente com a tela atual, antes de autorizar
   cliques;
3. `exigir_captura_valida()` — fluxo único para a cadeia de captura.

Regra do projeto: falha fechado. Dados de duvida zero viram sinal.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path

from PIL import Image


# ---------------------------------------------------------------------------
# Validação de captura
# ---------------------------------------------------------------------------

LARGURA_MINIMA = 400   # um gráfico utilizável nunca é menor que isso
ALTURA_MINIMA = 240


@dataclass(frozen=True)
class ResultadoValidacao:
    sucesso: bool
    mensagem: str
    largura: int | None = None
    altura: int | None = None


def validar_captura(caminho_captura) -> ResultadoValidacao:
    """Recusa capturas inutilizáveis antes de qualquer leitura.

    Checagens (todas devem passar):
    - arquivo existe e abre como imagem;
    - dimensões mínimas (descarta 2x2 e recortes acidentais);
    - proporção plausível (entre 0.4 e 3.5 — descarta fatias/colunas);
    - imagem não é de cor única (captura preta/branca travada).
    """
    if not caminho_captura or not os.path.isfile(caminho_captura):
        return ResultadoValidacao(False, "captura não encontrada")

    try:
        with Image.open(caminho_captura) as imagem:
            largura, altura = imagem.size
            amostra = imagem.convert("RGB").resize((32, 32))
    except (OSError, ValueError) as erro:
        return ResultadoValidacao(False, f"captura ilegível: {erro}")

    if largura < LARGURA_MINIMA or altura < ALTURA_MINIMA:
        return ResultadoValidacao(
            False,
            f"captura inutilizável ({largura}x{altura}px); mínimo "
            f"{LARGURA_MINIMA}x{ALTURA_MINIMA} — recapturar",
            largura, altura,
        )

    proporcao = largura / altura
    if not (0.4 <= proporcao <= 3.5):
        return ResultadoValidacao(
            False,
            f"proporção implausível ({proporcao:.2f}); janela de trading não tem esse formato",
            largura, altura,
        )

    if _imagem_monocromatica(amostra):
        return ResultadoValidacao(
            False,
            "captura com cor única (tela travada ou sem render); recapturar",
            largura, altura,
        )

    return ResultadoValidacao(
        True,
        f"captura utilizável ({largura}x{altura}px)",
        largura, altura,
    )


def _imagem_monocromatica(amostra, limite_desvio=2.0):
    """True se a imagem não tem variação perceptível (tela travada).

    Usa o desvio padrão por canal: capturas reais de trading têm texto,
    velas e bordas — desvio sempre bem acima de 2. Uma tela travada tem
    desvio ~0 mesmo após o resize (que faz média dos pixels).
    """
    canal_r, canal_g, canal_b = amostra.split()
    histogramas = [canal.histogram() for canal in (canal_r, canal_g, canal_b)]
    n = amostra.size[0] * amostra.size[1]
    if n == 0:
        return True
    desvios = []
    for hist in histogramas:
        media = sum(valor * quantidade for valor, quantidade in enumerate(hist)) / n
        variancia = sum(
            ((valor - media) ** 2) * quantidade for valor, quantidade in enumerate(hist)
        ) / n
        desvios.append(variancia ** 0.5)
    return max(desvios) < limite_desvio


def exigir_captura_valida(caminho_captura) -> ResultadoValidacao:
    """Ponto único de entrada da cadeia de captura: valida ou recusa."""
    return validar_captura(caminho_captura)


# ---------------------------------------------------------------------------
# Validação de calibração da Quotex
# ---------------------------------------------------------------------------

CAMINHO_PADRAO_CALIBRACAO_QUOTEX = os.path.expanduser(
    "~/Library/Application Support/BFT Winbot/calibracao_quotex.json"
)

CHAVES_OBRIGATORIAS = ("compra", "venda", "tela")


@dataclass(frozen=True)
class ResultadoCalibracao:
    sucesso: bool
    mensagem: str
    coordenadas: dict | None = None


def validar_calibracao_quotex(
    caminho=CAMINHO_PADRAO_CALIBRACAO_QUOTEX,
    tela_atual=None,
):
    """Checa se a calibração salva é completa e serve para a tela atual.

    - JSON ausente → falha (calibrar pela interface primeiro);
    - chaves incompletas → falha;
    - tela_atual informada e diferente da calibração → falha (mudou resolução).
    """
    if not os.path.isfile(caminho):
        return ResultadoCalibracao(
            False,
            "calibração da Quotex inexistente; abrir o app e calibrar os botões",
        )
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            coordenadas = json.load(arquivo)
    except (OSError, json.JSONDecodeError) as erro:
        return ResultadoCalibracao(False, f"calibração ilegível: {erro}")

    if not isinstance(coordenadas, dict):
        return ResultadoCalibracao(False, "calibração com formato inesperado")

    faltando = [chave for chave in CHAVES_OBRIGATORIAS if chave not in coordenadas]
    if faltando:
        return ResultadoCalibracao(
            False, f"calibração incompleta; faltam: {', '.join(faltando)}"
        )

    for chave in CHAVES_OBRIGATORIAS:
        valor = coordenadas[chave]
        if not isinstance(valor, (list, tuple)) or len(valor) != 2:
            return ResultadoCalibracao(False, f"'{chave}' deve ser [x, y]")
        if not all(isinstance(v, int) and v >= 0 for v in valor):
            return ResultadoCalibracao(False, f"'{chave}' com valores inválidos: {valor}")

    if tela_atual is not None:
        referida = tuple(coordenadas["tela"])
        if referida != tuple(tela_atual):
            return ResultadoCalibracao(
                False,
                f"tela mudou desde a calibração ({referida} != {tuple(tela_atual)}); recalibrar",
            )

    return ResultadoCalibracao(True, "calibração da Quotex válida", coordenadas)


def listar_capturas_inutilizaveis(pasta_assets) -> list[str]:
    """Varre uma pasta e lista capturas que falham na validação (auditoria)."""
    inutilizaveis = []
    pasta = Path(pasta_assets)
    if not pasta.is_dir():
        return inutilizaveis
    for arquivo in sorted(pasta.glob("*.png")):
        if not validar_captura(str(arquivo)).sucesso:
            inutilizaveis.append(arquivo.name)
    return inutilizaveis