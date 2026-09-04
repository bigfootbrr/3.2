#!/bin/bash
# Daemon do modo tray/serviço: executa core/runner.py em segundo plano.
# Uso: ./criar_daemon.sh start|stop|status|restart

RAIZ_PROJETO="$(cd -- "$(dirname -- "$0")/.." && pwd)"
DAEMON_PATH="$RAIZ_PROJETO/core/runner.py"
PID_FILE="/tmp/bft_daemon.pid"
LOG_FILE="$RAIZ_PROJETO/bft_daemon.log"

# Retorna 0 se o PID existe e é um processo python vivo
_pid_vivo() {
    local pid="$1"
    [ -n "$pid" ] || return 1
    ps -p "$pid" -o command= 2>/dev/null | grep -q "runner.py"
}

start() {
    if [ -f "$PID_FILE" ]; then
        PID_ATUAL=$(cat "$PID_FILE")
        if _pid_vivo "$PID_ATUAL"; then
            echo "Daemon já está rodando (PID $PID_ATUAL)"
            return 2
        fi
        echo "PID antigo ($PID_ATUAL) está órfão; removendo..."
        rm -f "$PID_FILE"
    fi
    echo "Iniciando daemon..."
    cd "$RAIZ_PROJETO/core" || return 1
    nohup python3 "$DAEMON_PATH" >> "$LOG_FILE" 2>&1 &
    DAEMON_PID=$!
    echo "$DAEMON_PID" > "$PID_FILE"
    sleep 1
    if _pid_vivo "$DAEMON_PID"; then
        echo "Daemon iniciado (PID $DAEMON_PID). Logs: $LOG_FILE"
    else
        rm -f "$PID_FILE"
        echo "ERRO: daemon morreu logo após iniciar. Veja $LOG_FILE"
        tail -5 "$LOG_FILE"
        return 1
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if _pid_vivo "$PID"; then
            kill "$PID" 2>/dev/null
            # Aguarda até 5s o processo encerrar
            for _ in 1 2 3 4 5; do
                _pid_vivo "$PID" || break
                sleep 1
            done
            # Força se ainda vivo
            _pid_vivo "$PID" && kill -9 "$PID" 2>/dev/null
            echo "Daemon parado (PID $PID)."
        else
            echo "PID $PID no arquivo já estava morto."
        fi
        rm -f "$PID_FILE"
    else
        echo "Nenhum daemon rodando."
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if _pid_vivo "$PID"; then
            echo "Daemon rodando (PID $PID)."
        else
            echo "PID $PID registrado mas o processo não está vivo."
        fi
    else
        echo "Nenhum daemon rodando."
    fi
}

restart() {
    stop
    start
}

case "$1" in
    start)
        start
        exit $?
        ;;
    stop)
        stop
        exit $?
        ;;
    status)
        status
        exit $?
        ;;
    restart)
        restart
        exit $?
        ;;
    *)
        echo "Uso: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac
