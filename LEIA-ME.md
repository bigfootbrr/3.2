# BFT WIN 3.2 — fase de testes reais

## Mapa do projeto

Consulte `MAPA_DO_PROJETO.md` antes de alterar a interface. Ele define os
produtos separados: BFT WIN BOT para PC, BFT WIN BOT para Web e a evolucao
futura para celular baseada na versao Web.

O BFT WIN mantém dois fluxos separados. Nenhum deles exige confirmação visual
do tipo de conta. Antes de um modo automático, a plataforma escolhida precisa
ser confirmada na aba **Plataformas**.

## Mercado Aberto

- Usa velas Forex externas reais por conexão online.
- Possui 28 pares em ordem alfabética.
- Não usa captura de tela, payout visual nem dados simulados para analisar.
- Se a fonte externa falhar, mostra **DADOS INDISPONÍVEIS** e não inventa velas.
- RSI, MACD, ADX, direção e confluência são calculados com as velas recebidas.
- No modo real, somente o par escolhido pode gerar um disparo.
- A plataforma confirmada e a armação de um único disparo continuam obrigatórias.

## OTC

- Usa exclusivamente a captura visual da corretora.
- Antes da análise, valida plataforma, ativo/par, timeframe, velas, payout e
  área dos botões.
- O payout digitado manualmente não autoriza entrada; vale somente o payout
  reconhecido na captura atual.
- Captura incompleta, ativo diferente, payout inválido ou troca de plataforma
  descarta a leitura e desarma o disparo real.

## Como abrir

1. Abra a pasta `pc/` e dê dois cliques em `ABRIR_BFT_WIN_3_2.command`.
2. Na aba **Plataformas**, escolha e confirme IQ Option, Quotex, Casa Trader ou
   Avallon.
3. Escolha **Mercado Aberto** ou **OTC**, o ativo, o timeframe e o modo.
4. Pressione **INICIAR**. Selecionar modo real e iniciar arma no máximo um
   disparo; depois de um clique bem-sucedido, é necessário iniciar novamente.

O login é sempre manual. Usuário e senha não são solicitados nem armazenados.
A parada de emergência interrompe o processamento e desarma o modo real.

## Observações sobre os dados

As velas do Mercado Aberto são dados externos reais, não uma simulação. A
latência e a disponibilidade dependem do provedor público; portanto, o app não
promete feed de bolsa de baixa latência. A confluência é uma pontuação técnica
experimental, não uma probabilidade garantida de resultado.
