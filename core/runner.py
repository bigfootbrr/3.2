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
PID_FILE = Path("/tmp/bft_daemon.pid")

def registrar_pid() -> None:
    """Grava o PID real do processo Python (o shell pai já morreu)."""
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

def limpar_pid() -> None:
    """Remove o arquivo PID na saída limpa."""
    PID_FILE.unlink(missing_ok=True)

def registrar_log(entry: dict) -> None:
    """
    Grava um entry de log em ~/bft_runner.log (append-only).
    Mantém formato JSON por linha para fácil ingestão posterior.
    """
    LOG_PATH = Path.home() / "bft_runner.log"
    with LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

def iterar(mercado: MercadoCriptoReal, iteracao: int) -> dict:
    """
    Executa UM ciclo completo de análise (sem loop).
    Retorna o entry de log correspondente — separado do loop para ser testável.
    """
    # 1) Busca última snapshot de velas (no-repaint)
    velas = mercado.atualizar()

    # 2) Analisa confluência
    resultado = analisar_confluencia(velas, "M1")

    # 3) Monta log compacto
    return {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "ativo": "BTC",
        "timeframe": "M1",
        "sinal": resultado.sinal.name if resultado.sinal else "NONE",
        "pontuacao": resultado.pontuacao,
        "regime": resultado.regime,
        "motivo": resultado.motivo,
        "iteracao": iteracao,
    }

def main() -> None:
    """
    Loop principal do daemon. Atualiza o mercado, analisa confluência
    e emite logs periódicos. Nunca aborta por exceções — apenas
    registra e segue.
    """
    registrar_pid()
    iteracao = 0

    print("[TRAy] Iniciado – escaneando mercado Binance a cada",
          PAUSA_ENTRE_ITERACOES, "segundos", file=sys.stderr, flush=True)

    # Encerramento limpo: Ctrl+C / SIGTERM remove o PID file
    import signal
    def _encerrar(signum, frame):
        limpar_pid()
        sys.exit(0)
    signal.signal(signal.SIGINT, _encerrar)
    signal.signal(signal.SIGTERM, _encerrar)

    mercado = MercadoCriptoReal("BTC", "M1")

    try:
        while True:
            iteracao += 1
            try:
                entry = iterar(mercado, iteracao)

                # 4) Loga a cada LOG_DISTANCIA iterações
                if iteracao % LOG_DISTANCIA == 0:
                    registrar_log(entry)
                    print(
                        f"[TRAy] it={iteracao} sinal={entry['sinal']} "
                        f"pts={entry['pontuacao']} regime={entry['regime']}",
                        file=sys.stderr, flush=True,
                    )

            except Exception as exc:
                # Nunca quebramos o daemon; apenas notificamos
                err_entry = {
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "erro": f"{type(exc).__name__}: {exc}",
                    "iteracao": iteracao,
                }
                registrar_log(err_entry)
                print(f"[TRAy] Erro runtime: {exc}", file=sys.stderr, flush=True)

            # 5) Espera antes da próxima iteração
            time.sleep(PAUSA_ENTRE_ITERACOES)
    finally:
        limpar_pid()

if __name__ == "__main__":
    main()