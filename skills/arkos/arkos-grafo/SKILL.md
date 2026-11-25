---
name: arkos-grafo
description: Mapa do código/projeto do cliente (grafo de dependências, god nodes, comunidades) para responder perguntas de base de código antes de mexer e atualizar depois. Embrulha o pacote público `graphifyy` (MIT): a skill só instala e usa a ferramenta, não reimplementa. Use em "como esse código se liga", "quem chama X", "mapa do projeto", "montar o grafo", e antes de alterar código que você não escreveu.
status: rascunho
versao: 0.1.0
modulos: [dev]
depende_de: []
---

# arkos-grafo

Clone de sala limpa só na **casca**: a ferramenta de grafo (`graphifyy`) é pública e MIT, então a ARKOS **instala e usa** o CLI `graphify` em vez de reimplementar. A skill padroniza como a ARKOS chama (consultar antes, atualizar depois) e garante janela oculta no Windows. Nenhum conteúdo do pacote é copiado.

## Quando usar e quando não usar

- **Usar:** perguntas sobre código que você não escreveu; antes de alterar; depois de mudar código (atualizar o grafo).
- **Não usar:** projeto trivial de poucos arquivos (o custo não compensa).

## Entradas

- A raiz do repositório do cliente (só o repo, nunca uma pasta-mãe).
- A pergunta (`query`/`path`/`explain`) ou o comando (`graph`/`update`).

## Passos

1. **Conferir o CLI:** `grafo.py check` roda `graphify --version` (subprocesso oculto). Ausente: instruir `uv tool install graphifyy` (não instala sozinho sem OK).
2. **Montar o grafo** na 1ª vez: `graphify extract <raiz>` (build AST + LLM, **custa** — avisar e confirmar o custo antes); pôr `graphify-out/` no `.gitignore`. (`graphify .` não existe no CLI.)
3. **Consultar** antes de responder: `graphify query "<pergunta>"` / `path "A" "B"` / `explain "<conceito>"`.
4. **Atualizar** depois de mudar código: `graphify update .` (AST, sem custo de LLM).
5. Respeitar a privacidade: nada que case com o `ignore` da casa entra na extração semântica.

## Saída

- O subgrafo/resposta do `graphify` repassado ao Claude. A skill não transforma o conteúdo, só organiza a chamada. `grafo.py build-cmd --dry-run` imprime o comando exato (para auditoria).

## Critério de pronto

- [ ] O grafo existe (`graphify-out/graph.json`) antes de responder pergunta de código.
- [ ] Depois de alterar código, o grafo foi atualizado.
- [ ] Todo subprocesso rodou com janela oculta (CREATE_NO_WINDOW).

## Exceções

- **`graphify` ausente:** devolver a instrução de instalação; não travar o fluxo (regra do Jev/decisor).
- **Licença:** se um dia o `graphifyy` deixar de ser MIT, parar de embrulhar e reavaliar (clonar). Confirmado MIT em 2026-11-22.
- **Repo grande:** avisar do tempo; `graphify` faz só AST na atualização.

## Alimenta

- Qualquer skill de dev (ex.: `arkos-impacto` usa o grafo para medir o raio de impacto).

## Regras duras

- Não reimplementar o `graphifyy`: a skill é só a casca (ele é MIT e público).
- Nunca rodar `graphify .` numa pasta-mãe ou no vault inteiro — só no repo.
- Janela sempre oculta no Windows.
