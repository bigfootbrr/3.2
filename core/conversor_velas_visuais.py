from datetime import datetime, timedelta

from dados_mercado import Vela


def converter_velas_visuais(velas_visuais, ativo, timeframe, referencia=None):
    velas_visuais = list(velas_visuais)
    if not velas_visuais:
        return ()

    maior_y = max(
        max(
            vela.abertura_y,
            vela.maxima_y,
            vela.minima_y,
            vela.fechamento_y,
        )
        for vela in velas_visuais
    )

    base = float(maior_y + 1000)

    minutos = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
    }.get(timeframe.upper(), 1)

    agora = referencia or datetime.now()
    # A última vela fechada termina no marco do timeframe. Assim, capturas
    # feitas em :00 e :30 dentro do mesmo minuto apontam para a mesma vela M1.
    fim_ultima = agora.replace(
        minute=(agora.minute // minutos) * minutos,
        second=0,
        microsecond=0,
    )
    total = len(velas_visuais)

    convertidas = []

    for indice, vela_visual in enumerate(velas_visuais, start=1):
        distancia = total - indice
        fim = fim_ultima - timedelta(minutes=distancia * minutos)
        inicio = fim - timedelta(minutes=minutos)

        abertura = base - vela_visual.abertura_y
        maxima = base - vela_visual.maxima_y
        minima = base - vela_visual.minima_y
        fechamento = base - vela_visual.fechamento_y

        convertidas.append(
            Vela(
                ativo=ativo,
                timeframe=timeframe.upper(),
                numero=indice,
                abertura=float(abertura),
                maxima=float(maxima),
                minima=float(minima),
                fechamento=float(fechamento),
                inicio=inicio,
                fim=fim,
            )
        )

    return tuple(convertidas)
