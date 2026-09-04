"""Navegação segura nas abas da IQ; nunca envia cliques de operação."""

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True)
class ResultadoNavegacao:
    sucesso: bool
    mensagem: str


def selecionar_aba(numero, executor=subprocess.run):
    if numero not in range(1, 10):
        return ResultadoNavegacao(False, "número da aba deve ficar entre 1 e 9")

    # `withdraw()` esconde a janela do BFT, mas o Python ainda pode continuar
    # como processo frontal. Portanto a IQ precisa receber foco explicitamente.
    script = f'''tell application "System Events"
if exists process "IQ Option" then
    set frontmost of process "IQ Option" to true
else if exists process "IQOption" then
    set frontmost of process "IQOption" to true
else
    error "aplicativo IQ Option não encontrado"
end if
delay 0.25
keystroke "{numero}" using command down
end tell'''
    try:
        resultado = executor(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as erro:
        return ResultadoNavegacao(False, f"falha ao selecionar aba {numero}: {erro}")

    if resultado.returncode != 0:
        detalhe = (resultado.stderr or resultado.stdout or "acesso negado").strip()
        return ResultadoNavegacao(False, f"atalho Cmd+{numero} bloqueado: {detalhe}")
    return ResultadoNavegacao(True, f"aba {numero} selecionada")
