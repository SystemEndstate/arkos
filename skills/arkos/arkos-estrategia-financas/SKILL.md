---
name: arkos-estrategia-financas
description: Finanças do negócio na suíte arkos-estrategia. Calcula unit economics (CAC, LTV, payback, margem de contribuição), projeção mensal de 12 a 36 meses em 3 cenários, caixa, vale de caixa, runway e break-even, numa planilha com fórmulas (anthropic-skills:xlsx) e uma leitura curta. A conta é sempre determinística, por script ou fórmula. Use quando pedirem "quanto preciso de caixa", "quando empata", "projeção", "unit economics", "LTV/CAC", "vale a pena investir em ads", "planilha financeira", "financial model", "break-even", "runway", "cash flow".
status: rascunho
versao: 0.1.0
modulos: [10, 11]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-estrategia-premissas, arkos-estrategia-preco, arkos-estrategia-gtm, anthropic-skills:xlsx, arkos-gate, jev]
---

# arkos-estrategia-financas

A pergunta é: **com estes números, o negócio para em pé, quanto dinheiro precisa até lá e qual número mata tudo se estiver errado?** O Claude monta as premissas e escreve a leitura. As contas ficam no script e nas fórmulas da planilha, nunca na cabeça do modelo.

## 1. Quando usar e quando não usar

**Usar:**
- No playbook `lancar-saas` e no `lancar-infoproduto`, depois de preço e GTM.
- Quando o dono pergunta "quanto posso gastar em anúncio por cliente", "quando volto o investimento" ou "preciso de quanto em caixa".
- Antes da banca, para que investidor e operador tenham números a atacar.

**Não usar:**
- Para uma proposta OaaS isolada, que é a `arkos-oaas-calculadora`.
- Para o preço em si, que é a `arkos-estrategia-preco`. Esta skill só confere se o preço fecha a conta.
- Para a contabilidade do negócio, o DRE oficial ou a apuração de impostos, que são do contador. Aqui é modelo de decisão.

## 2. Entradas

Lê do perfil `preco`, `icp.ticket`, `tipo_negocio`, `mercado` e `numeros` (privado). Do estado da suíte lê `preco.md` (faixas e parcelamento), `gtm.md` (canais e meta de clientes), `modelo.md` (custos) e `premissas.yaml`. O que já existir vira padrão e não é perguntado.

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: horizonte, pergunta: "Horizonte da projeção", opcoes: [12, 24, 36], padrao: 24, obrigatoria: true }
- { id: ticket, pergunta: "Ticket e forma de cobrança (mensal, anual, único, parcelado em N)", perfil: preco, obrigatoria: true }
- { id: canais, pergunta: "Canais de aquisição e custo por cliente esperado em cada um (ou 'não sei')", obrigatoria: true }
- { id: custos_fixos, pergunta: "Custos fixos por mês (pessoas, ferramentas, aluguel)", obrigatoria: true }
- { id: custo_variavel, pergunta: "Custo para entregar a cada cliente (servidor, insumo, hora de gente, taxa)", obrigatoria: true }
- { id: caixa_inicial, pergunta: "Caixa disponível hoje para o projeto", perfil: numeros, obrigatoria: false }
- { id: regime, pergunta: "Regime tributário (BR: Simples, Presumido, MEI; EUA: LLC, C-Corp)", padrao: "do arkos-mercado", obrigatoria: false }
```

Quem responde "não sei" recebe uma faixa com a lógica escrita, e a resposta vira premissa (ver §6).

## 3. Passos

1. **Montar `financas-entrada.json`** com os drivers por cenário (pessimista, base, otimista):
   - clientes novos por mês e por canal, CAC por canal e ticket;
   - churn mensal ou recompra, margem bruta, custos fixos e crescimento dos fixos;
   - impostos sobre receita, taxa do meio de pagamento e prazo de recebimento.
   Cada valor leva `fonte` (perfil, pesquisa, premissa P-xxx ou `estimativa`). *Claude.*
2. **Puxar as regras do mercado** com `arkos-mercado ficha <mercado>`. No BR entram Simples ou Presumido, taxa de Pix e cartão, e parcelamento com ou sem antecipação, que muda o caixa e não a receita. Nos EUA entram sales tax e taxa do processador; na EU, o IVA. A alíquota exata vem da ficha ou do contador; sem dado, entra como `estimativa`. *Skill.*
3. **Rodar o script** `scripts/financas.py financas-entrada.json`. Ele é determinístico, sem LLM, e fica coberto pelo guarda-regressao. Calcula por mês e por cenário:
   - receita reconhecida e recebida;
   - margem de contribuição por cliente: ticket − custo variável − impostos − taxa;
   - CAC misto, **LTV = CM2 acumulada da coorte em 12 meses** (mensal: mc × (1−(1−churn)¹²)/churn; único: mc × (1+recompra em 12 m)) e LTV:CAC;
   - **payback de caixa**, em meses e em **dias** (CM2 recebida; no BR a parcela conta quando cai);
   - **portão de unit economics** (lê o campo `capital`: `nenhum` | `credito` | `risco`): LTV:CAC ≥ 2,5:1 — sem capital externo exige 3:1 **ou** payback de caixa dentro do teto; teto do payback de caixa **≤ 90 dias** sem capital externo, **≤ 180** com crédito, **≤ 365** com capital de risco;
   - break-even em clientes ativos: fixos ÷ margem de contribuição por cliente;
   - fluxo de caixa acumulado, mês e valor do **vale de caixa**, e runway com o caixa inicial.
   Grava `financas-resultado.json`. *Script.*
4. **Gerar a planilha** com `anthropic-skills:xlsx`, seguindo as regras dela:
   - abas `Premissas` (células de entrada destacadas, uma linha por driver, com fonte), `Unit economics`, `Projeção` (mês a mês, 3 cenários), `Caixa` e `Sensibilidade`;
   - tudo em **fórmula** ligada às premissas, sem número colado no meio da conta;
   - recalcular e conferir zero erro de fórmula. *Skill xlsx.*
5. **Conferir as duas contas:** os totais-chave da planilha recalculada têm de bater com o `financas-resultado.json`. Diferença acima de arredondamento é bug: corrigir antes de seguir. *Script.*
6. **Sensibilidade:** variar ±20% cada driver no cenário base e ordenar pelo efeito no caixa mínimo. Os 3 primeiros são os números que mais importam. *Script.*
7. **Pre-mortem do pessimista:** "o caixa acabou no mês X; qual driver levou a isso?". O driver mais sensível sem evidência vira premissa de impacto alto. *Claude.*
8. **Classificar a saúde** com o Jev (`decide_many`), uma pergunta sim/não por linha:
   - O portão passou (LTV:CAC ≥ 2,5:1; 3:1 ou payback de caixa no teto quando não há capital externo)?
   - Payback de caixa dentro do teto do capital (90/180/365 dias)?
   - O caixa inicial cobre o vale do cenário pessimista?
   - Margem de contribuição positiva desde o primeiro cliente?
   O número sai do script; o Jev só ajuda a ler o caso de fronteira. *Jev.*
9. **Escrever `financas.md`:** 5 linhas de leitura, tabela de unit economics por cenário, vale de caixa, break-even, os 3 drivers mais sensíveis, "o que eu faria nesta semana" e "o que pode matar isto". *Claude.*
10. **Gate:** `arkos-gate` com o sub-gate de copy no texto e o checklist da §5. *Skill.*

## 4. Saída

Em `workspace/<cliente>/<projeto>/estrategia/`:
- `financas.xlsx`: as 5 abas, com fórmulas, recalculada.
- `financas.md`: a leitura.
- `financas-entrada.json` e `financas-resultado.json`: a fonte e o resultado do script, para refazer e comparar na retro.
- Linhas novas em `premissas.yaml`.

Exemplo de leitura (SaaS de agenda para salões de beleza, BR, valores ilustrativos): "No cenário base empata no mês 14 com 230 salões ativos. O vale de caixa é de R$ 86 mil no mês 9. O que mais pesa é o churn: subir de 4% para 6% ao mês empurra o empate para depois do mês 24."

## 5. Critério de pronto

Cada item é sim/não e verificável pelo Jev ou por script:
- [ ] A planilha abre, recalcula e tem zero erro de fórmula.
- [ ] Os totais da planilha batem com o `financas-resultado.json`.
- [ ] Os 3 cenários existem e o pessimista é de fato pior que o base em receita e caixa.
- [ ] Todo driver tem `fonte`; os sem dado estão marcados `estimativa` e têm premissa ligada.
- [ ] Mostra CAC, LTV (coorte 12 m), LTV:CAC, payback de caixa (meses e dias), portão, margem de contribuição, break-even, vale de caixa e runway.
- [ ] A sensibilidade lista os 3 drivers de maior efeito.
- [ ] Os impostos e taxas do mercado certo foram aplicados (BR, EUA ou EU).
- [ ] O `financas.md` tem "o que eu faria nesta semana" (até 3 ações) e "o que pode matar isto".
- [ ] Nenhum campo `privado` aparece na versão para cliente.

## 6. Exceções

- **Falta dado:** usar a faixa e a lógica (ex.: "CAC de Meta para serviço local BR: R$ 80–250, pela referência do módulo 6; sem dado da conta") e criar a premissa com `confianca` ≤ 0,3. Nunca preencher com número redondo sem origem.
- **Pesquisa não acha referência:** a faixa vem de uma conta reversa ("para empatar no mês 18, o CAC precisa ficar abaixo de R$ X"), e o teste da premissa passa a ser medir o CAC real.
- **O resultado deu ruim** (LTV:CAC < 1, margem negativa, caixa que nunca vira):
  - não maquiar os números;
  - mostrar qual alavanca resolve e quanto ela precisaria mudar (preço, churn, CAC ou custo de entrega);
  - devolver ao `arkos-estrategia` com a recomendação de voltar a preço ou modelo.
- **xlsx indisponível:** entregar o `financas-resultado.json` e uma tabela no `financas.md`, e marcar o gate como `amarelo`.

## 7. Alimenta

- **Perfil:** `numeros.cac`, `numeros.ltv` e `numeros.margem` como `estimativa`, sempre com confirmação do dono e `privado: true`.
- **Premissas:** cada driver sem evidência, com o `custo_teste` de como medir.
- **Relatório:** os KPIs (bloco `kpis`), a tabela de cenários e o vale de caixa.
- **Banca:** os números que investidor e operador atacam.
- **Retro:** o `financas-resultado.json`, base para comparar o projetado com o realizado.

## 8. Regras duras

- Nenhuma conta de cabeça. Todo número da saída sai do script ou de uma fórmula da planilha.
- Nunca inventar CAC, churn, alíquota ou taxa. Sem fonte, é `estimativa` com faixa e premissa.
- Receita e caixa são linhas separadas. Parcelamento e prazo de recebimento entram no caixa.
- Dado de `numeros` e qualquer campo `privado` não vai para o Jev nem para o relatório do cliente.
- Não é aconselhamento contábil nem tributário: a leitura diz isso numa linha e manda conferir com o contador.
