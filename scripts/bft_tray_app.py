#!/usr/bin/env python3

'''Status‑MenuApp – menubar utility for BFT daemon control.

Features:
  • Menubar icon (macOS / Linux) or tray (Windows pythonw).
  • Menu actions: “Iniciar Daemon”, “Parar Daemon”, “Sobre”.
  • Updates title to reflect daemon status (🟢 Rodando or 🛑 Parado).
  • Periodic title refresh every CHECK_INTERVAL seconds.
  • Shows latest log line for context.
  • Uses background thread for refresh – avoids reliance on rumps.set_timer.
'''

import os
import subprocess
import sys
import threading
import time

# ---------------------------------------------------------------------------
# Project setup – makes local imports work when run from workspace root
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHECK_INTERVAL = 60                     # seconds between UI refreshes
LOG_PATH = os.path.expanduser("~/bft_runner.log")


def _is_daemon_running() -> bool:
    """Return True if the daemon PID file exists."""
    return os.path.isfile("/tmp/bft_daemon.pid")


def _exec_daemon(action: str) -> subprocess.CompletedProcess:
    """Run the external script that starts or stops the daemon."""
    script_path = os.path.join(PROJECT_ROOT, "scripts", "criar_daemon.sh")
    return subprocess.run(["/bin/bash", script_path, action], capture_output=True, text=True)


def _latest_log_entry() -> str:
    """Fetch the last non‑empty line from the daemon log."""
    if not os.path.exists(LOG_PATH):
        return ""
    with open(LOG_PATH, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        return lines[-1] if lines else ""


class BFTApp:
    """
    Core logic for the menubar app.
    A separate lightweight class is used instead of inheriting from rumps.App
    to make unit‑testing easier, but it mimics the same public interface.
    """

    def __init__(self):
        # Import rumps lazily – raise a clear error if it is missing.
        try:
            import rumps
        except ImportError:
            raise RuntimeError(
                "O módulo 'rumps' não está instalado. Instale com:\n"
                "    pip install rumps psutil"
            )
        self._rumps = rumps

        # Create the actual menubar app instance.
        self.app = rumps.App("BFT Winbot Local")

        # Build the menu – callbacks are bound by name strings.
        self.app.menu = [
            ("Iniciar Daemon", "start_daemon"),
            ("Parar Daemon", "stop_daemon"),
            ("Sobre", "sobre"),
        ]

        # Initialise the title; will be refreshed periodically.
        self.title = "🛑 Parado – Nenhum daemon"

        # Store the latest refresh time to avoid blocking the UI loop.
        self._refresh_thread = threading.Thread(target=self._periodic_refresh, daemon=True)
        self._refresh_thread.start()

    # -----------------------------------------------------------------------
    # UI refresh logic
    # -----------------------------------------------------------------------
    def _refresh_title(self):
        """Update the menubar title based on daemon status and latest log entry."""
        if _is_daemon_running():
            icon = "🟢"
            try:
                pid = os.readlink("/tmp/bft_daemon.pid")
            except OSError:
                pid = "?"  # fallback if PID file is unreadable
            latest = _latest_log_entry()
            self.title = f'{icon} Rodando (PID {pid}) – {latest}'
        else:
            self.title = "🛑 Parado – Nenhum daemon"

    def _periodic_refresh(self):
        """Background loop that forces a title refresh every CHECK_INTERVAL seconds."""
        while True:
            time.sleep(CHECK_INTERVAL)
            # rumps.App.title is thread‑safe for reading; we just trigger an update.
            self._refresh_title()

    # -----------------------------------------------------------------------
    # Menu callbacks
    # -----------------------------------------------------------------------
    def start_daemon(self):
        """Handler for ‘Iniciar Daemon’ – starts the daemon if not already running."""
        if _is_daemon_running():
            self.title = "⚠️ Já está rodando"
            return

        result = _exec_daemon("start")
        if result.returncode == 0:
            print("✅ Daemon started successfully.")
            self._refresh_title()
        else:
            print("❌ Falha ao iniciar daemon:", result.stderr)
            self.title = "🔴 Falha ao iniciar"

    def stop_daemon(self):
        """Handler for ‘Parar Daemon’ – stops the daemon if it is running."""
        if not _is_daemon_running():
            self.title = "⚠️ Não está rodando"
            return

        result = _exec_daemon("stop")
        if result.returncode == 0:
            print("✅ Daemon stopped.")
            self._refresh_title()
        else:
            print("❌ Falha ao parar daemon:", result.stderr)
            self.title = "🔴 Falha ao parar"

    def sobre(self):
        """Handler for ‘Sobre’ – show version information via a notification."""
        # Use rumps notification to display version without altering the persistent title.
        self._rumps.main_loop_post(priority=self._rumps.MainLoopPriority.NOTIFY,
                                   func=lambda: self._rumps.App.notify(self.app,
                                                                        "BFT Winbot Local\nVersão 1.0.0",
                                                                        title="Sobre"))

    # -----------------------------------------------------------------------
    # Entry point
    # -----------------------------------------------------------------------
    def run(self):
        """Start the menubar app’s event loop."""
        self.app.run()


def main() -> None:  # pragma: no cover – executed when script is run directly
    """Entry point – instantiate the app and launch the UI."""
    BFTApp().run()


if __name__ == "__main__":
    main()