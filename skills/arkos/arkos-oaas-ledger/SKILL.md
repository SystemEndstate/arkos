---
name: arkos-oaas-ledger
description: Livro-razão de resultados OaaS - cada resultado vira uma linha com evidência, fonte, hora e status (cobrável, excluído, contestado), verificada pelo Jev + amostra humana antes de faturar, com relatório mensal auditável ao cliente e ligação com Asaas/Stripe. Use durante a entrega de contrato por resultado, no fechamento do mês, ao preparar fatura variável ou ao responder contestação do cliente.
status: rascunho
versao: 0.1.0
modulos: [P, E, D]
depende_de: [arkos-oaas-proposta, arkos-gate, arkos-guarda-escrita, jev]
---

# arkos-oaas-ledger

É o que torna a garantia **auditável**. Sem ledger, não há cobrança variável.

## Onde fica

- Ledger no `arkos-base` (tabela `oaas_ledger`, append-only: correção = linha nova que anula a anterior).
- Cópia de leitura em `workspace/<cliente>/<projeto>/oaas/ledger.csv` para o relatório.

## Linha do ledger

| Campo | Exemplo |
|---|---|
| `id`, `contrato`, `ficha_versao` | `led-000123`, `endstate-cli-07`, `v1` |
| `ocorrido_em`, `registrado_em` | ISO-8601 |
| `unidade` | `reuniao_qualificada` |
| `evidencia` | link/ID na fonte da verdade (evento do CRM, log do n8n, ID do Ads, evento GA4) + hash do payload |
| `fonte` | `n8n:exec/8812` |
| `verificacao` | `jev:0.93` + `amostra_humana:ok/pendente` |
| `status` | `cobravel` · `excluido:<motivo da ficha>` · `contestado` · `anulado` |
| `valor` | preço da unidade na versão da ficha |

## Passos

1. **Coletar** resultados da fonte da verdade (n8n-mcp, CRM, GA4, Meta Ads), só leitura, por janela.
2. **Aplicar a ficha:** cada critério de "não conta" vira regra determinística (duplicado, fora do ICP, no-show, já estava no CRM).
3. **Verificar:** Jev `decide_many` "este resultado cumpre a definição da ficha?" (limiar 0,8); abaixo disso, vai para revisão. **Amostra humana** de 10% (mín. 5) das cobráveis antes do fechamento.
4. **Fechar o mês** (D+5, conforme a ficha): total cobrável, excluídos por motivo, contestados.
5. **Relatório ao cliente** (`engine/report/`): contagem, evidências por amostra, comparação com a baseline, prazo de contestação.
6. **Faturar:** gerar a cobrança no Asaas ou Stripe **passando pelo `arkos-guarda-escrita`** (prévia, confirmação do dono).
7. **Contestação:** linha vira `contestado`; ao resolver, `cobravel` ou `anulado` com motivo. Prazo da ficha (ex.: 5 dias úteis).

## Regras duras

- Nada é cobrado sem evidência rastreável e verificação.
- Nunca editar linha antiga: só anular com linha nova.
- Sem dado pessoal na evidência (guardar ID e hash, não o conteúdo da conversa).
- O relatório ao cliente sai anonimizado quando tiver dado de lead.
