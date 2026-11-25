---
name: arkos-perfil
description: Memória por empresa ou projeto da ARKOS (oferta, preço, ICP, dores, mecanismo, marca, números, concorrentes, mercado). Comandos criar, ler, atualizar e diff. Use antes de qualquer módulo que precise saber "para quem" é o trabalho, quando o usuário disser "perfil", "cadastrar empresa", "contexto do cliente", ou quando uma skill descobrir um dado durável (preço validado, ICP novo).
status: rascunho
versao: 0.1.0
modulos: [A, todos]
depende_de: []
---

# arkos-perfil

Cada empresa tem **um** perfil. Todo módulo lê antes de rodar e grava de volta o que descobrir. Assim o prestador nunca repete contexto.

## Onde fica

- **Regra PASTA-CASA (2026-11-22):** tudo fica na casa da ARKOS.
  - Perfil do **prestador** (o dono da casa: padrões, `config.aprovadores`, `config.travas`): `<casa>/arkos.engine/perfil.json`. O terminal lê esse arquivo e mostra o nome no cabeçalho.
  - Perfil de cada **cliente**: `<casa>/workspace/<cliente>/_cliente/perfil.md` (frontmatter + texto livre). Vale para todos os projetos do cliente. O próprio negócio do prestador também é um cliente.
- Nuvem (quando o `arkos-base` existir): a fonte da verdade passa a ser a base. O arquivo local vira cache **sem** os campos `privado: true`.
- Compatibilidade: também gerar `workspace/<cliente>/_cliente/product-marketing-context.md` (e, se a skill exigir, uma cópia em `.agents/` na pasta do projeto), que as skills do coreyhaines procuram sem adaptação.

## Formato

```yaml
---
nome: Clínica Sorriso
slug: clinica-sorriso
mercado: BR            # BR | EUA | EU
tipo_negocio: servico-local   # saas | servico-local | agencia-oaas | infoproduto | high-ticket | ecommerce | imovel
oferta: { nome: "", promessa: "", entregavel: "", garantia: "", prazo: "" }
preco: { valor: 0, moeda: BRL, parcelas: 0, ancora: "" }
icp: { nicho: "", porte: "", local: "", cargo_decisor: "", ticket: "" }
dores: []
mecanismo: { nome: "", como_funciona: "", prova: "" }
marca: { voz: "", exemplos_voz: [], cores: [], logo: "" }
numeros: { ticket_medio: null, margem: null, cac: null, ltv: null, cpa_alvo: null, privado: true }
concorrentes: []
restricoes: []          # o que o dono não aceita (ex.: "sem desconto", "sem WhatsApp frio")
fontes: {}              # de onde veio cada campo (entrevista, skill X, data)
config:                 # padrões configuráveis das travas: TODOS "a confirmar" com o dono
  travas:
    budget_variacao_max_conjunto: 0.20      # a confirmar
    budget_variacao_max_conta: 0.30         # a confirmar
    intervalo_dias: 3                       # dias entre aumentos de budget (arkos-escala); 1-2 só com 30+ conv./dia, atribuição confiável e decisão do dono registrada
    folga_min: 0.10                         # folga mínima (meta − CPA 7d)/meta para escalar; passo = até metade da folga
    pagamento_segunda_confirmacao_acima: { BRL: 500, USD: 100 }   # a confirmar
    aprovacao_envio_validade: 2h            # a confirmar
    aprovacao_escrita_validade: 30min       # a confirmar
    envio_volume_diario: {}                 # por canal/caixa, a confirmar
  custos:
    perguntar_antes: true                   # fixo: sempre informa custo estimado e pergunta; sem teto
atualizado_em: 2026-11-21
---
```

## Comandos

| Comando | O que faz |
|---|---|
| `perfil criar` | Entrevista guiada (no máximo 12 perguntas, uma rodada). Reaproveita o roteiro do `product-marketing` (coreyhaines). Campos sem resposta ficam vazios, nunca inventados |
| `perfil ler [campo]` | Devolve o perfil ou o campo. Campo `privado: true` aparece como `[privado]` para prestador |
| `perfil atualizar <campo> <valor> --fonte <skill>` | Grava com fonte e data. Mudança em `preco`, `oferta` ou `numeros` mostra o antes e o depois e pede confirmação |
| `perfil diff [--desde AAAA-MM-DD]` | O que mudou, quem mudou e por quê |

## Regras duras

- **Nunca inventar** número, preço ou depoimento. Vazio é vazio.
- Toda escrita grava `fontes.<campo>` = `{skill, data, execucao}`.
- Campo `privado: true` não vai para prompt de terceiros, nem para o Jev, nem para o relatório de cliente.
- O perfil não guarda dado pessoal de lead nem de cliente final.

## Pendências

- Esquema JSON para validar o frontmatter (o terminal hoje só lê `nome`).
- Sincronização com a nuvem: quem ganha em conflito (proposta: a nuvem, com o diff mostrado).
