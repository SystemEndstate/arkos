---
name: arkos-estrategia-diagnostico
description: Diagnóstico de negócio que já roda, na suíte arkos-estrategia. Decompõe o resultado em funil, oferta, canal, operação e caixa, mede cada elo contra o período anterior e uma referência, acha o gargalo único (teoria das restrições) e entrega um plano de 30 dias focado nele. Use quando disserem "as vendas caíram", "não cresce", "onde está o problema", "por que não vende", "estou perdendo dinheiro", "diagnóstico", "auditoria do negócio", "what's wrong with my business", "find the bottleneck".
status: rascunho
versao: 0.1.0
modulos: [10, 5, 6, 12, E]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-estrategia-premissas, arkos-estrategia-retro, arkos-oferta, arkos-gate, jev]
---

# arkos-estrategia-diagnostico

A pergunta é: **qual é o único elo que, se melhorar, mexe no resultado inteiro?** Um negócio com dez problemas tem um gargalo. Atacar os outros nove antes dele gasta dinheiro sem mudar o número.

## 1. Quando usar e quando não usar

**Usar:**
- O negócio já vende. Tem pelo menos 3 meses de números, mesmo que imperfeitos.
- O dono sente que algo vai mal e não sabe onde.
- No fluxo "negócio que já roda": diagnostico → premissas → retro periódica.

**Não usar:**
- Para ideia ou pré-lançamento: aí é `arkos-estrategia-ideia` ou a auditoria pré-lançamento (módulo 11).
- Quando o problema é uma campanha específica. Aí é o módulo 6, que diagnostica por anúncio.
- Quando não há número nenhum. Primeiro vem a coleta (ver §6).

## 2. Entradas

Lê o perfil inteiro: `numeros` (privado), `oferta`, `preco`, `icp` e `restricoes`. Do estado da suíte lê `premissas.yaml` e a última `retro/`, se existirem.

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: sintoma, pergunta: "O que te fez pedir o diagnóstico, em uma frase", obrigatoria: true }
- { id: periodo, pergunta: "Comparar quais meses com quais (ex.: ago–out com mai–jul)", padrao: "últimos 3 meses × 3 anteriores", obrigatoria: true }
- { id: funil, pergunta: "Números por mês: visitas ou alcance, leads, conversas, propostas, vendas (o que tiver)", obrigatoria: true }
- { id: receita, pergunta: "Receita, ticket médio, recompra ou churn por mês", perfil: numeros, obrigatoria: true }
- { id: custos, pergunta: "Gasto em mídia, custo de entregar, custos fixos por mês", perfil: numeros, obrigatoria: true }
- { id: caixa, pergunta: "Caixa hoje e contas a receber e a pagar nos próximos 60 dias", obrigatoria: false }
- { id: fontes, pergunta: "De onde vêm os números (planilha, CRM, Meta, Asaas, banco)?", obrigatoria: false }
```

Pode receber um arquivo (CSV, planilha, export do CRM) em vez das respostas. A leitura é feita por script, nunca a olho.

## 3. Passos

1. **Normalizar os dados** com o `scripts/diagnostico.py`. Ele lê a entrada, gera a série mensal por métrica e calcula, por elo:
   - taxa de conversão de cada etapa do funil;
   - ticket, recompra ou churn, margem de contribuição, CAC e payback;
   - variação entre o período atual e o anterior.
   Grava `diagnostico-dados.json`. *Script.*
2. **Montar a árvore de métricas:** resultado (receita ou lucro) = clientes novos × ticket × vida + recompra − custos. Cada folha liga a um dos 5 elos:
   - **funil:** tráfego e conversão;
   - **oferta:** preço, promessa e garantia;
   - **canal:** CAC e volume por canal;
   - **operação:** entrega, prazo, suporte, churn por insatisfação;
   - **caixa:** prazo de recebimento, margem e custos fixos.
   *Claude.*
3. **Comparar com uma referência** de três fontes:
   - o período anterior do próprio negócio, que é a melhor referência;
   - a meta do perfil;
   - uma faixa pública do nicho, com a fonte citada (pesquisa web).
   Sem referência, o elo é comparado só consigo mesmo. *Script + pesquisa web.*
4. **Simular o efeito de cada elo:** para cada folha, melhorar 20% mantendo o resto igual e medir o efeito no resultado. A conta é do script. O elo de maior efeito **e** pior em relação à referência é o candidato a gargalo. *Script.*
5. **Confirmar com os 5 porquês:** do sintoma até a causa, cada porquê com um dado do passo 1. Porquê sem dado vira premissa. *Claude.*
6. **Checar armadilhas com o Jev** (`decide_many`), uma pergunta sim/não por item:
   - "O gargalo é de caixa e não de venda?"
   - "A queda é sazonal (mesmo mês do ano anterior)?"
   - "O dado do período é incompleto (mês corrente, export parcial)?"
   - "A oferta tem nota < 8 no `arkos-oferta`?"
   Um "sim" muda a leitura. *Jev.*
7. **Escolher um gargalo**, nunca uma lista. Escrever por que é ele e por que não são os outros dois candidatos. *Claude.*
8. **Plano de 30 dias:**
   - até 3 ações, todas no gargalo;
   - cada uma com dono (`arkos` ou `voce`), custo, a métrica que deve mexer e a data de conferência;
   - o resto vai para "não mexer agora".
   Ação com custo passa pelo portão `confirmacao_custo`. *Claude.*
9. **Registrar as hipóteses** em `premissas.yaml` (ex.: "o churn caiu porque o onboarding mudou em agosto") e marcar a data da próxima retro. *Claude.*
10. **Gate:** `arkos-gate` com o checklist da §5. *Skill.*

## 4. Saída

Em `workspace/<cliente>/<projeto>/estrategia/diagnostico.md`:
- **Sintoma e período** comparados.
- **Árvore de métricas**, com o valor de cada folha e a variação.
- **Gargalo:** qual é, a evidência, o efeito simulado e por que não são os outros dois candidatos.
- **Plano de 30 dias** (até 3 ações) e a lista "não mexer agora".
- **Data da próxima retro**, "o que eu faria nesta semana" e "o que pode matar isto".

Também gera `diagnostico-dados.json` e linhas novas em `premissas.yaml`.

Exemplo de gargalo (clínica odontológica, BR, ilustrativo): "Os leads subiram 30%, mas a taxa de agendamento caiu de 38% para 21%. O tempo de resposta no WhatsApp passou de 10 min para 4 h desde que a recepcionista saiu. O gargalo é de operação, não de mídia: aumentar o orçamento agora só compra mais leads sem resposta."

## 5. Critério de pronto

- [ ] As taxas e variações vieram do script, e o `diagnostico-dados.json` existe.
- [ ] Os 5 elos foram medidos ou marcados "sem dado".
- [ ] Há exatamente um gargalo, com evidência numérica.
- [ ] Os outros 2 candidatos foram descartados com motivo.
- [ ] As armadilhas (sazonalidade, dado incompleto, caixa) foram conferidas.
- [ ] O plano tem no máximo 3 ações, todas no gargalo, cada uma com métrica e data.
- [ ] As hipóteses sem dado estão em `premissas.yaml`.
- [ ] Tem "o que eu faria nesta semana" e "o que pode matar isto".
- [ ] Nenhum campo `privado` aparece na versão para cliente.

## 6. Exceções

- **Sem número nenhum:** não diagnosticar. Entregar um plano de coleta de 2 semanas: quais 6 números anotar, onde e como (planilha simples, UTM, etiqueta no WhatsApp). Marcar a volta da skill para depois da coleta.
- **Dados de um mês só:** comparar com a referência pública do nicho, marcar a confiança como baixa e repetir o diagnóstico com 3 meses.
- **Dois elos empatados no efeito:** escolher o mais barato de testar e dizer isso.
- **O gargalo é o próprio dono** (tempo, decisão, aprovação): dizer com cuidado e com o dado. Não esconder no "operação".

## 7. Alimenta

- **Perfil:** `numeros`, com os valores atualizados, sempre com confirmação e `privado: true`.
- **Premissas:** as hipóteses de causa, com o teste e a data.
- **Relatório:** a árvore, o gargalo e o plano.
- **Retro:** o plano de 30 dias é o que a próxima retro confere.
- **Outros módulos:** o gargalo chama o módulo certo (oferta, tráfego, operação), via `arkos-estrategia`.

## 8. Regras duras

- Um gargalo por diagnóstico.
- Nenhuma taxa calculada de cabeça.
- Não recomendar mais mídia quando o gargalo está depois do lead.
- Correlação não é causa: a causa sem teste fica como premissa `aberta`.
- O relatório do cliente não mostra os números privados do perfil, só as taxas e a direção.
