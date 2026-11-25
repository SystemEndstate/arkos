---
name: arkos-estrategia-modelo
description: Modelo de negócio - monta o canvas (cliente, problema, proposta de valor, canais, receita, custos, vantagem), escolhe o motor de receita (assinatura, projeto, por resultado/OaaS, transação, licença, híbrido), testa a coerência entre as peças e aponta a defensabilidade. Use para "modelo de negócio", "como ganhar dinheiro com isso", "assinatura ou projeto?", "business model", "canvas", ou no lancar-saas.
status: rascunho
versao: 0.1.0
modulos: [10, 9]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia-premissas, arkos-oaas-calculadora, jev]
---

# arkos-estrategia-modelo

**Princípio:** o modelo é a cadeia "quem paga, por quê, quanto, com que frequência e quanto custa entregar". Uma peça fraca derruba a cadeia inteira.

## 1. Quando usar e quando não usar

**Usar:**
- Ideia escolhida, antes do preço e do GTM.
- Negócio que fatura, mas sem margem ou sem recorrência.
- Na dúvida entre vender como projeto, assinatura ou por resultado.

**Não usar:**
- Ainda sem cliente definido. Rodar antes a `arkos-estrategia-ideia`.

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: cliente, pergunta: "Quem paga e quem usa (se forem diferentes)?", perfil: icp, obrigatoria: true }
- { id: entrega, pergunta: "O que é entregue e como (serviço, software, conteúdo, físico)?", perfil: oferta, obrigatoria: true }
- { id: custo_entrega, pergunta: "Quanto custa entregar uma unidade? (horas, ferramentas, IA)", obrigatoria: false }
- { id: frequencia, pergunta: "Com que frequência o cliente tem o problema?", opcoes: [uma vez, por projeto, todo mês, todo dia], obrigatoria: true }
```

## 3. Passos

1. **Canvas** em 9 blocos, uma frase cada. Cada bloco aponta a premissa que o sustenta (cria a premissa quando falta). *Claude + premissas.*
2. **Motor de receita:** comparar até 3 opções nos critérios abaixo, com nota de 1 a 5 e justificativa:
   - previsibilidade;
   - margem;
   - facilidade de venda (aceitação pelo cliente);
   - capital de giro (quem financia quem);
   - escala.

   | Frequência do problema | Motor que costuma encaixar |
   |---|---|
   | uma vez | projeto ou transação |
   | por projeto | projeto por marco + manutenção |
   | todo mês | assinatura ou retainer |
   | resultado mensurável | por resultado, só com os 3 "sim" de Bain; senão híbrido |

   *Claude + Jev para os 3 "sim".*
3. **Teste de coerência** (o Jev responde sim/não a cada pergunta): *Jev.*
   - o canal escolhido alcança esse cliente pelo CAC que a margem paga?
   - o preço provável cobre o custo de entrega com folga de pelo menos 3×?
   - o motor combina com a frequência do problema?
   - quem paga tem orçamento para isso?

   Cada "não" vira um risco crítico.
4. **Defensabilidade:** qual das fontes de vantagem existe ou pode ser construída? Opções: rede, escala, troca cara, marca, recurso exclusivo, processo, contraposicionamento. Escrever "nenhuma ainda" é aceitável. *Claude.*
5. **OaaS:** se o motor for por resultado ou híbrido, chamar a `arkos-oaas-calculadora` para conferir se o piso e a margem fecham. *Skill.*

## 4. Saída

`workspace/<cliente>/<projeto>/estrategia/modelo.md` com:
- o canvas;
- a comparação dos motores de receita, com o escolhido e o porquê;
- o teste de coerência;
- a defensabilidade;
- as premissas novas.

O `saida.json` leva `problema`, `motor_receita` e `cliente`.

## 5. Critério de pronto

- [ ] Os 9 blocos preenchidos, cada um com premissa ligada.
- [ ] Motor de receita escolhido entre pelo menos 2 alternativas, com notas.
- [ ] Teste de coerência rodado, e cada "não" virou premissa crítica.
- [ ] Fonte de vantagem declarada (ou "nenhuma ainda").

## 6. Exceções

- **Custo de entrega desconhecido:** estimar por faixa (horas × valor-hora do mercado), marcar `estimativa` e criar a premissa de custo.
- **Motor ideal incompatível com o caixa do cliente** (ex.: assinatura anual para quem só paga mensal): propor um híbrido e registrar o motivo.

## 7. Alimenta

- **Preço:** motor e unidade de cobrança.
- **GTM:** cliente e canal.
- **Finanças:** custo de entrega e frequência.
- **Banca-operador:** a entrega.
- **Perfil:** `tipo_negocio`, com confirmação.

## 8. Regras duras

- Não escolher "por resultado" sem os 3 "sim" de Bain.
- O motor por resultado sempre passa pela calculadora de OaaS antes de virar recomendação.
