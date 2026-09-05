# Pesquisa diária BFT WIN 4.0 — log do pesquisador

## Estado (atualizado em 2026-09-05 00h BR — primeira pesquisa ao vivo)
Temas já cobertos (NÃO repetir como "descoberta"; referência: docs/gestao_banca_risco_best_praticas.md + skill bft-win-bot):
- Gestão de banca: breakeven por payout, Kelly/Quarter-Kelly, fixed fractional 1–2%, martingale/gale com multiplicador 2÷payout, exposição máx ~8% na cadeia, stop diário −3/−5% e +8/+15%, streak breaker 3–4 derrotas, ALERTA do risco dinâmico que dobra risco em drawdown (inverter p/ reduzir).
- Motor BFT 4.0: multitempo M1/M5/M15, memória adaptativa por (timeframe×indicador) com anti-repaint, confluência normalizada 0–10, trava payout>=80%, confluência>=7.5, 5 travas, fontes Yahoo (Mercado Aberto) + OTC visual + Binance (Cripto).

### Descobertas 2026-09-05 (pesquisa ao vivo #1)
1. **RSI curto (RSI(2), Connors)** — RSI 14 é lento p/ 1m; extremos RSI(2)<10/>90 com filtro de tendência: backtests públicos com win rate 70–80% (quantifiedstrategies.com). Contra-ponto: estudo strike.money/Liberated Stock Trader — RSI(14) em 1m/5m sozinho tem só ~20–23% de acerto. Indicador certo depende do período.
2. **Feed OTC (Quotex) dissecado**: OTC = Binance(lag 5–60s) × escala + ruído, com balancer global 50/50 (170k+ ticks); toda "edge" session-specific morreu out-of-sample (74 testes documentados). Conclusão prática: NÃO modelar o feed OTC; medir a própria janela visual e validar com amostra separada (artificialanalysis.ai microeval).
3. **Limites Yahoo verificados AO VIVO** (yfinance 1.7.0, EURUSD=X): 30d/1m → 0 velas (erro "8 days per request"); 7d/1m → 9.889 velas OK; 60d/5m → 17.064 velas OK; 3mo/5m → 0. Binance 1m disponível desde jan/2019 (verificado ao vivo). Backtest do 4.0 deve paginar M1 Yahoo em blocos <=7d e M5 em blocos <=60d, ou usar Binance p/ histórico longo.

### Próximos temas candidatos (ainda não pesquisados)
- Confluência com score ponderado por regime (ADX trending/ranging)
- Vela de confirmação vs entrada na vela seguinte (literatura Pine/TradingView, anti-repaint)
- Sessão/horário como filtro (Londres/NY p/ Forex 1m)
- Correlação entre pares como filtro de confluência
- Payout/spread por horário nas OTC
- Teste de aleatoriedade (NIST/dieharder) na sequência de direção das velas OTC capturadas
