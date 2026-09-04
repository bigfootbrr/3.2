"""Planeja a navegação entre até nove abas da IQ, sem controlar a tela ainda."""

from dataclasses import dataclass, field

from maquina_operacao import EstadoOperacao, MaquinaOperacao


@dataclass
class AbaIq:
    numero: int
    ativo: str
    aberta: bool = True
    maquina: MaquinaOperacao = field(default_factory=MaquinaOperacao)


@dataclass(frozen=True)
class AcaoInterface:
    autorizada: bool
    comando: str | None
    motivo: str
    aba: int | None = None


class ControladorAbasIq:
    """Mapeia ativos a Cmd+1...Cmd+9 e falha fechado em qualquer dúvida."""

    def __init__(self):
        self._abas = {}
        self._aba_selecionada = None

    def registrar_aba(self, numero, ativo):
        if numero not in range(1, 10):
            raise ValueError("a IQ permite atalhos de aba entre 1 e 9")
        if not ativo or not ativo.strip():
            raise ValueError("ativo da aba não pode ser vazio")
        ativo = _normalizar(ativo)
        for existente in self._abas.values():
            if existente.ativo == ativo and existente.numero != numero:
                raise ValueError("o mesmo ativo não pode ocupar duas abas registradas")
        self._abas[numero] = AbaIq(numero, ativo)

    def fechar_aba(self, numero):
        aba = self._obter(numero)
        aba.aberta = False
        if self._aba_selecionada == numero:
            self._aba_selecionada = None

    def solicitar_fechar_aba_atual(self):
        if self._aba_selecionada is None:
            return AcaoInterface(False, None, "nenhuma aba está selecionada")
        aba = self._obter(self._aba_selecionada)
        if aba.maquina.estado != EstadoOperacao.PRONTO:
            return AcaoInterface(
                False, None, "aba possui operação ou resultado pendente", aba=aba.numero
            )
        abertas = sum(1 for item in self._abas.values() if item.aberta)
        if abertas <= 1:
            return AcaoInterface(
                False, None, "a IQ não fecha a única aba aberta com Cmd+W", aba=aba.numero
            )
        return AcaoInterface(
            True,
            "CMD+W",
            "fechar aba atual e depois confirmar visualmente",
            aba=aba.numero,
        )

    def confirmar_aba_fechada(self, numero, fechada):
        aba = self._obter(numero)
        if not fechada:
            return AcaoInterface(
                False, None, "a aba continua visível; registro preservado", aba=numero
            )
        self.fechar_aba(numero)
        return AcaoInterface(True, None, "fechamento da aba confirmado", aba=numero)

    def selecionar_proxima_aba_pronta(self):
        abertas = sorted(
            item.numero
            for item in self._abas.values()
            if item.aberta and item.maquina.estado == EstadoOperacao.PRONTO
        )
        if not abertas:
            return AcaoInterface(
                False, None, "nenhuma outra aba está pronta para receber sinais"
            )

        atual = self._aba_selecionada or 0
        posteriores = [numero for numero in abertas if numero > atual]
        destino = posteriores[0] if posteriores else abertas[0]

        if destino == self._aba_selecionada and len(abertas) == 1:
            return AcaoInterface(
                False, None, "somente a aba atual está pronta", aba=destino
            )

        self._aba_selecionada = destino
        return AcaoInterface(
            True,
            f"CMD+{destino}",
            "próxima aba pronta selecionada; aba do resultado permanece aberta",
            aba=destino,
        )

    def selecionar_ativo(self, ativo):
        ativo = _normalizar(ativo)
        aba = next(
            (item for item in self._abas.values() if item.ativo == ativo),
            None,
        )
        if aba is None:
            return AcaoInterface(False, None, "ativo não registrado nas nove abas")
        if not aba.aberta:
            return AcaoInterface(False, None, "aba do ativo está fechada", aba=aba.numero)
        if aba.maquina.estado != EstadoOperacao.PRONTO:
            return AcaoInterface(
                False, None, "aba ainda possui operação ou resultado pendente", aba=aba.numero
            )
        self._aba_selecionada = aba.numero
        return AcaoInterface(
            True,
            f"CMD+{aba.numero}",
            "selecionar aba e verificar visualmente o ativo antes de continuar",
            aba=aba.numero,
        )

    def confirmar_aba_visivel(self, numero, ativo_visivel):
        aba = self._obter(numero)
        if self._aba_selecionada != numero:
            return AcaoInterface(False, None, "aba esperada não está selecionada", aba=numero)
        if _normalizar(ativo_visivel) != aba.ativo:
            aba.maquina.bloquear("ativo visível diferente do ativo registrado")
            return AcaoInterface(False, None, "nome do ativo não confere", aba=numero)
        return AcaoInterface(True, None, "ativo da aba confirmado", aba=numero)

    def preparar_entrada_demo(self, numero, sinal, validacoes_aprovadas):
        aba = self._obter(numero)
        if self._aba_selecionada != numero:
            return AcaoInterface(False, None, "aba correta não está selecionada", aba=numero)
        recebida = aba.maquina.receber_sinal(aba.ativo, sinal)
        if not recebida.aceita:
            return AcaoInterface(False, None, recebida.motivo, aba=numero)
        validacao = aba.maquina.concluir_validacao(
            validacoes_aprovadas,
            "payout, probabilidade ou estado da tela recusaram a entrada",
        )
        if not validacao.aceita or not aba.maquina.pode_clicar:
            return AcaoInterface(False, None, validacao.motivo, aba=numero)
        comando = "CLICK_COMPRA_DEMO" if sinal == "ALTA" else "CLICK_VENDA_DEMO"
        return AcaoInterface(
            True, comando, "um único clique demo autorizado", aba=numero
        )

    def confirmar_clique_demo(self, numero):
        aba = self._obter(numero)
        transicao = aba.maquina.confirmar_clique_demo()
        return AcaoInterface(
            transicao.aceita,
            None,
            transicao.motivo,
            aba=numero,
        )

    def obter_estado(self, numero):
        return self._obter(numero).maquina.estado

    def _obter(self, numero):
        try:
            return self._abas[numero]
        except KeyError as erro:
            raise ValueError("aba ainda não registrada") from erro


def _normalizar(ativo):
    return ativo.strip().upper().replace("/", "").replace(" ", "")
