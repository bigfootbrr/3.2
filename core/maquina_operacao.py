"""Máquina de estados para impedir ações duplicadas na interface da corretora."""

from dataclasses import dataclass
from enum import Enum


class EstadoOperacao(str, Enum):
    PRONTO = "PRONTO"
    VALIDANDO = "VALIDANDO"
    ENTRADA_AUTORIZADA = "ENTRADA_AUTORIZADA"
    ENTRADA_ENVIADA = "ENTRADA_ENVIADA"
    EM_OPERACAO = "EM_OPERACAO"
    AGUARDANDO_RESULTADO = "AGUARDANDO_RESULTADO"
    FECHANDO_RESULTADO = "FECHANDO_RESULTADO"
    BLOQUEADO = "BLOQUEADO"
    EMERGENCIA = "EMERGENCIA"


@dataclass(frozen=True)
class Transicao:
    aceita: bool
    estado: EstadoOperacao
    motivo: str


class MaquinaOperacao:
    """Controla um ativo/aba; não contém código de clique ou ordem real."""

    def __init__(self):
        self.estado = EstadoOperacao.PRONTO
        self.ativo = None
        self.sinal = None
        self.resultado = None

    @property
    def pode_clicar(self):
        return self.estado == EstadoOperacao.ENTRADA_AUTORIZADA

    def receber_sinal(self, ativo, sinal):
        if sinal not in {"ALTA", "BAIXA"}:
            return Transicao(False, self.estado, "sinal sem direção")
        if self.estado != EstadoOperacao.PRONTO:
            return Transicao(False, self.estado, "interface ainda não está pronta")
        self.ativo = ativo
        self.sinal = sinal
        self.resultado = None
        return self._mudar(EstadoOperacao.VALIDANDO, "sinal recebido para validação")

    def concluir_validacao(self, aprovada, motivo=""):
        if self.estado != EstadoOperacao.VALIDANDO:
            return Transicao(False, self.estado, "não existe validação pendente")
        if not aprovada:
            self._limpar()
            return self._mudar(
                EstadoOperacao.PRONTO,
                motivo or "validação recusada; nenhuma entrada enviada",
            )
        return self._mudar(
            EstadoOperacao.ENTRADA_AUTORIZADA,
            "todas as travas aprovadas; um único clique permitido",
        )

    def confirmar_clique_demo(self):
        if not self.pode_clicar:
            return Transicao(False, self.estado, "clique duplicado ou não autorizado")
        return self._mudar(
            EstadoOperacao.ENTRADA_ENVIADA,
            "clique demo enviado; novos cliques bloqueados",
        )

    def confirmar_operacao_visivel(self):
        if self.estado != EstadoOperacao.ENTRADA_ENVIADA:
            return Transicao(False, self.estado, "entrada enviada não confirmada")
        return self._mudar(
            EstadoOperacao.EM_OPERACAO,
            "operação visível na plataforma",
        )

    def marcar_expiracao(self):
        if self.estado != EstadoOperacao.EM_OPERACAO:
            return Transicao(False, self.estado, "não existe operação ativa")
        return self._mudar(
            EstadoOperacao.AGUARDANDO_RESULTADO,
            "tempo expirou; aguardando resultado da plataforma",
        )

    def registrar_resultado(self, resultado):
        if self.estado != EstadoOperacao.AGUARDANDO_RESULTADO:
            return Transicao(False, self.estado, "resultado fora de sequência")
        self.resultado = resultado
        return self._mudar(
            EstadoOperacao.FECHANDO_RESULTADO,
            "resultado registrado; aguardando painel desaparecer",
        )

    def confirmar_tela_livre(self):
        if self.estado != EstadoOperacao.FECHANDO_RESULTADO:
            return Transicao(False, self.estado, "resultado anterior ainda não foi tratado")
        self._limpar()
        return self._mudar(
            EstadoOperacao.PRONTO,
            "painel fechado e botões disponíveis; próximo sinal liberado",
        )

    def bloquear(self, motivo):
        return self._mudar(EstadoOperacao.BLOQUEADO, motivo)

    def emergencia(self):
        return self._mudar(
            EstadoOperacao.EMERGENCIA,
            "parada de emergência; reativação manual obrigatória",
        )

    def rearmar_manualmente(self):
        if self.estado not in {EstadoOperacao.BLOQUEADO, EstadoOperacao.EMERGENCIA}:
            return Transicao(False, self.estado, "rearme não necessário")
        self._limpar()
        return self._mudar(EstadoOperacao.PRONTO, "máquina rearmada manualmente")

    def _mudar(self, estado, motivo):
        self.estado = estado
        return Transicao(True, estado, motivo)

    def _limpar(self):
        self.ativo = None
        self.sinal = None
        self.resultado = None
