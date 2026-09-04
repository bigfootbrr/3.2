"""Persistência local do histórico operacional exibido pela interface."""

import json
import os


CAMINHO_HISTORICO_PADRAO = os.path.expanduser(
    "~/Library/Application Support/BFT Winbot/historico_entradas.jsonl"
)
CAMPOS_HISTORICO = (
    "horario",
    "conta",
    "plataforma",
    "ativo",
    "direcao",
    "valor",
    "resultado",
    "sucesso",
)


def normalizar_registro(registro):
    """Mantém somente campos operacionais e nunca persiste credenciais."""
    registro = dict(registro or {})
    return {
        "horario": str(registro.get("horario") or "—"),
        "conta": str(registro.get("conta") or "—"),
        "plataforma": str(registro.get("plataforma") or "—"),
        "ativo": str(registro.get("ativo") or "—"),
        "direcao": str(registro.get("direcao") or "—"),
        "valor": str(registro.get("valor") or "—"),
        "resultado": str(registro.get("resultado") or "—"),
        "sucesso": bool(registro.get("sucesso", False)),
    }


def registrar_entrada(registro, caminho=CAMINHO_HISTORICO_PADRAO):
    item = normalizar_registro(registro)
    pasta = os.path.dirname(os.path.abspath(caminho))
    os.makedirs(pasta, exist_ok=True)
    with open(caminho, "a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def carregar_entradas(caminho=CAMINHO_HISTORICO_PADRAO, limite=200):
    if limite < 1:
        raise ValueError("limite precisa ser maior que zero")
    if not os.path.isfile(caminho):
        return ()
    itens = []
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            try:
                itens.append(normalizar_registro(json.loads(linha)))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    return tuple(itens[-limite:])
