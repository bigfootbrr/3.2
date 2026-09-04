import threading
import time

from dados_mercado import MercadoSimulado
from mercado_aberto_real import MercadoAbertoReal, ErroMercadoAberto
from painel_abas_iq import ATIVOS_MERCADO_ABERTO
from versao import NOME_COMPLETO_APP
from estrategia_otc_classica import analisar_otc_classico
from estrategia_kill_binary import analisar_kill_binary
from confluencia_indicadores import analisar_confluencia
from indicadores import adx as calcular_adx, atr as calcular_atr, ema as calcular_ema, rsi as calcular_rsi
from catalogo_indicadores import PADRAO_MANUAL, validar_selecao
from maquina_operacao import MaquinaOperacao
from modo_operacao import AUTOMATICO_DEMO, AUTOMATICO_REAL, SOMENTE_SINAIS, validar_modo
from simulador_demo import SimuladorDemo
from automatizador_operacao import criar_automatizador_padrao
from politica_operacao_real import criar_estado_padrao, ValidadorOperacao, ConfiguracaoOperacional



# Não representa uma probabilidade calibrada de acerto.
# Para a IQ Option, a regra operacional usada aqui é de confluência mínima de
# 75% e payout acima de 80%, ambos exigidos antes de qualquer ação visual.
PONTUACAO_MINIMA_CONFLUENCIA = 7.5


def confluencia_minima_aprovada(pontuacao):
    """Valida a confluência mínima necessária para operação segura."""
    try:
        return float(pontuacao) >= PONTUACAO_MINIMA_CONFLUENCIA
    except (TypeError, ValueError):
        return False


def avaliar_criterios_clique_automatico(sinal, pontuacao, payout):
    """Valida direção, confluência e payout antes de qualquer clique visual."""
    if sinal not in {"ALTA", "BAIXA"}:
        return False, "sem direção válida"
    if not confluencia_minima_aprovada(pontuacao):
        return False, "confluência abaixo de 75%"
    if payout is None:
        return False, "payout não informado"
    if not 0.0 <= payout <= 1.0:
        return False, "payout fora do intervalo de 0% a 100%"
    if payout <= 0.80:
        return False, "payout abaixo de 80%"
    return True, "direção, confluência e payout aprovados"


def direcao_confirmada_mercado_aberto(sinal, pontuacao):
    """Só publica CALL/PUT quando a combinação atinge a confluência mínima."""
    if not confluencia_minima_aprovada(pontuacao):
        return "AGUARDAR"
    if sinal == "ALTA":
        return "CALL"
    if sinal == "BAIXA":
        return "PUT"
    return "AGUARDAR"


def avaliar_criterios_mercado_aberto(sinal, pontuacao):
    """Valida apenas direção e confluência vindas das velas externas reais.

    Mercado aberto não depende de captura de tela nem de payout visual. A
    confirmação da plataforma e a armação de um único disparo ficam na camada
    da interface, imediatamente antes do clique.
    """
    if sinal not in {"ALTA", "BAIXA"}:
        return False, "sem direção online válida"
    if not confluencia_minima_aprovada(pontuacao):
        return False, "aguardando confluência online de 75%"
    return True, "direção e confluência online aprovadas"


def construir_series_tecnicas(historico, limite=60):
    """Calcula RSI, MACD/sinal e ADX usando somente velas fechadas."""
    velas = list(historico)
    if not velas:
        return ()
    fechamentos = [vela.fechamento for vela in velas]
    serie_rsi = calcular_rsi(fechamentos, 14)
    serie_atr = calcular_atr(velas, 14)
    ema_12 = calcular_ema(fechamentos, 12)
    ema_26 = calcular_ema(fechamentos, 26)
    serie_macd = [
        None if curta is None or longa is None else curta - longa
        for curta, longa in zip(ema_12, ema_26)
    ]
    macd_validos = [valor for valor in serie_macd if valor is not None]
    sinal_validos = calcular_ema(macd_validos, 9)
    serie_sinal = [None] * len(serie_macd)
    indice_valido = 0
    for indice, valor in enumerate(serie_macd):
        if valor is None:
            continue
        serie_sinal[indice] = sinal_validos[indice_valido]
        indice_valido += 1
    serie_adx, serie_di_mais, serie_di_menos = calcular_adx(velas, 14)

    inicio = max(0, len(velas) - limite)
    return tuple(
        {
            "horario": velas[indice].fim.strftime("%H:%M"),
            "rsi": serie_rsi[indice],
            "atr": serie_atr[indice],
            "ema_12": ema_12[indice],
            "ema_26": ema_26[indice],
            "macd": serie_macd[indice],
            "sinal_macd": serie_sinal[indice],
            "histograma_macd": (
                None
                if serie_macd[indice] is None or serie_sinal[indice] is None
                else serie_macd[indice] - serie_sinal[indice]
            ),
            "adx": serie_adx[indice],
            "di_mais": serie_di_mais[indice],
            "di_menos": serie_di_menos[indice],
        }
        for indice in range(inicio, len(velas))
    )


def ordenar_ativos_mercado_aberto(ativo_selecionado):
    """Mantém a análise da sessão restrita ao par Forex escolhido."""
    if ativo_selecionado not in ATIVOS_MERCADO_ABERTO:
        raise ValueError(f"ativo de mercado aberto inválido: {ativo_selecionado}")
    return (ativo_selecionado,)


robo_ativo = False
robo_pausado = False
thread_robo = None
mercado = MercadoSimulado(ticks_por_vela=5, timeframe="M1")
mercados_abertos = []
tipo_mercado_atual = "MERCADO ABERTO"
payout_atual = None
estrategia_atual = "Automático"
recuperacao_ativada = False
modo_operacao_atual = SOMENTE_SINAIS
emergencia_ativa = False
maquina_operacao = MaquinaOperacao()
simulador_demo = SimuladorDemo()
callback_evento = None
historico_visual = ()
ativo_visual_atual = None
timeframe_visual_atual = None
versao_historico_visual = 0
assinatura_historico_visual = None
lock_historico_visual = threading.Lock()
indicadores_automaticos = True
indicadores_selecionados = set(PADRAO_MANUAL)


def definir_configuracao_indicadores(automatico=True, codigos=None):
    """Atualiza a seleção usada pelo motor sem iniciar ou executar operações."""
    global indicadores_automaticos, indicadores_selecionados
    indicadores_automaticos = bool(automatico)
    if codigos is not None:
        indicadores_selecionados = validar_selecao(codigos)
    return indicadores_automaticos, set(indicadores_selecionados)


def atualizar_historico_visual(velas, ativo, timeframe):
    """Recebe um snapshot de velas fechadas lidas visualmente da IQ."""
    global historico_visual, ativo_visual_atual, timeframe_visual_atual
    global versao_historico_visual, assinatura_historico_visual

    velas = tuple(velas)
    if not velas:
        return False

    timeframe = timeframe.upper()
    assinatura = (
        ativo,
        timeframe,
        velas[-1].fim,
    )

    with lock_historico_visual:
        if assinatura == assinatura_historico_visual:
            print(
                f"[BFT VISUAL] mesma vela fechada ignorada | "
                f"{velas[-1].fim:%H:%M} | {ativo} | {timeframe}"
            )
            return True
        historico_visual = velas
        ativo_visual_atual = ativo
        timeframe_visual_atual = timeframe
        assinatura_historico_visual = assinatura
        versao_historico_visual += 1
        
    print(
        f"[BFT VISUAL] {len(velas)} velas recebidas | "
        f"{ativo} | {timeframe} | fechamento {velas[-1].fim:%H:%M} | "
        f"snapshot {versao_historico_visual}"
    )
    return True

def definir_callback_evento(callback):
    """Registra uma saída observacional; nunca executa ação de negociação."""
    global callback_evento
    callback_evento = callback


def atualizar_payout_atual(payout):
    """Atualiza o payout reconhecido na tela sem reiniciar o motor."""
    global payout_atual
    payout_atual = payout


def _emitir_evento(evento):
    if callback_evento is not None:
        callback_evento(evento)


def _estimativa_experimental(pontuacao):
    """Converte a pontuação em força indicativa; não é probabilidade calibrada."""
    return max(0.0, min(1.0, float(pontuacao) / 10.0))


def loop_robo():
    global robo_ativo, robo_pausado

    ciclo = 0
    ultima_versao_visual_analisada = 0
    avisou_espera_visual = False
    while robo_ativo:
        if robo_pausado:
            time.sleep(1)
            continue

        if tipo_mercado_atual == "OTC":
            snapshot = _obter_snapshot_visual(
                mercado.ativo,
                mercado.timeframe,
            )
            if snapshot is None:
                if not avisou_espera_visual:
                    print(
                        "[BFT OTC] Aguardando snapshot visual compatível "
                        f"| {mercado.ativo} | {mercado.timeframe} | SEM ORDENS"
                    )
                    avisou_espera_visual = True
                time.sleep(3)
                continue

            historico_analise, versao = snapshot
            if versao == ultima_versao_visual_analisada:
                time.sleep(3)
                continue

            avisou_espera_visual = False
            ultima_versao_visual_analisada = versao
            _analisar_snapshot_otc(historico_analise, versao)
            time.sleep(3)
            continue

        ciclo += 1
        _atualizar_radar_mercado_aberto(ciclo)
        # M1 só precisa ser atualizado no fechamento de uma nova vela. A fonte
        # pode devolver o mesmo candle entre duas consultas; a interface apenas
        # substitui a linha correspondente no radar.
        for _ in range(60):
            if not robo_ativo or robo_pausado:
                break
            time.sleep(1)

    print("[BFT] Loop encerrado.")


def _atualizar_radar_mercado_aberto(ciclo):
    """Atualiza o Forex real e autoriza somente o par operacional escolhido."""
    for fonte in mercados_abertos:
        if not robo_ativo or robo_pausado:
            return
        try:
            historico = fonte.atualizar()
            resumo = fonte.resumo()
            resultado = analisar_confluencia(
                historico,
                fonte.timeframe,
                indicadores_selecionados,
                indicadores_automaticos,
            )
            print(
                f"[BFT ABERTO] {fonte.ativo} | {resumo['preco']:.5f} | "
                f"{resumo['variacao']:+.2f}% | {resultado.sinal.value} | "
                f"Confluência {resultado.pontuacao}/10 | FONTE REAL"
            )
            ativo_em_operacao = fonte.ativo == mercado.ativo
            criterios_aprovados, motivo_criterios = (
                avaliar_criterios_mercado_aberto(
                    resultado.sinal.value,
                    resultado.pontuacao,
                )
            )
            clique_real_autorizado = bool(
                ativo_em_operacao
                and modo_operacao_atual == AUTOMATICO_REAL
                and criterios_aprovados
            )
            _emitir_evento({
                "tipo": "radar_mercado_aberto",
                "mercado": "MERCADO ABERTO",
                "ativo": fonte.ativo,
                "timeframe": fonte.timeframe,
                "vela": historico[-1].numero,
                "horario": historico[-1].fim.strftime("%H:%M"),
                "preco": resumo["preco"],
                "variacao": resumo["variacao"],
                "sinal": resultado.sinal.value,
                "direcao": direcao_confirmada_mercado_aberto(
                    resultado.sinal.value,
                    resultado.pontuacao,
                ),
                "pontuacao": resultado.pontuacao,
                "confluencia": float(resultado.pontuacao) / 10.0,
                "motivo": resultado.motivo,
                "regime": getattr(resultado, "regime", "—"),
                "indicadores_ativos": getattr(resultado, "indicadores_ativos", ()),
                "diagnosticos": [
                    {
                        "nome": item.nome,
                        "direcao": item.direcao,
                        "peso": item.peso,
                        "motivo": item.motivo,
                    }
                    for item in getattr(resultado, "diagnosticos", ())
                ],
                "velas_grafico": [
                    {
                        "horario": vela.fim.strftime("%H:%M"),
                        "abertura": vela.abertura,
                        "maxima": vela.maxima,
                        "minima": vela.minima,
                        "fechamento": vela.fechamento,
                    }
                    for vela in historico[-30:]
                ],
                "series_tecnicas": construir_series_tecnicas(historico),
                "maxima": max(v.maxima for v in historico[-30:]),
                "suporte": min(v.minima for v in historico[-30:]),
                "resistencia": max(v.maxima for v in historico[-30:]),
                "risco": "1.5% da banca",
                "fonte": "Yahoo Finance",
                "payout": payout_atual,
                "modo_operacao": modo_operacao_atual,
                "execucao_autorizada": clique_real_autorizado,
                "clique_real_autorizado": clique_real_autorizado,
                "clique_demo_autorizado": False,
                "motivo_execucao": (
                    motivo_criterios
                    if ativo_em_operacao and modo_operacao_atual == AUTOMATICO_REAL
                    else "par fora da seleção operacional ou modo somente sinais"
                ),
            })
        except ErroMercadoAberto as erro:
            print(f"[BFT ABERTO] {fonte.ativo} | indisponível: {erro}")
            _emitir_evento({
                "tipo": "radar_mercado_aberto",
                "mercado": "MERCADO ABERTO",
                "ativo": fonte.ativo,
                "timeframe": fonte.timeframe,
                "sinal": "SEM DADOS",
                "pontuacao": 0,
                "confluencia": 0.0,
                "motivo": str(erro),
                "fonte": "indisponível",
            })


def _obter_snapshot_visual(ativo, timeframe):
    with lock_historico_visual:
        if (
            historico_visual
            and ativo_visual_atual == ativo
            and timeframe_visual_atual == timeframe.upper()
        ):
            return historico_visual, versao_historico_visual
    return None


def snapshot_visual_disponivel(ativo, timeframe):
    """Informa à interface se já existe leitura compatível carregada."""
    return _obter_snapshot_visual(ativo, timeframe) is not None


def _analisar_snapshot_otc(historico_analise, versao):
    resultado_demo = simulador_demo.avaliar(historico_analise[-1])
    if resultado_demo is not None:
        resumo_demo = simulador_demo.resumo()
        taxa = resumo_demo["taxa_acerto"]
        print(
            f"[BFT DEMO] {resultado_demo.resultado} | "
            f"{resultado_demo.entrada.direcao} | "
            f"vela {resultado_demo.entrada.expira_em:%H:%M} | "
            f"Placar: {resumo_demo['vitorias']}V/"
            f"{resumo_demo['derrotas']}D/{resumo_demo['empates']}E | "
            f"Taxa observada: {'—' if taxa is None else f'{taxa:.1%}'}"
        )
    vela = historico_analise[-1]
    print(
        f"[BFT VISUAL] Analisando snapshot {versao} | "
        f"Vela fechada {vela.fim:%H:%M} {vela.timeframe} | "
        f"Histórico: {len(historico_analise)} | Fonte: VISUAL | "
        f"Modo: {modo_operacao_atual}"
    )
    if estrategia_atual == "Kill Binary":
        resultado = analisar_kill_binary(historico_analise)
    else:
        resultado = analisar_confluencia(
            historico_analise,
            vela.timeframe,
            indicadores_selecionados,
            indicadores_automaticos,
        )
    entrada_demo = None
    if modo_operacao_atual == AUTOMATICO_DEMO:
        entrada_demo = simulador_demo.registrar(resultado.sinal.value, vela)
        if entrada_demo is not None:
            print(
                f"[BFT DEMO] Entrada hipotética registrada | "
                f"{entrada_demo.direcao} | próxima vela fecha "
                f"{entrada_demo.expira_em:%H:%M} | SEM CLIQUE NA IQ"
            )
    criterios_aprovados, motivo_criterios = avaliar_criterios_clique_automatico(
        resultado.sinal.value,
        resultado.pontuacao,
        payout_atual,
    )
    clique_demo_autorizado = bool(
        entrada_demo is not None
        and criterios_aprovados
        and modo_operacao_atual == AUTOMATICO_DEMO
    )
    clique_real_autorizado = bool(
        criterios_aprovados and modo_operacao_atual == AUTOMATICO_REAL
    )
    execucao_autorizada = clique_demo_autorizado or clique_real_autorizado
    motivo_execucao = (
        motivo_criterios
        if modo_operacao_atual in {AUTOMATICO_DEMO, AUTOMATICO_REAL}
        else "modo Somente Sinais não executa entradas"
    )
    if resultado.sinal.value in {"ALTA", "BAIXA"}:
        transicao = maquina_operacao.receber_sinal(
            vela.ativo, resultado.sinal.value
        )
        if transicao.aceita:
            maquina_operacao.concluir_validacao(
                execucao_autorizada,
                motivo_execucao,
            )
    print(
        f"[BFT OTC] {resultado.sinal.value} | "
        f"Pontuação: {resultado.pontuacao}/10 | {resultado.motivo} | "
        f"Estimativa experimental: "
        f"{_estimativa_experimental(resultado.pontuacao):.0%} (NÃO CALIBRADA) | "
        f"ORDEM: {'AUTORIZADA PELAS TRAVAS' if execucao_autorizada else 'BLOQUEADA'}"
    )
    resumo_demo = simulador_demo.resumo()
    direcao_analise = {
        "ALTA": "CALL / HIGHER",
        "BAIXA": "PUT / LOWER",
        "AGUARDAR": "AGUARDAR",
    }.get(resultado.sinal.value, "AGUARDAR")
    entrada_analise = {
        "ALTA": "Executar CALL / HIGHER após confirmação da vela e payout válido",
        "BAIXA": "Executar PUT / LOWER após confirmação da vela e payout válido",
        "AGUARDAR": "Aguardando confirmação de vela",
    }.get(resultado.sinal.value, "Aguardando confirmação de vela")
    _emitir_evento({
        "tipo": "sinal",
        "mercado": "OTC",
        "ativo": vela.ativo,
        "estrategia": estrategia_atual,
        "timeframe": vela.timeframe,
        "vela": vela.numero,
        "vela_horario": vela.fim.strftime("%H:%M"),
        "sinal": resultado.sinal.value,
        "pontuacao": resultado.pontuacao,
        "confluencia": float(resultado.pontuacao) / 10.0,
        "motivo": resultado.motivo,
        "probabilidade": None,
        "estimativa_experimental": _estimativa_experimental(resultado.pontuacao),
        "payout": payout_atual,
        "execucao_autorizada": execucao_autorizada,
        "motivo_execucao": motivo_execucao,
        "recuperacao_ativada": recuperacao_ativada,
        "modo_operacao": modo_operacao_atual,
        "estado_operacao": maquina_operacao.estado.value,
        "demo_entrada_registrada": entrada_demo is not None,
        "clique_demo_autorizado": clique_demo_autorizado,
        "clique_real_autorizado": clique_real_autorizado,
        "demo_resultado": (
            None if resultado_demo is None else resultado_demo.resultado
        ),
        "demo_resumo": resumo_demo,
        "regime": getattr(resultado, "regime", "—"),
        "direcao": direcao_analise,
        "entrada": entrada_analise,
        "risco": "1.5% da banca",
        "indicadores_ativos": getattr(resultado, "indicadores_ativos", ()),
        "velas_grafico": [
            {
                "horario": item.fim.strftime("%H:%M"),
                "abertura": item.abertura,
                "maxima": item.maxima,
                "minima": item.minima,
                "fechamento": item.fechamento,
            }
            for item in historico_analise[-30:]
        ],
        "series_tecnicas": construir_series_tecnicas(historico_analise),
        "diagnosticos": [
            {
                "nome": item.nome,
                "direcao": item.direcao,
                "peso": item.peso,
                "motivo": item.motivo,
            }
            for item in getattr(resultado, "diagnosticos", ())
        ],
    })


def _obter_historico_analise(ativo, timeframe):
    snapshot = _obter_snapshot_visual(ativo, timeframe)
    if snapshot is not None:
        return snapshot[0], "VISUAL"

    return mercado.obter_historico(), "SIMULADO"

def iniciar_robo(
    banca, entrada, stop_gain, stop_loss, estrategia,
    timeframe="M1", tipo_mercado="MERCADO ABERTO", payout=None,
    ativar_recuperacao=False, modo_operacao=SOMENTE_SINAIS, ativo="SIMULADO",
):
    global robo_ativo, robo_pausado, thread_robo, mercado, mercados_abertos
    global tipo_mercado_atual, payout_atual, estrategia_atual, recuperacao_ativada
    global modo_operacao_atual, emergencia_ativa, maquina_operacao, simulador_demo

    permissao_modo = validar_modo(modo_operacao)
    if not permissao_modo.permitido:
        raise ValueError(permissao_modo.motivo)

    if robo_ativo and robo_pausado:
        robo_pausado = False
        print("[BFT] Robô continuando...")
        return

    if robo_ativo:
        print("[BFT] Robô já está rodando.")
        return

    robo_ativo = True
    robo_pausado = False
    tipo_mercado_atual = tipo_mercado
    payout_atual = payout
    estrategia_atual = estrategia
    recuperacao_ativada = bool(ativar_recuperacao) and tipo_mercado == "OTC"
    modo_operacao_atual = modo_operacao
    emergencia_ativa = False
    maquina_operacao = MaquinaOperacao()
    if tipo_mercado == "MERCADO ABERTO":
        mercados_abertos = [
            MercadoAbertoReal(item, timeframe=timeframe)
            for item in ordenar_ativos_mercado_aberto(ativo)
        ]
        mercado = mercados_abertos[0]
    else:
        mercados_abertos = []
        mercado = MercadoSimulado(
            ativo=ativo, ticks_por_vela=5, timeframe=timeframe
        )

    print("")
    print(f"=== {NOME_COMPLETO_APP} ===")
    print("Robô iniciado")
    print(f"Banca: {banca}")
    print(f"Entrada: {entrada}")
    print(f"Stop Gain: {stop_gain}")
    print(f"Stop Loss: {stop_loss}")
    print(f"Estratégia: {estrategia}")
    print(f"Gráfico: {timeframe}")
    print(f"Mercado: {tipo_mercado}")
    print(f"Ativo da análise: {ativo}")
    print(f"Modo de operação: {modo_operacao_atual}")
    if tipo_mercado == "MERCADO ABERTO":
        print(
            f"Fonte: YAHOO FINANCE — "
            f"{len(ATIVOS_MERCADO_ABERTO)} PARES FOREX REAIS"
        )
    elif tipo_mercado == "OTC":
        print("Fonte: LEITURA VISUAL DA CORRETORA")
    else:
        print("Fonte: SIMULADA")
    print("==================")
    print("")

    thread_robo = threading.Thread(target=loop_robo, daemon=True)
    thread_robo.start()


def acionar_parada_emergencia():
    global robo_ativo, robo_pausado, emergencia_ativa, maquina_operacao
    emergencia_ativa = True
    robo_ativo = False
    robo_pausado = False
    maquina_operacao.emergencia()
    print("[BFT] PARADA DE EMERGÊNCIA ACIONADA — PROCESSAMENTO INTERROMPIDO")


def pausar_robo():
    global robo_pausado

    if not robo_ativo:
        print("[BFT] O robô não está rodando.")
        return

    robo_pausado = True
    print("[BFT] Robô pausado.")


def parar_robo():
    global robo_ativo, robo_pausado

    if not robo_ativo:
        print("[BFT] O robô já está parado.")
        return

    robo_ativo = False
    robo_pausado = False
    print("[BFT] Parando robô...")
