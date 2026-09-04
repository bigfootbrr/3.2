import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "web"))

import interface_tempo_real

import main  # assuming "main" is the module you want to import
import main  # assuming "main" is the module you want to import


class InterfaceWebOtcTest(unittest.TestCase):
    def test_iniciar_otc_preserva_mercado_e_ativo_selecionados(self):
        with patch.object(interface_tempo_real, "criar_conector_padrao", return_value=object()):
            interface = interface_tempo_real.InterfaceTempoReal()
        interface.mudar_ativo("EUR/GBP (OTC)")
        interface.confirmar_plataforma()

        with patch.object(interface_tempo_real, "iniciar_robo") as iniciar_robo:
            iniciado, _ = interface.iniciar_motor()

        self.assertTrue(iniciado)
        iniciar_robo.assert_called_once()
        argumentos = iniciar_robo.call_args.kwargs
        self.assertEqual("OTC", argumentos["tipo_mercado"])
        self.assertEqual("EUR/GBP (OTC)", argumentos["ativo"])

    def test_painel_permanece_na_aba_otc_apos_recarregar(self):
        conector = unittest.mock.Mock()
        conector.obter_cotacao.return_value = None
        with patch.object(interface_tempo_real, "criar_conector_padrao", return_value=conector):
            interface = interface_tempo_real.InterfaceTempoReal()
        interface.mudar_ativo("EUR/GBP (OTC)")

        html = interface.gerar_html()

        self.assertIn('class="asset-mode active" id="aba-otc"', html)
        self.assertIn('class="asset-view active" id="mercado-otc"', html)
        self.assertIn('class="asset-view" id="mercado-aberto"', html)

    def test_aba_otc_oferece_leitura_de_tela_pela_janela_nativa(self):
        conector = unittest.mock.Mock()
        conector.obter_cotacao.return_value = None
        with patch.object(interface_tempo_real, "criar_conector_padrao", return_value=conector):
            interface = interface_tempo_real.InterfaceTempoReal()
        interface.mudar_ativo("EUR/GBP (OTC)")

        html = interface.gerar_html()

        self.assertIn('id="botao-leitura-otc"', html)
        self.assertIn("pywebview.api.ler_tela_otc", html)

    def test_painel_recebe_analise_otc_emitida_pelo_motor(self):
        with patch.object(interface_tempo_real, "criar_conector_padrao", return_value=object()):
            interface = interface_tempo_real.InterfaceTempoReal()
        interface.mudar_ativo("EUR/GBP (OTC)")
        evento = {
            "tipo": "sinal",
            "mercado": "OTC",
            "ativo": "EUR/GBP (OTC)",
            "sinal": "ALTA",
            "direcao": "CALL / HIGHER",
            "pontuacao": 8.0,
        }

        interface.receber_evento_motor(evento)

        self.assertEqual(evento, interface.ultima_analise)
        self.assertEqual("8.0/10", interface.estado_operacional["confluencia"])
        self.assertEqual("CALL / HIGHER", interface.estado_operacional["entrada"])

    def test_leitura_completa_carrega_snapshot_otc_no_motor(self):
        with patch.object(interface_tempo_real, "criar_conector_padrao", return_value=object()):
            interface = interface_tempo_real.InterfaceTempoReal()
        interface.mudar_ativo("EUR/GBP (OTC)")
        interface.confirmar_plataforma()
        velas = tuple(
            SimpleNamespace(
                x=100 + indice * 12,
                abertura_y=400,
                maxima_y=380,
                minima_y=430,
                fechamento_y=395,
                direcao="ALTA",
            )
            for indice in range(20)
        )

        with (
            patch.object(
                interface_tempo_real,
                "testar_captura",
                return_value=SimpleNamespace(
                    sucesso=True,
                    caminho="/private/tmp/bft_web_otc_teste.png",
                    mensagem="captura autorizada",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_ativo",
                return_value=SimpleNamespace(
                    sucesso=True,
                    ativo="EUR/GBP (OTC)",
                    mensagem="ativo observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_payout",
                return_value=SimpleNamespace(
                    sucesso=True,
                    payout=0.85,
                    mensagem="payout observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_timeframe",
                return_value=SimpleNamespace(
                    sucesso=True,
                    timeframe="M1",
                    mensagem="timeframe observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_velas",
                return_value=SimpleNamespace(
                    sucesso=True,
                    velas=velas,
                    mensagem="20 velas reconhecidas",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_botoes",
                return_value=SimpleNamespace(
                    sucesso=True,
                    prontos=True,
                    mensagem="botões reconhecidos",
                ),
                create=True,
            ),
        ):
            ler_tela = getattr(
                interface,
                "ler_tela_otc",
                lambda: (False, "leitura OTC ainda não implementada"),
            )
            primeira, mensagem_primeira = ler_tela()
            self.assertFalse(primeira, mensagem_primeira)
            self.assertIn("Primeira captura", mensagem_primeira)
            self.assertFalse(main.snapshot_visual_disponivel("EUR/GBP (OTC)", "M1"))

            segunda, mensagem_segunda = ler_tela()
            self.assertTrue(segunda, mensagem_segunda)
            self.assertTrue(main.snapshot_visual_disponivel("EUR/GBP (OTC)", "M1"))
            self.assertEqual(85.0, interface.estado_operacional["payout"])

    def test_captura_timeframe_incompativel_rejeitada(self):
        with patch.object(interface_tempo_real, "criar_conector_padrao", return_value=object()):
            interface = interface_tempo_real.InterfaceTempoReal()
        interface.mudar_ativo("EUR/GBP (OTC)")
        interface.confirmar_plataforma()
        velas = tuple(
            SimpleNamespace(
                x=100 + indice * 12,
                abertura_y=400,
                maxima_y=380,
                minima_y=430,
                fechamento_y=395,
                direcao="ALTA",
            )
            for indice in range(20)
        )

        with (
            patch.object(
                interface_tempo_real,
                "testar_captura",
                return_value=SimpleNamespace(
                    sucesso=True,
                    caminho="/private/tmp/bft_web_otc_teste.png",
                    mensagem="captura autorizada",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_ativo",
                return_value=SimpleNamespace(
                    sucesso=True,
                    ativo="EUR/GBP (OTC)",
                    mensagem="ativo observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_payout",
                return_value=SimpleNamespace(
                    sucesso=True,
                    payout=0.85,
                    mensagem="payout observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_timeframe",
                return_value=SimpleNamespace(
                    sucesso=True,
                    timeframe="M5",
                    mensagem="timeframe observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_velas",
                return_value=SimpleNamespace(
                    sucesso=True,
                    velas=velas,
                    mensagem="20 velas reconhecidas",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_botoes",
                return_value=SimpleNamespace(
                    sucesso=True,
                    prontos=True,
                    mensagem="botões reconhecidos",
                ),
                create=True,
            ),
        ):
            sucesso, mensagem = interface.ler_tela_otc()

        self.assertFalse(sucesso)
        self.assertIn("timeframe M5", mensagem)
        self.assertFalse(main.snapshot_visual_disponivel("EUR/GBP (OTC)", "M1"))

    def test_capturas_incompativeis_resetam_referencia(self):
        with patch.object(interface_tempo_real, "criar_conector_padrao", return_value=object()):
            interface = interface_tempo_real.InterfaceTempoReal()
        interface.mudar_ativo("EUR/GBP (OTC)")
        interface.confirmar_plataforma()

        velas_altas = tuple(
            SimpleNamespace(
                x=100 + indice * 12,
                abertura_y=400,
                maxima_y=380,
                minima_y=430,
                fechamento_y=395,
                direcao="ALTA",
            )
            for indice in range(20)
        )
        velas_baixas = tuple(
            SimpleNamespace(
                x=100 + indice * 12,
                abertura_y=400,
                maxima_y=380,
                minima_y=430,
                fechamento_y=405,
                direcao="BAIXA",
            )
            for indice in range(20)
        )

        with (
            patch.object(
                interface_tempo_real,
                "testar_captura",
                return_value=SimpleNamespace(
                    sucesso=True,
                    caminho="/private/tmp/bft_web_otc_teste.png",
                    mensagem="captura autorizada",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_ativo",
                return_value=SimpleNamespace(
                    sucesso=True,
                    ativo="EUR/GBP (OTC)",
                    mensagem="ativo observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_payout",
                return_value=SimpleNamespace(
                    sucesso=True,
                    payout=0.85,
                    mensagem="payout observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_timeframe",
                return_value=SimpleNamespace(
                    sucesso=True,
                    timeframe="M1",
                    mensagem="timeframe observado",
                ),
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_velas",
                side_effect=[
                    SimpleNamespace(
                        sucesso=True,
                        velas=velas_altas,
                        mensagem="20 velas reconhecidas",
                    ),
                    SimpleNamespace(
                        sucesso=True,
                        velas=velas_baixas,
                        mensagem="20 velas reconhecidas",
                    ),
                ],
                create=True,
            ),
            patch.object(
                interface_tempo_real,
                "ler_botoes",
                return_value=SimpleNamespace(
                    sucesso=True,
                    prontos=True,
                    mensagem="botões reconhecidos",
                ),
                create=True,
            ),
        ):
            primeira, _ = interface.ler_tela_otc()
            self.assertFalse(primeira)
            # Captura diferente: a referência anterior é substituída.
            segunda, _ = interface.ler_tela_otc()
            self.assertFalse(segunda)

        self.assertIsNone(interface._assinatura_otc_confirmada)
        self.assertFalse(main.snapshot_visual_disponivel("EUR/GBP (OTC)", "M1"))

    def test_api_dispara_leitura_otc_e_retorna_resultado(self):
        interface = unittest.mock.Mock()
        interface.ler_tela_otc.return_value = (True, "snapshot carregado")
        interface_tempo_real.BFTRequestHandler.interface = interface
        handler = object.__new__(interface_tempo_real.BFTRequestHandler)
        handler.path = "/api/ler-tela-otc"

        with (
            patch.object(handler, "_enviar_json") as enviar_json,
            patch.object(handler, "_enviar_erro") as enviar_erro,
        ):
            handler.do_POST()

        interface.ler_tela_otc.assert_called_once_with()
        enviar_json.assert_called_once_with(
            {"ok": True, "mensagem": "snapshot carregado"}
        )
        enviar_erro.assert_not_called()


if __name__ == "__main__":
    unittest.main()
