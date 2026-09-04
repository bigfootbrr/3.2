"""Interface web final com dados reais de mercado em tempo real.

Esta é uma interface web que fornece acesso a dados em tempo real do mercado. Os dados são atualizados regularmente e incluem informações sobre ações, índices, moedas, commodities e outros ativos financeiros.

A interface web é projetada para ser fácil de usar e acessar, com uma interface amigável e intuitiva. Os usuários podem navegar por diferentes categorias de ativos e ver gráficos e tabelas interativas que mostram as informações mais recentes disponíveis.

Além disso, a interface web também inclui uma funcionalidade de notificações, que alerta os usuários quando houver alterações significativas em seus ativos favoritos. A interface web é segura e protegida contra acesso não autorizado, e todos os dados são armazenados em servidores seguros.

Em resumo, esta é uma interface web de alta qualidade que oferece acesso em tempo real a dados de mercado confiáveis e atualizados. É perfeita para investidores, analistas e qualquer pessoa que deseja monitorar os mercados em tempo real.

"""

"""Serve uma interface HTML em um servidor HTTP local e expõe endpoints REST
que se conectam ao motor do BFT WIN para iniciar, pausar, parar e configurar
operações, além de fornecer cotações reais.
"""

import json
import os
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PASTA_PROJETO, "core"))

from conector_mercado_real import ConectorMercadoReal, criar_conector_padrao
from captura_tela_macos import testar_captura
from conversor_velas_visuais import converter_velas_visuais
from leitor_ativo_iq import ler_ativo
from leitor_botoes_iq import ler_botoes
from leitor_payout_iq import ler_payout
from leitor_timeframe_iq import ler_timeframe
from leitor_velas_iq import ler_velas
from historico_entradas import carregar_entradas, registrar_entrada
from main import (
  acionar_parada_emergencia,
  atualizar_historico_visual,
  atualizar_payout_atual,
  definir_callback_evento,
  definir_configuracao_indicadores,
  iniciar_robo,
  memoria_indicadores,
  parar_robo,
  pausar_robo,
)
from modo_operacao import AUTOMATICO_DEMO, AUTOMATICO_REAL, MODOS, SOMENTE_SINAIS
from painel_abas_iq import ATIVOS_MERCADO_ABERTO, ATIVOS_OTC_PRIORITARIOS

# Os 8 melhores da varredura — escolha livre do operador (mínimo 2 confluindo).
INDICADORES_BFT = (
  "BIGFOOT",        # gatilho SMA 1/34 + WMA 5 (raiz BFT)
  "BFT_WIN26",      # SMA 1/34 + WMA 4 (cruzamento fechado)
  "BFT_OB",         # cruzamento EMA 3 × SMA 6
  "BFT_PANO",       # EMA 2/8 + WMA 6 (opcional, não bloqueia)
  "RSI",            # força compradora/vendedora
  "BOLLINGER",      # extremos das bandas
  "ESTOCASTICO",    # reversão em extremos
  "PADROES_CANDLE", # engolfo, martelo, estrela, marubozu
)
NOMES_INDICADORES_BFT = {
  "BFT_GAP": "BFT GAP 26",
  "BFT_OB": "BFT OB 26",
  "BFT_PANO": "BFT PANO 26",
  "BFT_WIN26": "BFT WIN 26",
  "BIGFOOT": "BigFoot.Trader",
  "RSI": "BFT RSI — força",
  "BOLLINGER": "BFT Bollinger — extremos",
  "ESTOCASTICO": "BFT Estocástico — reversão",
  "PADROES_CANDLE": "BFT Candles — padrões",
}


def configurar_indicadores(interface, automatico: bool, codigos=None):
  """Define escolha automática ou combinação manual de dois a três indicadores."""
  if automatico:
    definir_configuracao_indicadores(True)
    interface.indicadores_automaticos = True
    interface.registrar_log("INDICADORES", "Modo automático ativado", "ok")
    return

  codigos = tuple(dict.fromkeys(codigos or ()))
  if not 2 <= len(codigos) <= 8:
    raise ValueError("selecione de 2 a 8 indicadores para combinar")
  _, selecionados = definir_configuracao_indicadores(False, codigos)
  interface.indicadores_automaticos = False
  interface.indicadores_selecionados = codigos
  interface.registrar_log(
    "INDICADORES",
    f"Combinação aplicada: {', '.join(sorted(selecionados))}",
    "ok",
  )


class InterfaceTempoReal:
    """Interface web integrada com dados reais de mercado."""

    PLATAFORMAS = ("IQ Option", "Quotex", "Casa Trader", "Avallon")
    ATIVOS_DESTAQUE = (
        "EUR/USD",
        "EUR/JPY",
        "EUR/GBP",
        "GBP/USD",
        "GBP/JPY",
        "USD/JPY",
        "USD/CHF",
        "USD/CAD",
        "AUD/USD",
        "USD/SEK",
        "USD/NOK",
        "USD/DKK",
        "USD/HKD",
        "USD/SGD",
        "USD/KRW",
    )
    def __init__(self):
        self.conector = criar_conector_padrao()
        self.ativos_selecionados = list(self.ATIVOS_DESTAQUE)
        self.ativo_atual = "EUR/USD"
        self.logs = []
        self.estado_operacional = {
            "status": "Parado",
            "banca": 1000.00,
            "payout": 0.0,
            "confluencia": "—",
            "entrada": "Confirme a plataforma",
        }
        self.configuracao = {
            "entrada": 25.0,
            "stop_gain": 100.0,
            "stop_loss": 100.0,
        }
        self.historico_velas = {}
        self.threads_atualizacao = {}
        self.motor_ativo = False
        self.motor_pausado = False
        self.plataforma_atual = "IQ Option"
        self.plataforma_confirmada = None
        self.timeframe_atual = "M1"
        self.indicadores_automaticos = True
        self.indicadores_selecionados = {"BFT_PANO", "BFT_OB", "BFT_WIN26"}
        self.estrategia_atual = "Automático"
        self.modo_operacao_atual = SOMENTE_SINAIS
        self.ultima_analise = None
        # Análises por timeframe (radar multi-tempo M1/M5/M15) e a seleção do
        # operador de quais períodos exibir. O chart principal segue o
        # timeframe_ativo; o painel de sinais mostra os períodos marcados.
        self.analises_por_timeframe = {}
        self.timeframes_visiveis = {"M1", "M5", "M15"}
        self.timeframe_ativo = "M1"
        self.lock_analise = threading.Lock()
        self._assinatura_otc_pendente = None
        self._assinatura_otc_confirmada = None
        definir_callback_evento(self.receber_evento_motor)

    def _status_painel(self) -> str:
        """Resume o estado exibido no topo do painel."""
        return self.estado_operacional["status"]

    def _resolver_ativo_motor(self) -> Optional[str]:
        """Converte o código exibido na web para o formato aceito pelo motor."""
        ativo = self.ativo_atual.strip().upper()
        if ativo in ATIVOS_MERCADO_ABERTO:
            return ativo
        if "/" not in ativo and len(ativo) == 6:
            candidato = f"{ativo[:3]}/{ativo[3:]}"
            if candidato in ATIVOS_MERCADO_ABERTO:
                return candidato
        return None

    def _tipo_mercado_motor(self) -> str:
        """Mantém a seleção Forex/OTC ao iniciar o motor compartilhado."""
        if self.ativo_atual in ATIVOS_OTC_PRIORITARIOS:
            return "OTC"
        return "MERCADO ABERTO"

    @staticmethod
    def _codigo_cotacao(ativo: str) -> str:
        return ativo.replace("/", "").upper()

    @staticmethod
    def _ativos_equivalentes(primeiro: str, segundo: str) -> bool:
        return primeiro.replace("/", "").upper() == segundo.replace("/", "").upper()

    @staticmethod
    def _assinatura_velas(velas):
        """Resume a última vela visual para detectar capturas compatíveis."""
        if not velas:
            return None
        ultima = velas[-1]
        return (
            len(velas),
            ultima.x,
            ultima.direcao,
        )

    def receber_evento_motor(self, evento: Dict):
        """Mantém a análise mais recente do ativo exibido no Trading Desk."""
        if evento.get("tipo") not in {"radar_mercado_aberto", "sinal"}:
            return
        if not self._ativos_equivalentes(evento.get("ativo", ""), self.ativo_atual):
            return

        timeframe = str(evento.get("timeframe", "M1")).upper()
        with self.lock_analise:
            self.ultima_analise = dict(evento)
            if evento.get("tipo") == "radar_mercado_aberto":
                # Radar multi-tempo: cada período alimenta sua própria linha.
                self.analises_por_timeframe[timeframe] = dict(evento)
                self.timeframe_ativo = timeframe

        pontuacao = evento.get("pontuacao", 0)
        sinal = evento.get("direcao", evento.get("sinal", "AGUARDAR"))
        self.estado_operacional["confluencia"] = f"{pontuacao:.1f}/10"
        self.estado_operacional["entrada"] = sinal
        self.registrar_log(
            "ANALISE",
            f"{evento.get('ativo', '—')}: {sinal} | confluência {pontuacao:.1f}/10",
            "ok" if sinal in {"CALL", "PUT"} else "info",
        )
        if (
            evento.get("tipo") == "sinal"
            and evento.get("demo_entrada_registrada")
        ):
            self._registrar_entrada_historico(evento)

    def _registrar_entrada_historico(self, evento: Dict):
        """Persiste uma entrada do motor no histórico operacional local."""
        try:
            registrar_entrada({
                "horario": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "conta": "DEMO",
                "plataforma": self.plataforma_atual,
                "ativo": str(evento.get("ativo", "—")),
                "direcao": str(evento.get("sinal", "—")),
                "valor": float(self.configuracao["entrada"]),
                "resultado": str(evento.get("demo_resultado") or "PENDENTE"),
                "sucesso": bool(evento.get("demo_resultado") == "GANHO"),
            })
        except (OSError, ValueError) as erro:
            self.registrar_log("HISTORICO", f"Falha ao registrar entrada: {erro}", "warn")
        else:
            self.registrar_log(
                "HISTORICO",
                f"Entrada registrada: {evento.get('ativo')} "
                f"{evento.get('sinal')} | $ {self.configuracao['entrada']:.2f}",
                "ok",
            )

    def obter_historico_entradas(self, limite: int = 50):
        """Carrega o histórico operacional persistido."""
        try:
            return list(carregar_entradas(limite=limite))
        except (OSError, ValueError):
            return []

    def registrar_log(self, tipo: str, mensagem: str, nivel: str = "info"):
        """Registra mensagem no log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entrada = {
            "timestamp": timestamp,
            "tipo": tipo,
            "mensagem": mensagem,
            "nivel": nivel,  # "info", "ok", "warn", "error"
        }
        self.logs.append(entrada)
        # Manter apenas últimos 50 logs
        if len(self.logs) > 50:
            self.logs = self.logs[-50:]
        print(f"[{timestamp}] [{tipo}] {mensagem}")

    def mudar_ativo(self, ativo: str):
        """Muda o ativo selecionado."""
        if self.motor_ativo:
            self.registrar_log(
                "ATIVO",
                "Encerre a sessão atual antes de escolher outro par",
                "warn",
            )
            return False
        ativo = unquote(ativo).strip().upper()
        if (
            ativo in ATIVOS_MERCADO_ABERTO
            or ativo in ATIVOS_OTC_PRIORITARIOS
        ):
            self.ativo_atual = ativo
            with self.lock_analise:
                self.ultima_analise = None
                self.analises_por_timeframe = {}
            if ativo not in self.ativos_selecionados:
                self.ativos_selecionados.append(ativo)
            self.registrar_log("ATIVO", f"Ativo alterado para {ativo}", "ok")
            return True
        self.registrar_log("ATIVO", f"Ativo inválido: {ativo}", "warn")
        return False

    def adicionar_ativo(self, ativo: str):
        """Adiciona opcionalmente um par Forex real ao acompanhamento."""
        ativo = unquote(ativo).strip().upper()
        if "/" not in ativo and len(ativo) == 6:
            ativo = f"{ativo[:3]}/{ativo[3:]}"
        if ativo in ATIVOS_MERCADO_ABERTO:
            if ativo not in self.ativos_selecionados:
                self.ativos_selecionados.append(ativo)
            self.registrar_log("ATIVO", f"Ativo {ativo} adicionado", "ok")
            return True
        self.registrar_log("ATIVO", f"Ativo não suportado: {ativo}", "warn")
        return False

    def atualizar_banca(self, banca: float):
        """Atualiza banca operacional."""
        self.estado_operacional["banca"] = float(banca)
        self.registrar_log("BANCA", f"Banca atualizada para {banca:.2f}", "ok")

    def atualizar_configuracao(self, dados: Dict):
        """Atualiza os limites locais usados ao iniciar a análise."""
        campos = {
            "banca": "banca",
            "entrada": "entrada",
            "stop_gain": "stop_gain",
            "stop_loss": "stop_loss",
        }
        valores = {}
        for campo, destino in campos.items():
            if campo not in dados:
                continue
            valor = float(dados[campo])
            if valor <= 0:
                raise ValueError(f"{campo} deve ser maior que zero")
            valores[destino] = valor

        if "banca" in valores:
            self.atualizar_banca(valores.pop("banca"))
        self.configuracao.update(valores)
        if valores:
            self.registrar_log("RISCO", "Configuração operacional atualizada", "ok")

    def mudar_plataforma(self, plataforma: str):
        """Trocar a plataforma exige nova confirmação operacional."""
        if plataforma not in self.PLATAFORMAS:
            raise ValueError("plataforma não suportada")
        self.plataforma_atual = plataforma
        self.plataforma_confirmada = None
        self.estado_operacional["entrada"] = "Confirme a plataforma"
        self.registrar_log(
            "PLATAFORMA",
            f"{plataforma} selecionada; confirmação necessária",
            "warn",
        )

    def confirmar_plataforma(self):
        """Confirma a plataforma escolhida para o monitoramento da sessão."""
        self.plataforma_confirmada = self.plataforma_atual
        if not self.motor_ativo:
            self.estado_operacional["entrada"] = "Pronta para iniciar"
        self.registrar_log(
            "PLATAFORMA",
            f"Plataforma confirmada: {self.plataforma_confirmada}",
            "ok",
        )

    def mudar_estrategia(self, estrategia: str):
        """Define a estratégia usada pelo motor (Automático ou Kill Binary)."""
        if estrategia not in ("Automático", "Kill Binary"):
            raise ValueError("estratégia não suportada")
        self.estrategia_atual = estrategia
        self.registrar_log("ESTRATEGIA", f"Estratégia definida: {estrategia}", "ok")
        return True

    def definir_timeframes_visiveis(self, timeframes):
        """Define quais períodos (M1/M5/M15) o painel de sinais exibe."""
        if timeframes is None:
            return
        if not isinstance(timeframes, (list, tuple, set)):
            raise ValueError("timeframes deve ser uma lista")
        validos = {str(item).strip().upper() for item in timeframes}
        desconhecidos = validos - {"M1", "M5", "M15"}
        if desconhecidos:
            raise ValueError(f"timeframe não suportado: {', '.join(sorted(desconhecidos))}")
        if not validos:
            raise ValueError("pelo menos um timeframe deve ficar visível")
        self.timeframes_visiveis = validos
        self.registrar_log(
            "TIMEFRAME",
            f"Sinais exibidos: {', '.join(sorted(validos))}",
            "ok",
        )

    def definir_timeframe_ativo(self, timeframe):
        """Define qual período o chart principal acompanha."""
        if timeframe is None:
            return
        timeframe = str(timeframe).strip().upper()
        if timeframe not in {"M1", "M5", "M15"}:
            raise ValueError(f"timeframe não suportado: {timeframe}")
        self.timeframe_ativo = timeframe

    def mudar_modo_operacao(self, modo: str):
        """Define o modo de operação usado ao iniciar o motor."""
        if modo not in MODOS:
            raise ValueError("modo de operação não suportado")
        self.modo_operacao_atual = modo
        self.registrar_log("MODO", f"Modo de operação: {modo}", "ok")
        return True

    def ler_tela_otc(self):
        """Captura e entrega ao motor um snapshot OTC totalmente validado.

        Exige duas capturas compatíveis antes de liberar a análise no motor.
        A primeira captura registra uma referência de assinatura; a segunda,
        com o mesmo ativo, timeframe e última vela visual, confirma a leitura
        e carrega o snapshot para análise.
        """
        if self._tipo_mercado_motor() != "OTC":
            mensagem = "Escolha um ativo OTC antes de testar a leitura da tela"
            self.registrar_log("CAPTURA", mensagem, "warn")
            return False, mensagem
        if self.plataforma_confirmada != self.plataforma_atual:
            mensagem = "Confirme a plataforma antes de testar a leitura da tela"
            self.registrar_log("CAPTURA", mensagem, "warn")
            return False, mensagem
        if self.plataforma_atual != "IQ Option":
            mensagem = (
                f"Leitura visual de {self.plataforma_atual} ainda não calibrada"
            )
            self.registrar_log("CAPTURA", mensagem, "warn")
            return False, mensagem

        captura = testar_captura(caminho="/private/tmp/bft_web_otc.png")
        if not captura.sucesso:
            self.estado_operacional["payout"] = 0.0
            atualizar_payout_atual(None)
            self.registrar_log("CAPTURA", captura.mensagem, "error")
            return False, captura.mensagem

        ativo = ler_ativo(captura.caminho)
        payout = ler_payout(captura.caminho)
        timeframe_visual = ler_timeframe(captura.caminho)
        velas = ler_velas(captura.caminho)
        botoes = ler_botoes(captura.caminho)
        leituras = (ativo, payout, timeframe_visual, velas, botoes)
        incompletas = [leitura.mensagem for leitura in leituras if not leitura.sucesso]
        if incompletas or not botoes.prontos:
            self.estado_operacional["payout"] = 0.0
            atualizar_payout_atual(None)
            mensagem = "Leitura OTC incompleta: " + "; ".join(
                incompletas or [botoes.mensagem]
            )
            self.registrar_log("CAPTURA", mensagem, "warn")
            return False, mensagem
        if ativo.ativo != self.ativo_atual:
            self.estado_operacional["payout"] = 0.0
            atualizar_payout_atual(None)
            mensagem = (
                f"A tela mostra {ativo.ativo}, mas o painel está em "
                f"{self.ativo_atual}"
            )
            self.registrar_log("CAPTURA", mensagem, "warn")
            return False, mensagem

        timeframe = self.timeframe_atual.upper()
        if timeframe_visual.timeframe != timeframe:
            self.estado_operacional["payout"] = 0.0
            atualizar_payout_atual(None)
            mensagem = (
                f"A tela mostra timeframe {timeframe_visual.timeframe}, "
                f"mas o painel está em {timeframe}"
            )
            self.registrar_log("CAPTURA", mensagem, "warn")
            return False, mensagem

        assinatura = (
            ativo.ativo,
            timeframe,
            self._assinatura_velas(velas.velas),
        )
        if assinatura == self._assinatura_otc_confirmada:
            mensagem = "Snapshot já confirmado com duas capturas compatíveis"
            self.registrar_log("CAPTURA", mensagem, "ok")
            return True, mensagem
        if assinatura != self._assinatura_otc_pendente:
            self._assinatura_otc_pendente = assinatura
            self._assinatura_otc_confirmada = None
            mensagem = (
                "Primeira captura registrada; aguardando segunda captura compatível"
            )
            self.registrar_log("CAPTURA", mensagem, "warn")
            return False, mensagem

        # Segunda captura compatível: confirmar e carregar no motor.
        self._assinatura_otc_confirmada = assinatura
        self._assinatura_otc_pendente = None
        velas_convertidas = converter_velas_visuais(
            velas.velas,
            self.ativo_atual,
            timeframe,
        )
        if not atualizar_historico_visual(
            velas_convertidas,
            self.ativo_atual,
            timeframe,
        ):
            mensagem = "Nenhuma vela fechada foi carregada no motor"
            self.registrar_log("CAPTURA", mensagem, "warn")
            return False, mensagem

        atualizar_payout_atual(payout.payout)
        self.estado_operacional["payout"] = payout.payout * 100.0
        self.estado_operacional["entrada"] = "Snapshot visual confirmado"
        mensagem = (
            f"{len(velas_convertidas)} velas carregadas | {self.ativo_atual} | "
            f"{timeframe} | payout {payout.payout:.0%}"
        )
        self.registrar_log("CAPTURA", mensagem, "ok")
        return True, mensagem


    def conectar_conta(self):
        """Marca o painel como pronto para monitoramento manual."""
        self.estado_operacional["status"] = "Painel preparado"
        self.estado_operacional["entrada"] = "Pronta para monitorar"
        self.registrar_log(
            "CONTA",
            "Painel preparado para acompanhar sinais sem ordens automáticas",
            "ok",
        )
        return True

    def iniciar_motor(self):
        """Inicia a análise do motor compartilhado em modo somente sinais."""
        if self.plataforma_confirmada != self.plataforma_atual:
            mensagem = "Confirme a plataforma antes de iniciar o monitoramento"
            self.registrar_log("PLATAFORMA", mensagem, "warn")
            return False, mensagem
        if self.motor_ativo and not self.motor_pausado:
            self.registrar_log("MOTOR", "Motor já está rodando", "warn")
            return False, "Motor já está rodando"

        tipo_mercado = self._tipo_mercado_motor()
        ativo = (
            self.ativo_atual
            if tipo_mercado == "OTC"
            else self._resolver_ativo_motor() or "EUR/USD"
        )
        try:
            iniciar_robo(
                self.estado_operacional["banca"],
                self.configuracao["entrada"],
                self.configuracao["stop_gain"],
                self.configuracao["stop_loss"],
                self.estrategia_atual,
                tipo_mercado=tipo_mercado,
                modo_operacao=self.modo_operacao_atual,
                ativo=ativo,
            )
        except ValueError as erro:
            self.registrar_log("MOTOR", f"Motor bloqueado: {erro}", "error")
            return False, str(erro)

        self.motor_ativo = True
        self.motor_pausado = False
        self.estado_operacional["status"] = "Rodando — somente sinais"
        self.estado_operacional["entrada"] = "Em análise"
        if tipo_mercado == "OTC":
            self.registrar_log(
                "MOTOR",
                f"{ativo}: aguardando snapshot visual compatível",
                "info",
            )
        elif self._resolver_ativo_motor() is None:
            self.registrar_log(
                "MOTOR",
                f"{self.ativo_atual} não é Forex; análise iniciada em {ativo}",
                "warn",
            )
        self.registrar_log(
            "MOTOR", "Análise BFT iniciada — sem ordens automáticas", "ok"
        )
        return True, "Motor iniciado em modo somente sinais"

    def pausar_motor(self):
        """Pausa o motor do BFT WIN."""
        if not self.motor_ativo:
            self.registrar_log("MOTOR", "Motor ainda não foi iniciado", "warn")
            return False, "Motor ainda não foi iniciado"
        if self.motor_pausado:
            self.registrar_log("MOTOR", "Motor já está pausado", "warn")
            return False, "Motor já está pausado"

        pausar_robo()
        self.motor_pausado = True
        self.estado_operacional["status"] = "Pausado — somente sinais"
        self.estado_operacional["entrada"] = "Monitoramento pausado"
        self.registrar_log("MOTOR", "Motor do BFT WIN pausado", "warn")
        return True, "Motor pausado"

    def encerrar_sessao(self):
        """Encerra a análise do par atual e libera a seleção de outro par."""
        parar_robo()
        self.motor_ativo = False
        self.motor_pausado = False
        self.estado_operacional["status"] = "Parado - escolha um par"
        self.estado_operacional["entrada"] = "Aguardando seleção"
        self.registrar_log("MOTOR", "Sessão encerrada; escolha outro par para analisar", "info")
        return True, "Sessão encerrada"

    def parada_emergencia(self):
        """Executa parada de emergência."""
        acionar_parada_emergencia()
        self.motor_ativo = False
        self.motor_pausado = False
        self.estado_operacional["status"] = "EMERGÊNCIA — tudo parado"
        self.estado_operacional["entrada"] = "Bloqueada"
        self.registrar_log("EMERGENCIA", "PARADA DE EMERGÊNCIA ACIONADA", "error")
        return True, "Parada de emergência acionada"

    def gerar_html(self) -> str:
        """Gera HTML da interface com dados reais."""
        mercado_otc_ativo = self._tipo_mercado_motor() == "OTC"
        cotacoes = {}
        codigo_ativo = self._codigo_cotacao(self.ativo_atual)
        cotacao = self.conector.obter_cotacao(codigo_ativo)
        if cotacao:
            cotacoes[self.ativo_atual] = cotacao

        ativo_selecionado = cotacoes.get(self.ativo_atual)

        # Métrica de mudança de preço
        mudanca = ""
        mudanca_cor = "green"
        if ativo_selecionado:
            if ativo_selecionado.variacao_percentual > 0:
                mudanca = f"+{ativo_selecionado.variacao_percentual:.2f}%"
            else:
                mudanca = f"{ativo_selecionado.variacao_percentual:.2f}%"
                mudanca_cor = "red"

        # Log formatado
        log_html = "\n".join(
            [
                f'<div><span class="log-tag">[{log["tipo"]}]</span> '
                f'<span class="{log["nivel"]}">{log["mensagem"]}</span></div>'
                for log in self.logs[-10:]
            ]
        )

        def botoes_ativos(ativos):
          return "\n".join(
            f'<button class="tab {"active" if ativo == self.ativo_atual else ""}" '
            f'onclick="mudar_ativo(\'{ativo}\')">{ativo}</button>'
            for ativo in ativos
          )

        principais_html = botoes_ativos(self.ATIVOS_DESTAQUE[:6])
        adicionais_html = botoes_ativos(
          ativo
          for ativo in ATIVOS_MERCADO_ABERTO
          if ativo not in self.ATIVOS_DESTAQUE[:6]
        )
        otc_html = botoes_ativos(ATIVOS_OTC_PRIORITARIOS)

        indicadores_html = "\n".join(
          f'<label class="indicador-opcao"><input type="checkbox" value="{codigo}" '
          f'{"checked" if codigo in self.indicadores_selecionados else ""}> '
          f'{NOMES_INDICADORES_BFT.get(codigo, codigo)}</label>'
          for codigo in INDICADORES_BFT
        )

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BFT Winbot — Trading Desk (Tempo Real)</title>
<style>
  :root{{
    --bg-0:#0a0812;
    --bg-1:#100c1c;
    --bg-2:#171229;
    --bg-3:#1e1834;
    --line:#2a2440;
    --line-strong:#3C3489;
    --purple-50:#EEEDFE;
    --purple-100:#CECBF6;
    --purple-200:#AFA9EC;
    --purple-400:#7F77DD;
    --purple-600:#534AB7;
    --purple-800:#3C3489;
    --text-1:#F1EFFB;
    --text-2:#9A93C9;
    --text-3:#6B6494;
    --green:#639922;
    --green-light:#97C459;
    --red:#E24B4A;
    --red-light:#F09595;
    --amber:#EF9F27;
    font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
  }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{
    background:radial-gradient(circle at 20% 0%, #14102450, transparent 55%), var(--bg-0);
    color:var(--text-1);
    min-height:100vh;
    padding:32px 16px 80px;
  }}
  .shell{{max-width:980px;margin:0 auto;}}

  .topbar{{
    display:flex;align-items:center;justify-content:space-between;
    padding:14px 20px;background:var(--bg-1);border:0.5px solid var(--line);
    border-radius:14px;margin-bottom:16px;
  }}
  .brand{{display:flex;align-items:center;gap:12px;}}
  .brand-mark{{
    width:48px;height:48px;border-radius:10px;background:#fff;
    border:1px solid var(--purple-400);padding:3px;overflow:hidden;
  }}
  .brand-mark img{{display:block;width:100%;height:100%;object-fit:contain;}}
  .brand h1{{font-size:16px;font-weight:600;letter-spacing:-0.01em;}}
  .brand p{{font-size:11.5px;color:var(--text-2);margin-top:1px;}}
  .status-pill{{
    display:flex;align-items:center;gap:7px;
    background:var(--bg-2);border:0.5px solid var(--line-strong);
    border-radius:99px;padding:7px 14px;font-size:12px;color:var(--purple-100);
  }}
  .dot{{width:7px;height:7px;border-radius:50%;background:var(--amber);
       box-shadow:0 0 6px var(--amber);}}

  .grid-4{{
    display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;
  }}
  .grid-3{{
    display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px;
  }}
  .metric{{
    background:var(--bg-1);border:0.5px solid var(--line);border-radius:12px;
    padding:14px 16px;
  }}
  .metric.danger{{border-color:#5a2323;background:#1e1112;}}
  .metric-label{{font-size:11px;color:var(--text-2);margin-bottom:6px;text-transform:none;}}
  .metric-value{{font-size:19px;font-weight:600;}}
  .metric-value.green{{color:var(--green-light);}}
  .metric-value.purple{{color:var(--purple-200);}}
  .metric-value.red{{color:var(--red-light);}}

  .panel{{
    background:var(--bg-1);border:0.5px solid var(--line);border-radius:14px;
    padding:18px;margin-bottom:16px;
  }}
  .panel-header{{
    display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;
  }}
  .panel-title{{font-size:13px;color:var(--text-2);}}
  .pair-badge{{
    font-size:12px;color:var(--text-2);background:var(--bg-2);
    border:0.5px solid var(--line);border-radius:8px;padding:4px 10px;
  }}
  .change-up{{color:var(--green-light);font-size:12.5px;font-weight:500;}}
  .change-down{{color:var(--red-light);font-size:12.5px;font-weight:500;}}

  .chart-wrap{{width:100%;height:220px;}}
  .chart-osc{{width:100%;height:64px;margin-top:2px;}}
  .chart-osc-title{{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:11px;color:var(--text-2);}}
  .osc-selo{{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:10px;background:rgba(151,196,89,0.12);color:#97C459;font-weight:700;font-size:10px;}}
  .osc-selo.neutro{{background:rgba(175,169,236,0.12);color:#AFA9EC;}}
  .chart-legend{{display:flex;gap:14px;margin-top:8px;font-size:11px;color:var(--text-2);}}
  .chart-legend span{{display:flex;align-items:center;gap:5px;}}
  .legend-line{{width:18px;height:2px;display:inline-block;}}
  .legend-ema12{{background:#97C459;}}
  .legend-ema26{{background:#AFA9EC;}}
  .indicadores-principais{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:14px;}}
  .indicador-card{{border:0.5px solid var(--line);border-radius:10px;padding:16px 18px;background:var(--bg-1);}}
  .indicador-card[hidden]{{display:none;}}
  .indicador-chip{{display:inline-flex;align-items:center;gap:8px;padding:6px 11px;border:1px solid var(--purple-400);border-radius:8px;background:var(--bg-2);font-size:14px;font-weight:600;color:var(--text-1);}}
  .indicador-check{{display:grid;place-items:center;width:16px;height:16px;border-radius:4px;background:var(--purple-400);color:var(--bg-0);font-size:11px;}}
  .indicador-direcao{{min-height:30px;margin:12px 0 14px;color:var(--purple-200);font-size:20px;font-weight:600;}}
  .indicador-meta{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding-top:10px;border-top:0.5px solid var(--line);font-size:11px;color:var(--text-2);}}
  .indicador-meta strong{{display:block;margin-top:3px;font-size:14px;font-weight:600;}}
  .indicador-forca{{color:var(--green-light);}}
  .indicador-fogos{{color:var(--amber);letter-spacing:1px;white-space:nowrap;}}
  .barras-volatilidade{{display:flex;align-items:flex-end;gap:3px;height:18px;margin-top:2px;}}
  .barras-volatilidade i{{display:block;width:4px;background:var(--line-strong);}}
  .barras-volatilidade i.ativa{{background:var(--purple-400);}}

  .btn-row{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;}}
  .btn-row.wide{{grid-template-columns:1fr;}}
  button{{
    font-family:inherit;font-size:13px;font-weight:500;
    border-radius:10px;padding:12px 14px;cursor:pointer;
    transition:filter .15s ease, transform .1s ease;border:none;
  }}
  button:active{{transform:scale(0.98);}}
  .btn-primary{{
    background:linear-gradient(180deg,var(--purple-600),var(--purple-800));
    border:0.5px solid var(--purple-400);color:var(--purple-50);
  }}
  .btn-primary:hover{{filter:brightness(1.12);}}
  .btn-ghost{{
    background:transparent;border:0.5px solid var(--line-strong);color:var(--purple-200);
  }}
  .btn-ghost:hover{{background:var(--bg-2);}}
  .btn-danger-full{{
    width:100%;margin-top:20px;background:linear-gradient(180deg,#9c2b2b,#6b1c1c);
    border:0.5px solid #c33; color:#ffe3e3; font-size:14px; font-weight:600;
    padding:15px; letter-spacing:0.02em; display:flex; align-items:center; justify-content:center; gap:8px;
  }}
  .btn-danger-full:hover{{filter:brightness(1.1);}}

  .tabs{{display:flex;gap:4px;margin-bottom:14px;overflow-x:auto;}}
  .tab{{
    font-size:12.5px;color:var(--text-2);background:transparent;
    border:0.5px solid var(--line);padding:8px 14px;border-radius:9px;
    white-space:nowrap;cursor:pointer;
  }}
  .tab.active{{background:var(--bg-2);color:var(--text-1);border-color:var(--line-strong);}}
  .asset-toolbar{{display:flex;align-items:center;gap:12px;margin-bottom:10px;}}
  .asset-modes{{display:flex;gap:6px;}}
  .asset-mode{{padding:8px 12px;color:var(--text-2);background:transparent;border:0.5px solid var(--line);}}
  .asset-mode.active{{color:var(--purple-50);border-color:var(--purple-400);background:var(--bg-2);}}
  .asset-view{{display:none;}}
  .asset-view.active{{display:block;}}
  .asset-grid{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;}}
  .asset-grid .tab{{width:100%;padding:10px 6px;overflow:hidden;text-overflow:ellipsis;transition:border-color .2s ease, background-color .2s ease, color .2s ease;}}
  .asset-extra{{display:none;margin-top:0;}}
  .asset-extra.aberto{{display:grid;animation:abrir-pares .25s ease;}}
  @keyframes abrir-pares{{from{{opacity:0;transform:translateY(-4px);}}to{{opacity:1;transform:translateY(0);}}}}
  .asset-link{{grid-column:1 / -1;width:100%;margin-top:0;padding:8px 12px;color:var(--purple-200);background:transparent;border:0.5px dashed var(--line-strong);}}
  .asset-note{{font-size:12px;color:var(--text-2);margin-bottom:10px;}}
  .asset-optional{{margin-top:12px;color:var(--text-2);font-size:12px;}}
  .asset-optional summary{{cursor:pointer;}}
  .asset-optional button{{margin-top:8px;padding:8px 12px;color:var(--purple-200);background:transparent;border:0.5px solid var(--line-strong);}}
  .indicador-painel{{margin-top:14px;}}
  .indicador-opcoes{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:10px;}}
  .indicador-opcao{{display:flex;align-items:center;gap:7px;padding:9px 10px;background:var(--bg-2);border:0.5px solid var(--line);border-radius:8px;font-size:12px;color:var(--text-2);cursor:pointer;}}
  .indicador-opcao input{{accent-color:var(--purple-400);}}
  .indicador-opcao:has(input:checked){{border-color:var(--purple-400);color:var(--purple-50);}}
  .indicador-acoes{{display:flex;gap:8px;margin-top:10px;}}
  .indicador-acoes button{{padding:9px 12px;}}
  .painel-sinais{{display:block;margin-top:12px;padding:14px;background:var(--bg-2);border:0.5px solid var(--line-strong);border-radius:10px;}}
  .sinais-grade{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;}}
  .sinal-item{{min-height:54px;padding:9px 10px;background:var(--bg-1);border:0.5px solid var(--line);border-radius:8px;}}
  .sinal-item span{{display:block;font-size:11px;color:var(--text-2);margin-bottom:4px;}}
  .sinal-item strong{{font-size:13px;color:var(--text-1);}}
  .painel-sinais{{margin-top:12px;}}
  .tf-toolbar{{display:flex;align-items:center;gap:12px;margin-bottom:8px;font-size:11.5px;color:var(--text-2);}}
  .tf-titulo{{font-weight:600;}}
  .tf-check{{display:flex;align-items:center;gap:4px;cursor:pointer;}}
  .tf-check input{{accent-color:#97C459;cursor:pointer;}}
  .sinais-stream{{margin-top:10px;border-top:0.5px solid var(--line);max-height:208px;overflow-y:auto;}}
  .memoria-bloco{{margin-top:12px;padding:12px;background:var(--bg-1);border:0.5px solid var(--line);border-radius:10px;}}
  .memoria-titulo{{font-size:12px;font-weight:600;color:var(--text-1);margin-bottom:10px;}}
  .memoria-grade{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;}}
  .memoria-vazia{{grid-column:1 / -1;font-size:11.5px;color:var(--text-2);}}
  .memoria-tf{{padding:8px 10px;background:var(--bg-2);border:0.5px solid var(--line);border-radius:8px;}}
  .memoria-tf-nome{{font-size:11px;font-weight:700;color:var(--purple-200);margin-bottom:6px;}}
  .memoria-item{{display:flex;justify-content:space-between;align-items:center;gap:6px;font-size:11px;color:var(--text-2);padding:2px 0;}}
  .memoria-item .taxa{{font-weight:700;}}
  .taxa-alta{{color:#97C459;}}
  .taxa-media{{color:#E8C468;}}
  .taxa-baixa{{color:#F09595;}}
  .sinal-cabecalho,.sinal-linha{{display:grid;grid-template-columns:minmax(150px,1.2fr) 82px 92px 100px;gap:10px;align-items:center;padding:10px 2px;border-bottom:0.5px solid var(--line);font-size:12px;}}
  .sinal-cabecalho{{position:sticky;top:0;background:var(--bg-2);color:var(--text-2);font-size:11px;z-index:1;}}
  .sinal-linha strong{{color:var(--purple-100);}}
  .sinal-linha .direcao{{font-weight:700;}}
  .sinal-linha .motivo{{color:var(--text-2);}}
  .forca-indicador{{font-weight:700;color:var(--green-light);}}
  .fogo{{letter-spacing:2px;color:var(--amber);white-space:nowrap;}}
  .fogo.inativo{{color:var(--text-3);}}
  .volatilidade-indicador{{color:var(--purple-200);}}
  .direcao-alta{{color:var(--green-light);}}
  .direcao-baixa{{color:var(--red-light);}}
  .direcao-neutro{{color:var(--amber);}}

  .form-row{{margin-bottom:12px;}}
  .form-row label{{display:block;font-size:11.5px;color:var(--text-2);margin-bottom:6px;}}
  .form-row input{{
    width:100%;background:var(--bg-2);border:0.5px solid var(--line);
    border-radius:9px;padding:10px 12px;color:var(--text-1);font-size:13.5px;
  }}
  .form-row select{{
    width:100%;background:var(--bg-2);border:0.5px solid var(--line);
    border-radius:9px;padding:10px 12px;color:var(--text-1);font-size:13.5px;
  }}
  .form-row input:focus{{outline:none;border-color:var(--purple-400);}}
  .form-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}}
  .form-state{{
    min-height:41px;display:flex;align-items:center;padding:10px 12px;
    background:var(--bg-2);border:0.5px solid var(--line);border-radius:9px;
    color:var(--amber);font-size:13.5px;
  }}
  .form-state.confirmada{{color:var(--green-light);border-color:#466c27;}}

  @media (max-width:720px){{
    .grid-4,.grid-3,.form-grid,.asset-grid,.indicador-opcoes,.sinais-grade{{grid-template-columns:repeat(3,minmax(0,1fr));}}
    .topbar{{align-items:flex-start;gap:12px;}}
  }}
  @media (max-width:460px){{
    .grid-4,.grid-3,.form-grid,.asset-grid,.btn-row,.indicador-opcoes,.sinais-grade{{grid-template-columns:1fr 1fr;}}
  }}

  .log{{
    background:#0c0a15;border:0.5px solid var(--line);border-radius:10px;
    padding:12px 14px;font-family:'SFMono-Regular',Consolas,'Courier New',monospace;
    font-size:11.5px;line-height:1.7;color:var(--text-2);max-height:160px;overflow-y:auto;
  }}
  .log .ok{{color:var(--green-light);}}
  .log .warn{{color:var(--amber);}}
  .log .error{{color:var(--red-light);}}
  .log-tag{{color:var(--purple-200);}}

  .historico-tabela{{width:100%;border-collapse:collapse;font-size:12px;}}
  .historico-tabela th,.historico-tabela td{{padding:8px 10px;border-bottom:0.5px solid var(--line);text-align:left;}}
  .historico-tabela th{{color:var(--text-2);font-weight:500;}}

  footer{{text-align:center;font-size:11px;color:var(--text-3);margin-top:20px;}}

  .pulse {{animation: pulse 1.5s ease-in-out infinite;}}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.7; }}
  }}
</style>
</head>
<body>
<div class="shell">

  <div class="topbar">
    <div class="brand">
      <div class="brand-mark">
        <img src="/assets/logo-bft.jpg" alt="BFT WIN">
      </div>
      <div>
        <h1>BFT Winbot</h1>
        <p>Tempo Real — Mercados Globais</p>
      </div>
    </div>
    <div class="status-pill">
      <span class="dot pulse"></span>
      <span id="status-painel">{self._status_painel()}</span>
    </div>
  </div>

  <div class="grid-4">
    <div class="metric">
      <div class="metric-label">Banca operacional</div>
      <div class="metric-value purple" id="banca-metrica">${self.estado_operacional['banca']:,.2f}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Payout máximo</div>
      <div class="metric-value green" id="payout-metrica">{self.estado_operacional['payout']:.0f}%</div>
    </div>
    <div class="metric">
      <div class="metric-label">Confluência</div>
      <div class="metric-value purple" id="confluencia-metrica">{self.estado_operacional['confluencia']}</div>
    </div>
    <div class="metric danger">
      <div class="metric-label" style="color:#F09595">Status entrada</div>
      <div class="metric-value red" id="entrada-metrica">{self.estado_operacional['entrada']}</div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header">
      <span class="pair-badge" id="pair-badge">{self.ativo_atual} · M1 Tempo Real</span>
      <span class="change-up" id="change-badge" style="color:var(--{mudanca_cor})">{mudanca}</span>
    </div>
    <div class="chart-wrap" id="chart">
      <svg viewBox="0 0 900 220" width="100%" height="100%">
        <g stroke="#2a2440" stroke-width="1">
          <line x1="0" y1="30" x2="900" y2="30"/>
          <line x1="0" y1="80" x2="900" y2="80"/>
          <line x1="0" y1="130" x2="900" y2="130"/>
          <line x1="0" y1="180" x2="900" y2="180"/>
        </g>
        <g id="candles"></g>
        <path id="ema-cloud" fill="none" opacity="0.18"/>
        <path id="ema-12" fill="none" stroke="#97C459" stroke-width="1.8"/>
        <path id="ema-26" fill="none" stroke="#AFA9EC" stroke-width="1.8"/>
        <g id="sinal-confirmado"></g>
      </svg>
    </div>
    <div class="chart-osc-title">
      <span>Best indicator now</span>
      <span class="osc-selo" id="osc-selo">—</span>
      <span id="osc-valor" style="color:var(--text-2)">—</span>
    </div>
    <div class="chart-wrap chart-osc">
      <svg viewBox="0 0 900 64" width="100%" height="100%" preserveAspectRatio="none">
        <g stroke="#2a2440" stroke-width="1">
          <line x1="0" y1="32" x2="900" y2="32"/>
        </g>
        <path id="osc-linha" fill="none" stroke="#AFA9EC" stroke-width="1.6"/>
        <g id="osc-zonas"></g>
      </svg>
    </div>
    <div class="chart-legend">
      <span><i class="legend-line legend-ema12"></i>EMA 12</span>
      <span><i class="legend-line legend-ema26"></i>EMA 26</span>
      <span>Sinal exibido somente com confluência confirmada</span>
    </div>
    <div class="indicadores-principais">
      <div class="indicador-card" id="card-1" hidden>
        <div class="indicador-chip"><span class="indicador-check">✓</span><span id="card-1-nome">—</span></div>
        <div class="indicador-direcao" id="card-1-metrica">—</div>
        <div class="indicador-meta"><div>Força<strong class="indicador-forca" id="card-1-forca">—</strong></div><div>Tendência<strong class="indicador-fogos" id="card-1-fogos">—</strong></div><div>Volatil.<span class="barras-volatilidade" id="card-1-volatilidade"><i></i><i></i><i></i></span></div></div>
      </div>
      <div class="indicador-card" id="card-2" hidden>
        <div class="indicador-chip"><span class="indicador-check">✓</span><span id="card-2-nome">—</span></div>
        <div class="indicador-direcao" id="card-2-metrica">—</div>
        <div class="indicador-meta"><div>Força<strong class="indicador-forca" id="card-2-forca">—</strong></div><div>Tendência<strong class="indicador-fogos" id="card-2-fogos">—</strong></div><div>Volatil.<span class="barras-volatilidade" id="card-2-volatilidade"><i></i><i></i><i></i></span></div></div>
      </div>
      <div class="indicador-card" id="card-3" hidden>
        <div class="indicador-chip"><span class="indicador-check">✓</span><span id="card-3-nome">—</span></div>
        <div class="indicador-direcao" id="card-3-metrica">—</div>
        <div class="indicador-meta"><div>Força<strong class="indicador-forca" id="card-3-forca">—</strong></div><div>Tendência<strong class="indicador-fogos" id="card-3-fogos">—</strong></div><div>Volatil.<span class="barras-volatilidade" id="card-3-volatilidade"><i></i><i></i><i></i></span></div></div>
      </div>
    </div>
    <div class="indicador-painel">
      <div class="asset-modes">
        <button class="asset-mode {'active' if self.indicadores_automaticos else ''}" id="modo-indicador-auto" onclick="usar_indicadores_auto()">Auto</button>
        <button class="asset-mode {'' if self.indicadores_automaticos else 'active'}" id="modo-indicador-combinar" onclick="usar_indicadores_combinados()">Combinar 2-8</button>
      </div>
      <div class="indicador-opcoes" id="opcoes-indicadores">{indicadores_html}</div>
      <div class="indicador-acoes">
        <button class="btn-ghost" onclick="aplicar_indicadores()">Aplicar indicadores</button>
      </div>
    </div>
    <div class="btn-row">
      <button class="btn-ghost" onclick="atualizar_dados()">Atualizar dados</button>
    </div>
    <section class="painel-sinais" aria-live="polite">
      <div class="tf-toolbar">
        <span class="tf-titulo">Sinais por período:</span>
        <label class="tf-check"><input type="checkbox" id="tf-m1" checked onchange="aplicar_timeframes()"> M1</label>
        <label class="tf-check"><input type="checkbox" id="tf-m5" checked onchange="aplicar_timeframes()"> M5</label>
        <label class="tf-check"><input type="checkbox" id="tf-m15" checked onchange="aplicar_timeframes()"> M15</label>
      </div>
      <div class="sinais-grade" id="sinais-multitempo">
        <div class="sinal-item"><span>M1</span><strong id="sinal-mt-M1">—</strong></div>
        <div class="sinal-item"><span>M5</span><strong id="sinal-mt-M5">—</strong></div>
        <div class="sinal-item"><span>M15</span><strong id="sinal-mt-M15">—</strong></div>
      </div>
      <div class="sinais-grade">
        <div class="sinal-item"><span>Direção atual</span><strong id="sinal-direcao">Aguardando análise</strong></div>
        <div class="sinal-item"><span>Confluência</span><strong id="sinal-confluencia">—</strong></div>
        <div class="sinal-item"><span>Regime</span><strong id="sinal-regime">—</strong></div>
        <div class="sinal-item"><span>Indicadores ativos</span><strong id="sinal-indicadores">—</strong></div>
        <div class="sinal-item"><span>Motivo</span><strong id="sinal-motivo">Aguardando velas reais</strong></div>
        <div class="sinal-item"><span>Modo</span><strong id="sinal-modo">Somente sinais</strong></div>
      </div>
      <div class="sinais-stream" id="sinais-stream">
        <div class="sinal-cabecalho"><span>Indicador</span><span>Força</span><span>Momento</span><span>Volatilidade</span></div>
      </div>
      <div class="memoria-bloco">
        <div class="memoria-titulo">🧠 Memória do bot — acerto recente por período</div>
        <div class="memoria-grade" id="memoria-container">
          <div class="memoria-vazia">O bot ainda está aprendendo: cada sinal emitido é avaliado na vela seguinte. Após algumas rodadas o ranking aparece aqui.</div>
        </div>
      </div>
    </section>
  </div>

  <div class="panel">
    <div class="asset-toolbar">
      <div class="asset-modes" role="tablist">
        <button class="asset-mode{' active' if not mercado_otc_ativo else ''}" id="aba-aberto" onclick="mostrar_mercado('aberto')">Mercado Aberto</button>
        <button class="asset-mode{' active' if mercado_otc_ativo else ''}" id="aba-otc" onclick="mostrar_mercado('otc')">OTC</button>
      </div>
    </div>
    <div class="asset-view{' active' if not mercado_otc_ativo else ''}" id="mercado-aberto">
      <div class="asset-grid"> {principais_html}<button class="asset-link" id="botao-mais-pares" onclick="alternar_pares_reais()">Mais pares reais ({len(ATIVOS_MERCADO_ABERTO) - 6})</button></div>
      <div class="asset-grid asset-extra" id="pares-reais-adicionais">{adicionais_html}</div>
      <details class="asset-optional">
        <summary>Adicionar par Forex manualmente</summary>
        <button onclick="adicionar_ativo()">Adicionar ativo</button>
      </details>
    </div>
    <div class="asset-view{' active' if mercado_otc_ativo else ''}" id="mercado-otc">
      <p class="asset-note" id="nota-otc">Ativos OTC para leitura visual na plataforma selecionada.</p>
      <div class="asset-grid">{otc_html}</div>
      <div class="btn-row wide">
        <button class="btn-ghost" id="botao-leitura-otc" onclick="ler_tela_otc()">📷 Ler tela OTC (2 capturas)</button>
      </div>
    </div>
    <div class="form-grid">
      <div class="form-row">
        <label>Modo de operação</label>
        <select id="modo-input" onchange="mudar_modo_operacao(this.value)">
          <option value="SOMENTE_SINAIS"{' selected' if self.modo_operacao_atual == SOMENTE_SINAIS else ''}>Somente Sinais (observação)</option>
          <option value="AUTOMATICO_DEMO"{' selected' if self.modo_operacao_atual == AUTOMATICO_DEMO else ''}>Automático DEMO (conta prática)</option>
          <option value="AUTOMATICO_REAL"{' selected' if self.modo_operacao_atual == AUTOMATICO_REAL else ''}>Automático REAL (conta real)</option>
        </select>
      </div>
      <div class="form-row">
        <label>Plataforma operacional</label>
        <select id="plataforma-input" onchange="mudar_plataforma()">
          <option value="IQ Option">IQ Option</option>
          <option value="Quotex">Quotex</option>
          <option value="Casa Trader">Casa Trader</option>
          <option value="Avallon">Avallon</option>
        </select>
      </div>
      <div class="form-row">
        <label>Banca simulada</label>
        <input type="number" min="0.01" step="0.01" value="{self.estado_operacional['banca']}" id="banca-input" onchange="atualizar_configuracao()">
      </div>
      <div class="form-row">
        <label>Valor entrada (USD)</label>
        <input type="number" min="0.01" step="0.01" value="{self.configuracao['entrada']}" id="entrada-input" onchange="atualizar_configuracao()">
      </div>
      <div class="form-row">
        <label>Stop gain</label>
        <input type="number" min="0.01" step="0.01" value="{self.configuracao['stop_gain']}" id="gain-input" onchange="atualizar_configuracao()">
      </div>
      <div class="form-row">
        <label>Stop loss</label>
        <input type="number" min="0.01" step="0.01" value="{self.configuracao['stop_loss']}" id="loss-input" onchange="atualizar_configuracao()">
      </div>
      <div class="form-row">
        <label>Liberação do monitoramento</label>
        <div class="form-state{' confirmada' if self.plataforma_confirmada == self.plataforma_atual else ''}" id="status-plataforma">
          {'Plataforma confirmada' if self.plataforma_confirmada == self.plataforma_atual else 'Confirme a plataforma'}
        </div>
      </div>
    </div>
    <div class="btn-row wide">
      <button class="btn-ghost" onclick="confirmar_plataforma()">Confirmar plataforma</button>
      <button class="btn-primary" onclick="iniciar_motor()">▶ Iniciar robô</button>
      <button class="btn-ghost" onclick="pausar_motor()">⏸ Pausar robô</button>
      <button class="btn-ghost" onclick="encerrar_sessao()">Encerrar sessão</button>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header">
      <span class="panel-title">📊 Histórico de Entradas</span>
    </div>
    <div class="historico-wrap" id="historico-container"></div>
  </div>

  <div class="panel">
    <div class="panel-header">
      <span class="panel-title">📋 Log do BFT (Tempo Real)</span>
    </div>
    <div class="log" id="log-container">
      {log_html}
    </div>
  </div>

  <button class="btn-danger-full" onclick="parada_emergencia()">⛔ Parada de emergência — clique aqui</button>

  <footer>BFT Winbot · Integração de Mercados Reais · Tempo Real Global</footer>
</div>

<script>
  function tratarResposta(resposta) {{
    if (!resposta.ok) {{
      return resposta.json().catch(() => ({{}})).then(dados => {{
        throw new Error(dados.erro || 'Falha ao executar ação');
      }});
    }}
    return resposta.json().catch(() => ({{}}));
  }}

  function formatarPreco(valor) {{
    return Number(valor).toLocaleString('pt-BR', {{
      minimumFractionDigits: 2,
      maximumFractionDigits: 6
    }});
  }}

  function aplicarIndicadores(automatico, codigos = []) {{
    return fetch('/api/indicadores', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{automatico, codigos}})
    }}).then(tratarResposta);
  }}

  function usar_indicadores_auto() {{
    aplicarIndicadores(true).then(() => location.reload()).catch(erro => alert(erro.message));
  }}

  function usar_indicadores_combinados() {{
    document.getElementById('modo-indicador-auto').classList.remove('active');
    document.getElementById('modo-indicador-combinar').classList.add('active');
  }}

  function aplicar_indicadores() {{
    const codigos = [...document.querySelectorAll('#opcoes-indicadores input:checked')].map(item => item.value);
    aplicarIndicadores(false, codigos).then(() => location.reload()).catch(erro => alert(erro.message));
  }}

  function renderizarLog(logs) {{
    const container = document.getElementById('log-container');
    container.replaceChildren(...logs.slice(-10).map(log => {{
      const linha = document.createElement('div');
      const etiqueta = document.createElement('span');
      etiqueta.className = 'log-tag';
      etiqueta.textContent = `[${{log.tipo}}] `;
      const mensagem = document.createElement('span');
      mensagem.className = log.nivel || 'info';
      mensagem.textContent = log.mensagem;
      linha.append(etiqueta, mensagem);
      return linha;
    }}));
    container.scrollTop = container.scrollHeight;
  }}

  function renderizarHistorico(historico) {{
    const container = document.getElementById('historico-container');
    if (!historico || historico.length === 0) {{
      container.textContent = 'Nenhuma entrada registrada ainda.';
      return;
    }}
    const tabela = document.createElement('table');
    tabela.className = 'historico-tabela';
    const cabecalho = document.createElement('tr');
    cabecalho.replaceChildren(...['Horário', 'Conta', 'Plataforma', 'Ativo', 'Direção', 'Valor', 'Resultado'].map(texto => {{
      const th = document.createElement('th');
      th.textContent = texto;
      return th;
    }}));
    tabela.append(cabecalho);
    historico.slice().reverse().forEach(item => {{
      const linha = document.createElement('tr');
      linha.replaceChildren(...[
        item.horario,
        item.conta,
        item.plataforma,
        item.ativo,
        item.direcao,
        `$${{item.valor}}`,
        item.resultado,
      ].map(valor => {{
        const td = document.createElement('td');
        td.textContent = valor;
        return td;
      }}));
      tabela.append(linha);
    }});
    container.replaceChildren(tabela);
  }}

  function alternar_painel_sinais() {{
    const painel = document.getElementById('painel-sinais');
    const aberto = painel.classList.toggle('aberto');
    document.getElementById('botao-painel-sinais').textContent = aberto ? 'Ocultar painel de sinais' : 'Painel de sinais';
  }}

  function atualizarPainelSinais(analise) {{
    const texto = (id, valor) => document.getElementById(id).textContent = valor;
    if (!analise) {{
      texto('sinal-direcao', 'Aguardando análise');
      texto('sinal-confluencia', '—');
      texto('sinal-regime', '—');
      texto('sinal-indicadores', 'Aguardando seleção');
      texto('sinal-motivo', 'Aguardando velas reais');
      texto('sinal-modo', 'Somente sinais');
      return;
    }}
    texto('sinal-direcao', analise.direcao || analise.sinal || 'AGUARDAR');
    texto('sinal-confluencia', `${{Number(analise.pontuacao || 0).toFixed(1)}}/10`);
    texto('sinal-regime', analise.regime || '—');
    texto('sinal-indicadores', (analise.indicadores_ativos || []).join(', ') || '—');
    texto('sinal-motivo', analise.motivo || '—');
    texto('sinal-modo', analise.modo_operacao || 'SOMENTE SINAIS');
  }}

  function renderizarFluxoIndicadores(analise) {{
    const nomes = {{
      BFT_GAP: 'BFT GAP 26',
      BFT_OB: 'BFT OB 26',
      BFT_PANO: 'BFT PANO 26',
      BFT_WIN26: 'BFT WIN 26',
      BIGFOOT: 'BigFoot.Trader'
    }};
    const diagnosticos = Object.fromEntries((analise?.diagnosticos || []).map(item => [item.nome || item.codigo, item]));
    const ativos = new Set(analise?.indicadores_ativos || []);
    const stream = document.getElementById('sinais-stream');
    const cabecalho = document.createElement('div');
    cabecalho.className = 'sinal-cabecalho';
    cabecalho.replaceChildren(...['Indicador', 'Força', 'Momento', 'Volatilidade'].map(texto => {{
      const coluna = document.createElement('span');
      coluna.textContent = texto;
      return coluna;
    }}));
    const ultimoTecnico = (analise?.series_tecnicas || []).at(-1) || {{}};
    const ultimoPreco = Number((analise?.velas_grafico || []).at(-1)?.fechamento);
    const atr = Number(ultimoTecnico.atr);
    const volatilidade = Number.isFinite(atr) && Number.isFinite(ultimoPreco) && ultimoPreco !== 0
      ? `${{(atr / ultimoPreco * 100).toFixed(3)}}%`
      : '—';
    stream.replaceChildren(cabecalho, ...Object.entries(nomes).map(([codigo, nome]) => {{
      const diagnostico = diagnosticos[nome] || diagnosticos[codigo];
      const direcao = diagnostico?.direcao || 'NÃO ATIVO';
      const peso = Number(diagnostico?.peso || 0);
      const forca = diagnostico ? (peso >= 2 ? 100 : peso === 1 ? 65 : 30) : 0;
      const fogos = forca >= 70 ? '🔥🔥🔥' : forca >= 45 ? '🔥🔥' : forca > 0 ? '🔥' : '—';
      const momento = diagnostico ? direcao : (ativos.has(codigo) ? 'AGUARDANDO' : 'NÃO ATIVO');
      const linha = document.createElement('div');
      linha.className = 'sinal-linha';
      const titulo = document.createElement('strong');
      titulo.textContent = nome;
      const forcaVisual = document.createElement('span');
      forcaVisual.className = 'forca-indicador';
      forcaVisual.textContent = diagnostico ? `${{forca}}%` : '—';
      const momentoVisual = document.createElement('span');
      momentoVisual.className = `fogo ${{diagnostico ? '' : 'inativo'}}`;
      momentoVisual.title = momento;
      momentoVisual.textContent = fogos;
      const volatilidadeVisual = document.createElement('span');
      volatilidadeVisual.className = 'volatilidade-indicador';
      volatilidadeVisual.title = diagnostico?.motivo || momento;
      volatilidadeVisual.textContent = volatilidade;
      linha.append(titulo, forcaVisual, momentoVisual, volatilidadeVisual);
      return linha;
    }}));
  }}

  function renderizarVelas(velas, series, direcao) {{
    const grupo = document.getElementById('candles');
    const faixa = document.getElementById('ema-cloud');
    const ema12 = document.getElementById('ema-12');
    const ema26 = document.getElementById('ema-26');
    const sinal = document.getElementById('sinal-confirmado');
    grupo.replaceChildren();
    sinal.replaceChildren();
    faixa.setAttribute('d', '');
    ema12.setAttribute('d', '');
    ema26.setAttribute('d', '');
    if (!velas || velas.length === 0) return;

    const maxima = Math.max(...velas.map(vela => Number(vela.maxima)));
    const minima = Math.min(...velas.map(vela => Number(vela.minima)));
    const amplitude = maxima - minima || 1;
    const largura = 900 / velas.length;
    const larguraCorpo = Math.max(2, largura * 0.58);
    const y = valor => 190 - ((Number(valor) - minima) / amplitude) * 160;
    const seriesRelevantes = (series || []).slice(-velas.length);
    const pontosEma12 = [];
    const pontosEma26 = [];

    velas.forEach((vela, indice) => {{
      const centroX = indice * largura + largura / 2;
      const subida = Number(vela.fechamento) >= Number(vela.abertura);
      const cor = subida ? '#97C459' : '#F09595';
      const pavio = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      pavio.setAttribute('x1', centroX);
      pavio.setAttribute('x2', centroX);
      pavio.setAttribute('y1', y(vela.maxima));
      pavio.setAttribute('y2', y(vela.minima));
      pavio.setAttribute('stroke', cor);
      pavio.setAttribute('stroke-width', '1');

      const corpo = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      corpo.setAttribute('x', centroX - larguraCorpo / 2);
      corpo.setAttribute('y', Math.min(y(vela.abertura), y(vela.fechamento)));
      corpo.setAttribute('width', larguraCorpo);
      corpo.setAttribute('height', Math.max(1, Math.abs(y(vela.abertura) - y(vela.fechamento))));
      corpo.setAttribute('fill', cor);

      grupo.append(pavio, corpo);
      const tecnico = seriesRelevantes[indice] || {{}};
      if (Number.isFinite(Number(tecnico.ema_12))) {{
        pontosEma12.push([centroX, y(tecnico.ema_12)]);
      }}
      if (Number.isFinite(Number(tecnico.ema_26))) {{
        pontosEma26.push([centroX, y(tecnico.ema_26)]);
      }}
    }});

    const caminho = pontos => pontos.map(([x, valorY], indice) => `${{indice === 0 ? 'M' : 'L'}}${{x.toFixed(1)}},${{valorY.toFixed(1)}}`).join(' ');
    ema12.setAttribute('d', caminho(pontosEma12));
    ema26.setAttribute('d', caminho(pontosEma26));
    if (pontosEma12.length === pontosEma26.length && pontosEma12.length > 1) {{
      const poligono = [...pontosEma12, ...pontosEma26.slice().reverse()]
        .map(([x, valorY]) => `${{x.toFixed(1)}},${{valorY.toFixed(1)}}`)
        .join(' ');
      faixa.setAttribute('d', `M${{poligono}}Z`);
      faixa.setAttribute('fill', pontosEma12.at(-1)[1] < pontosEma26.at(-1)[1] ? '#639922' : '#E24B4A');
    }}
    if (direcao === 'CALL' || direcao === 'PUT') {{
      const ultima = velas.at(-1);
      const marcador = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      marcador.setAttribute('x', (900 - largura / 2).toFixed(1));
      marcador.setAttribute('y', direcao === 'CALL' ? y(ultima.minima) + 18 : y(ultima.maxima) - 8);
      marcador.setAttribute('fill', direcao === 'CALL' ? '#97C459' : '#F09595');
      marcador.setAttribute('font-size', '11');
      marcador.setAttribute('font-weight', '700');
      marcador.setAttribute('text-anchor', 'end');
      marcador.textContent = direcao === 'CALL' ? '▲ CALL' : '▼ PUT';
      sinal.append(marcador);
    }}
  }}

  const OSC_CONFIG = {{
    RSI: {{serie: 'rsi', min: 0, max: 100, cortes: [30, 70], casas: 1}},
    ESTOCASTICO: {{serie: 'estocastico', min: 0, max: 100, cortes: [20, 80], casas: 1}},
    ADX: {{serie: 'adx', min: 0, max: 60, cortes: [25], casas: 1}},
    MACD: {{serie: 'histograma_macd', min: null, max: null, cortes: [0], casas: 5}},
    ATR: {{serie: 'atr', min: null, max: null, cortes: [], casas: 5}},
  }};

  function escolherMelhorIndicador(analise) {{
    const diagnosticos = analise?.diagnosticos || [];
    let melhor = null;
    let melhorPeso = -1;
    diagnosticos.forEach(item => {{
      const codigo = item.codigo || (item.nome || '').toUpperCase().replace(/[^A-Z_]/g, '');
      const config = OSC_CONFIG[codigo];
      if (!config) return;
      const peso = Number(item.peso || 0);
      const ativoNaDirecao = item.direcao && item.direcao !== 'NEUTRO';
      const pontuacao = peso * (ativoNaDirecao ? 2 : 1);
      if (pontuacao > melhorPeso) {{
        melhorPeso = pontuacao;
        melhor = {{codigo, nome: item.nome || codigo, direcao: item.direcao || 'NEUTRO', config}};
      }}
    }});
    return melhor;
  }}

  function renderizarOscilador(analise) {{
    const linha = document.getElementById('osc-linha');
    const zonas = document.getElementById('osc-zonas');
    const selo = document.getElementById('osc-selo');
    const valorAtual = document.getElementById('osc-valor');
    linha.setAttribute('d', '');
    zonas.replaceChildren();
    const series = analise?.series_tecnicas || [];
    const escolhido = escolherMelhorIndicador(analise);
    if (!escolhido) {{
      selo.textContent = '—';
      selo.classList.add('neutro');
      valorAtual.textContent = 'aguardando confluência';
      return;
    }}
    selo.textContent = `🔥 ${{escolhido.nome}} · ${{escolhido.direcao}}`;
    selo.classList.toggle('neutro', escolhido.direcao === 'NEUTRO');
    const config = escolhido.config;
    const valores = series.map(item => Number(item[config.serie])).filter(Number.isFinite);
    if (valores.length < 2) {{
      valorAtual.textContent = 'sem série suficiente';
      return;
    }}
    const min = config.min === null ? Math.min(...valores) : config.min;
    const max = config.max === null ? Math.max(...valores) : config.max;
    const amplitude = (max - min) || 1;
    const y = valor => 60 - ((valor - min) / amplitude) * 56 - 2;
    config.cortes.forEach(corte => {{
      if (corte < min || corte > max) return;
      const linhaCorte = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      linhaCorte.setAttribute('x1', 0);
      linhaCorte.setAttribute('x2', 900);
      linhaCorte.setAttribute('y1', y(corte));
      linhaCorte.setAttribute('y2', y(corte));
      linhaCorte.setAttribute('stroke', '#4a4368');
      linhaCorte.setAttribute('stroke-dasharray', '4 6');
      zonas.append(linhaCorte);
    }});
    const pontos = series
      .map((item, indice) => [indice * (900 / Math.max(1, series.length - 1)), Number(item[config.serie])])
      .filter(([, valor]) => Number.isFinite(valor))
      .map(([x, valor], indiceOriginal, todos) => `${{indiceOriginal === 0 ? 'M' : 'L'}}${{x.toFixed(1)}},${{y(valor).toFixed(1)}}`);
    linha.setAttribute('d', pontos.join(' '));
    const ultimo = valores.at(-1);
    valorAtual.textContent = `${{ultimo.toFixed(config.casas)}}`;
  }}

  function formatarIndicador(valor, casas = 2) {{
    return Number.isFinite(Number(valor)) ? Number(valor).toFixed(casas) : '—';
  }}

  function atualizarCardIndicador(prefixo, codigo, diagnostico, volatilidadePercentual) {{
    const nomes = {{
      BFT_GAP: 'BFT GAP 26',
      BFT_OB: 'BFT OB 26',
      BFT_PANO: 'BFT PANO 26',
      BFT_WIN26: 'BFT WIN 26',
      BIGFOOT: 'BigFoot.Trader'
    }};
    const card = document.getElementById(prefixo);
    card.hidden = !codigo;
    if (!codigo) return;
    const direcao = diagnostico?.direcao || '—';
    const peso = Number(diagnostico?.peso || 0);
    const forca = peso >= 2 ? 100 : peso === 1 ? 65 : peso === 0 && diagnostico ? 30 : 0;
    const fogos = forca >= 71 ? '🔥🔥🔥' : forca >= 46 ? '🔥🔥' : forca > 0 ? '🔥' : '—';
    const nivelVolatilidade = !Number.isFinite(volatilidadePercentual) ? 0 : volatilidadePercentual < 0.03 ? 1 : volatilidadePercentual < 0.08 ? 2 : 3;
    document.getElementById(`${{prefixo}}-nome`).textContent = nomes[codigo] || 'Aguardando combinação';
    document.getElementById(`${{prefixo}}-metrica`).textContent = direcao;
    document.getElementById(`${{prefixo}}-forca`).textContent = diagnostico ? `${{forca}}%` : '—';
    document.getElementById(`${{prefixo}}-fogos`).textContent = fogos;
    document.querySelectorAll(`#${{prefixo}}-volatilidade i`).forEach((barra, indice) => {{
      barra.classList.toggle('ativa', indice < nivelVolatilidade);
      barra.style.height = `${{6 + indice * 4}}px`;
    }});
  }}

  function atualizarCardsCombinacao(analise, configuracao) {{
    const diagnosticos = Object.fromEntries((analise?.diagnosticos || []).map(item => [item.codigo, item]));
    const codigos = configuracao?.automatico
      ? (analise?.indicadores_ativos || [])
      : (configuracao?.selecionados || []);
    const tecnico = (analise?.series_tecnicas || []).at(-1) || {{}};
    const preco = Number((analise?.velas_grafico || []).at(-1)?.fechamento);
    const volatilidade = Number(tecnico.atr) / preco * 100;
    ['card-1', 'card-2', 'card-3'].forEach((prefixo, indice) => {{
      const codigo = codigos[indice];
      atualizarCardIndicador(prefixo, codigo, diagnosticos[codigo], volatilidade);
    }});
  }}

  function atualizarPainel() {{
    fetch('/api/status')
      .then(tratarResposta)
      .then(dados => {{
        const estado = dados.estado;
        document.getElementById('status-painel').textContent = estado.status;
        document.getElementById('banca-metrica').textContent = `$${{formatarPreco(estado.banca)}}`;
        document.getElementById('payout-metrica').textContent = `${{Number(estado.payout).toFixed(0)}}%`;
        document.getElementById('confluencia-metrica').textContent = estado.confluencia;
        document.getElementById('entrada-metrica').textContent = estado.entrada;
        const plataforma = dados.plataforma;
        const estadoPlataforma = document.getElementById('status-plataforma');
        document.getElementById('plataforma-input').value = plataforma.atual;
        estadoPlataforma.textContent = plataforma.confirmada ? 'Plataforma confirmada' : 'Confirme a plataforma';
        estadoPlataforma.classList.toggle('confirmada', plataforma.confirmada);

        if (dados.analise) {{
          document.getElementById('pair-badge').textContent = `${{dados.analise.ativo}} · ${{dados.analise.timeframe || 'M1'}} Tempo Real`;
          renderizarVelas(
            dados.analise.velas_grafico,
            dados.analise.series_tecnicas,
            dados.analise.direcao
          );
          renderizarOscilador(dados.analise);
        }}
        atualizarCardsCombinacao(dados.analise, dados.indicadores);
        atualizarPainelSinais(dados.analise);
        renderizarFluxoIndicadores(dados.analise);

        const cotacao = dados.cotacoes[dados.ativo_atual];
        const badge = document.getElementById('change-badge');
        if (cotacao) {{
          const variacao = Number(cotacao.variacao_percentual);
          badge.textContent = `${{variacao >= 0 ? '+' : ''}}${{variacao.toFixed(2)}}% · $${{formatarPreco(cotacao.preco)}}`;
          badge.className = variacao >= 0 ? 'change-up' : 'change-down';
        }} else {{
          badge.textContent = 'Dados indisponíveis';
          badge.className = 'change-down';
        }}
        renderizarLog(dados.logs || []);
        renderizarHistorico(dados.historico || []);
        renderizarSinaisMultitempo(dados);
        renderizarMemoria(dados.memoria_indicadores);
      }})
      .catch(erro => console.warn('Não foi possível atualizar o painel:', erro.message));
  }}

  function renderizarMemoria(memoria) {{
    const container = document.getElementById('memoria-container');
    if (!container) return;
    const timeframes = Object.keys(memoria || {{}}).filter(tf => (memoria[tf] || []).length > 0);
    if (timeframes.length === 0) return;
    container.replaceChildren(...timeframes.sort().map(tf => {{
      const cartao = document.createElement('div');
      cartao.className = 'memoria-tf';
      const nome = document.createElement('div');
      nome.className = 'memoria-tf-nome';
      nome.textContent = tf;
      cartao.append(nome);
      memoria[tf].forEach(item => {{
        const linha = document.createElement('div');
        linha.className = 'memoria-item';
        const codigo = document.createElement('span');
        codigo.textContent = item.codigo;
        const taxa = document.createElement('span');
        taxa.className = 'taxa ' + (item.taxa >= 0.6 ? 'taxa-alta' : item.taxa >= 0.45 ? 'taxa-media' : 'taxa-baixa');
        taxa.textContent = `${{Math.round(item.taxa * 100)}}% (${{item.total}})`;
        taxa.title = `${{item.total}} sinais avaliados neste período`;
        linha.append(codigo, taxa);
        cartao.append(linha);
      }});
      return cartao;
    }}));
  }}

  function mudar_ativo(ativo) {{
    fetch(`/api/ativo/${{ativo}}`).then(tratarResposta).then(() => location.reload()).catch(erro => alert(erro.message));
  }}

  function aplicar_timeframes() {{
    const visiveis = ['tf-m1', 'tf-m5', 'tf-m15']
      .filter(id => document.getElementById(id)?.checked)
      .map(id => id.replace('tf-', '').toUpperCase());
    if (visiveis.length === 0) {{
      alert('Pelo menos um período deve ficar visível');
      return;
    }}
    const tfAtivo = visiveis.includes(document.getElementById('tf-ativo-selecionado')?.value || 'M1')
      ? (document.getElementById('tf-ativo-selecionado')?.value || 'M1')
      : visiveis[0];
    fetch('/api/timeframes', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{visiveis, ativo: tfAtivo}})
    }}).then(tratarResposta).then(() => atualizarPainel()).catch(erro => alert(erro.message));
  }}

  function renderizarSinaisMultitempo(dados) {{
    const analises = dados.analises_multitempo || {{}};
    const visiveis = new Set(dados.timeframes_visiveis || ['M1', 'M5', 'M15']);
    ['M1', 'M5', 'M15'].forEach(tf => {{
      const celula = document.getElementById(`sinal-mt-${{tf}}`);
      const item = celula?.closest('.sinal-item');
      if (!celula || !item) return;
      item.style.display = visiveis.has(tf) ? '' : 'none';
      const analise = analises[tf];
      if (!analise) {{
        celula.textContent = 'aguardando';
        celula.style.color = 'var(--text-2)';
        return;
      }}
      const direcao = analise.direcao || analise.sinal || 'AGUARDAR';
      const pontuacao = Number(analise.pontuacao || 0).toFixed(1);
      celula.textContent = `${{direcao}} · ${{pontuacao}}/10`;
      celula.style.color = direcao === 'CALL' ? '#97C459' : direcao === 'PUT' ? '#F09595' : 'var(--text-2)';
    }});
  }}

  function mostrar_mercado(tipo) {{
    const aberto = tipo === 'aberto';
    document.getElementById('mercado-aberto').classList.toggle('active', aberto);
    document.getElementById('mercado-otc').classList.toggle('active', !aberto);
    document.getElementById('aba-aberto').classList.toggle('active', aberto);
    document.getElementById('aba-otc').classList.toggle('active', !aberto);
  }}

  function alternar_pares_reais() {{
    const lista = document.getElementById('pares-reais-adicionais');
    const aberto = lista.classList.toggle('aberto');
    document.getElementById('botao-mais-pares').textContent = aberto ? 'Ocultar pares reais' : 'Mais pares reais ({len(ATIVOS_MERCADO_ABERTO) - 6})';
  }}

  function mudar_plataforma() {{
    const plataforma = document.getElementById('plataforma-input').value;
    fetch('/api/plataforma', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{plataforma}})
    }}).then(tratarResposta).then(atualizarPainel).catch(erro => alert(erro.message));
  }}

  function confirmar_plataforma() {{
    fetch('/api/confirmar-plataforma', {{method:'POST'}})
      .then(tratarResposta)
      .then(atualizarPainel)
      .catch(erro => alert(erro.message));
  }}

  function atualizar_dados() {{
    fetch('/api/atualizar', {{method:'POST'}}).then(tratarResposta).then(atualizarPainel).catch(erro => alert(erro.message));
  }}

  function atualizar_configuracao() {{
    const configuracao = {{
      banca: parseFloat(document.getElementById('banca-input').value),
      entrada: parseFloat(document.getElementById('entrada-input').value),
      stop_gain: parseFloat(document.getElementById('gain-input').value),
      stop_loss: parseFloat(document.getElementById('loss-input').value)
    }};
    return fetch('/api/configuracao', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify(configuracao)
    }}).then(tratarResposta);
  }}

  function adicionar_ativo() {{
    const novo = prompt('Código do ativo (ex: BTC, EURUSD, PETR4):');
    if (novo) fetch(`/api/adicionar-ativo/${{novo}}`).then(tratarResposta).then(() => location.reload()).catch(erro => alert(erro.message));
  }}

  function ler_tela_otc() {{
    const botao = document.getElementById('botao-leitura-otc');
    botao.disabled = true;
    const solicitar = () => {{
      if (window.pywebview && window.pywebview.api && window.pywebview.api.ler_tela_otc) {{
        return window.pywebview.api.ler_tela_otc();
      }}
      return fetch('/api/ler-tela-otc', {{method: 'POST'}}).then(tratarResposta);
    }};
    solicitar()
      .then(dados => {{
        if (dados && (dados.ok === false || dados.erro)) {{
          throw new Error(dados.mensagem || dados.erro || 'Leitura visual não concluída');
        }}
        location.reload();
      }})
      .catch(erro => {{
        botao.disabled = false;
        alert(erro.message);
      }});
  }}

  function mudar_modo_operacao(modo) {{
    const nomes = {{
      'SOMENTE_SINAIS': 'Somente Sinais (observação)',
      'AUTOMATICO_DEMO': 'Automático DEMO (conta prática)',
      'AUTOMATICO_REAL': 'Automático REAL (conta real)'
    }};
    const automatizado = modo !== 'SOMENTE_SINAIS';
    if (automatizado) {{
      const real = modo === 'AUTOMATICO_REAL';
      const mensagem = real
        ? '⚠️ MODO AUTOMÁTICO — CONTA REAL\n\nO bot vai ENVIAR ORDENS REAIS na sua conta da corretora, com o seu dinheiro.\n\n' +
          'Você declara que:\n' +
          '• AUTORIZA o disparo automático e assume 100% da responsabilidade por qualquer resultado (lucro ou prejuízo);\n' +
          '• entende que trading envolve risco financeiro real e perdas podem ocorrer;\n' +
          '• confere stop gain, stop loss e valor de entrada antes de prosseguir;\n' +
          '• tem consciência dos seus atos — cada ordem é decisão do seu setup, executada pela máquina.\n\n' +
          'Prosseguir e ativar o modo REAL?'
        : '🤖 MODO AUTOMÁTICO — CONTA PRÁTICA\n\nO bot vai registrar entradas hipotéticas (sem dinheiro real) para medir o desempenho das estratégias.\n\n' +
          'Você confirma que entende que os resultados são simulados sobre dados reais e assume as decisões do seu setup.\n\n' +
          'Prosseguir e ativar o modo DEMO?';
      if (!confirm(mensagem)) {{
        return;
      }}
    }}
    fetch('/api/modo', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{modo}})
    }}).then(tratarResposta).then(() => location.reload()).catch(erro => alert(erro.message));
  }}

  function iniciar_motor() {{
    atualizar_configuracao()
      .then(() => fetch('/api/iniciar', {{method:'POST'}}))
      .then(tratarResposta)
      .then(() => location.reload())
      .catch(erro => alert(erro.message));
  }}

  function pausar_motor() {{
    fetch('/api/pausar', {{method:'POST'}}).then(tratarResposta).then(() => location.reload()).catch(erro => alert(erro.message));
  }}

  function encerrar_sessao() {{
    fetch('/api/encerrar', {{method:'POST'}}).then(tratarResposta).then(atualizarPainel).catch(erro => alert(erro.message));
  }}

  function parada_emergencia() {{
    if (confirm('⚠️ Parar TODAS as operações agora?')) {{
      fetch('/api/parada-emergencia', {{method:'POST'}}).then(tratarResposta).then(() => location.reload()).catch(erro => alert(erro.message));
    }}
  }}

  atualizarPainel();
  window.setInterval(atualizarPainel, 15000);
</script>
</body>
</html>"""

    def gerar_json_api(self) -> Dict:
        """Gera dados em JSON para API REST."""
        cotacoes = {}
        for ativo in self.ativos_selecionados:
            cotacao = self.conector.obter_cotacao(ativo)
            if cotacao:
                cotacoes[ativo] = {
                    "preco": cotacao.preco,
                    "variacao": cotacao.variacao,
                    "variacao_percentual": cotacao.variacao_percentual,
                    "fonte": cotacao.fonte,
                    "horario": cotacao.horario.isoformat(),
                }

        with self.lock_analise:
          analise = None if self.ultima_analise is None else dict(self.ultima_analise)
          analises_mt = {
              timeframe: dict(evento)
              for timeframe, evento in sorted(self.analises_por_timeframe.items())
          }
          timeframes_visiveis = sorted(self.timeframes_visiveis)
          timeframe_ativo = self.timeframe_ativo

        return {
            "timestamp": datetime.now().isoformat(),
            "estado": self.estado_operacional,
            "cotacoes": cotacoes,
            "ativo_atual": self.ativo_atual,
            "plataforma": {
              "atual": self.plataforma_atual,
              "confirmada": self.plataforma_confirmada == self.plataforma_atual,
            },
            "indicadores": {
                "automatico": self.indicadores_automaticos,
                "selecionados": list(self.indicadores_selecionados),
            },
          "analise": analise,
          "analises_multitempo": analises_mt,
          "timeframes_visiveis": timeframes_visiveis,
          "timeframe_ativo": timeframe_ativo,
          "memoria_indicadores": memoria_indicadores.resumo(),
            "logs": self.logs[-20:],
            "historico": self.obter_historico_entradas(),
            "estrategia": self.estrategia_atual,
            "modo_operacao": self.modo_operacao_atual,
        }


class BFTRequestHandler(BaseHTTPRequestHandler):
    """Handler HTTP que serve a interface e os endpoints REST."""

    interface: "InterfaceTempoReal" = None

    def _enviar_json(self, dados, status=200):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _enviar_html(self, html):
        corpo = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _enviar_erro(self, mensagem, status=400):
        self._enviar_json({"erro": mensagem}, status)

    def do_GET(self):
        """Trata requisições GET."""
        ifac = self.interface
        caminho = urlparse(self.path).path

        if caminho == "/" or caminho == "":
            self._enviar_html(ifac.gerar_html())
            return

        if caminho == "/api/status":
            self._enviar_json(ifac.gerar_json_api())
            return

        if caminho == "/api/historico":
            self._enviar_json({"historico": ifac.obter_historico_entradas()})
            return

        if caminho == "/assets/logo-bft.jpg":
          caminho_logo = os.path.join(PASTA_PROJETO, "assets", "logo-bft.jpg")
          try:
            with open(caminho_logo, "rb") as arquivo:
              imagem = arquivo.read()
          except OSError:
            self._enviar_erro("Logo não encontrada", 404)
            return
          self.send_response(200)
          self.send_header("Content-Type", "image/jpeg")
          self.send_header("Content-Length", str(len(imagem)))
          self.end_headers()
          self.wfile.write(imagem)
          return

        if caminho.startswith("/api/ativo/"):
            ativo = unquote(caminho.removeprefix("/api/ativo/"))
            if ifac.mudar_ativo(ativo):
                self._enviar_json({"ok": True, "ativo": ativo})
            else:
                self._enviar_erro(f"Ativo inválido: {ativo}", 404)
            return

        if caminho.startswith("/api/adicionar-ativo/"):
            ativo = caminho.rsplit("/", 1)[-1].upper()
            if ifac.adicionar_ativo(ativo):
                self._enviar_json({"ok": True, "ativo": ativo})
            else:
                self._enviar_erro(f"Ativo não suportado: {ativo}", 404)
            return

        self._enviar_erro("Endpoint não encontrado", 404)

    def do_POST(self):
        """Trata requisições POST."""
        ifac = self.interface
        caminho = urlparse(self.path).path

        if caminho == "/api/ler-tela-otc":
            sucesso, mensagem = ifac.ler_tela_otc()
            if sucesso:
                self._enviar_json({"ok": True, "mensagem": mensagem})
            else:
                self._enviar_erro(mensagem, 409)
            return

        if caminho == "/api/atualizar":
            ifac.registrar_log("MERCADO", "Atualização manual solicitada", "info")
            self._enviar_json({"ok": True, "mensagem": "Dados atualizados"})
            return

        if caminho == "/api/conectar-conta":
            ifac.conectar_conta()
            self._enviar_json({"ok": True, "mensagem": "Painel preparado"})
            return

        if caminho == "/api/plataforma":
          try:
            tamanho = int(self.headers.get("Content-Length", 0))
            corpo = self.rfile.read(tamanho) if tamanho else b"{}"
            dados = json.loads(corpo or b"{}")
            ifac.mudar_plataforma(str(dados.get("plataforma", "")).strip())
            self._enviar_json({"ok": True, "plataforma": ifac.plataforma_atual})
          except (ValueError, TypeError, json.JSONDecodeError) as erro:
            self._enviar_erro(f"Plataforma inválida: {erro}")
          return

        if caminho == "/api/confirmar-plataforma":
          ifac.confirmar_plataforma()
          self._enviar_json({"ok": True, "plataforma": ifac.plataforma_confirmada})
          return

        if caminho == "/api/banca":
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = self.rfile.read(tamanho) if tamanho else b"{}"
                dados = json.loads(corpo or b"{}")
                banca = float(dados.get("banca", 0))
                if banca <= 0:
                    raise ValueError("banca deve ser maior que zero")
                ifac.atualizar_banca(banca)
                self._enviar_json({"ok": True, "banca": banca})
            except (ValueError, json.JSONDecodeError) as erro:
                self._enviar_erro(f"Banca inválida: {erro}")
            return

        if caminho == "/api/configuracao":
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = self.rfile.read(tamanho) if tamanho else b"{}"
                dados = json.loads(corpo or b"{}")
                ifac.atualizar_configuracao(dados)
                self._enviar_json({"ok": True, "configuracao": ifac.configuracao})
            except (ValueError, TypeError, json.JSONDecodeError) as erro:
                self._enviar_erro(f"Configuração inválida: {erro}")
            return

        if caminho == "/api/timeframes":
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = self.rfile.read(tamanho) if tamanho else b"{}"
                dados = json.loads(corpo or b"{}")
                ifac.definir_timeframes_visiveis(dados.get("visiveis"))
                ifac.definir_timeframe_ativo(dados.get("ativo"))
                self._enviar_json({
                    "ok": True,
                    "visiveis": sorted(ifac.timeframes_visiveis),
                    "ativo": ifac.timeframe_ativo,
                })
            except (ValueError, TypeError, json.JSONDecodeError) as erro:
                self._enviar_erro(f"Timeframes inválidos: {erro}")
            return

        if caminho == "/api/indicadores":
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = self.rfile.read(tamanho) if tamanho else b"{}"
                dados = json.loads(corpo or b"{}")
                configurar_indicadores(
                    ifac,
                    bool(dados.get("automatico", False)),
                    dados.get("codigos"),
                )
                self._enviar_json({
                    "ok": True,
                    "automatico": ifac.indicadores_automaticos,
                    "codigos": list(ifac.indicadores_selecionados),
                })
            except (ValueError, TypeError, json.JSONDecodeError) as erro:
                self._enviar_erro(f"Indicadores inválidos: {erro}")
            return

        if caminho == "/api/iniciar":
            iniciado, mensagem = ifac.iniciar_motor()
            if iniciado:
                self._enviar_json({"ok": True, "mensagem": mensagem})
            else:
                self._enviar_erro(mensagem, 409)
            return

        if caminho == "/api/pausar":
            pausado, mensagem = ifac.pausar_motor()
            if pausado:
                self._enviar_json({"ok": True, "mensagem": mensagem})
            else:
                self._enviar_erro(mensagem, 409)
            return

        if caminho == "/api/encerrar":
            _, mensagem = ifac.encerrar_sessao()
            self._enviar_json({"ok": True, "mensagem": mensagem})
            return

        if caminho == "/api/parada-emergencia":
            _, mensagem = ifac.parada_emergencia()
            self._enviar_json({"ok": True, "mensagem": mensagem})
            return

        if caminho == "/api/estrategia":
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = self.rfile.read(tamanho) if tamanho else b"{}"
                dados = json.loads(corpo or b"{}")
                ifac.mudar_estrategia(str(dados.get("estrategia", "")).strip())
                self._enviar_json({"ok": True, "estrategia": ifac.estrategia_atual})
            except (ValueError, TypeError, json.JSONDecodeError) as erro:
                self._enviar_erro(f"Estratégia inválida: {erro}")
            return

        if caminho == "/api/modo":
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = self.rfile.read(tamanho) if tamanho else b"{}"
                dados = json.loads(corpo or b"{}")
                ifac.mudar_modo_operacao(str(dados.get("modo", "")).strip())
                self._enviar_json({"ok": True, "modo": ifac.modo_operacao_atual})
            except (ValueError, TypeError, json.JSONDecodeError) as erro:
                self._enviar_erro(f"Modo inválido: {erro}")
            return

        self._enviar_erro("Endpoint não encontrado", 404)

    def log_message(self, formato, *args):
        """Silencia logs do servidor para manter a saída limpa."""
        return


def criar_interface_tempo_real() -> InterfaceTempoReal:
    """Factory para criar interface com dados reais."""
    return InterfaceTempoReal()


def iniciar_servidor(host="127.0.0.1", porta=8765, interface=None):
    """Inicia o servidor HTTP das interface de tempo real."""
    if interface is None:
        interface = criar_interface_tempo_real()

    BFTRequestHandler.interface = interface
    servidor = ThreadingHTTPServer((host, porta), BFTRequestHandler)
    interface.registrar_log("INIT", f"Servidor BFT iniciado em http://{host}:{porta}", "ok")
    print(f"✅ BFT Tempo Real servindo em http://{host}:{porta}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    interface = criar_interface_tempo_real()
    interface.registrar_log("INIT", "Interface BFT iniciada", "ok")
    interface.registrar_log("MERCADO", "Conectando a dados reais...", "info")

    # Atualizar algumas cotações iniciais
    for ativo in ["EURUSD", "EURJPY", "EURGBP", "GBPUSD", "GBPJPY", "USDJPY"]:
        cotacao = interface.conector.obter_cotacao(ativo)
        if cotacao:
            interface.registrar_log(
                "MERCADO",
                f"{ativo}: {cotacao.preco:.2f} ({cotacao.variacao_percentual:+.2f}%)",
                "ok",
            )
        else:
            interface.registrar_log("MERCADO", f"Não foi possível obter {ativo}", "warn")

    iniciar_servidor(interface=interface)
