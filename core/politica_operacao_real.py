"""Política de operação responsável para todas as plataformas.

Define limites operacionais, gatilhos de pausa e regras de recuperação
para garantir operação conservadora em contas reais.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


@dataclass
class ConfiguracaoOperacional:
    """Limites operacionais por sessão."""
    # Limites de volume
    max_trades_por_sessao: int = 10
    max_trades_consecutivos_sem_pausa: int = 3

    # Limites de perda
    perda_maxima_percentual: float = 0.03  # 3% do capital
    perda_gatilho_pausa_minutos: int = 30

    # Janelas de operação
    horario_inicio_operacao: str = "09:00"
    horario_fim_operacao: str = "16:00"
    permitir_otc_fora_horario: bool = True

    # Recuperação após perda
    reducao_posicao_apos_drawdown: float = 0.5  # 50% da posição normal
    vitoria_consecutivas_para_recuperacao: int = 3

    # Segurança geral
    exigir_confirmacao_plataforma: bool = True
    exigir_snapshot_anterior: bool = True
    exigir_payout_maior_que_oitenta: bool = True
    exigir_confluencia_minima_setenta_e_cinco: bool = True


@dataclass
class EstadoOperacional:
    """Rastreia o estado operacional da sessão em tempo real."""
    # Identificação
    plataforma: str = "IQ Option"
    sessao_id: str = field(default_factory=lambda: str(int(time.time())))
    tipo_conta: str = "DEMO"  # DEMO ou REAL

    # Contadores de volume
    trades_realizados: int = 0
    trades_consecutivos_sem_pausa: int = 0

    # Rastreamento de perda
    perda_percentual_sessao: float = 0.0
    em_pausa_apos_perda: bool = False
    tempo_pausa_fim: Optional[float] = None

    # Rastreamento de vitórias para recuperação
    vitoria_consecutivas: int = 0
    posicao_reduzida: bool = False

    # Histórico de eventos
    eventos: list = field(default_factory=list)
    horario_inicio_sessao: float = field(default_factory=time.time)

    def registrar_evento(self, tipo: str, descricao: str, dados: Optional[Dict] = None):
        """Registra um evento operacional para auditoria."""
        evento = {
            "timestamp": time.time(),
            "tipo": tipo,
            "descricao": descricao,
            "dados": dados or {},
        }
        self.eventos.append(evento)

    def trade_executado_com_sucesso(self):
        """Incrementa contadores após um trade bem-sucedido."""
        self.trades_realizados += 1
        self.trades_consecutivos_sem_pausa += 1
        self.vitoria_consecutivas += 1
        self.registrar_evento("TRADE_EXECUTADO", f"Trade #{self.trades_realizados}")

    def trade_executado_com_perda(self, percentual_perda: float):
        """Processa um trade com perda."""
        self.perda_percentual_sessao += percentual_perda
        self.trades_consecutivos_sem_pausa += 1
        self.vitoria_consecutivas = 0
        self.registrar_evento(
            "TRADE_PERDA",
            f"Perda: {percentual_perda:.2%}",
            {"perda": percentual_perda},
        )

    def pausa_apos_perda(self, minutos: int):
        """Inicia pausa após atingir limite de perda."""
        self.em_pausa_apos_perda = True
        self.tempo_pausa_fim = time.time() + (minutos * 60)
        self.registrar_evento(
            "PAUSA_PERDA",
            f"Pausa de {minutos} minutos ativada após perda",
        )

    def retomar_apos_pausa(self):
        """Permite retomada após pausa."""
        self.em_pausa_apos_perda = False
        self.tempo_pausa_fim = None
        self.trades_consecutivos_sem_pausa = 0
        self.registrar_evento("PAUSA_FINALIZADA", "Retomada operacional permitida")

    def ativar_reducao_posicao(self):
        """Ativa redução de posição após drawdown."""
        self.posicao_reduzida = True
        self.vitoria_consecutivas = 0
        self.registrar_evento("POSICAO_REDUZIDA", "Redução de posição ativada")

    def desativar_reducao_posicao(self):
        """Desativa redução após N vitórias consecutivas."""
        self.posicao_reduzida = False
        self.vitoria_consecutivas = 0
        self.registrar_evento("POSICAO_NORMALIZADA", "Posição retornada ao normal")


class ValidadorOperacao:
    """Valida operações contra a política operacional."""

    def __init__(self, config: ConfiguracaoOperacional = None):
        self.config = config or ConfiguracaoOperacional()

    def validar_para_operacao_real(
        self,
        estado: EstadoOperacional,
        confluencia: float,
        payout: float,
        plataforma_confirmada: bool,
        snapshot_valido: bool,
    ) -> tuple[bool, str]:
        """Valida se a operação pode prosseguir em modo real."""
        # 1. Verificar confirmação de plataforma
        if self.config.exigir_confirmacao_plataforma and not plataforma_confirmada:
            return False, "Plataforma não confirmada"

        # 2. Verificar snapshot anterior
        if self.config.exigir_snapshot_anterior and not snapshot_valido:
            return False, "Snapshot visual não capturado"

        # 3. Verificar confluência mínima
        if self.config.exigir_confluencia_minima_setenta_e_cinco:
            if confluencia < 0.75:
                return False, f"Confluência {confluencia:.1%} abaixo de 75%"

        # 4. Verificar payout mínimo
        if self.config.exigir_payout_maior_que_oitenta:
            if payout <= 0.80:
                return False, f"Payout {payout:.1%} não maior que 80%"

        # 5. Verificar se está em pausa após perda
        if estado.em_pausa_apos_perda:
            tempo_restante = (estado.tempo_pausa_fim - time.time()) / 60
            if tempo_restante > 0:
                return False, f"Em pausa após perda: {tempo_restante:.0f}min restantes"
            estado.retomar_apos_pausa()

        # 6. Verificar limite de trades por sessão
        if estado.trades_realizados >= self.config.max_trades_por_sessao:
            return False, f"Limite de {self.config.max_trades_por_sessao} trades atingido"

        # 7. Verificar limites de perda
        if estado.perda_percentual_sessao >= self.config.perda_maxima_percentual:
            return (
                False,
                f"Perda máxima {self.config.perda_maxima_percentual:.1%} atingida",
            )

        # 8. Verificar pausa entre trades consecutivos
        if (
            estado.trades_consecutivos_sem_pausa
            >= self.config.max_trades_consecutivos_sem_pausa
        ):
            return (
                False,
                f"Máximo de {self.config.max_trades_consecutivos_sem_pausa} trades consecutivos atingido",
            )

        return True, "Operação aprovada"

    def calcular_tamanho_posicao(self, posicao_normal: float, estado: EstadoOperacional) -> float:
        """Calcula o tamanho da posição considerando a política de recuperação."""
        if estado.posicao_reduzida:
            return posicao_normal * self.config.reducao_posicao_apos_drawdown
        return posicao_normal

    def avaliar_recuperacao(self, estado: EstadoOperacional) -> str:
        """Avalia e aplica regras de recuperação após drawdown."""
        if not estado.posicao_reduzida:
            return ""

        if estado.vitoria_consecutivas >= self.config.vitoria_consecutivas_para_recuperacao:
            estado.desativar_reducao_posicao()
            return "Posição retornada ao tamanho normal após recuperação"

        return f"Posição reduzida: {estado.vitoria_consecutivas}/{self.config.vitoria_consecutivas_para_recuperacao} vitórias para recuperação"


def criar_estado_padrao(plataforma: str = "IQ Option", tipo_conta: str = "DEMO") -> EstadoOperacional:
    """Factory para criar estado operacional padrão."""
    return EstadoOperacional(plataforma=plataforma, tipo_conta=tipo_conta)
