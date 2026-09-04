"""Abre o Trading Desk Web como aplicativo nativo do macOS."""

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import socket

import webview


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
URL_DASHBOARD = "http://127.0.0.1:8765"


class PonteDesktop:
    """Ações nativas que precisam ocultar a janela antes da captura."""

    def __init__(self, requisitar=None, pausar=time.sleep):
        self.janela = None
        self._requisitar = requisitar or self._requisitar_leitura_otc
        self._pausar = pausar

    @staticmethod
    def _requisitar_leitura_otc():
        requisicao = Request(
            f"{URL_DASHBOARD}/api/ler-tela-otc",
            method="POST",
        )
        try:
            with urlopen(requisicao, timeout=30) as resposta:
                corpo = resposta.read()
        except HTTPError as erro:
            corpo = erro.read()
        except (OSError, URLError) as erro:
            return {"ok": False, "mensagem": f"Painel local indisponível: {erro}"}

        try:
            dados = json.loads(corpo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"ok": False, "mensagem": "Resposta inválida do painel local"}
        if not dados.get("ok"):
            dados["mensagem"] = dados.get("erro", "Leitura visual não concluída")
        return dados

    def ler_tela_otc(self):
        """Oculta o BFT, captura a corretora e sempre restaura a janela."""
        if self.janela is None:
            return {"ok": False, "mensagem": "Janela do BFT não está pronta"}
        try:
            self.janela.hide()
            self._pausar(1.0)
            return self._requisitar()
        except Exception as erro:
            return {"ok": False, "mensagem": f"Leitura visual falhou: {erro}"}
        finally:
            self.janela.show()


def servidor_disponivel():
    endereco = urlparse(URL_DASHBOARD)
    try:
        with socket.create_connection(
            (endereco.hostname, endereco.port or 80), timeout=1
        ):
            return True
    except OSError:
        return False


def iniciar_servidor():
    if servidor_disponivel():
        return None

    processo = subprocess.Popen(
        [sys.executable, str(RAIZ_PROJETO / "web" / "interface_tempo_real.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if servidor_disponivel():
            return processo
        time.sleep(0.2)
    encerrar_servidor(processo)
    raise RuntimeError("Não foi possível iniciar o Trading Desk local.")


def encerrar_servidor(processo):
    """Encerra o servidor filho sem deixar processo local em segundo plano."""
    processo.terminate()
    try:
        processo.wait(timeout=5)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait()


def main():
    processo_servidor = iniciar_servidor()
    ponte = PonteDesktop()
    try:
        janela = webview.create_window(
            "BFT Winbot - Trading Desk",
            URL_DASHBOARD,
            width=1200,
            height=900,
            min_size=(900, 650),
            js_api=ponte,
        )
        ponte.janela = janela
        webview.start(gui="cocoa", debug=True)
    finally:
        if processo_servidor is not None:
            encerrar_servidor(processo_servidor)


if __name__ == "__main__":
    main()
