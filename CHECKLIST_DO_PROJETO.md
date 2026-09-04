# Checklist do Projeto BFT WIN 3.2

Atualizado em: 2026-09-02

## Estrutura

- [x] Motor compartilhado em `core/`.
- [x] Produto PC separado em `pc/`.
- [x] Produto Web separado em `web/`.
- [x] Pasta `mobile/` reservada para futura PWA.
- [x] Mapa de arquitetura em `MAPA_DO_PROJETO.md`.
- [x] Checkpoints de fonte em `backups/`.

## PC

- [x] Janela WebView criada em `pc/app_desktop.py`.
- [x] Trading Desk Web carregado dentro da janela macOS.
- [ ] Migrar controles operacionais do Tkinter para a API Web.
- [ ] Reempacotar `pc/BFT WIN 3.2.app` com a janela WebView.
- [ ] Gerar o DMG final após os testes.

## Web e Mobile

- [x] Trading Desk disponível em `web/interface_tempo_real.py`.
- [x] Conectar iniciar, pausar e emergência Web ao motor em somente sinais.
- [x] Conectar configurações, plataformas e indicadores ao motor.
- [x] Fazer a seleção OTC iniciar o mercado e o ativo corretos no motor.
- [x] Exibir no Trading Desk a análise OTC emitida pelo motor.
- [ ] Levar a captura visual OTC da interface nativa para o Trading Desk.
- [ ] Conectar o histórico de entradas ao Trading Desk.
- [ ] Adaptar a interface como PWA para celular.

## OTC e Segurança

- [x] Leitura de ativo, payout, velas e botões existente.
- [x] Plataforma confirmada e armação de uma entrada real existente.
- [ ] Exigir duas capturas OTC compatíveis antes de liberar análise.
- [ ] Confirmar visualmente o timeframe da corretora.
- [ ] Criar testes com capturas aprovadas e rejeitadas.

## Regra de Backup

Antes e depois de cada etapa concluída, executar:

```zsh
./scripts/criar_checkpoint.sh nome-da-etapa
```

Cada arquivo em `backups/` salva fontes, assets, scripts e documentação, com
manifesto e SHA-256. O aplicativo compilado não entra no backup porque pode ser
reconstruído a partir do código-fonte.
