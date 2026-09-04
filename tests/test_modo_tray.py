"""Testes do modo tray/serviço: runner (ciclo único) e ciclo de vida do daemon."""

import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Importa o runner pelo caminho do core
import sys
CORE_DIR = Path(__file__).parent.parent / "core"
sys.path.insert(0, str(CORE_DIR))

import runner  # noqa: E402

SCRIPT = Path(__file__).parent.parent / "scripts" / "criar_daemon.sh"


# ---------------------------------------------------------------------------
# runner.iterar — ciclo único testável
# ---------------------------------------------------------------------------

class _ResultadoFake:
    def __init__(self):
        from estrategia_otc_classica import Sinal  # enum real
        self.sinal = Sinal.ALTA
        self.pontuacao = 42
        self.regime = "TENDENCIA"
        self.motivo = "teste"


def test_iterar_retorna_entry_completo():
    """iterar() deve devolver todas as chaves esperadas do entry de log."""
    mercado = MagicMock()
    mercado.atualizar.return_value = [[1, 2, 3, 4]]  # formato velas irrelevante

    with patch.object(runner, "analisar_confluencia", return_value=_ResultadoFake()):
        entry = runner.iterar(mercado, 7)

    assert entry["iteracao"] == 7
    assert entry["ativo"] == "BTC"
    assert entry["timeframe"] == "M1"
    assert entry["sinal"] == "ALTA"
    assert entry["pontuacao"] == 42
    assert entry["regime"] == "TENDENCIA"
    assert "timestamp" in entry
    assert "motivo" in entry


def test_iterar_com_sinal_none_usa_none_string():
    """Quando não há sinal, o campo 'sinal' deve ser a string 'NONE'."""
    mercado = MagicMock()
    mercado.atualizar.return_value = []

    resultado = _ResultadoFake()
    resultado.sinal = None

    with patch.object(runner, "analisar_confluencia", return_value=resultado):
        entry = runner.iterar(mercado, 1)

    assert entry["sinal"] == "NONE"


def test_registrar_log_escreve_jsonl(tmp_path, monkeypatch):
    """registrar_log deve gravar JSON por linha no arquivo de log."""
    log_path = tmp_path / "runner_test.log"
    monkeypatch.setattr(runner.Path, "home", lambda: tmp_path)

    # Redefine o caminho usado dentro da função (usa Path.home())
    def _fake_log(entry):
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

    entrada = {"timestamp": "2026-09-04T00:00:00+00:00", "sinal": "VENDA"}
    _fake_log(entrada)
    _fake_log({"timestamp": "2026-09-04T00:01:00+00:00", "sinal": "COMPRA"})

    linhas = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 2
    primeiro = json.loads(linhas[0])
    assert primeiro["sinal"] == "VENDA"


def test_registrar_pid_grava_pid_real(tmp_path, monkeypatch):
    """registrar_pid deve gravar o PID do processo atual."""
    monkeypatch.setattr(runner, "PID_FILE", tmp_path / "bft_daemon.pid")
    runner.registrar_pid()
    conteudo = (tmp_path / "bft_daemon.pid").read_text(encoding="utf-8")
    assert int(conteudo) == os.getpid()


def test_limpar_pid_remove_arquivo(tmp_path, monkeypatch):
    """limpar_pid deve remover o arquivo PID sem erro se não existir."""
    pid_file = tmp_path / "bft_daemon.pid"
    monkeypatch.setattr(runner, "PID_FILE", pid_file)
    pid_file.write_text("123")
    runner.limpar_pid()
    assert not pid_file.exists()
    # Não deve levantar se já não existir
    runner.limpar_pid()


# ---------------------------------------------------------------------------
# criar_daemon.sh — ciclo de vida end-to-end
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_daemon_ciclo_completo_start_status_stop():
    """start → status mostra vivo → stop encerra e remove PID."""
    if not SCRIPT.exists():
        pytest.skip("criar_daemon.sh não encontrado")

    # Garante início limpo
    subprocess.run(["/bin/bash", str(SCRIPT), "stop"], capture_output=True)
    time.sleep(1)

    # start
    r_start = subprocess.run(["/bin/bash", str(SCRIPT), "start"],
                             capture_output=True, text=True, timeout=30)
    assert r_start.returncode == 0, r_start.stdout + r_start.stderr
    assert "iniciado" in r_start.stdout.lower()

    pid_file = Path("/tmp/bft_daemon.pid")
    assert pid_file.exists(), "PID file deve existir após start"
    pid = int(pid_file.read_text().strip())

    # O PID gravado deve ser um processo runner.py vivo (não um shell morto)
    comando = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                             capture_output=True, text=True).stdout
    assert "runner.py" in comando, f"PID {pid} não é o runner: {comando!r}"

    # status
    r_status = subprocess.run(["/bin/bash", str(SCRIPT), "status"],
                              capture_output=True, text=True, timeout=15)
    assert "rodando" in r_status.stdout.lower()

    # start duplicado deve falhar (exit != 0)
    r_dup = subprocess.run(["/bin/bash", str(SCRIPT), "start"],
                           capture_output=True, text=True, timeout=30)
    assert r_dup.returncode != 0, "start duplicado deve falhar"
    assert "já está rodando" in r_dup.stdout

    # stop
    r_stop = subprocess.run(["/bin/bash", str(SCRIPT), "stop"],
                            capture_output=True, text=True, timeout=30)
    assert r_stop.returncode == 0, r_stop.stdout + r_stop.stderr
    assert not pid_file.exists(), "PID file deve ser removido após stop"

    # status final
    r_final = subprocess.run(["/bin/bash", str(SCRIPT), "status"],
                             capture_output=True, text=True, timeout=15)
    assert "nenhum daemon" in r_final.stdout.lower()


@pytest.mark.slow
def test_daemon_stop_sem_pid_nao_falha():
    """stop sem daemon rodando deve ser idempotente (exit 0)."""
    subprocess.run(["/bin/bash", str(SCRIPT), "stop"], capture_output=True)
    r = subprocess.run(["/bin/bash", str(SCRIPT), "stop"],
                       capture_output=True, text=True, timeout=15)
    assert r.returncode == 0
    assert "nenhum" in r.stdout.lower()


@pytest.mark.slow
def test_daemon_start_com_pid_orfao_recupera():
    """Se o PID file existe mas o processo morreu, start deve se recuperar."""
    pid_file = Path("/tmp/bft_daemon.pid")
    subprocess.run(["/bin/bash", str(SCRIPT), "stop"], capture_output=True)

    # Grava um PID que quase certeza que não existe (usar PID 999999)
    pid_file.write_text("999999")
    time.sleep(0.5)

    r = subprocess.run(["/bin/bash", str(SCRIPT), "start"],
                       capture_output=True, text=True, timeout=30)
    # Deve detectar o PID órfão, limpar e iniciar normalmente
    assert r.returncode == 0, r.stdout + r.stderr
    assert "órfão" in r.stdout or "orfa" in r.stdout.lower() or "iniciado" in r.stdout.lower()

    # Limpeza
    subprocess.run(["/bin/bash", str(SCRIPT), "stop"], capture_output=True, timeout=30)