# Mapa do Projeto BFT WIN 3.2

Este mapa separa os produtos do BFT WIN para evitar que uma interface, um
arquivo de referencia ou um executavel sejam confundidos com outro.

## Escopo: Day Trading

O BFT WIN sera desenvolvido somente para necessidades de Day Trading:

- dados intraday e historico de velas;
- indicadores e analise tecnica;
- validacao e backtest das regras;
- risco operacional: valor por entrada, stop gain, stop loss e parada de emergencia;
- execucao controlada por plataforma/API e registro de cada tentativa;
- auditoria de sinais, bloqueios, ordens e resultados;
- interfaces PC, Web e Celular usando o mesmo motor em `core/`.

Uma tecnologia, plugin ou biblioteca so entra no projeto se apoiar uma dessas
necessidades. Ferramentas sem uso direto em Day Trading ficam fora.

## 1. PC - BFT WIN BOT para PC

Produto principal atual para macOS.

- Pasta: `pc/`
- Entrada: `pc/ABRIR_BFT_WIN_3_2.command`
- Aplicativo compilado 3.2: pendente de reconstrução e teste de abertura
- Janela Trading Desk: `pc/app_desktop.py`
- Interface nativa anterior: `pc/interface.py` (fonte das funções em migração)
- Logica do robô: `core/`
- Funcoes: plataformas, leitura de tela, OTC, Mercado Aberto, indicadores,
  estrategias, historico, calibracao, controles de iniciar/pausar/parar e
  parada de emergencia.

Regra: a aparencia do aplicativo para PC deve seguir o Trading Desk, mas todas
as funcoes continuam dentro da janela nativa do BFT.

## 2. Web - BFT WIN BOT para Web

Projeto web separado, para acesso pelo navegador na rede local.

- Pasta: `web/`
- Entrada: `web/ABRIR_BFT_TEMPO_REAL.command`
- Fonte: `web/interface_tempo_real.py`
- Endereco local: `http://127.0.0.1:8765`
- Referencia visual: Trading Desk.

Regra: o HTML de referencia serve de guia visual para a versao web e para o
visual da versao PC. Ele nao substitui o aplicativo nativo nem seus modulos.

## 3. Celular - BFT WIN BOT para Celular

Evolucao futura baseada na versao Web.

- Pasta: `mobile/`
- Base inicial: projeto Web responsivo.
- Uso imediato: abrir o endereco da versao Web pelo celular na mesma rede.
- Caminho futuro: transformar a versao Web em PWA instalavel, sem duplicar a
  logica do robô.

Regra: a versao mobile nao deve criar outro motor de analise. Ela reutiliza a
API e a interface da versao Web.

## Estrutura de Pastas

```text
3.2/
  pc/                         aplicativo nativo BFT WIN BOT para PC
    app_desktop.py            janela desktop com o Trading Desk Web
    interface.py              interface Tkinter anterior, em migração
    BFT WIN 3.1.app           compilação anterior preservada como referência
    ABRIR_BFT_WIN_3_2.command atalho de abertura PC 3.2
  web/                        BFT WIN BOT para Web
    interface_tempo_real.py   servidor e interface Web
    ABRIR_BFT_TEMPO_REAL.command atalho de abertura Web
  mobile/                     futuro app de celular baseado na Web
  core/                       motor compartilhado, leitura e regras
  assets/                     marca e imagens do PC
  scripts/                    suporte macOS
  backups/                    checkpoints automáticos das fontes
  MAPA_DO_PROJETO.md          este mapa
```

## Regra de Trabalho

Antes de cada mudanca, definir qual produto sera alterado:

1. PC: `pc/interface.py`
2. Web: `web/interface_tempo_real.py`
3. Motor compartilhado: `core/`
4. Mobile futuro: partir da Web, nao criar uma terceira logica.
