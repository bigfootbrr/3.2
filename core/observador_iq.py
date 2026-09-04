"""Valida uma leitura da tela da IQ antes de qualquer ação de interface.

Não tira capturas, não move o mouse e não envia ordens. Recebe uma leitura
produzida por uma futura camada visual e falha fechado se houver dúvida.
"""

from dataclasses import dataclass
import time


@dataclass(frozen=True)
class LeituraTelaIq:
    ativo: str | None
    payout: float | None
    conta_demo: bool | None
    botoes_operacao_visiveis: bool
    painel_resultado_visivel: bool
    operacao_em_andamento: bool
    capturada_em: float


@dataclass(frozen=True)
class ValidacaoTelaIq:
    aprovada: bool
    motivo: str
    ativo: str | None = None
    payout: float | None = None


class ObservadorIq:
    """Confere a leitura visual; não confia em valores digitados no app."""

    def __init__(self, payout_minimo=0.80, idade_maxima_segundos=2.0):
        if not 0 <= payout_minimo <= 1:
            raise ValueError("payout mínimo deve estar entre 0 e 1")
        if idade_maxima_segundos <= 0:
            raise ValueError("idade máxima deve ser positiva")
        self.payout_minimo = payout_minimo
        self.idade_maxima_segundos = idade_maxima_segundos

    def validar_entrada(self, leitura, ativo_esperado, tipo_conta="DEMO", agora=None):
        tipo_conta = str(tipo_conta or "DEMO").strip().upper()
        if tipo_conta not in {"DEMO", "REAL"}:
            raise ValueError("tipo de conta deve ser DEMO ou REAL")

        agora = time.monotonic() if agora is None else agora
        if agora - leitura.capturada_em > self.idade_maxima_segundos:
            return ValidacaoTelaIq(False, "leitura da tela está desatualizada")
        if leitura.capturada_em > agora:
            return ValidacaoTelaIq(False, "horário da leitura da tela é inválido")

        if tipo_conta == "DEMO":
            conta_confirmada = leitura.conta_demo is True
            nome_conta = "demonstração"
            mensagem_sucesso = "tela demo confirmada, ativo confere e payout aprovado"
        else:
            conta_confirmada = leitura.conta_demo is False
            nome_conta = "real"
            mensagem_sucesso = "tela real confirmada, ativo confere e payout aprovado"

        if not conta_confirmada:
            return ValidacaoTelaIq(False, f"conta de {nome_conta} não confirmada")
        if not leitura.ativo:
            return ValidacaoTelaIq(False, "ativo não foi reconhecido na tela")

        ativo = _normalizar_ativo(leitura.ativo)
        if ativo != _normalizar_ativo(ativo_esperado):
            return ValidacaoTelaIq(False, "ativo visível diferente do esperado", ativo)
        if leitura.payout is None:
            return ValidacaoTelaIq(False, "payout não foi reconhecido", ativo)
        if not 0 <= leitura.payout <= 1:
            return ValidacaoTelaIq(False, "payout reconhecido é inválido", ativo)
        if leitura.payout <= self.payout_minimo:
            return ValidacaoTelaIq(
                False,
                f"payout abaixo do mínimo de {self.payout_minimo:.0%}",
                ativo,
                leitura.payout,
            )
        if leitura.operacao_em_andamento:
            return ValidacaoTelaIq(False, "já existe operação em andamento", ativo, leitura.payout)
        if leitura.painel_resultado_visivel:
            return ValidacaoTelaIq(False, "resultado anterior ainda está visível", ativo, leitura.payout)
        if not leitura.botoes_operacao_visiveis:
            return ValidacaoTelaIq(False, "botões de compra e venda não estão disponíveis", ativo, leitura.payout)

        return ValidacaoTelaIq(
            True,
            mensagem_sucesso,
            ativo,
            leitura.payout,
        )

    def validar_entrada_demo(self, leitura, ativo_esperado, agora=None):
        return self.validar_entrada(leitura, ativo_esperado, tipo_conta="DEMO", agora=agora)

    def validar_entrada_real(self, leitura, ativo_esperado, agora=None):
        return self.validar_entrada(leitura, ativo_esperado, tipo_conta="REAL", agora=agora)


def _normalizar_ativo(ativo):
    return ativo.strip().upper().replace("/", "").replace(" ", "")
