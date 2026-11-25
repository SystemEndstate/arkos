---
name: arkos-estrategia-banca-investidor
description: Banca da suíte arkos-estrategia na lente do investidor (ou do dono que põe o próprio dinheiro). Julga tamanho de mercado bottom-up, retorno e unit economics, risco, defensabilidade e por que agora, e dá parecer padrão da banca (nota 0–10, veredito seguir / seguir com condições / parar, 3 exigências, premissas atacadas). Use quando pedirem "vale investir?", "como um investidor veria isto", "banca", "revisão de investidor", "pitch review", "investor review", "is this fundable", ou no playbook lancar-saas depois de finanças.
status: rascunho
versao: 0.1.0
modulos: [11, G, 14]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia-premissas, arkos-estrategia-financas, arkos-estrategia-modelo, arkos-gate, jev]
---

# arkos-estrategia-banca-investidor

**Persona:** quem põe dinheiro e quer saber se ele volta multiplicado, e quando. Vale para o fundo, para o anjo e para o dono que tira da reserva. A pergunta é: **por que este dinheiro aqui, e não em outro lugar?**

## 1. Quando usar e quando não usar

**Usar:**
- Depois de `arkos-estrategia-financas`, porque sem números esta banca só opina.
- Antes de captar, de investir do próprio bolso ou de contratar.
- No playbook `lancar-saas` (banca das 4 personas).

**Não usar:**
- Para negócio de subsistência ou freelancer solo sem plano de escala. Aí a lente certa é a do operador, e a do investidor só gera ruído.
- Para avaliar uma empresa para compra (valuation, due diligence). Isso é do módulo 14.

## 2. Entradas

Lê `tese.md`, `modelo.md`, `preco.md`, `gtm.md`, `financas.md` com o `financas-resultado.json`, `produto.md`, `premissas.yaml` e o perfil (sem `privado`, salvo no uso interno).

**Independência:** não lê `banca/*.md` das outras personas antes de escrever o próprio parecer, para não ancorar.

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: capital, pergunta: "Quem põe o dinheiro", opcoes: [proprio, anjo, fundo, sem-capital-externo], padrao: proprio, obrigatoria: true }
- { id: valor, pergunta: "Quanto se pretende investir ou captar, e para quê", obrigatoria: false }
- { id: retorno, pergunta: "Retorno esperado: renda mensal, venda da empresa ou crescimento", padrao: "renda mensal", obrigatoria: false }
```

## 3. Passos

1. **Riscos críticos primeiro:** listar as premissas de impacto alto com confiança < 0,5, pelo `arkos-estrategia/scripts/criticos.py`. Toda banca começa por elas. *Script.*
2. **Tamanho (bottom-up):**
   - SOM = clientes alcançáveis × ticket anual. Os clientes alcançáveis saem de uma contagem real (ex.: escritórios contábeis numa capital, pela base pública de CNPJ por CNAE), nunca de "1% de um mercado de bilhões";
   - SAM e TAM só como contexto;
   - a conta é feita pelo `scripts/som.py`, que recusa contagem sem fonte e percentual top-down. *Pesquisa web + script.*
3. **Retorno:** ler LTV:CAC, payback, margem de contribuição e vale de caixa do cenário pessimista. Perguntar "quanto dinheiro até o caixa virar e em quanto tempo ele volta?". *Claude.*
4. **Defensabilidade:**
   - as 5 forças competitivas, curtas: o que impede um concorrente com mais dinheiro de copiar em 6 meses?;
   - a "vantagem injusta" do Lean Canvas: dado, rede, canal, marca ou custo;
   - "nenhuma" é resposta aceitável, desde que dita. *Claude.*
5. **Por que agora:** que mudança (regra, tecnologia, comportamento, preço) abre a janela hoje e não abria há 3 anos? Sem resposta, cai a nota do critério. *Claude + pesquisa web.*
6. **Pontuar a rubrica** (0–10 por critério, com a justificativa de uma linha):

   | Critério | Peso |
   |---|---|
   | Tamanho alcançável (SOM bottom-up) | 0,20 |
   | Retorno e unit economics | 0,30 |
   | Risco (críticos e vale de caixa) | 0,20 |
   | Defensabilidade | 0,15 |
   | Por que agora | 0,15 |

   A nota final, a média ponderada, sai do `arkos-estrategia/scripts/banca_nota.py`, o mesmo das 4 bancas. *Claude + script.*
7. **Checar o parecer com o Jev** (`decide_many`), uma pergunta sim/não por item:
   - "Alguma justificativa cita número que não está no estado?"
   - "Toda exigência aponta para uma premissa?"
   - "O veredito segue a regra?"
   Um "sim" na primeira ou um "não" nas outras manda refazer. *Jev.*
8. **Aplicar a regra do veredito** (comum às 4 bancas) e escrever as 3 exigências. Cada exigência diz o que provar, como, até quando e qual premissa fecha. *Claude.*
9. **Registrar** as premissas novas que a banca levantou (`origem: arkos-estrategia-banca-investidor`) e gravar o parecer. *Claude.*

## 4. Saída

O arquivo é `workspace/<cliente>/<projeto>/estrategia/banca/investidor.md`, no **formato comum da banca**:

```markdown
---
persona: investidor
nota: 0.0            # do banca_nota.py
veredito: seguir | seguir com condições | parar
rubrica: { tamanho: 0, retorno: 0, risco: 0, defensabilidade: 0, por_que_agora: 0 }
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
## Perguntas sem resposta
## O que eu faria nesta semana
## O que pode matar isto
```

**Regra do veredito** (igual nas 4 bancas):
- **parar:** nota < 4, ou uma premissa de impacto alto está `refutada` sem plano de troca;
- **seguir com condições:** nota de 4 a 6,9, ou existe risco crítico sem teste com data;
- **seguir:** nota ≥ 7 e todo risco crítico tem teste com data.

## 5. Critério de pronto

- [ ] O parecer segue o formato comum, com todos os campos do frontmatter.
- [ ] A nota veio do `banca_nota.py`, com a rubrica preenchida.
- [ ] O veredito bate com a regra comum.
- [ ] Os riscos críticos foram lidos e estão listados.
- [ ] O SOM é bottom-up, com a fonte da contagem.
- [ ] Há exatamente 3 exigências, cada uma ligada a uma premissa e com prazo.
- [ ] Pelo menos 2 premissas foram atacadas, com "o que me convenceria".
- [ ] Nenhum número do parecer está fora do estado da suíte ou das fontes citadas.
- [ ] O parecer foi escrito sem ler os das outras bancas.

## 6. Exceções

- **Sem `financas.md`:** o critério "retorno" fica sem nota, a nota final é calculada sobre os outros 4 critérios e marcada "parcial", e a primeira exigência passa a ser rodar finanças.
- **Sem como contar o mercado bottom-up:** a primeira exigência vira a contagem (ex.: "contar os salões de beleza ativos em 3 capitais pela base de CNPJ"), e o critério "tamanho" recebe no máximo 5.
- **Capital próprio, sem plano de venda da empresa:** trocar "múltiplo de saída" por "renda mensal do dono e tempo até ela". O resto da rubrica fica igual.
- **O veredito é parar:** dizer na primeira linha. Não suavizar para "seguir com condições".

## 7. Alimenta

- **Perfil:** nada.
- **Premissas:** as premissas novas, e a evidência ou a dúvida nas atacadas.
- **Relatório:** a linha da banca (nota, veredito e a exigência principal).
- **Retro:** as 3 exigências entram como o que a próxima retro confere.

## 8. Regras duras

- A banca é simulação de uma lente, não opinião de investidor real, e diz isso numa linha do parecer.
- Mercado top-down ("1% de R$ 10 bi") não conta como tamanho.
- A nota sai do script, e o veredito sai da regra.
- Não reescreve as skills de estratégia: aponta, exige e cria premissas.
- Dado privado só no uso interno. O parecer para cliente usa taxas.
