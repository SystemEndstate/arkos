---
name: arkos-gate-rag
description: Portão de qualidade de pesquisa e de resposta com RAG na ARKOS — confere, por script, se cada afirmação tem fonte, se a confiança foi marcada, se a afirmação com número foi triangulada em 2 domínios e se toda fonte tem URL e data de acesso. Reprova o relatório antes de ele chegar ao cliente. Use em "conferir a pesquisa", "checar as fontes", "a resposta tem fonte?", "gate da pesquisa", "validar o relatório de mercado", "RAG com citação", e na etapa de verificação de pesquisa-mercado.
status: rascunho
versao: 0.1.0
modulos: [P]
depende_de: [arkos-pesquisa]
substitui: clarity-gate (sem fonte livre; esta é uma implementação própria, escrita do zero)
---

# arkos-gate-rag

O `arkos-pesquisa` organiza a busca; esta skill é o **portão** no fim: nada de pesquisa, relatório de mercado ou resposta montada com RAG sai sem passar aqui. Ela não escreve nem corrige o texto — aponta linha por linha o que falta.

## Comando

```bash
py -3 scripts/gate_rag.py checar relatorio.md [--casa C --cliente X --projeto Y]
py -3 scripts/gate_rag.py checar ledger.json        # ledger do arkos-pesquisa também vale
```

Código 0 = verde, 1 = vermelho (lista dos problemas com a linha), 2 = entrada incompleta. Com `--casa`, o resultado fica em `workspace/<cliente>/<projeto>/pesquisa/gate-rag-<nome>-<data>.json`.

## Formato que o gate lê

- Cada item de lista ou parágrafo do corpo é **uma afirmação**. Ficam de fora as seções Fontes, Referências, Lacunas, Método e Perguntas.
- A afirmação termina com as fontes e a confiança: `… vale desde 2018 [1, 2] {alta}`.
- `Lacuna:` e `Opinião:` no começo dispensam fonte. Opinião não pode trazer número.
- Seção `## Fontes`: uma linha por fonte, `[n] título — URL (acesso AAAA-MM-DD)`.

Exemplo verde em `engine/skills-rascunho/_comum/exemplo-pesquisa.md`.

## Regras duras (cada uma reprova)

1. `sem_fonte`: afirmação sem `[n]`.
2. `sem_confianca`: afirmação sem `{alta}`, `{média}` ou `{baixa}`.
3. `fonte_inexistente`: `[n]` que não está na lista de fontes.
4. `critica_sem_triangular`: afirmação com número citando menos de 2 domínios diferentes. Resolve com a 2ª fonte independente ou baixando para `{baixa}`.
5. `alta_com_fonte_unica`: confiança alta com um domínio só.
6. `fonte_sem_url` e `fonte_sem_data_de_acesso`.
7. `opiniao_com_numero`: número dentro de opinião é afirmação disfarçada.

Fonte listada e não citada vira **aviso**, não reprova.

## Passos

1. O `arkos-pesquisa` monta o ledger e o Claude escreve o relatório no formato acima.
2. `checar`. Vermelho: corrigir **a afirmação** (achar a 2ª fonte, baixar a confiança ou virar lacuna); nunca apagar a regra nem tirar o número para passar.
3. Verde: segue para o `arkos-gate` (copy) e para a entrega.

## Pronto quando

`checar` sai com código 0 no relatório final que vai para o cliente.

## Exceções

- `entrada_incompleta`: arquivo inexistente, sem a seção de Fontes ou sem nenhuma afirmação. Código 2 e a lista.
- `resultado_ruim`: vermelho 3 vezes seguidas no mesmo relatório. Escalar para o dono com a lista de lacunas: a pesquisa não achou o que precisava.

## Limites

- O gate confere a **forma** da evidência (há fonte, há data, há 2 domínios), não se a fonte diz mesmo aquilo. Quem lê a fonte é o Claude no `arkos-pesquisa`. Dois domínios do mesmo grupo (portais que copiam a mesma nota) contam como dois: na dúvida, baixar a confiança.
