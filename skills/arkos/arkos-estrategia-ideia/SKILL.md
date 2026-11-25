---
name: arkos-estrategia-ideia
description: Descoberta e triagem de ideias de negócio - gera candidatas a partir das dores reais de um público e da vantagem de quem vai executar, e dá nota a cada uma (dor, poder de compra, alcance, concorrência, vantagem, velocidade até a primeira venda), escolhendo até 3 para validar. Use para "ideia de negócio", "o que eu poderia vender", "qual nicho escolher", "SaaS em alta", "tenho 3 ideias, qual?", "business idea", ou no validar-nicho-48h.
status: rascunho
versao: 0.1.0
modulos: [9, 5]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia-premissas, anthropic-skills:deep-research, jev]
---

# arkos-estrategia-ideia

**Princípio:** uma boa ideia é a interseção entre uma **dor cara** de um público **alcançável** e uma **vantagem injusta** de quem executa. A originalidade conta pouco.

## 1. Quando usar e quando não usar

**Usar:**
- Partir do zero.
- Escolher entre ideias candidatas.
- Achar o próximo produto para uma base que já existe.

**Não usar:**
- Ideia já escolhida e com cliente pagando. Ir para `arkos-estrategia-diagnostico` ou `arkos-estrategia-premissas`.

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: ponto_partida, pergunta: "Ponto de partida", opcoes: [um público que conheço, uma habilidade minha, uma base que já tenho, ideias prontas], obrigatoria: true }
- { id: detalhe, pergunta: "Descreva (o público, a habilidade, a base ou as ideias)", obrigatoria: true }
- { id: vantagem, pergunta: "O que você tem que os outros não têm? (acesso, audiência, know-how, dinheiro, time)", obrigatoria: true }
- { id: restricoes, pergunta: "Limites: dinheiro, horas por semana, prazo para a 1ª venda", obrigatoria: false }
- { id: modelo_preferido, pergunta: "Preferência de modelo", opcoes: [serviço, SaaS, infoproduto, produto físico, OaaS, sem preferência], padrao: sem preferência, obrigatoria: false }
```

## 3. Passos

1. **Mapear as dores do público:** pesquisa de voz do cliente (fóruns, Reclame Aqui, reviews, grupos, Reddit nos EUA). Formato JTBD: "quando [situação], quero [progresso], mas [obstáculo]". Pelo menos 10 dores, cada uma com fonte. *deep-research + Claude.*
2. **Gerar candidatas:** de 8 a 15 combinações de dor × veículo (serviço, software, info, OaaS), sempre ligadas à vantagem declarada. *Claude.*
3. **Triagem rápida pelo Jev** (`decide_many`, sim/não por candidata): "a dor é paga hoje (gente já gasta dinheiro ou tempo com ela)?" e "dá para vender sem construir nada?". O que tiver dois "não" sai. *Jev.*
4. **Nota de 1 a 5** nos 6 critérios, com uma frase de justificativa cada:

   | Critério | Pergunta |
   |---|---|
   | dor | é urgente e cara? |
   | poder de compra | o público tem dinheiro e autonomia para pagar? |
   | alcance | dá para chegar em 100 dessas pessoas em 2 semanas? |
   | concorrência | existe demanda provada e espaço para diferença? (zero concorrente é sinal ruim) |
   | vantagem | a vantagem declarada pesa aqui? |
   | velocidade | dá para chegar à 1ª venda em menos de 30 dias? |

   Pesos padrão: dor 25%, compra 20%, alcance 20%, vantagem 15%, velocidade 10%, concorrência 10%. Cálculo por script, nunca de cabeça.
5. **Escolher até 3** (maior nota, desempate pela velocidade). Para cada uma, de 3 a 5 premissas iniciais no `premissas.yaml`: problema, cliente, canal e preço. *Claude + premissas.*
6. **Teste mais barato de cada uma:** 10 conversas no formato do Mom Test, landing com pré-venda ou oferta manual a 5 pessoas. *Claude.*

## 4. Saída

`workspace/<cliente>/<projeto>/estrategia/ideias.md` com:
- dores com fonte;
- tabela de candidatas com nota por critério;
- as 3 escolhidas, cada uma com uma frase de tese, as premissas e o teste;
- as descartadas, com motivo.

O `saida.json` leva `nicho`, `local`, `oferta_rascunho` e `tese` para o próximo elo.

## 5. Critério de pronto

- [ ] ≥ 10 dores, todas com fonte.
- [ ] Nota calculada por script, com justificativa em cada critério.
- [ ] Até 3 escolhidas, cada uma com premissas registradas e um teste com custo e prazo.
- [ ] As descartadas estão registradas, com motivo.

## 6. Exceções

- **A pesquisa não acha dor com fonte:** o público é vago demais. Pedir um recorte (cargo, cidade, porte) e rodar de novo. Não inventar dores.
- **Todas as candidatas com nota < 3:** dizer isso com clareza e propor outro ponto de partida (outro público ou outra vantagem).
- **Prestador apegado a uma ideia de nota baixa:** manter a ideia na lista, mostrar os critérios fracos e rodar a banca-cético nela.

## 7. Alimenta

- **Premissas:** as iniciais de cada escolhida.
- **Perfil:** `icp.nicho` provisório, com confirmação.
- **Relatório:** a tabela de candidatas.
- **Retro:** a ideia escolhida × o resultado dos testes.

## 8. Regras duras

- Nada de dor ou número inventado. Sem fonte, não entra.
- Não recomendar ideia que dependa de contato frio por WhatsApp (regra de opt-in).
- Pesquisa paga (Apify ou outra) passa pelo portão `confirmacao_custo`.
