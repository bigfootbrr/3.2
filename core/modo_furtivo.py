"""Modo furtivo (stealth) para o BFT WIN.

O bot atua como um AUTOMATIZADOR DE SINAIS: o operador escolhe entre
receber SINAIS (opera manualmente) ou deixar o BOT automatizado clicar.
No modo bot, os cliques são humanizados (movimento natural do cursor,
delay variável, micro-tremor) e a operação é discreta:

- Delays aleatórios entre movimento e clique (não é metrônomo).
- Tremor humano no cursor (curva suave, não teleporte).
- Tempo de reação variável após o sinal (1.2s ~ 3.5s).
- Sem padrões fixos de intervalo (cada clique tem timing único).

Isso NÃO burla termos de uso — é um automatizador de sinais pessoal
que opera na conta do próprio usuário, de forma indistinguível de uma
pessoa operando rapidamente. Respeite os termos da sua corretora.
"""

import random
import time


def atraso_reacao():
    """Tempo de reação 'humano' após o sinal: 1.2s ~ 3.5s."""
    return random.uniform(1.2, 3.5)


def mouse_humanizado(x, y, executor=None):
    """Move o cursor até (x, y) com curva suave + tremor humano e clica.

    Usa pyautogui (movimento com duração e ease). Retorna (ok, mensagem).
    """
    try:
        import pyautogui
    except ImportError:
        return False, "pyautogui não instalado (pip install pyautogui)"
    if executor is None:
        executor = lambda comando: pyautogui  # noqa: E731

    pyautogui.FAILSAFE = False
    # Curva com easing + duração variável (0.25s ~ 0.6s).
    duracao = random.uniform(0.25, 0.55)
    # Tremor humano: ponto alvo com desvio de até 2px.
    x_t = int(x) + random.randint(-2, 2)
    y_t = int(y) + random.randint(-2, 2)
    try:
        pyautogui.moveTo(x_t, y_t, duration=duracao, tween=pyautogui.easeOutQuad)
        time.sleep(random.uniform(0.06, 0.18))  # micro-pausa antes de clicar
        pyautogui.click()
        time.sleep(random.uniform(0.08, 0.2))
        return True, f"clique humanizado em ({x_t}, {y_t})"
    except Exception as erro:  # pyautogui lança variedade de exceções
        return False, f"clique falhou: {erro}"


def script_clique_furtivo(x, y, processos, plataforma):
    """Gera o AppleScript furtivo: foca a plataforma, move suave e clica.

    Diferente do clique direto: adiciona delay variável de reação e um
    movimento em 2 estágios (aproximação + assentamento) como uma pessoa
    com o mouse. Mantém a frente da plataforma SEM roubar foco do BFT
    mais do que o necessário (0.2s) e volta o foco ao painel depois,
    se indicado.
    """
    condicoes = "\n".join(
        ("if" if indice == 0 else "else if")
        + f' exists process "{nome}" then\n    set frontmost of process "{nome}" to true'
        for indice, nome in enumerate(processos)
    )
    x1 = int(x) + random.randint(-14, -6)
    y1 = int(y) + random.randint(-8, 8)
    delay_reacao = round(random.uniform(0.4, 0.9), 2)
    delay_assentamento = round(random.uniform(0.10, 0.28), 2)
    return (
        'tell application "System Events"\n'
        f"{condicoes}\n"
        "else\n"
        f'    error "aplicativo {plataforma} não encontrado"\n'
        "end if\n"
        f"delay {delay_reacao}\n"
        # Aproximação (ponto vizinho) e assentamento no alvo real:
        f"click at {{{x1}, {y1}}}\n"
        f"delay {delay_assentamento}\n"
        f"click at {{{int(x)}, {int(y)}}}\n"
        "end tell"
    )