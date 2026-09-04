"""Memória de clique para o BFT WIN — posições ensinadas pelo operador.

IDEIA:
- O robô guarda em um arquivo JSON (click_memory.json) posições (x, y) onde
  ele deve clicar, tanto na inicialização quanto durante a operação.
- Modo "ensinar": o operador posiciona o mouse no ponto certo durante uma
  contagem e a posição é salva com um nome (label).
- Nas próximas vezes o robô lê o JSON e clica sozinho, sem reconfigurar.

Uso típico: sequências de configuração da corretora (abrir aba, selecionar
ativo, ajustar timeframe) que não têm cor ou texto para detecção automática.

Os cliques de COMPRA/VENDA não passam por aqui: eles usam a detecção por cor
(``detector_botoes_cor``) com fallback na calibração fixa.
"""

import json
import os
import threading
import time

try:  # pyautogui está nas dependências de desktop; opcional no container.
    import pyautogui
except ImportError:  # pragma: no cover - ambiente sem GUI
    pyautogui = None

MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "click_memory.json"
)

if pyautogui is not None:
    # Mover o mouse para o canto (0,0) cancela a ação: segurança em testes.
    pyautogui.FAILSAFE = True


def _carregar_memoria() -> dict:
    """Lê o arquivo de memória. Se não existir, retorna estrutura vazia."""
    if not os.path.exists(MEMORY_PATH):
        return {"cliques_iniciais": []}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as arquivo:
            memoria = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        return {"cliques_iniciais": []}
    if not isinstance(memoria, dict):
        return {"cliques_iniciais": []}
    memoria.setdefault("cliques_iniciais", [])
    return memoria


def _salvar_memoria(memoria: dict) -> None:
    with open(MEMORY_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(memoria, arquivo, indent=2, ensure_ascii=False)


def _exigir_pyautogui():
    if pyautogui is None:
        raise RuntimeError("pyautogui não está instalado neste ambiente")
    return pyautogui


def ensinar_posicao_direta(label: str, coordenadas) -> dict:
    """Salva uma posição conhecida na memória (sem clicar no mouse).

    Usado pela calibração automática: a detecção por cor encontra os
    botões e a posição é gravada direto — nada de interação manual.
    """
    label = str(label).strip()
    if not label:
        raise ValueError("label do clique é obrigatório")
    if not coordenadas or len(coordenadas) != 2:
        raise ValueError("coordenadas inválidas (esperado (x, y))")
    x, y = int(coordenadas[0]), int(coordenadas[1])
    memoria = _carregar_memoria()
    memoria["cliques_iniciais"] = [
        clique
        for clique in memoria.get("cliques_iniciais", [])
        if clique.get("label") != label
    ]
    memoria["cliques_iniciais"].append({"label": label, "x": x, "y": y})
    _salvar_memoria(memoria)
    print(f"[MEMORIA] Posição direta salva: '{label}' -> ({x}, {y})")
    return {"label": label, "x": x, "y": y}


def ensinar_posicao(label: str, espera_segundos: int = 5) -> dict:
    """Modo de aprendizado: conta o tempo e salva a posição atual do mouse."""
    mouse = _exigir_pyautogui()
    label = str(label).strip()
    if not label:
        raise ValueError("label do clique é obrigatório")
    for restante in range(espera_segundos, 0, -1):
        print(f"[MEMORIA] '{label}' em {restante}s...")
        time.sleep(1)

    x, y = mouse.position()
    memoria = _carregar_memoria()
    memoria["cliques_iniciais"] = [
        clique
        for clique in memoria.get("cliques_iniciais", [])
        if clique.get("label") != label
    ]
    memoria["cliques_iniciais"].append(
        {"label": label, "x": int(x), "y": int(y)}
    )
    _salvar_memoria(memoria)
    print(f"[MEMORIA] Posição salva: '{label}' -> ({x}, {y})")
    return {"label": label, "x": int(x), "y": int(y)}


def ensinar_posicao_async(
    label: str, espera_segundos: int = 5, ao_concluir=None
) -> threading.Thread:
    """Ensina a posição em segundo plano (para uso via interface web)."""

    def _tarefa():
        try:
            resultado = ensinar_posicao(label, espera_segundos)
        except (RuntimeError, ValueError) as erro:
            resultado = {"erro": str(erro), "label": label}
        if ao_concluir is not None:
            try:
                ao_concluir(resultado)
            except Exception:  # pragma: no cover - callback do chamador
                pass

    thread = threading.Thread(
        target=_tarefa, daemon=True, name=f"ensinar-clique-{label}"
    )
    thread.start()
    return thread


def executar_cliques_de_inicio(atraso_entre_cliques: float = 0.5) -> list:
    """Executa em ordem todos os cliques memorizados na inicialização."""
    mouse = _exigir_pyautogui()
    memoria = _carregar_memoria()
    cliques = memoria.get("cliques_iniciais", [])
    if not cliques:
        print("[MEMORIA] Nenhum clique memorizado ainda.")
        return []

    print(f"[MEMORIA] Executando {len(cliques)} clique(s) memorizado(s)...")
    executados = []
    for clique in cliques:
        label = clique.get("label")
        x, y = int(clique.get("x", 0)), int(clique.get("y", 0))
        print(f"  -> Clicando em '{label}' ({x}, {y})")
        try:
            mouse.click(x, y)
            executados.append({"label": label, "x": x, "y": y})
        except Exception as erro:  # pragma: no cover - falha de GUI
            print(f"  -> Falha em '{label}': {erro}")
        time.sleep(atraso_entre_cliques)
    print("[MEMORIA] Cliques de inicialização concluídos.")
    return executados


def listar_posicoes() -> list:
    """Retorna as posições memorizadas."""
    return list(_carregar_memoria().get("cliques_iniciais", []))


def remover_posicao(label: str) -> bool:
    """Remove uma posição memorizada. Retorna True se removeu algo."""
    label = str(label).strip()
    memoria = _carregar_memoria()
    antes = len(memoria.get("cliques_iniciais", []))
    memoria["cliques_iniciais"] = [
        clique
        for clique in memoria.get("cliques_iniciais", [])
        if clique.get("label") != label
    ]
    if len(memoria["cliques_iniciais"]) != antes:
        _salvar_memoria(memoria)
        return True
    return False


if __name__ == "__main__":
    nome = input("Nome para essa posição de clique (ex: abrir_corretora): ").strip()
    ensinar_posicao(nome)

def capturar_posicao_agora(label: str) -> dict:
    """Salva a posição ATUAL do mouse SEM esperar (o operador já teve o
    tempo dele antes do clique no botão — o endpoint captura imediatamente).

    Usado pela calibração CALL/PUT/Execução: o temporizador vive só no
    JavaScript do painel (evita esperar 2x — JS + backend).
    """
    mouse = _exigir_pyautogui()
    label = str(label).strip()
    if not label:
        raise ValueError("label do clique é obrigatório")
    x, y = mouse.position()
    memoria = _carregar_memoria()
    memoria["cliques_iniciais"] = [
        clique
        for clique in memoria.get("cliques_iniciais", [])
        if clique.get("label") != label
    ]
    memoria["cliques_iniciais"].append(
        {"label": label, "x": int(x), "y": int(y)}
    )
    _salvar_memoria(memoria)
    print(f"[MEMORIA] Posição capturada AGORA: '{label}' -> ({x}, {y})")
    return {"label": label, "x": int(x), "y": int(y)}
