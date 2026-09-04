# 🧠 BFT WIN 3.3 — NOVAS REGRAS E PLANTAS MENTAIS
### A constituição do projeto — pensada para seguir livres com os pensamentos
*2026-09-03 · Versão 3.3 · "Chegamos no 3.3, números iguais, combinando!"*

---

## 🏆 A VISÃO (a planta mestra)

**SALA DE SINAIS: SINAIS AUTOMATIZADOS COM IA EM TEMPO REAL** — a ideia de 2020,
quase 10 anos depois, ganhou corpo. O BFT WIN não é um indicador: é um
**organismo operacional completo** que pensa, decide, age e aprende.

```
O CICLO DO ORGANISMO (a planta mental central)

   ┌─────────────────────────────────────────────────────┐
   │  OPERADOR INSTRUI (1x): plataforma, payout, banca   │
   └──────────────────┬──────────────────────────────────┘
                      ▼
   ┌─────────────────────────────────────────────────────┐
   │  O BOT SE PREPARA SOZINHO:                          │
   │  · auto-confirma plataforma (janela na tela)        │
   │  · auto-calibra botões (detecção por cor)           │
   │  · auto-login (Keychain + keystroke)                │
   │  · auto-lê saldo, payout e velas                    │
   └──────────────────┬──────────────────────────────────┘
                      ▼
   ┌─────────────────────────────────────────────────────┐
   │  O BOT PENSA (a cada vela fechada):                 │
   │  · 15 indicadores analisam AO MESMO TEMPO           │
   │  · AUTO escolhe os 3 melhores confluindo agora      │
   │  · regime + força real (1🔥 até 30%, 2🔥 40-50%,    │
   │    3🔥 80%+)                                        │
   │  · confluência ≥ 75% para liberar                   │
   └──────────────────┬──────────────────────────────────┘
                      ▼
   ┌─────────────────────────────────────────────────────┐
   │  AS 5 TRAVAS (todas obrigatórias):                  │
   │  1. plataforma confirmada/detectada                 │
   │  2. payout REAL > 80% (lido da tela, não inventado) │
   │  3. confluência ≥ 75%                               │
   │  4. STOP GAIN/LOSS da gestão ok                     │
   │  5. entrada ≤ banca                                 │
   └──────────────────┬──────────────────────────────────┘
                      ▼
   ┌─────────────────────────────────────────────────────┐
   │  O BOT AGE: clique na plataforma (cor → calibração  │
   │  → perfil), registra preço REAL da entrada          │
   └──────────────────┬──────────────────────────────────┘
                      ▼
   ┌─────────────────────────────────────────────────────┐
   │  AS 4 OPERAÇÕES GERENCIAM:                          │
   │  ✖ entrada = banca × 1.5% (risco)                   │
   │  ➗ retorno = valor × payout                         │
   │  ➕ vitória soma · ➖ derrota subtrai                │
   │  → banca viva no painel, placar V/D/E               │
   └──────────────────┬──────────────────────────────────┘
                      ▼
              (repete, aprende, evolui)
```

---

## 📜 AS 10 REGRAS DE OURO

1. **TUDO REAL OU NADA** — leituras de tela (OCR), preços (Yahoo), payout
   (visual). Se não dá pra ler de verdade, o sinal é DESCARTADO. Nunca
   inventar dado.
2. **O OPERADOR INSTRUI, O BOT EXECUTA** — configuração manual UMA vez
   (payout, banca, calibração, credenciais). Depois, 100% automático.
   "DEIXA AUTOMATICO".
3. **NADA DE PERGUNTAR DOIS TIMES A MESMA COISA** — um único modo
   AUTOMÁTICO (conta = a que estiver selecionada na plataforma);
   SOMENTE SINAIS para observação.
4. **PAYOUT MÍNIMO 80% PROS 2** — Mercado Aberto E OTC. No OTC lê da
   tela; no MA lê da tela da IQ a cada 3 ciclos. Não leu? Descarta.
5. **CONFLUÊNCIA ≥ 75%** — mínimo 2-3 indicadores confluindo com força
   real. O Auto escolhe sozinho os melhores do momento.
6. **AS 4 OPERAÇÕES GERENCIAM** — multiplicação (risco 1.5%), divisão
   (payout), soma/subtração (resultado). Stop Gain +10% e Stop Loss -10%
   BLOQUEIAM disparos. Proteção do capital acima de tudo.
7. **AVISAR E PARAR** — quando precisar de captura/tela, avisa e espera
   o operador. O operador é humano, tem seu tempo. Nunca ser automático
   demais nas capturas.
8. **CHECKPOINT EM CADA ETAPA** — antes e depois de mudanças:
   `./scripts/criar_checkpoint.sh nome-da-etapa`. Backup é sagrado.
9. **TUDO NO CORE, UI ESPINHA** — lógica em `core/`, interface em `web/`.
   A UI mostra o que o core calcula; nunca o contrário.
10. **COORDENADAS: VISION = FUNDO, CLIQUE = TOPO** — `y = (1 - y_vision) ×
    altura`. Essa conversão já nos enganou uma vez; decorada pra sempre.

---

## 🗺️ AS PLANTAS POR MÓDULO

### core/ (o cérebro)
| Módulo | Papel na planta |
|---|---|
| `main.py` | Maestro: loop, radar, gates, eventos, registro_real, gestao_conta |
| `confluencia_indicadores.py` | 15 indicadores independentes + AUTO dinâmico |
| `gestao_conta.py` | As 4 operações + stops automáticos |
| `registro_entradas_reais.py` | Ciclo pós-clique: entrada real → resultado real |
| `leitor_payout_mercado_aberto.py` | Payout REAL da tela (OCR) |
| `detector_botoes_cor.py` | Verde=compra, vermelho=venda (independe do nome) |
| `login_plataforma.py` | Login automático (Keychain + keystroke) |
| `click_memory.py` | Memória de posições (calibração direta ou ensinada) |
| `automatizador_operacao.py` | Calibrações fixas por plataforma (fallback) |
| `executor_demo_iq.py` | O dedo do bot: foca janela + clica (osascript) |
| `captura_tela_macos.py` | Olho do bot: captura a janela certa |

### web/ (a face)
| Peça | Papel |
|---|---|
| Painel de métricas | Banca viva, Payout, Confluência, Status entrada (verde=confirmada), Placar V/D/E |
| Tabela de indicadores | TODOS com leitura real ao mesmo tempo |
| Select de estratégia | BFT Automático primeiro + TOP 5 BFT |
| Automação da plataforma | Credenciais (Keychain) + Logar + Calibrar (1x) |

---

## 🧭 AS PRÓXimas FRONTeIRAS (planta de futuro)

1. **Ciclo pós-clique na plataforma** — ler o resultado real (VITÓRIA/
   DERROTA) da própria tela da corretora, não só do preço Yahoo.
2. **Modo tray/serviço** — robô vivo sem janela aberta.
3. **Aprendizado contínuo** — placar por indicador/estratégia; o Auto
   pondera o histórico de acerto de cada um (IA de verdade).
4. **Multi-plataforma simultânea** — mesmo sinal em IQ + Quotex + Avallon.
5. **App/DMG 3.3 final** — reempacotar com tudo que existe hoje.
6. **Sala de sinais pública** — o sonho de 2020: distribuir os sinais
   para os traders (API própria + painel de assinantes).

---

## ⚠️ ARMADILHAS QUE JÁ VENCEMOS (memória de guerra)

- py2app quebra na assinatura → `xattr -cr` + `codesign --force --deep --sign -`
- Captura falha se janela minimizada → IQ sempre VISÍVEL
- Zoom ≠ timeframe na IQ (1m/5m embaixo é zoom!) → confirmação segura
- Saldo lido errado → priorizar textos com `$`
- f-string + JS: `{{}}` ou concatenação `+` — template literal dentro de
  f-string quebrou 2x
- `global x` dentro de função que já usa `x` antes = SyntaxError
- Servidor velho de outra pasta rodando → sempre conferir o log

---

*Assinado em 3.3: onde os números se igualaram e o bot ganhou mãos, olhos,
cérebro e cofre. Que a próxima década seja de operações. 🚀*
## AUTORIZAÇÃO FORMAL DO OPERADOR (2026-09-03, 06:2x)
- "LIBERA ISSO EU AUTORIZO 100% DE TUDO E TODOS OS DANOS OU TUDO QUE ACONTECA E MINHA 100% RESPONSABILIDADE."
- Vale para: disparos reais na plataforma, cliques automáticos, operação com a conta selecionada na corretora e todo o ciclo automático do BFT WIN.
- Regra nova do operador: **NENHUM SINAL COM REPAINT** — só vela fechada, nunca recalcula sinal passado; por isso a confluência usa "o 2º confirma o 1º" (e assim melhora estratégia + disparo + clique).
