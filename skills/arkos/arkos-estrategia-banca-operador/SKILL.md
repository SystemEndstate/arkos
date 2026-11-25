---
name: arkos-estrategia-banca-operador
description: Banca da suíte arkos-estrategia na lente do operador, quem vai entregar no dia a dia. Julga se dá para entregar o que se vende - capacidade, custo real por unidade entregue, gargalo, time e contratação, dependência de plataforma e fornecedor, suporte, LGPD e risco operacional - e dá o parecer padrão da banca (nota 0–10, veredito seguir / seguir com condições / parar, 3 exigências, premissas atacadas). Use quando pedirem "dá para entregar?", "quanto custa operar", "precisa de quantas pessoas", "banca do operador", "operator review", "can we deliver this", "ops review", ou no playbook lancar-saas.
status: rascunho
versao: 0.1.0
modulos: [11, G, 12]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia-premissas, arkos-estrategia-financas, arkos-estrategia-produto, arkos-gate, jev]
---

# arkos-estrategia-banca-operador

**Persona:** quem já tocou operação e sabe que o plano quebra na segunda-feira às 9h, quando 40 clientes chegam juntos e a pessoa do suporte está de atestado. A pergunta é: **com as pessoas, as ferramentas e o dinheiro que existem, dá para entregar o que se promete, no volume do plano, sem derreter a margem?**

## 1. Quando usar e quando não usar

**Usar:**
- Depois de finanças e produto, porque o operador ataca o custo de entregar e o esforço.
- Antes de vender serviço feito para o cliente, OaaS ou qualquer coisa com SLA.
- No `lancar-saas`, como uma das 4 personas. Em agência e serviço local, é a banca mais importante.

**Não usar:**
- Para desenhar o processo em si: SOPs e contratação são do módulo 12 e do módulo I. Esta banca aponta o furo e exige, não escreve o SOP.
- Para arquitetura técnica e escala de servidor: módulo 1.

## 2. Entradas

Lê `modelo.md` (atividades, recursos e parceiros), `produto.md` (esforço e escopo), `gtm.md` (volume esperado), `financas.md` e `financas-entrada.json` (custo variável e fixos), `premissas.yaml` (categorias `operacao` e `custo`) e o perfil (`restricoes`; `numeros` só no uso interno).

**Independência:** não lê os pareceres das outras bancas antes de escrever o seu.

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: time, pergunta: "Quem entrega hoje: pessoas, papel e horas por semana de cada uma", obrigatoria: true }
- { id: tempo_unidade, pergunta: "Quanto tempo de gente leva para entregar a um cliente (setup e por mês)", obrigatoria: true }
- { id: dependencias, pergunta: "Plataformas e fornecedores de que a entrega depende (Meta, WhatsApp/BSP, gateway, freelancer)", obrigatoria: true }
- { id: sla, pergunta: "O que foi prometido em prazo e resposta (SLA)", perfil: oferta.prazo, obrigatoria: false }
```

## 3. Passos

1. **Riscos críticos primeiro:** as premissas de impacto alto e confiança < 0,5, pelo `arkos-estrategia/scripts/criticos.py`, com destaque para as das categorias `operacao` e `custo`. *Script.*
2. **Mapa da entrega:** de 5 a 10 etapas, da venda ao cliente com resultado: quem faz, quanto tempo leva e qual ferramenta usa. Etapa sem dono é furo. *Claude.*
3. **Capacidade × demanda** com o `scripts/capacidade.py`:
   - horas disponíveis por papel ÷ horas por cliente = clientes atendidos por mês;
   - comparar com os clientes ativos do plano, mês a mês, nos 3 cenários;
   - mostrar o mês em que cada papel estoura;
   - a Lei de Little dá o tempo de fila do suporte com o volume previsto.
   *Script.*
4. **Custo real de servir:** comparar o custo variável usado em finanças com o do mapa (horas × custo da hora + ferramentas + taxas). Diferença acima de 15% vira premissa, e a margem de contribuição é recalculada pelo script de finanças, nunca de cabeça. *Script.*
5. **O gargalo:** a etapa de menor capacidade define o volume do negócio inteiro. Dizer qual é e o que acontece com prazo e qualidade quando ela enche. *Claude.*
6. **Dependências:** para cada plataforma ou fornecedor, perguntar "se isto parar ou mudar a regra amanhã, o que acontece?" e "existe plano B?". Exemplos: a Meta bloqueia a conta de anúncio, o BSP do WhatsApp suspende o número, o gateway segura o saque. O Jev (`decide_many`) responde por dependência "é ponto único de falha?". *Claude + Jev.*
7. **Pessoas:** quem contratar primeiro, quando (pelo mês do estouro do passo 3), quanto tempo leva para a pessoa nova ficar produtiva e o que acontece se o dono ficar 2 semanas fora. *Claude.*
8. **Conformidade operacional:** pela ficha do `arkos-mercado`:
   - BR: LGPD na base de clientes, opt-in de WhatsApp e CDC (arrependimento de 7 dias);
   - EUA: CAN-SPAM e TCPA;
   - EU: GDPR.
   A pergunta é se o processo cumpre, não se a lei existe. *Skill.*
9. **Pontuar a rubrica** (0–10 por critério, com a justificativa de uma linha):

   | Critério | Peso |
   |---|---|
   | Capacidade cobre o volume do plano | 0,25 |
   | Custo real de servir bate com finanças | 0,25 |
   | Gargalo conhecido e com plano | 0,20 |
   | Dependências com plano B | 0,15 |
   | Pessoas e conformidade | 0,15 |

   A nota sai do `arkos-estrategia/scripts/banca_nota.py`, o mesmo das 4 bancas. *Claude + script.*
10. **Checar o parecer com o Jev** ("toda exigência tem dono e prazo?", "o veredito segue a regra?"), gravar o parecer e as premissas novas. *Jev.*

## 4. Saída

O arquivo é `workspace/<cliente>/<projeto>/estrategia/banca/operador.md`, no **formato comum da banca**:

```markdown
---
persona: operador
nota: 0.0            # do banca_nota.py
veredito: seguir | seguir com condições | parar
rubrica: { capacidade: 0, custo_servir: 0, gargalo: 0, dependencias: 0, pessoas_conformidade: 0 }
riscos_criticos: [P-xxx]
premissas_atacadas: [P-xxx]
premissas_novas: [P-xxx]
data: AAAA-MM-DD
---
## Parecer em 5 linhas
## As 3 exigências
1. <o que provar> · <como> · <até quando> · fecha P-xxx
## Premissas que ataquei
| id | o que diz | por que duvido | o que me convenceria |
## Mapa da entrega e gargalo
## Capacidade × demanda (mês do estouro por papel)
## Dependências e plano B
## Perguntas sem resposta
## O que eu faria nesta semana
## O que pode matar isto
```

**Regra do veredito** (igual nas 4 bancas):
- **parar:** nota < 4, ou uma premissa de impacto alto está `refutada` sem plano de troca;
- **seguir com condições:** nota de 4 a 6,9, ou existe risco crítico sem teste com data;
- **seguir:** nota ≥ 7 e todo risco crítico tem teste com data.

Também gera `banca/operador-capacidade.json`, a saída do script.

## 5. Critério de pronto

- [ ] O parecer segue o formato comum, com todos os campos do frontmatter.
- [ ] A nota veio do `banca_nota.py`, e o veredito bate com a regra comum.
- [ ] O mapa da entrega tem dono em toda etapa, ou o furo está apontado.
- [ ] A capacidade × demanda veio do script, com o mês do estouro por papel.
- [ ] O custo real de servir foi comparado com o de finanças, com a diferença em %.
- [ ] Há um gargalo nomeado.
- [ ] Toda dependência tem sim/não para ponto único de falha e plano B (ou "sem plano B").
- [ ] A conformidade foi conferida pela ficha do mercado certo.
- [ ] Há 3 exigências, cada uma com dono e prazo.
- [ ] O parecer foi escrito sem ler os das outras bancas.

## 6. Exceções

- **Sem o tempo por cliente:** a primeira exigência vira medir (cronometrar 3 entregas reais ou simuladas). A nota de "capacidade" fica em no máximo 5 e o parecer fica parcial.
- **Entrega 100% software, sem gente:** trocar as horas por suporte, onboarding e custo de infraestrutura por cliente. O resto da rubrica fica igual.
- **O dono é o único operador:** dizer com clareza que o gargalo é ele. A exigência passa a ser documentar a etapa mais repetida e testar com outra pessoa.
- **O veredito é parar:** dizer na primeira linha, com o mês em que a operação quebra.

## 7. Alimenta

- **Perfil:** `restricoes`, quando o dono confirmar um limite ("não atendo mais de 30 clientes").
- **Premissas:** as premissas de custo de servir, de capacidade e de dependência.
- **Finanças:** o custo variável corrigido, para rodar a projeção de novo.
- **Relatório:** a linha da banca, o gargalo e o mês do estouro.
- **Retro:** as 3 exigências e o mês do estouro, para conferir.
- **Módulo 12:** o gargalo e as contratações, para o SOP e o plano de time.

## 8. Regras duras

- A banca é simulação de uma lente, não um parecer de operador real, e diz isso numa linha.
- Capacidade, custo de servir e margem saem de script, nunca de cabeça.
- Não aceitar "a gente dá um jeito" como plano B.
- Não escrever o SOP aqui. Esta banca aponta e exige.
- A nota sai do script, e o veredito sai da regra.
