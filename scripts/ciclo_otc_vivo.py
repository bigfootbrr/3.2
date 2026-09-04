#!/usr/bin/env python3
"""Ciclo OTC completo ao vivo: captura → leitura → confluência → veredito.

Uso: python3 scripts/ciclo_otc_vivo.py [--capturas N] [--intervalo SEG]

Rodar com a IQ aberta no ativo OTC desejado (M1 quando disponível).
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "core"))

from calibracao_iq_contexto import capturar_janela_iq  # noqa: E402
from validacao_captura import validar_captura  # noqa: E402
from leitor_ativo_iq import ler_ativo  # noqa: E402
from leitor_payout_iq import ler_payout  # noqa: E402
from leitor_velas_iq import ler_velas  # noqa: E402
from acumulador_velas import AcumuladorVelas  # noqa: E402
from confluencia_indicadores import analisar_confluencia  # noqa: E402

CAPTURA = "/private/tmp/bft_ciclo_otc_vivo.png"
PAYOUT_MINIMO = 0.80


def converter_velas(acumulador, ativo):
    """Converte VelaVisual (y em pixels, menor=alto) para objetos Vela do motor."""
    agora = datetime.now(timezone.utc)
    velas = list(acumulador._velas)
    total = len(velas)
    adaptadas = []
    for i, v in enumerate(reversed(velas)):  # mais antiga primeiro
        invertido = lambda y: -y
        adaptadas.append(type("VelaAdaptada", (), {
            "abertura": invertido(v.abertura_y),
            "maxima": invertido(v.minima_y),   # topo visual = máxima real
            "minima": invertido(v.maxima_y),   # fundo visual = mínima real
            "fechamento": invertido(v.fechamento_y),
            "numero": i,
            "ativo": ativo,
            "timeframe": "M1",
            "inicio": agora - timedelta(minutes=total - i),
            "fim": agora - timedelta(minutes=total - i - 1),
        }))
    return adaptadas


def ciclo_unico(acumulador: AcumuladorVelas) -> dict:
    """Uma captura + leitura + acumulação. Retorna o veredito se pronto."""
    sucesso, msg = capturar_janela_iq(CAPTURA)
    if not sucesso:
        return {"status": "captura_falhou", "mensagem": msg}

    validacao = validar_captura(CAPTURA)
    if not validacao.sucesso:
        return {"status": "captura_invalida", "mensagem": validacao.mensagem}

    r_ativo = ler_ativo(CAPTURA)
    r_payout = ler_payout(CAPTURA)
    r_velas = ler_velas(CAPTURA)

    if r_velas.sucesso:
        acumulador.adicionar(r_velas.velas, r_velas.linha_expiracao_x)

    veredito = {"status": "aguardando_historico",
                "ativo": r_ativo.ativo if r_ativo.sucesso else None,
                "payout": r_payout.payout if r_payout.sucesso else None,
                "acumulado": acumulador.quantidade()}

    if not acumulador.pronto():
        veredito["mensagem"] = (
            f"acumulando histórico: {acumulador.quantidade()}/105 velas"
        )
        return veredito

    velas_motor = converter_velas(acumulador, veredito["ativo"] or "DESCONHECIDO")
    resultado = analisar_confluencia(velas_motor, "M1")
    veredito.update({
        "sinal": resultado.sinal.name,
        "pontuacao": resultado.pontuacao,
        "regime": resultado.regime,
        "motivo": resultado.motivo,
    })

    payout = r_payout.payout
    if resultado.sinal.name in ("ALTA", "BAIXA"):
        if payout is None:
            veredito["acao"] = "BLOQUEADO — payout não lido"
        elif payout >= PAYOUT_MINIMO:
            veredito["acao"] = f"SINAL LIBERADO ({payout:.0%})"
        else:
            veredito["acao"] = f"BLOQUEADO — payout {payout:.0%} < 80%"
    else:
        veredito["acao"] = "AGUARDAR"
    return veredito


def main():
    capturas = int(sys.argv[sys.argv.index("--capturas") + 1]) if "--capturas" in sys.argv else 1
    intervalo = float(sys.argv[sys.argv.index("--intervalo") + 1]) if "--intervalo" in sys.argv else 5.0

    acumulador = AcumuladorVelas(minimo=105)
    print(f"=== CICLO OTC VIVO — {capturas} leitura(s), intervalo {intervalo}s ===\n")

    for rodada in range(1, capturas + 1):
        veredito = ciclo_unico(acumulador)
        agora = datetime.now().strftime("%H:%M:%S")
        print(f"[{agora}] #{rodada}: {veredito}")
        if veredito.get("acao", "").startswith("SINAL"):
            break
        if rodada < capturas:
            time.sleep(intervalo)


if __name__ == "__main__":
    main()