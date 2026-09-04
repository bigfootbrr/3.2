"""Detecta os botões de compra e venda pela COR na tela da corretora.

Independente dos nomes usados por cada plataforma (HIGHER/LOWER, COMPRAR/
VENDER, BUY/SELL, Para cima/Para baixo), o botão de compra é o bloco VERDE
e o de venda é o bloco VERMELHO no lado direito da tela.
"""

from PIL import Image


def detectar_botoes_cor(
    caminho_captura,
    faixa_x=(0.85, 0.99),
    faixa_y=(0.10, 0.98),
):
    """Varre a região direita procurando os blocos verde e vermelho.

    Retorna (centro_compra, centro_venda): cada um é (x, y) em pixels da
    imagem, ou None quando o botão não é encontrado.
    """
    if not caminho_captura:
        return None, None
    try:
        im = Image.open(caminho_captura).convert("RGB")
    except (OSError, ValueError):
        return None, None
    largura, altura = im.size
    x_min = int(largura * faixa_x[0])
    x_max = int(largura * faixa_x[1])
    y_min = int(altura * faixa_y[0])
    y_max = int(altura * faixa_y[1])

    verdes, vermelhos = [], []
    for y in range(y_min, y_max, 4):
        for x in range(x_min, x_max, 8):
            r, g, b = im.getpixel((x, y))[:3]
            if g > 90 and g > r + 20 and g > b + 20:
                verdes.append((x, y))
            elif r > 130 and r > g + 40 and b < 130:
                vermelhos.append((x, y))

    def _centro(pontos):
        if not pontos:
            return None
        xs = [p[0] for p in pontos]
        ys = [p[1] for p in pontos]
        return (sum(xs) // len(xs), sum(ys) // len(ys))

    return _centro(verdes), _centro(vermelhos)