"""Reconhece o ativo selecionado usando apenas a região do nome no gráfico."""

from dataclasses import dataclass
import os
import re

from PIL import Image

from calibracao_iq import PERFIL_IQ_2026_08_30
from leitor_texto_macos import ler_textos
from painel_abas_iq import ATIVOS_IQ_CONHECIDOS


@dataclass(frozen=True)
class ResultadoAtivo:
    sucesso: bool
    ativo: str | None
    mensagem: str


def ler_ativo(
    caminho_captura,
    caminho_recorte="/private/tmp/bft_iq_ativo.png",
    leitor=ler_textos,
    ativos=ATIVOS_IQ_CONHECIDOS,
):
    if not os.path.isfile(caminho_captura):
        return ResultadoAtivo(False, None, "captura da IQ não encontrada")
    try:
        with Image.open(caminho_captura) as imagem:
            caixa = PERFIL_IQ_2026_08_30.ativo_selecionado.converter(*imagem.size)
            imagem.crop(caixa).save(caminho_recorte)
    except (OSError, ValueError) as erro:
        return ResultadoAtivo(False, None, f"não foi possível recortar o ativo: {erro}")

    leitura = leitor(caminho_recorte)
    if not leitura.sucesso:
        return ResultadoAtivo(False, None, leitura.mensagem)
    reconhecido = _normalizar(" ".join(leitura.textos))
    encontrados = []
    for ativo in ativos:
        completo = _normalizar(ativo)
        base = completo.replace("OTC", "")
        if completo in reconhecido or (base and base in reconhecido):
            encontrados.append(ativo)
    if len(encontrados) != 1:
        generico = _extrair_ativo_otc(leitura.textos)
        if generico is None:
            return ResultadoAtivo(False, None, "ativo não reconhecido com segurança")
        return ResultadoAtivo(True, generico, f"novo ativo observado: {generico}")
    return ResultadoAtivo(True, encontrados[0], f"ativo observado: {encontrados[0]}")


def _normalizar(texto):
    return re.sub(r"[^A-Z0-9]", "", texto.upper())


def _extrair_ativo_otc(textos):
    """Extrai somente um cabeçalho explícito `NOME (OTC)`; falha fechado."""
    candidatos = []
    for texto in textos:
        for nome in re.findall(
            r"([A-Z0-9][A-Z0-9 ./_&+-]{1,44}?)\s*\(\s*OTC\s*\)",
            texto.upper(),
        ):
            nome = re.sub(r"\s+", " ", nome).strip(" .-_")
            if 2 <= len(re.sub(r"[^A-Z0-9]", "", nome)) <= 40:
                candidatos.append(f"{nome} (OTC)")
    unicos = list(dict.fromkeys(candidatos))
    return unicos[0] if len(unicos) == 1 else None
