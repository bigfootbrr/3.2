"""Confirma visualmente o tipo de conta exibido pela IQ Option."""

from dataclasses import dataclass
import os

from leitor_texto_macos import detectar_tipo_conta, ler_textos


@dataclass(frozen=True)
class ResultadoConta:
    sucesso: bool
    tipo: str
    mensagem: str

    @property
    def demo(self):
        return self.tipo == "PRÁTICA"


def ler_tipo_conta(caminho_captura, leitor=ler_textos):
    """Exige o texto explícito do seletor de conta; saldo não é suficiente."""
    if not os.path.isfile(caminho_captura):
        return ResultadoConta(False, "DESCONHECIDA", "captura da IQ não encontrada")
    leitura = leitor(caminho_captura)
    if not leitura.sucesso:
        return ResultadoConta(False, "DESCONHECIDA", leitura.mensagem)
    tipo = detectar_tipo_conta(leitura.textos)
    if tipo == "PRÁTICA":
        return ResultadoConta(True, tipo, "conta de prática confirmada na tela")
    if tipo == "REAL":
        return ResultadoConta(True, tipo, "conta real confirmada na tela")
    return ResultadoConta(
        False,
        tipo,
        "tipo de conta não apareceu por escrito; abra o seletor de saldo da IQ",
    )
