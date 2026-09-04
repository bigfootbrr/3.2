import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "core"))

from versao import NOME_COMPLETO_APP, VERSAO_APP


class VersaoTest(unittest.TestCase):
    def test_identidade_da_copia_de_trabalho_e_3_2(self):
        self.assertEqual("3.2", VERSAO_APP)
        self.assertEqual("BFT WIN 3.2", NOME_COMPLETO_APP)


if __name__ == "__main__":
    unittest.main()
