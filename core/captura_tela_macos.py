"""Teste local de permissão de captura; não controla mouse nem teclado."""

from dataclasses import dataclass
import os
import subprocess


@dataclass(frozen=True)
class ResultadoCaptura:
    sucesso: bool
    caminho: str | None
    mensagem: str


def testar_captura(
    caminho="/private/tmp/bft_iq_teste.png",
    executor=subprocess.run,
):
    try:
        resultado = executor(
            ["/usr/sbin/screencapture", "-x", caminho],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as erro:
        return ResultadoCaptura(False, None, f"falha ao iniciar captura: {erro}")

    existe = os.path.isfile(caminho) and os.path.getsize(caminho) > 0
    if resultado.returncode != 0 or not existe:
        detalhe = (resultado.stderr or resultado.stdout or "permissão não concedida").strip()
        return ResultadoCaptura(
            False,
            None,
            f"captura bloqueada pelo macOS: {detalhe}",
        )
    return ResultadoCaptura(True, caminho, "captura autorizada; IQ ainda não foi analisada")
