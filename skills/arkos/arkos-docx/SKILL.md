---
name: arkos-docx
description: Gera e edita documentos Word (.docx) na pasta do cliente com bibliotecas livres (python-docx), na identidade ARKOS — proposta, contrato, relatório, briefing, ata, com capa, cabeçalho, tabelas e notas. Edita um .docx existente trocando {{chaves}} sem perder a formatação e sem sobrescrever o original. Use em "documento Word", "proposta em .docx", "editar o contrato", "trocar o nome no documento", "relatório em Word", "gerar docx", "Word document".
status: rascunho
versao: 0.1.0
modulos: [D, O]
depende_de: []
substitui: anthropic-skills:docx (clone de sala limpa; texto e código escritos do zero)
---

# arkos-docx

Word sai de um **spec JSON** e de um script determinístico (`scripts/docx_arkos.py`). O Claude escreve o conteúdo no spec; o script cuida da forma. Nada de montar o .docx à mão no chat.

## Pasta-casa

Tudo vai para `workspace/<cliente>/<projeto>/documentos/`, com nome `<titulo-em-slug>-<AAAA-MM-DD>.docx`. Se o nome já existir, sai `-v2`, `-v3`: **nunca sobrescreve**.

## Comandos

```bash
py -3 scripts/docx_arkos.py gerar spec.json [--trocar chaves.json] --casa <casa> --cliente <c> --projeto <p>
py -3 scripts/docx_arkos.py editar entrada.docx [--trocar chaves.json] [--anexar spec.json] --casa <casa> --cliente <c> --projeto <p>
py -3 scripts/docx_arkos.py ler arquivo.docx      # texto e tabelas em JSON: ler antes de editar
```

Spec (blocos em ordem): `{"h": "Seção"}`, `{"h2": ...}`, `{"p": "texto"}`, `{"lista": [...], "numerada": false}`, `{"tabela": {"colunas": [...], "linhas": [[...]]}}`, `{"nota": "...", "rotulo": "Estimativa"}`, `{"quebra": true}`. Exemplo em `engine/skills-rascunho/_comum/exemplo-proposta.json`.

## Passos

1. Pedir ao `arkos-intake` o que faltar: título, tipo do documento, cliente e os fatos. Número que ninguém mediu entra como `{"nota": ..., "rotulo": "Estimativa"}`.
2. Escrever o spec. Valores que o prestador ainda vai decidir ficam como `{{chave}}`.
3. `gerar`. Se a saída vier `amarelo` com `nao_trocadas`, ainda há `{{chave}}` aberta: o documento **não está pronto**.
4. Para mudar um documento que já existe: `ler`, depois `editar --trocar` (e `--anexar` para acrescentar seções). O original fica intocado.
5. Passar pelo `arkos-gate` (copy) antes de mandar ao cliente.

## Identidade

Capa com o tipo em mono (aço), título grande em Ink e régua grafite. Cabeçalho `ARKOS ENGINE · <CLIENTE>`, rodapé com tipo, data e número da página. Tabela com cabeçalho Ink. **Volt não vai no papel claro.** Fontes Inter Tight e JetBrains Mono; o Word troca por uma equivalente se não estiverem instaladas.

## Regras duras

- O arquivo fica na pasta-casa, com data no nome, e nunca sobrescreve outro.
- Metadados preenchidos: título, autor `ARKOS Engine`, assunto e cliente.
- Documento com `{{chave}}` sobrando não é entregue.
- Não inventar número, cliente, depoimento ou preço: o que não é fato vira nota de estimativa ou `{{chave}}`.
- A edição não altera o original; sai um `-editado` novo.

## Pronto quando

O script devolve `status: ok` (sem `nao_trocadas`) e o arquivo passa nas regras acima (`_testes/aceitacao_clones.py`, T3). Depois disso vem o gate de copy do `arkos-gate`.

## Exceções

- `entrada_incompleta`: sem `titulo` ou `blocos` (ou arquivo de entrada inexistente), o script sai com código 2, lista **tudo** o que falta e não escreve nada. O `arkos-intake` pergunta num bloco só.
- `resultado_ruim`: o gate de copy reprovou; corrigir o spec e gerar de novo (sai `-v2`).

## Pendências

- Converter para PDF sem Word instalado: hoje usar o `arkos-pdf gerar` com o mesmo spec.
- Comentários e controle de alterações (revisão do cliente dentro do Word).
