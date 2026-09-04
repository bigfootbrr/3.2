"""
Runner daemon para o modo tray/serviço.

Mantém o ciclo de análise em tempo real usando dados de criptomoedas
da Binance (24/7). Quando a interface não está aberta, o serviço
continua rodando e registrando sinais de confluência para posterior
revisão. Não emite GUI nem dispara ordens — apenas coleta sinal
para análise humana ou integração futura com o motor.

Funcionalidades:
- Atualiza mercado a cada PAUSA_ENTRE_ITERACOES segundos
- Executa análise confluência (analisar_confluencia)
- Registra timestamp, sinal, pontos, regime e motivo
- Captura exceções e continua rodando
- Saída por stdout para logs ou encaminhamento externo
"""

import os
import sys
import time
import json
from datetime import datetime, timezone
from pathlib import Path

# Adiciona raiz do projeto ao PYTHONPATH para importes locais
PROJETO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJETO_ROOT))

from mercado_cripto_real import MercadoCriptoReal
from confluencia_indicadores import analisar_confluencia

# Configurações internas -----
PAUSA_ENTRE_ITERACOES = 60  # segundos entre atualizações de mercado
LOG_DISTANCIA = 10          # a cada N iterações grava no disco

def registrar_log(entry: dict) -> None:
    """
    Grava um entry de log em ~/bft_runner.log (append-only).
    Mantém formato JSON por linha para fácil ingestão posterior.
    """
    LOG_PATH = Path.home() / "bft_runner.log"
    with LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

def main() -> None:
    """
    Loop principal do daemon. Atualiza o mercado, analisa confluência
    e emite logs periódicamente. Nunca aborta por exceções — apenas
    registra e segue.
    """
    mercado = MercadoCriptoReal("BTC", "M1")
    global _iteracao
    _iteracao = 0

    print("[TRAy] Iniciado – escaneando mercado Binance a cada",
          PAUSA_ENTRE_ITERACOES, "segundos", file=sys.stderr)

    while True:
        _iteracao += 1
        try:
            # 1) Busca última snapshot de velas (no‑repaint)
            velas = mercado.atualizar()

            # 2) Analisa confluência
            resultado = analisar_confluencia(velas, "M1")

            # 3) Monta log compacto
            entry = {
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "ativo": "BTC",
                "timeframe": "M1",
                "sinal": resultado.sinal.name if resultado.sinal else "NONE",
                "pontuacao": resultado.pontuacao,
                "regime": resultado.regime,
                "motivo": resultado.motivo,
                "iteracao": _iteracao,
            }

            # 4) Loga a cada LOG_DISTANCIA iterações
            if _iteracao % LOG_DISTANCIA == 0:
                registrar_log(entry)

        except Exception as exc:
            # Nunca quebramos o daemon; apenas notificamos
            err_entry = {
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "erro": f"{type(exc).__name__}: {exc}",
                "iteracao": _iteracao,
            }
            registrar_log(err_entry)
            print(f"[TRAy] Erro runtime: {exc}", file=sys.stderr)

        # 5) Espera antes da próxima iteração
        time.sleep(PAUSA_ENTRE_ITERACOES)

if __name__ == "__main__":
    main()