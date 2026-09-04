"""Conversão tolerante de números digitados nos formatos BR e internacional."""

import math
import re


def converter_numero(texto, nome="valor"):
    bruto = str(texto).strip().replace(" ", "")
    bruto = re.sub(r"[^0-9,\.\-+]", "", bruto)
    if not bruto or bruto in {"+", "-"}:
        raise ValueError(f"{nome} está vazio")

    if "," in bruto and "." in bruto:
        decimal = "," if bruto.rfind(",") > bruto.rfind(".") else "."
        milhar = "." if decimal == "," else ","
        normalizado = bruto.replace(milhar, "").replace(decimal, ".")
    elif "," in bruto:
        normalizado = _normalizar_separador_unico(bruto, ",")
    elif "." in bruto:
        normalizado = _normalizar_separador_unico(bruto, ".")
    else:
        normalizado = bruto

    try:
        valor = float(normalizado)
    except ValueError as erro:
        raise ValueError(f"{nome} inválido: {texto}") from erro
    if not math.isfinite(valor):
        raise ValueError(f"{nome} inválido: {texto}")
    return valor


def _normalizar_separador_unico(texto, separador):
    partes = texto.split(separador)
    if len(partes) > 2:
        return "".join(partes)
    antes, depois = partes
    # Um único separador seguido de três dígitos é tratado como milhar.
    if len(depois) == 3 and 1 <= len(antes.lstrip("+-")) <= 3:
        return antes + depois
    return antes + "." + depois
