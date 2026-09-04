"""Executa OCR nativo da Apple sobre uma captura já autorizada."""

from dataclasses import dataclass
import os
import re
import subprocess


@dataclass(frozen=True)
class LeituraTexto:
    sucesso: bool
    textos: tuple[str, ...]
    mensagem: str


def ler_textos(caminho_imagem, executor=subprocess.run):
    if not os.path.isfile(caminho_imagem):
        return LeituraTexto(False, (), "captura não encontrada")
    pasta_scripts = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
    )
    fonte = os.path.join(pasta_scripts, "ocr_macos.m")
    binario = "/private/tmp/bft_ocr_macos"
    try:
        precisa_compilar = (
            executor is not subprocess.run
            or not os.path.isfile(binario)
            or os.path.getmtime(binario) < os.path.getmtime(fonte)
        )
        if precisa_compilar:
            compilacao = executor(
                [
                    "/usr/bin/clang", "-fobjc-arc",
                    "-framework", "Foundation",
                    "-framework", "Vision",
                    "-framework", "ImageIO",
                    "-framework", "CoreGraphics",
                    fonte, "-o", binario,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env={**os.environ, "CLANG_MODULE_CACHE_PATH": "/private/tmp/bft_clang_cache"},
            )
            if compilacao.returncode != 0:
                detalhe = (compilacao.stderr or "erro desconhecido").strip()
                return LeituraTexto(False, (), f"leitor visual não compilou: {detalhe}")
        resultado = executor(
            [binario, caminho_imagem],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as erro:
        return LeituraTexto(False, (), f"leitor visual não iniciou: {erro}")
    if resultado.returncode != 0:
        detalhe = (resultado.stderr or "erro desconhecido").strip()
        return LeituraTexto(False, (), f"leitor visual falhou: {detalhe}")
    textos = tuple(linha.strip() for linha in resultado.stdout.splitlines() if linha.strip())
    if not textos:
        return LeituraTexto(False, (), "nenhum texto reconhecido")
    return LeituraTexto(True, textos, f"{len(textos)} textos reconhecidos")


def detectar_tipo_conta(textos):
    unido = " ".join(textos).upper()
    if any(rotulo in unido for rotulo in (
        "PRACTICE ACCOUNT", "CONTA DE PRÁTICA", "DEMO ACCOUNT",
        "CONTA DEMO", "DEMO BALANCE",
    )):
        return "PRÁTICA"
    if "REAL ACCOUNT" in unido or "CONTA REAL" in unido:
        return "REAL"
    return "DESCONHECIDA"


def extrair_payouts(textos):
    """Extrai percentuais; a região visual decidirá depois quais são Profit."""
    encontrados = []
    for texto in textos:
        for valor in re.findall(r"(?<!\d)(\d{1,3})\s*%", texto):
            numero = int(valor)
            if 0 <= numero <= 100:
                encontrados.append(numero / 100)
    return tuple(encontrados)
