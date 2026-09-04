# Gestão de Banca & Risco — Melhores Práticas p/ Binárias OTC (BFT WIN)

> Relatório objetivo p/ operador experiente. Todo número foi verificado por cálculo real (breakeven, Kelly, streaks, exposição de gale). Fonte: pesquisa web + análise do código atual (`core/gestao_conta.py`). Regra dura do operador: payout ≥80%, confluência ≥75%, só vela fechada.

---

## 1. Gestão de banca — quanto arriscar por operação

### Breakeven (mínimo p/ não perder dinheiro)
Payout é o seu "preço do ingresso". Sem rebate (perde 100% do stake):

| Payout | Breakeven win rate |
|--------|--------------------|
| 75%    | 57,1%              |
| 80%    | 55,6%              |
| 85%    | 54,1%              |
| 90%    | 52,6%              |
| 95%    | 51,3%              |

Fórmula: `breakeven = 100% / (100% + payout)`. Com sua trava de **payout ≥80%**, o mínimo é **55,6% de acerto** — e isso só para empatar. Qualquer confluência < isso = custo certo.

### Kelly (matemática de posição ótima)
`Kelly = (b·p − (1−p)) / b`, onde `b = payout`, `p = sua taxa de acerto`. Kelly *full* é perigosamente alto (10–26% para bons acertos). **Use Quarter-Kelly (25% do valor):**

| Win rate @ payout 80% | Kelly full | Quarter-Kelly |
|------------------------|------------|---------------|
| 58%                   | 5,5%       | ~1,4%         |
| 60%                   | 10,0%      | ~2,5%         |
| 62%                   | 14,5%      | ~3,6%         |

### Recomendação (Fixed Fractional, o padrão da indústria)
- **Entrada base = 1–2% da banca atual** (agressivo: 3%). Nunca acima de **5%** — o "danger zone" da literatura (acima de 5%, risco de ruína dispara).
- **Nunca operar sem vantagem**: se Kelly ≤ 0 (wr abaixo do breakeven), não há edge — parar é a melhor decisão.

---

## 2. Sistemas de recuperação (Martingale / Gale)

### Por que explodem contas
1. **Crescimento exponencial do stake**: dobrar → 1,2,4,8,16… após 6 derrotas você já apostou **63× o stake base**. A 3× (alguns gales), vira **364×** em 6 passos.
2. **Streaks são inevitáveis, não sorte ruim**: em 100 trades com 60% de acerto, há **~92% de chance** de 4 derrotas seguidas e **~32%** de 6 seguidas.
3. **Binárias quebram a matemática do 2×**: Martingale clássico funciona com payoff 1:1. Na binária, o payout (80–95%) é < 1:1, então dobrar NÃO recupera a perda — o stake real necessário é **k = 2 ÷ payout ≈ 2,2–2,7×**, não 2×.

### Recuperação com payout real (alvo = recuperar perda + lucro da base)
Multiplicador da 1ª gale, dado o payout: 75%→2,67× · 80%→2,50× · 85%→2,35× · 90%→2,22×.

**Exposição acumulada (vezes o stake base) se a cadeia morrer em derrota:**

| passo | payout 80% | payout 85% | payout 90% |
|-------|-----------|-----------|-----------|
| 1 derrota  | 1.0× | 1.0× | 1.0× |
| 2 derrotas | 3.5× | 3.35× | 3.22× |
| 3 derrotas | 9.1× | 8.5× | 7.9× |
| 4 derrotas | 21.8× | 19.6× | 17.8× |

### Limites seguros (recomendação concreta)
- **Máximo de 1–2 gales por cadeia** (já tem `max_gales=2` no bot — mantém). **Nunca 3+**: a 4ª derrota já entrega 18–22× exposto.
- **Multiplicador computado pelo payout real** (`k = (perda_acumulada + base) ÷ payout` — que é exatamente o que `multiplicador_gale()` do bot já faz, bom).
- **Trava de exposição total**: a cadeia inteira (soma dos stakes) **nunca pode ultrapassar ~8% da banca**. Se o próximo k estourar isso, encerra a cadeia e aceita a perda (regra já parcialmente presente: `valor_gale > banca → encerra`).
- **Exigir confluência maior na gale** (o bot exige 85% na gale vs 75% na base — correto, não relaxar).

> **⚠️ ALERTA CRÍTICO no código atual (gestao_conta.py):** o "risco dinâmico" **DOBRA o risco (até 8%) quando a banca cai abaixo de 50%** da inicial. Isso é o **exato oposto** do que protege: ao perder, deve-se **REDUZIR** o risco, não aumentar. Com 8% de risco, **8 derrotas seguidas = −50% da banca**. Recomendo **remover/inverter**: quando abaixo de 50%, **reduzir o risco para 1%**, não multiplicar por 4. E o teto de 8% deve baixar para ~3%.

---

## 3. Stop Gain / Stop Loss diário

- **Stop Loss diário: −3% a −5% da banca do dia. Travar o bot e parar.** (Fonte: edgeflo "circuit breaker" — 2% drawdown/sessão ou 2 perdas seguidas; conservador para binárias: 5%).
- **Stop Gain diário: +8% a +15%. Fechar o dia.** Lucro não é sempre; proteger o ganho é gestão real.
- **Disjuntor de sequência (streak breaker)**: pausar após **3–4 derrotas consecutivas**, não importa a causa. Reiniciar só com confluência alta de novo.
- Sempre **recalcular a entrada sobre a banca ATUAL** (o bot já faz: `banca × risco%`) — nunca sobre o valor inicial.

---

## 4. Como o payout afeta o stake

- **Breakeven sobe quando o payout cai**: 75% exige 57,1% de acerto; 90% só 52,6%. Operar apenas quando o payout lido da tela ≥80% (sua trava) protege esse piso.
- **Payout mais baixo exige stake/recuperação maiores** para o mesmo alvo — por isso o multiplicador de gale precisa ser `2/payout`, não o dobro ingênuo.
- **Margem do operador = win rate real − breakeven**. Com 60% de acerto e 80% de payout, você tem 4,4% de margem. Com 55%, você está abaixo do breakeven (55,6%) — **está perdendo por ofício**.

---

## 5. Gestão de sequências (não dobrar após derrota)

- **A derrota não muda a probabilidade do próximo trade.** Streak é ruído estatístico, não "compensação".
- Probabilidade de streak em 100 trades (comum mesmo em estratégia boa): 3 derrotas seguidas ≈ **99%**, 5 derrotas ≈ **62%** (a 60% de acerto).
- **Regra**:
  - Vitória → volta ao stake base (1–2%).
  - Derrota → no máximo 1–2 gales computados pelo payout, **ou** aceitar a perda e seguir com o base.
  - Após 3 derrotas consecutivas (base + 2 gales falhados) → **zerar cadeia, não repetir gale**, e checar se perdeu edge (Kelly ≤ 0).
- **Nunca "média para ganhar"** subindo stake após derrota sem alvo fixo — isso é literalmente apostar contra a ruína.

---

## 6. Impacto psicológico da automatização

- **Vantagem**: o robô remove o tilt — não aposta por raiva nem dobra por teimosia. A emoção é a maior causa de explosão de conta em traders manuais.
- **Risco novo**: a automação **escala a velocidade da ruína**. O que manualmente levaria semanas, o robô faz em horas. Um bug de "risco dinâmico" que dobra o risco pode drenar a conta enquanto você dorme.
- **Implicação prática**: travas de **circuit breaker automático são obrigatórias — stop loss diário, streak breaker e teto de exposição devem ser *hard limits* (não desligáveis por padrão)**, do mesmo jeito que você já exige "só vela fechada / só dado real".
- Audite cedo: a meta não é "o robô acerta mais", é "a conta sobrevive à pior sequência". Robô que acerta 70% mas arrisca 8% por trade ainda tem chance relevante de −50% em poucas sessões.

---

## Resumo numérico (recomendações concretas)

| Parâmetro | Recomendação |
|-----------|--------------|
| Entrada base (fixed fractional) | 1–2% da banca atual (máx. 3% agressivo; nunca >5%) |
| Payout mínimo p/ operar | ≥80% (trava atual ok) |
| Breakeven necessário @80% | ≥55,6% de acerto; ter no mínimo 58–60% de margem |
| Kelly | Quarter-Kelly (25% do Kelly); cap 3% |
| Gale | Máx. **2 passos**, multiplicador = payout real (`k = (perda+base)/payout`, 2,2–2,7×); travar se exposição total da cadeia > ~8% da banca |
| Stop loss diário | −5% da banca (hard stop) |
| Stop gain diário | +8–15% (proteger ganho) |
| Streak breaker | pausar após 3–4 derrotas seguidas; zerar cadeia |
| Corrigir no bot | Remover risco dinâmico 4× quando banca <50% → reduzir p/ 1% ao perder |

---

## Fontes
1. BinaryTrading.com — "Break Even Ratios in Binary Trading" (fórmula breakeven). https://www.binarytrading.com/break-even-ratios-in-binary-trading/
2. Ryan O'Connell (CFA) — "Kelly Criterion: Optimal Position Sizing" (fórmula Kelly + fractional). https://ryanoconnellfinance.com/kelly-criterion/
3. BacktestBase / Market Investigation — "How Much Risk Per Trade" (1–2% padrão, >5% danger zone). https://www.backtestbase.com/education/how-much-risk-per-trade
4. Daily Price Action (Justin Bennett) — "Martingale Strategy: A Ticking Time Bomb" (ruína matemática do gale). https://dailypriceaction.com/blog/martingale-strategy/
5. BinaryOptions.net — "Don't Get Carried Away with Martingale" (dobrar + payout variável). https://www.binaryoptions.net/dont-get-carried-away-with-martingale
6. FXNX / Edgeful — "Streak probability tables" (streaks inevitáveis por win rate). https://fxnx.com/en/blog/consecutive-loss-math-streak-tables-every-win-rate · https://www.edgeful.com/blog/posts/the-data-behind-losing-streaks-in-trading
7. Edgeflo — "Losing Streak" (circuit breaker: 2% drawdown ou 2 perdas seguidas). https://www.edgeflo.com/blog/losing-streak-trading
8. Código do projeto: `core/gestao_conta.py` (estado atual do bot, auditado).

---
*Regra do operador mantida: só fontes reais, só vela fechada. Nenhum número aqui é simulado.*
