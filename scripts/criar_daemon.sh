#!/bin/bash
# Script de daemon para executar o runner.py em segundo plano.
# Cria um daemon que roda o runner.py e mantém persistência.
# Uso: ./criar_daemon.sh start|stop|status|restart

DAEMON_PATH="$(dirname "$(readlink -f "$0")/../core/runner.py")"
PID_FILE="/tmp/bft_daemon.pid"
LOG_FILE="/tmp/bft_daemon.log"

start() {
    if [ -f "$PID_FILE" ]; then
        echo "Daemon já está rodando (PID $(cat $PID_FILE))"
        return 1
    fi
    echo "Iniciando daemon..."
    nohup python3 "$DAEMON_PATH" >> "$LOG_FILE" 2>&1 &
    DAEMON_PID=$!
    echo "$DAEMON_PID" > "$PID_FILE"
    echo "Daemon iniciado (PID $DAEMON_PID). Logs: $LOG_FILE"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        echo "Daemon parado (PID $PID)."
    else
        echo "Nenhum daemon rodando."
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        echo "Daemon rodando (PID $(cat $PID_FILE))."
    else
        echo "Nenhum daemon rodando."
    fi
}

restart() {
    stop && start
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart)
        restart
        ;;
    *)
        echo "Uso: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac
exit 0
