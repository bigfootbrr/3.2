# 🔍 ESTUDO: AUTOMATIZADORES DO MERCADO → O QUE A BFT TRAZ
*2026-09-03 · Pesquisa em bots open-source de opções binárias (GitHub)*

---

## O QUE EXISTE LÁ FORA

| Projeto | ⭐ | O que faz | Fraqueza |
|---|---|---|---|
| **Iq_Option_Bots** (metheuspsc) | 134 | Web app (Streamlit), login + config, várias estratégias e corretoras | Credenciais em texto; usa API não-oficial (detectável, contra ToS) |
| **bot-iqoption-mhi** (iago-silva) | 24 | Estratégia MHI com ciclos: Stop Gain ÷ ciclos = entrada base (calculada pelo payout) | Credenciais hardcoded; sem gestão de risco |
| **TradeBotIQOption** (kushaln3) | 2 | Cadeia de recuperação de capital (Soros ×k) + motor de simulação/backtesting com milhões de rodadas | **O autor QUEBROU a conta**: 8 derrotas seguidas sem stop comeram tudo |
| **pypocketoption** (usmanch96) | — | API assíncrona WebSocket p/ PocketOption | Só PocketOption |
| **ejtraderiq-js** (ejtraderLabs) | 11 | API JS com IA | Só IQ, via API |

## O QUE A BFT JÁ TEM (e os outros NÃO têm)

| Recurso | BFT 3.3 | Mercado |
|---|---|---|
| **Leitura visual (OCR)** em vez de API | ✅ | ❌ (usam API = detectável/banível) |
| **Cl furtivo humanizado** (timing único) | ✅ | ❌ nenhum tem |
| **Login com Keychain** (nunca texto puro) | ✅ | ❌ (hardcode no código) |
| **AUTO dinâmico** (testa 15 indicadores, escolhe 3) | ✅ | ❌ (MHI fixo ou sinal ALEATÓRIO!) |
| **Gate de payout >80%** lido da tela | ✅ | ❌ (opram sem ver payout) |
| **Stop Gain + Stop Loss bloqueando disparo** | ✅ | parcial (kushaln3 provou o porquê) |
| **Placar V/D/E em tempo real** | ✅ | raro |
| **Sinais OU Bot** (escolha do operador) | ✅ | ❌ (só bot) |
| **4 plataformas** (IQ/Quotex/Casa/Avallon) | ✅ | 1-2 cada |

## 🎯 O QUE VAMOS TRAZER DA BFT (aprovado do estudo)

### 1. SOROS/GALE inteligente (da cadeia de recuperação do kushaln3)
Após derrota, a próxima entrada é multiplicada por k (calculado pelo
payout) para recuperar a perda + lucro alvo — **MAS** com:
- Limite de cadeia N=2 (no máximo 2 gales; kushaln3 quebrou com 8!)
- Nível de confluência MAIOR pra aceitar gale (exigir +10%)
- STOP LOSS da gestão sempre acima da cadeia (proteção total)

### 2. Ciclos MHI (do bot MHI)
Stop Gain ÷ ciclos = meta por ciclo. A gestão já faz isso por operação;
vamos expor o "meta por ciclo" no placar.

### 3. Motor de simulação (backtesting) — fronteira
Rodar as TOP 5 estratégias sobre histórico real (Yahoo) e ranquear por
taxa de acerto antes de operar. (próxima fronteira — já documentada)

---

## LIÇÃO DE OURO DO ESTUDO

> kushaln3 transformou $10.000 em $33.000 em 3 dias — e perdeu TUDO numa
> cadeia de 8 derrotas porque não tinha stop. A BFT nasceu com o que ele
> percebeu tarde demais: **cadeia limitada + stop obrigatório + payout
> mínimo + confluência real**. Nosso organismo já nasce blindado.