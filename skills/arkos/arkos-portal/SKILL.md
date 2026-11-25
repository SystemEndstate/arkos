---
name: arkos-portal
description: Testar e conferir páginas web (landing, app, checkout do cliente) com Playwright headless — abrir a URL, tirar print, ler erros de console e checar se o texto/elemento esperado está lá. Use em "conferir a página", "testar a landing no navegador", "tirar print do site", "o botão apareceu?", "ver se deu erro no console", e na etapa de verificação de site/landing.
status: rascunho
versao: 0.1.0
modulos: [site, dev]
depende_de: []
---

# arkos-portal

Clone de sala limpa só na casca: usa o **Playwright** (público, Apache-2.0) headless para abrir a página, tirar print e ler o console, sem nenhum app/portal pessoal. Roda o node com janela oculta no Windows. Serve para conferir a própria entrega antes de mostrar ao cliente.

## Quando usar e quando não usar

- **Usar:** conferir uma página local/pública (texto, elemento, print, erro de console) depois de mexer nela.
- **Não usar:** monitorar uptime de produção (isso é `arkos-monitor`); automação que escreve em conta de terceiro.

## Entradas

- `url` (http(s) ou `file://` local).
- O que checar: `goal`/`texto_esperado`/`seletor`; caminho do `out` do print.

## Passos

1. **Conferir ferramenta:** `portal.py check` vê node + `npx playwright` (janela oculta). Ausente: instruir `npm i -D playwright && npx playwright install chromium`.
2. **Montar o roteiro** headless (`portal.py testar --dry-run` mostra o script node): abrir a URL, esperar a rede parar, tirar o print em `out`, coletar erros de console e checar `texto_esperado`/`seletor`.
3. **Rodar** o node com `windowsHide: true` (e o subprocesso python com CREATE_NO_WINDOW).
4. **Ler o resultado:** print salvo, lista de erros de console, achou/não achou o esperado.
5. Corrigir o que apareceu e rodar de novo.

## Saída

JSON: `{url, print, console_erros:[...], encontrou:bool, dry_run?}`. Em `--dry-run`, o script node e o comando, sem executar.

## Critério de pronto

- [ ] A URL é http(s) ou file:// (recusa o resto).
- [ ] O print foi salvo no `out`.
- [ ] Erros de console foram listados (não escondidos).
- [ ] node rodou com janela oculta.

## Exceções

- **node/playwright ausente:** devolver a instrução de instalação; não travar.
- **URL inválida:** recusar antes de abrir o navegador.
- **Página não carrega (timeout):** registrar o erro e o print do que deu.

## Alimenta

- A etapa de verificação de `site-landing`; o resultado volta ao Claude para corrigir.

## Regras duras

- Só headless; nunca abrir janela de navegador visível (regra da casa).
- node sempre com `windowsHide: true`; python com CREATE_NO_WINDOW.
- Não reimplementar o Playwright: a skill é só a casca.
