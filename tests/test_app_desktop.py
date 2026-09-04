import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "pc"))

import app_desktop


class JanelaFalsa:
    def __init__(self, eventos):
        self.eventos = eventos

    def hide(self):
        self.eventos.append("ocultou")

    def show(self):
        self.eventos.append("mostrou")


class PonteDesktopTest(unittest.TestCase):
    def test_leitura_oculta_janela_captura_e_mostra_novamente(self):
        classe_ponte = getattr(app_desktop, "PonteDesktop", None)
        self.assertIsNotNone(classe_ponte, "PonteDesktop ainda não implementada")
        eventos = []

        def requisitar():
            eventos.append("capturou")
            return {"ok": True, "mensagem": "snapshot carregado"}

        ponte = classe_ponte(
            requisitar=requisitar,
            pausar=lambda _segundos: eventos.append("aguardou"),
        )
        ponte.janela = JanelaFalsa(eventos)

        resultado = ponte.ler_tela_otc()

        self.assertEqual(
            ["ocultou", "aguardou", "capturou", "mostrou"],
            eventos,
        )
        self.assertEqual({"ok": True, "mensagem": "snapshot carregado"}, resultado)


if __name__ == "__main__":
    unittest.main()
