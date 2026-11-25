---
name: arkos-oaas-proposta
description: Proposta por resultado (OaaS) de ponta a ponta - diagnóstico (o resultado é observável, atribuível e contratável?), ficha de resultado de 10 campos, escolha do modelo (fixo por marco, retainer + success fee, por resultado, gain-share, híbrido), proposta, SOW e anexo de critérios de aceite. Use quando o usuário pedir proposta, orçamento, SOW, "resultado garantido", "cobrar por resultado", ou no playbook proposta-oaas.
status: rascunho
versao: 0.1.0
modulos: [P, N]
depende_de: [arkos-intake, arkos-perfil, arkos-oaas-calculadora, proposal-builder, sow-generator, deliver-acceptance-criteria, deal-desk, review-proposals]
---

# arkos-oaas-proposta

Inclui a etapa de **diagnóstico** (o `arkos-oaas-diagnostico` do MAPA), para não criar uma skill a mais.

## 1. Discovery (via arkos-intake)

Serviço (site, SaaS, software sob medida, automação n8n, processo/SOP, tráfego, SDR) · resultado que o cliente quer · como ele mede hoje · últimos 90 dias de números · o que depende do cliente · prazo · orçamento.

## 2. Diagnóstico Bain (sim/não, pelo Jev + revisão)

1. **Observável?** dá para ver que aconteceu?
2. **Atribuível?** dá para atribuir de forma única à entrega?
3. **Contratável?** dá para escrever no contrato sem ambiguidade?

Três "sim" = pode cobrar por resultado. Qualquer "não" = **preço fixo por marco** (com aceite), ou híbrido com variável pequena. Guia por serviço (pesquisa 09 §4): automação n8n é a melhor candidata a pay-per-outcome; site, SaaS e software ficam com marco fixo.

## 3. Ficha de resultado (10 campos, todos obrigatórios)

definição · o que NÃO conta · fonte da verdade (log que os dois lados leem) · linha de base (90 dias, assinada no kickoff) · janela de medição e fechamento · dependências do cliente (com SLA) · exclusões (fora do controle: mudança de oferta, bloqueio de plataforma, sazonalidade acima de X%) · regra de contestação (prazo, amostra auditada) · remédio se falhar (crédito, refazer, devolução até o teto) · teto de responsabilidade.

## 4. Modelo e preço

Chamar `arkos-oaas-calculadora` com os números. Padrão: **híbrido** (base que cobre o custo + variável por resultado). Puro por resultado só com os 3 "sim" e compromisso mínimo.

## 5. Documentos

- Proposta (estrutura do `proposal-builder` + `jezweb proposal-writer`), com vídeo demo opcional (`explainer-default`).
- SOW (`sow-generator`): todo entregável com critério de aceite mensurável.
- Anexo de aceite: Given/When/Then (`deliver-acceptance-criteria`) para entregas técnicas; ficha de resultado para o variável.
- Saída: `workspace/<cliente>/<projeto>/propostas/<data>/` (md + docx/pdf/pptx pelas skills Anthropic, ou Artifact).

## 6. Portões (nesta ordem)

1. `review-proposals` (revisão jurídica automática) + `deal-desk` (desconto e garantia pelo roteador de aprovação).
2. **Aprovação do dono antes de oferecer qualquer garantia ou desconto.** Sem ela, a proposta sai sem garantia.
3. Contrato: a proposta **não** é contrato. O contrato BR (`arkos-oaas-contrato-br`, P2) passa por advogado.

## Regras duras

- Nunca prometer resultado sem ficha completa.
- Nunca citar a Gartner com o nome errado: o termo dela é "Outcome-as-Agentic-Solution" (OaAS). A decisão sobre o nome da Endstate está pendente.
- Proposta não vai ao cliente pela ARKOS: o humano envia.
