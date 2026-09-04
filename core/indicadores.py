"""Indicadores calculados exclusivamente com velas fechadas."""


def ema(valores, periodo):
    """Retorna a série EMA; posições sem dados suficientes recebem None."""
    _validar_periodo(periodo)
    valores = [float(valor) for valor in valores]
    resultado = [None] * len(valores)
    if len(valores) < periodo:
        return resultado

    atual = sum(valores[:periodo]) / periodo
    resultado[periodo - 1] = atual
    multiplicador = 2.0 / (periodo + 1)

    for indice in range(periodo, len(valores)):
        atual = (valores[indice] - atual) * multiplicador + atual
        resultado[indice] = atual
    return resultado


def sma(valores, periodo):
    """Média móvel simples com None antes da primeira janela completa."""
    _validar_periodo(periodo)
    valores = [float(valor) for valor in valores]
    resultado = [None] * len(valores)
    if len(valores) < periodo:
        return resultado
    soma = sum(valores[:periodo])
    resultado[periodo - 1] = soma / periodo
    for indice in range(periodo, len(valores)):
        soma += valores[indice] - valores[indice - periodo]
        resultado[indice] = soma / periodo
    return resultado


def wma(valores, periodo):
    """Média móvel ponderada linear, dando maior peso ao valor recente."""
    _validar_periodo(periodo)
    valores = [float(valor) for valor in valores]
    resultado = [None] * len(valores)
    divisor = periodo * (periodo + 1) / 2
    for indice in range(periodo - 1, len(valores)):
        janela = valores[indice - periodo + 1 : indice + 1]
        resultado[indice] = sum(
            valor * peso for peso, valor in enumerate(janela, start=1)
        ) / divisor
    return resultado


def rsi(fechamentos, periodo=14):
    """RSI de Wilder; posições sem dados suficientes recebem None."""
    _validar_periodo(periodo)
    fechamentos = [float(valor) for valor in fechamentos]
    resultado = [None] * len(fechamentos)
    if len(fechamentos) <= periodo:
        return resultado

    variacoes = [
        fechamentos[indice] - fechamentos[indice - 1]
        for indice in range(1, len(fechamentos))
    ]
    ganhos = [max(variacao, 0.0) for variacao in variacoes]
    perdas = [max(-variacao, 0.0) for variacao in variacoes]

    ganho_medio = sum(ganhos[:periodo]) / periodo
    perda_media = sum(perdas[:periodo]) / periodo
    resultado[periodo] = _valor_rsi(ganho_medio, perda_media)

    for indice in range(periodo + 1, len(fechamentos)):
        ganho_medio = (
            ganho_medio * (periodo - 1) + ganhos[indice - 1]
        ) / periodo
        perda_media = (
            perda_media * (periodo - 1) + perdas[indice - 1]
        ) / periodo
        resultado[indice] = _valor_rsi(ganho_medio, perda_media)
    return resultado


def atr(velas, periodo=14):
    """Average True Range de Wilder para objetos com máxima, mínima e fechamento."""
    _validar_periodo(periodo)
    velas = list(velas)
    resultado = [None] * len(velas)
    if len(velas) < periodo:
        return resultado

    amplitudes = []
    for indice, vela in enumerate(velas):
        if indice == 0:
            amplitude = vela.maxima - vela.minima
        else:
            fechamento_anterior = velas[indice - 1].fechamento
            amplitude = max(
                vela.maxima - vela.minima,
                abs(vela.maxima - fechamento_anterior),
                abs(vela.minima - fechamento_anterior),
            )
        amplitudes.append(amplitude)

    atual = sum(amplitudes[:periodo]) / periodo
    resultado[periodo - 1] = atual
    for indice in range(periodo, len(velas)):
        atual = (atual * (periodo - 1) + amplitudes[indice]) / periodo
        resultado[indice] = atual
    return resultado


def adx(velas, periodo=14):
    """Retorna ADX, +DI e -DI de Wilder usando apenas velas fechadas."""
    _validar_periodo(periodo)
    velas = list(velas)
    quantidade = len(velas)
    serie_adx = [None] * quantidade
    serie_di_mais = [None] * quantidade
    serie_di_menos = [None] * quantidade
    if quantidade <= periodo:
        return serie_adx, serie_di_mais, serie_di_menos

    amplitudes = [0.0] * quantidade
    movimentos_mais = [0.0] * quantidade
    movimentos_menos = [0.0] * quantidade
    for indice in range(1, quantidade):
        vela = velas[indice]
        anterior = velas[indice - 1]
        alta = float(vela.maxima) - float(anterior.maxima)
        baixa = float(anterior.minima) - float(vela.minima)
        movimentos_mais[indice] = alta if alta > baixa and alta > 0 else 0.0
        movimentos_menos[indice] = baixa if baixa > alta and baixa > 0 else 0.0
        amplitudes[indice] = max(
            float(vela.maxima) - float(vela.minima),
            abs(float(vela.maxima) - float(anterior.fechamento)),
            abs(float(vela.minima) - float(anterior.fechamento)),
        )

    tr_suavizado = sum(amplitudes[1 : periodo + 1])
    dm_mais_suavizado = sum(movimentos_mais[1 : periodo + 1])
    dm_menos_suavizado = sum(movimentos_menos[1 : periodo + 1])
    serie_dx = [None] * quantidade

    for indice in range(periodo, quantidade):
        if indice > periodo:
            tr_suavizado = (
                tr_suavizado - tr_suavizado / periodo + amplitudes[indice]
            )
            dm_mais_suavizado = (
                dm_mais_suavizado
                - dm_mais_suavizado / periodo
                + movimentos_mais[indice]
            )
            dm_menos_suavizado = (
                dm_menos_suavizado
                - dm_menos_suavizado / periodo
                + movimentos_menos[indice]
            )

        if tr_suavizado == 0:
            di_mais = 0.0
            di_menos = 0.0
        else:
            di_mais = 100.0 * dm_mais_suavizado / tr_suavizado
            di_menos = 100.0 * dm_menos_suavizado / tr_suavizado
        serie_di_mais[indice] = di_mais
        serie_di_menos[indice] = di_menos
        soma = di_mais + di_menos
        serie_dx[indice] = (
            0.0 if soma == 0 else 100.0 * abs(di_mais - di_menos) / soma
        )

    primeiro_adx = periodo * 2 - 1
    if primeiro_adx >= quantidade:
        return serie_adx, serie_di_mais, serie_di_menos
    serie_adx[primeiro_adx] = sum(
        serie_dx[periodo : primeiro_adx + 1]
    ) / periodo
    for indice in range(primeiro_adx + 1, quantidade):
        serie_adx[indice] = (
            serie_adx[indice - 1] * (periodo - 1) + serie_dx[indice]
        ) / periodo
    return serie_adx, serie_di_mais, serie_di_menos


def bandas_bollinger(valores, periodo=20, desvios=2.0):
    """Retorna bandas superior, média e inferior."""
    import statistics

    _validar_periodo(periodo)
    valores = [float(valor) for valor in valores]
    superior = [None] * len(valores)
    media = [None] * len(valores)
    inferior = [None] * len(valores)
    for indice in range(periodo - 1, len(valores)):
        janela = valores[indice - periodo + 1:indice + 1]
        centro = sum(janela) / periodo
        desvio = statistics.pstdev(janela)
        media[indice] = centro
        superior[indice] = centro + desvios * desvio
        inferior[indice] = centro - desvios * desvio
    return superior, media, inferior


def estocastico(velas, periodo=14):
    """%K estocástico calculado com máximas e mínimas de velas fechadas."""
    _validar_periodo(periodo)
    velas = list(velas)
    resultado = [None] * len(velas)
    for indice in range(periodo - 1, len(velas)):
        janela = velas[indice - periodo + 1:indice + 1]
        maxima = max(vela.maxima for vela in janela)
        minima = min(vela.minima for vela in janela)
        amplitude = maxima - minima
        resultado[indice] = (
            50.0 if amplitude == 0
            else 100.0 * (velas[indice].fechamento - minima) / amplitude
        )
    return resultado


def ultimo_valor_valido(serie):
    for valor in reversed(serie):
        if valor is not None:
            return valor
    return None


def _valor_rsi(ganho_medio, perda_media):
    if perda_media == 0:
        return 100.0 if ganho_medio > 0 else 50.0
    proporcao = ganho_medio / perda_media
    return 100.0 - 100.0 / (1.0 + proporcao)


def _validar_periodo(periodo):
    if not isinstance(periodo, int) or periodo < 1:
        raise ValueError("periodo precisa ser um inteiro maior que zero")
