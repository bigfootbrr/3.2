"""Testes do leitor de velas reais de cripto (Binance).

Tudo injetado: nenhum teste fala com a internet. A regra do projeto é
nunca operar com dado simulado — os fixtures aqui representam RESPOSTAS
reais da API para validar conversão, no-repaint e no-repeat.
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "core"))

from mercado_cripto_real import (  # noqa: E402
    ErroMercadoCripto,
    MercadoCriptoReal,
    _converter_klines_em_velas,
)


KLINE_REAL = [
    # Formato exato da Binance: [openTime, O, H, L, C, V, ...]
    [1788468360000, "81449.27", "81459.16", "81444.00", "81444.00", "6.687"],
    [1788468420000, "81444.00", "81508.00", "81429.06", "81495.30", "11.644"],
    [1788468480000, "81495.31", "81556.00", "81495.30", "81555.99", "13.550"],
    [1788468540000, "81555.99", "81564.17", "81525.36", "81525.36", "10.458"],
    [1788468600000, "81525.37", "81536.09", "81525.36", "81536.09", "2.157"],
]


class ConversaoTest(unittest.TestCase):
    def test_converte_klines_em_velas_descartando_vela_em_formacao(self):
        velas = _converter_klines_em_velas(KLINE_REAL, "BTC", "M1")
        # A última vela (em formação) deve ser descartada.
        self.assertEqual(len(velas), len(KLINE_REAL) - 1)
        primeira = velas[0]
        self.assertEqual(primeira.ativo, "BTC")
        self.assertEqual(primeira.timeframe, "M1")
        self.assertEqual(primeira.abertura, 81449.27)
        self.assertEqual(primeira.fechamento, 81444.00)
        self.assertEqual(primeira.maxima, 81459.16)
        self.assertEqual(primeira.minima, 81444.00)
        self.assertEqual(primeira.volume, 6.687)
        self.assertEqual(primeira.fim.tzinfo, timezone.utc)

    def test_volumes_e_horarios_preservados(self):
        velas = _converter_klines_em_velas(KLINE_REAL, "BTC", "M1")
        ultima = velas[-1]
        self.assertEqual(ultima.fim, datetime.fromtimestamp(
            1788468540000 / 1000, tz=timezone.utc
        ))
        self.assertEqual(ultima.volume, 10.458)


class MercadoCriptoTest(unittest.TestCase):
    def _fabrica(self, klines):
        def downloader(simbolo, intervalo, quantidade):
            self.capturado = (simbolo, intervalo, quantidade)
            return klines
        return downloader

    def setUp(self):
        self.capturado = None

    def test_ativo_invalido_rejeita(self):
        with self.assertRaises(ValueError):
            MercadoCriptoReal("MOEDA_INEXISTENTE")

    def test_timeframe_invalido_rejeita(self):
        with self.assertRaises(ValueError):
            MercadoCriptoReal("BTC", "M2")

    def test_atualizar_usa_simbolo_e_intervalo_corretos(self):
        mercado = MercadoCriptoReal(
            "BTC", "M1", downloader=self._fabrica(KLINE_REAL)
        )
        velas = mercado.atualizar()
        self.assertEqual(self.capturado[0], "BTCUSDT")
        self.assertEqual(self.capturado[1], "1m")
        self.assertEqual(len(velas), len(KLINE_REAL) - 1)

    def test_no_repeat_vela_repetida_nao_reanalisa(self):
        mercado = MercadoCriptoReal(
            "BTC", "M1", downloader=self._fabrica(KLINE_REAL)
        )
        primeira = mercado.atualizar()
        # Segunda chamada retorna o MESMO kline (nenhuma vela nova fechou).
        segunda = mercado.atualizar()
        self.assertEqual(primeira[-1].fim, segunda[-1].fim)
        self.assertEqual(len(primeira), len(segunda))

    def test_snapshot_mantido_se_fonte_falha(self):
        chamadas = {"n": 0}

        def downloader_que_falha(simbolo, intervalo, quantidade):
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                return KLINE_REAL
            raise ErroMercadoCripto("binance fora do ar")

        mercado = MercadoCriptoReal("BTC", "M1", downloader=downloader_que_falha)
        primeira = mercado.atualizar()
        segunda = mercado.atualizar()  # falhou; deve manter snapshot
        self.assertEqual(primeira, segunda)

    def test_erro_sem_snapshot_eh_lancado(self):
        def downloader_que_falha(simbolo, intervalo, quantidade):
            raise ErroMercadoCripto("sem rede")

        mercado = MercadoCriptoReal("BTC", "M1", downloader=downloader_que_falha)
        with self.assertRaises(ErroMercadoCripto):
            mercado.atualizar()

    def test_resumo_apos_atualizacao(self):
        mercado = MercadoCriptoReal(
            "BTC", "M1", downloader=self._fabrica(KLINE_REAL)
        )
        mercado.atualizar()
        resumo = mercado.resumo()
        self.assertEqual(resumo["ativo"], "BTC")
        self.assertEqual(resumo["velas"], len(KLINE_REAL) - 1)
        self.assertEqual(resumo["preco"], 81525.36)

    def test_resumo_sem_atualizacao_levanta_erro(self):
        mercado = MercadoCriptoReal("BTC", "M1", downloader=self._fabrica(KLINE_REAL))
        with self.assertRaises(ErroMercadoCripto):
            mercado.resumo()


if __name__ == "__main__":
    unittest.main()