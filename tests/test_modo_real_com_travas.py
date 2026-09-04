import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "core"))

from executor_demo_iq import ExecutorDemoIq
from modo_operacao import AUTOMATICO_REAL, validar_modo


class ProcessoConcluido:
    returncode = 0
    stdout = ""
    stderr = ""


class ModoRealComTravasTest(unittest.TestCase):
    def test_modo_real_permanece_disponivel(self):
        permissao = validar_modo(AUTOMATICO_REAL)

        self.assertTrue(permissao.permitido)

    def test_clique_real_exige_armacao_e_desarma_apos_sucesso(self):
        chamadas = []

        def executor_falso(*argumentos, **opcoes):
            chamadas.append((argumentos, opcoes))
            return ProcessoConcluido()

        executor = ExecutorDemoIq(executor=executor_falso)
        parametros = {
            "sinal": "ALTA",
            "chave_vela": "EURGBP-OTC-M1-10:30",
            "caminho_captura": None,
            "conta_confirmada": True,
            "largura_tela": 1440,
            "altura_tela": 900,
            "plataforma": "Quotex",
            "coordenadas": {"tela": (1440, 900), "ALTA": (1100, 360)},
            "tipo_conta": "REAL",
            "plataforma_confirmada": True,
        }

        bloqueado = executor.executar(**parametros)
        self.assertFalse(bloqueado.sucesso)
        self.assertEqual([], chamadas)

        self.assertTrue(executor.armar_conta_real(True))
        executado = executor.executar(**parametros)

        self.assertTrue(executado.sucesso)
        self.assertEqual(1, len(chamadas))
        self.assertFalse(executor.conta_real_armada)


if __name__ == "__main__":
    unittest.main()
