---
name: arkos-artes
description: Cria criativos estáticos na marca do cliente — story/reels 9:16, feed 4:5, quadrado 1:1 e carrossel com PDF — a partir de um spec, por HTML renderizado no Chrome headless sem janela, com safe zone, limite de texto e contraste conferidos. Use em "criativo", "arte para o Instagram", "carrossel", "story", "post 4:5", "arte do anúncio", "PDF do carrossel", "criar artes".
status: rascunho
versao: 0.1.1
modulos: [C, 7, 8]
depende_de: []
substitui: criar-artes (repo de colega; esta é uma implementação própria, escrita do zero)
---

# arkos-artes

Criativo sai de um **spec** e de um script (`scripts/artes_arkos.py`), que monta uma página HTML por peça e tira a foto no tamanho exato pelo Chrome headless. **A marca é a do cliente**, não a da ARKOS.

## Pasta-casa

Cada lote numa pasta nova: `workspace/<cliente>/<projeto>/criativos/<slug>-<AAAA-MM-DD>/`, com `peca-01.png`… e `carrossel.pdf`, além do `artes.json` usado (para refazer igual) e do HTML de cada peça.

## Comandos

```bash
py -3 scripts/artes_arkos.py gerar artes.json --casa C --cliente X --projeto Y
py -3 scripts/artes_arkos.py checar <pasta-do-lote>
```

Spec: `titulo`, `formato` (`9:16` 1080×1920, `4:5` 1080×1350, `1:1` 1080×1080), `marca` (`nome`, `fundo`, `texto`, `acento`, `logo` opcional) e `pecas` (`kicker`, `titulo`, `texto`, `cta`, `imagem` local opcional). Exemplo em `_comum/exemplo-artes.json`.

## Passos

1. Copy primeiro: gancho no título da 1ª peça, uma ideia por peça, CTA só na última (ou na única).
2. Marca do cliente: cores do perfil (`arkos-perfil`) e logo dele, se houver. Foto: só material do cliente ou banco licenciado; nunca gerar rosto de cliente real.
3. `gerar`. Olhar as PNG: o texto lê bem no celular?
4. Passar pelo `arkos-gate` (copy e criativo) antes de publicar ou subir no anúncio.

## Regras duras

- **Safe zone.** No 9:16 (1080×1920) nada de texto nem logo nos **270 px de cima (14%)** e nos **672 px de baixo (35%)**, como pede o guia de anúncios da Meta para Stories e Reels; a numeração do carrossel fica no topo, ao lado da marca (regra do `arkos-gate`). No 4:5 e no 1:1, 110/100 px de margem em cima e embaixo, 90 px nos lados.
- **Limite de texto:** kicker 32, título 70, texto 200, CTA 28 caracteres. Passou, a saída é erro de entrada: corta-se o texto, não a fonte.
- **Contraste** texto/fundo ≥ 4,5:1, conferido antes de renderizar. A cor do acento só vira cor de texto quando tem contraste.
- Tamanho exato em pixels, uma PNG por peça e PDF com uma página por peça.
- Chrome headless sem janela (`CREATE_NO_WINDOW`) e com perfil temporário. Fontes Inter Tight e JetBrains Mono (OFL, em `fonts/`) embutidas na página.

## Pronto quando

`checar` sai com código 0: quantidade, tamanho de cada peça, nenhuma peça vazia e páginas do PDF batendo (T3 de `_testes/aceitacao_clones.py`). Depois vem o gate de copy.

## Exceções

- `entrada_incompleta`: falta campo, formato inválido, texto acima do limite, contraste baixo ou imagem e logo que não existem. Sai com código 2, a lista completa e nenhum arquivo.
- `fora_do_ar`: sem Chrome/Edge, código 3 e o que instalar (ou `ARKOS_CHROME`).

## Pendências

- Vídeo curto e animação: ficam com as skills de vídeo (hyperframes/remotion), não aqui.
- Modelos de layout extras (foto em tela cheia, antes e depois, depoimento com aprovação do cliente).
