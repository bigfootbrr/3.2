"""Reconhece o saldo (banca) exibido pela IQ Option na tela."""

from dataclasses import dataclass
import os
import re

from leitor_texto_macos import ler_textos


@dataclass(frozen=True)
class ResultadoSaldo:
    sucesso: bool
    saldo: float | None
    mensagem: str


def _normalizar_valor(texto):
    """Extrai um valor monetário de um texto, aceitando vírgula e ponto.

    Exemplos aceitos: "8.026,86", "8026.86", "$8,026.86", "8 026,86".
    Retorna o valor como float, ou None se não for um valor válido.
    """
    # Remove símbolo de moeda e espaços.
    limpo = re.sub(r"[^\d.,]", "", texto)
    if not limpo:
        return None
    # Se tem vírgula e ponto, assume vírgula como separador decimal.
    if "," in limpo and "." in limpo:
        # Último separador é o decimal (padrão brasileiro: 1.000,50).
        if limpo.rfind(",") > limpo.rfind("."):
            limpo = limpo.replace(".", "").replace(",", ".")
        else:
            limpo = limpo.replace(",", "")
    elif "," in limpo:
        # Só vírgula: pode ser decimal (1,50) ou milhar (1,000).
        partes = limpo.split(",")
        if len(partes) == 2 and len(partes[1]) <= 2:
            limpo = limpo.replace(",", ".")
        else:
            limpo = limpo.replace(",", "")
    try:
        valor = float(limpo)
    except ValueError:
        return None
    if valor <= 0:
        return None
    return valor


def ler_saldo(
    caminho_captura,
    leitor=ler_textos,
):
    """Lê o saldo da IQ Option a partir da captura da tela."""
    if not os.path.isfile(caminho_captura):
        return ResultadoSaldo(False, None, "captura da IQ não encontrada")
    leitura = leitor(caminho_captura)
    if not leitura.sucesso:
        return ResultadoSaldo(False, None, leitura.mensagem)

    # Procura por um valor monetário nos textos reconhecidos.
    # Prioriza textos com cifrão ($), que é o padrão do saldo da IQ.
    candidatos = []
    for texto in leitura.textos:
        if "$" in texto:
            valor = _normalizar_valor(texto)
            if valor is not None:
                candidatos.append((valor, texto))

    if not candidatos:
        return ResultadoSaldo(False, None, "saldo não reconhecido na tela")

    # Pega o maior valor com cifrão (o saldo costuma ser o maior).
    candidatos.sort(key=lambda x: x[0], reverse=True)
    saldo, texto = candidatos[0]
    return ResultadoSaldo(True, saldo, f"saldo observado: {texto}")
