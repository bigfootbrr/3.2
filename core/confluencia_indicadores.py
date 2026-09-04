"""Confluência transparente de indicadores sobre velas já fechadas."""

from dataclasses import dataclass

from catalogo_indicadores import POR_CODIGO, selecionar_para_regime, validar_selecao
from estrategia_otc_classica import Sinal, _cruzamentos, _cruzamentos_zero, _media_sobre_validos, _subtrair_series
from indicadores import atr, bandas_bollinger, ema, estocastico, rsi, sma, wma
from regime import Regime, classificar_regime


@dataclass(frozen=True)
class DiagnosticoIndicador:
    codigo: str
    nome: str
    direcao: str
    peso: int
    motivo: str


@dataclass(frozen=True)
class ResultadoConfluencia:
    sinal: Sinal
    pontuacao: int
    motivo: str
    regime: str
    indicadores_ativos: tuple
    diagnosticos: tuple


def _diag(codigo, direcao="NEUTRO", peso=0, motivo="sem condição"):
    return DiagnosticoIndicador(codigo, POR_CODIGO[codigo].nome, direcao, peso, motivo)


def _padrao_candle(velas):
    anterior, atual = velas[-2], velas[-1]
    a0, c0, h0, l0 = atual.abertura, atual.fechamento, atual.maxima, atual.minima
    a1, c1, h1, l1 = anterior.abertura, anterior.fechamento, anterior.maxima, anterior.minima
    amplitude = max(h0 - l0, 1e-12)
    corpo = abs(c0 - a0)
    if c1 < a1 and c0 > a0 and c0 > h1:
        return "ALTA", "engolfo de alta"
    if c1 > a1 and c0 < a0 and c0 < l1:
        return "BAIXA", "engolfo de baixa"
    if c0 > a0 and c0 >= h0 - amplitude * .05 and .1 * amplitude < corpo < .4 * amplitude:
        return "ALTA", "martelo de alta"
    if c0 < a0 and c0 <= l0 + amplitude * .05 and .1 * amplitude < corpo < .4 * amplitude:
        return "BAIXA", "estrela/enforcado de baixa"
    if corpo >= amplitude * .90:
        return ("ALTA", "marubozu de alta") if c0 > a0 else ("BAIXA", "marubozu de baixa")
    return "NEUTRO", "nenhum padrão forte"


def analisar_confluencia(velas, timeframe="M1", codigos=None, automatico=True):
    velas = list(velas)
    if len(velas) < 105:
        return ResultadoConfluencia(Sinal.AGUARDAR, 0, f"histórico insuficiente: {len(velas)}/105 velas fechadas", "DADOS_INSUFICIENTES", (), ())
    regime = classificar_regime(velas, timeframe).regime
    ativos = selecionar_para_regime(regime) if automatico else validar_selecao(codigos or ())
    # Memória adaptativa: quando o bot já tem placar suficiente neste
    # timeframe, os dois indicadores com melhor taxa RECENTE entram na
    # confluência (o regime continua definindo a base).
    from memoria_indicadores import JANELA_RECENTE  # evita ciclo de importação
    try:
        from main import memoria_indicadores as _memoria
    except ImportError:
        _memoria = None
    if automatico and _memoria is not None:
        melhores = _memoria.melhores(timeframe, limite=2)
        if melhores:
            ativos = set(ativos) | {item["codigo"] for item in melhores}
    fechamentos = [v.fechamento for v in velas]
    ds = []

    if "ATR" in ativos:
        valores = [x for x in atr(velas, 14)[-50:] if x is not None]
        relativo = valores[-1] / sorted(valores)[len(valores)//2] if valores and valores[len(valores)//2] else 1
        ds.append(_diag("ATR", motivo=f"volatilidade relativa {relativo:.2f}x"))
        if regime == Regime.VOLATILIDADE_ANORMAL:
            return ResultadoConfluencia(Sinal.AGUARDAR, 0, "volatilidade anormal: entrada bloqueada", regime.value, tuple(sorted(ativos)), tuple(ds))
    if "EMA_TENDENCIA" in ativos:
        e9, e21, e100 = ema(fechamentos, 9)[-1], ema(fechamentos, 21)[-1], ema(fechamentos, 100)[-1]
        if e9 > e21 > e100: ds.append(_diag("EMA_TENDENCIA", "ALTA", 2, "EMA 9 > 21 > 100"))
        elif e9 < e21 < e100: ds.append(_diag("EMA_TENDENCIA", "BAIXA", 2, "EMA 9 < 21 < 100"))
        else: ds.append(_diag("EMA_TENDENCIA", motivo="médias sem alinhamento"))
    if "RSI" in ativos:
        valor = rsi(fechamentos, 14)[-1]
        direcao = "ALTA" if valor >= 55 else "BAIXA" if valor <= 45 else "NEUTRO"
        ds.append(_diag("RSI", direcao, 1 if direcao != "NEUTRO" else 0, f"RSI {valor:.1f}"))
    if "MACD" in ativos:
        linha_macd = _subtrair_series(ema(fechamentos, 12), ema(fechamentos, 26))
        sinal_macd = _media_sobre_validos(linha_macd, ema, 9)
        evento_macd = _cruzamentos(linha_macd, sinal_macd)[-1]
        ds.append(_diag(
            "MACD", evento_macd or "NEUTRO", 2 if evento_macd else 0,
            "cruzamento MACD 12/26/9" if evento_macd else "MACD sem cruzamento fechado",
        ))
    if "BOLLINGER" in ativos:
        sup, _, inf = bandas_bollinger(fechamentos)
        direcao = "BAIXA" if fechamentos[-1] >= sup[-1] else "ALTA" if fechamentos[-1] <= inf[-1] else "NEUTRO"
        ds.append(_diag("BOLLINGER", direcao, 1 if direcao != "NEUTRO" else 0, "extremo das bandas" if direcao != "NEUTRO" else "preço dentro das bandas"))
    if "ESTOCASTICO" in ativos:
        valor = estocastico(velas)[-1]
        direcao = "ALTA" if valor <= 20 else "BAIXA" if valor >= 80 else "NEUTRO"
        ds.append(_diag("ESTOCASTICO", direcao, 1 if direcao != "NEUTRO" else 0, f"%K {valor:.1f}"))
    if "PRICE_ACTION" in ativos:
        v = velas[-1]; amplitude = max(v.maxima-v.minima, 1e-12); corpo = abs(v.fechamento-v.abertura)/amplitude
        direcao = "ALTA" if v.fechamento > v.abertura else "BAIXA" if v.fechamento < v.abertura else "NEUTRO"
        peso = 1 if corpo >= .35 and direcao != "NEUTRO" else 0
        ds.append(_diag("PRICE_ACTION", direcao if peso else "NEUTRO", peso, f"corpo {corpo:.0%} da amplitude"))
    if "PADROES_CANDLE" in ativos:
        direcao, motivo = _padrao_candle(velas); ds.append(_diag("PADROES_CANDLE", direcao, 2 if direcao != "NEUTRO" else 0, motivo))
    if "BOMBRIL" in ativos:
        base = sma([v.abertura for v in velas], 2)[-1]; media = sma(fechamentos, 2)[-1]
        direcao = "ALTA" if velas[-1].abertura < base and velas[-1].fechamento > media else "BAIXA" if velas[-1].abertura > base and velas[-1].fechamento < media else "NEUTRO"
        ds.append(_diag("BOMBRIL", direcao, 1 if direcao != "NEUTRO" else 0, "retorno à banda curta" if direcao != "NEUTRO" else "sem retorno à banda"))
    if "BIGFOOT" in ativos:
        dif = _subtrair_series(sma(fechamentos, 1), sma(fechamentos, 34)); sig = _media_sobre_validos(dif, wma, 5); ev = _cruzamentos(dif, sig)[-1]
        ds.append(_diag("BIGFOOT", ev or "NEUTRO", 2 if ev else 0, "cruzamento atual" if ev else "sem cruzamento atual"))
    if "BFT_PANO" in ativos:
        dif = _subtrair_series(ema(fechamentos, 2), ema(fechamentos, 8)); sig = _media_sobre_validos(dif, wma, 6); ev = _cruzamentos_zero(_subtrair_series(dif, sig))[-1]
        ds.append(_diag("BFT_PANO", ev or "NEUTRO", 1 if ev else 0, "confluência PANO opcional" if ev else "PANO neutro — não bloqueia"))
    if "BFT_GAP" in ativos:
        gap = velas[-1].abertura - velas[-2].fechamento
        gap_minimo = 5 / (10 ** 5)
        direcao = "ALTA" if gap >= gap_minimo else "BAIXA" if gap <= -gap_minimo else "NEUTRO"
        ds.append(_diag(
            "BFT_GAP", direcao, 1 if direcao != "NEUTRO" else 0,
            f"gap fechado {gap:+.5f}" if direcao != "NEUTRO" else "sem gap mínimo de 5 pontos",
        ))
    if "BFT_WIN26" in ativos:
        diferenca = _subtrair_series(sma(fechamentos, 1), sma(fechamentos, 34))
        sinal_26 = _media_sobre_validos(diferenca, wma, 4)
        evento_26 = _cruzamentos(diferenca, sinal_26)[-1]
        ds.append(_diag(
            "BFT_WIN26", evento_26 or "NEUTRO", 2 if evento_26 else 0,
            "cruzamento SMA 1/34 + WMA 4" if evento_26 else "sem cruzamento fechado",
        ))
    if "BFT_OB" in ativos:
        evento_ob = _cruzamentos(ema(fechamentos, 3), sma(fechamentos, 6))[-1]
        ds.append(_diag(
            "BFT_OB", evento_ob or "NEUTRO", 2 if evento_ob else 0,
            "cruzamento EMA 3/SMA 6" if evento_ob else "sem cruzamento fechado",
        ))

    alta = sum(d.peso for d in ds if d.direcao == "ALTA")
    baixa = sum(d.peso for d in ds if d.direcao == "BAIXA")
    if alta > baixa:
        direcao, favor, contra = "ALTA", alta, baixa
    elif baixa > alta:
        direcao, favor, contra = "BAIXA", baixa, alta
    else:
        direcao, favor, contra = "AGUARDAR", alta, baixa
    # Normaliza a força para 0..10. Como cada estratégia usa no máximo três
    # módulos, a soma bruta costuma ficar entre 3 e 5 e não deve ser comparada
    # diretamente com o limiar visual de 7/10.
    peso_total = sum(d.peso for d in ds)
    pontos = 0 if peso_total == 0 else min(10, round(10 * favor / peso_total))
    if favor < 3 or favor - contra < 2:
        direcao = "AGUARDAR"
    sinal = Sinal(direcao)
    motivo = f"confluência {alta} alta × {baixa} baixa; PANO é opcional"
    return ResultadoConfluencia(sinal, pontos, motivo, regime.value, tuple(sorted(ativos)), tuple(ds))
