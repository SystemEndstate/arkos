---
name: arkos-estrategia-preco
description: Preço e empacotamento - define a unidade de cobrança, a faixa de preço pelo valor entregue (e não pelo custo), a âncora, os planos (bom/melhor/ótimo), o parcelamento e o teste de preço com critério escrito antes. Use para "quanto cobrar", "preço", "planos", "pacotes", "está caro?", "pricing", "precificação", ou no lancar-saas e no lancar-infoproduto. Para oferta completa (bônus, garantia, nome), usar arkos-oferta.
status: rascunho
versao: 0.1.0
modulos: [10]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia-modelo, arkos-estrategia-premissas, arkos-oferta, jev]
---

# arkos-estrategia-preco

**Princípio:** o preço é uma fração do **valor que o cliente percebe**. O custo só define o piso, e a concorrência só dá a referência.

## 1. Quando usar e quando não usar

**Usar:**
- Primeiro preço.
- Revisão de preço (margem baixa, "está caro", "está barato demais").
- Criar planos e pacotes.

**Não usar:**
- Oferta completa (bônus, garantia, nome, stack). Usar a `arkos-oferta`, que chama esta skill no passo de preço.
- Preço por resultado (OaaS). Usar a `arkos-oaas-calculadora`.

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: resultado, pergunta: "Que resultado o cliente tem, em dinheiro ou tempo? (ex.: +10 consultas/mês × R$ 300)", obrigatoria: true }
- { id: preco_atual, pergunta: "Preço atual, se houver", perfil: preco, obrigatoria: false }
- { id: custo, pergunta: "Custo para entregar uma unidade", obrigatoria: false }
- { id: concorrentes, pergunta: "Preços de 2 ou 3 alternativas (concorrente, fazer sozinho, não fazer)", obrigatoria: false }
- { id: motor, pergunta: "Unidade de cobrança", opcoes: [por mês, por projeto, por uso, por assento, por resultado], obrigatoria: true }
```

## 3. Passos

1. **Valor:** resultado anual do cliente em dinheiro. Se for tempo, horas × valor-hora do cargo. Sem número do cliente, faixa `estimativa` + premissa. *Claude + script.*
2. **Faixa de preço (hipótese, marcada `estimativa` — o alvo sai de teste com dinheiro):**
   - de 10% a 20% do valor anual é **estimativa**, não alvo; sem número do cliente, ancorar nas alternativas e no **limite de aprovação de compra** do comprador (o que ele aprova sem subir de alçada);
   - piso pela margem, no **pior** custo de uso:
     - **sem IA pesada:** margem bruta ≥ 75% (custo × 4);
     - **com IA:** margem bruta ≥ 60% (custo × 2,5), calculada no **custo do usuário P90**, nunca no médio (usuário pesado custa várias vezes o preço);
   - teto = a alternativa mais cara crível.

   Se o piso passar do teto, o modelo não fecha: devolver à `arkos-estrategia-modelo`. *Script.*
3. **Âncora:** o número caro e crível que aparece primeiro (custo de não fazer, de contratar uma pessoa, da agência). *Claude.*
4. **Planos (2 a 4, não "sempre 3"):**
   - a diferença principal entre planos é a **métrica de valor** (o que escala com o quanto o cliente usa), não uma lista de recursos;
   - o plano de cima ancora, o de baixo filtra; **plano de cima que não vende em 90 dias sai**;
   - **SaaS com IA:** preço-base com **créditos incluídos, teto e excedente** cobrado à parte. *Claude.*
5. **Mercado (pela ficha do arkos-mercado):**
   - BR: Pix à vista com desconto, parcelamento ("12x de R$ X", com ou sem juros) e Simples Nacional na conta;
   - EUA: preço "$X/mo"; **anual = 10 × mensal (desconto nunca acima de 20%)**, oferecido também no **mês 2** e em **todo aumento de preço**; não tornar o plano só-anual abaixo de US$ 1M de ARR; sales tax por estado;
   - EU: preço com IVA incluído para consumidor final.

   *Claude.*
6. **O preço se decide por pagamento, não por survey.** O teste tem critério escrito antes:
   - as quatro perguntas de Van Westendorp ("tão barato que desconfia?", "pechincha?", "começa a ficar caro?", "caro demais?") **mais "o que justificaria o dobro?"** viram **roteiro qualitativo** — nunca curva de "preço ótimo": é **proibido** calcular preço ótimo com menos de **200 respostas**;
   - a decisão de preço vem de **pagamento real**: pré-venda, sinal, piloto, ou **duas landings com checkout** em preços diferentes.

   O critério de passar e de falhar vira premissa. *Claude + premissas.*
7. **Primeiro preço (SaaS):** cobrar **desde o dia 1**, com **trial de 7 a 14 dias com cartão** (sem cartão só se faltar usuário para aprender, e com prazo). Entrada B2B **não abaixo de US$ 25/mês**. Rever o preço **a cada trimestre ou a cada 20 vendas**, subindo primeiro para clientes novos. *Claude.*
8. **Produto físico (loja/marketplace):** markup mínimo **3× o custo em loja própria** e **4× em marketplace ou TikTok Shop para item abaixo de R$ 50** (a comissão + tarifa fixa come ~30% num item de R$ 20). Confere com a margem real do canal (`uma ferramenta do plano VIP` para TikTok Shop) antes de fechar o preço. *Claude + script do canal.*
9. **Margem:** conferir com a `arkos-estrategia-financas`, que dá o break-even e o CAC máximo para cada preço. *Skill.*

## 4. Saída

`workspace/<cliente>/<projeto>/estrategia/preco.md` com:
- valor estimado;
- faixa, mostrando piso, alvo e teto;
- âncora;
- planos;
- regras do mercado;
- teste com critério;
- premissas.

Grava `preco` no perfil, com confirmação do dono.

## 5. Critério de pronto

- [ ] Valor calculado (ou estimado por faixa, com premissa); a faixa de 10-20% está marcada `estimativa`.
- [ ] Piso pela margem no pior custo de uso (≥ 75% sem IA, ≥ 60% com IA no P90) ≤ alvo ≤ teto, conferido por script.
- [ ] 2 a 4 planos, diferença pela métrica de valor; plano de cima com prazo de 90 dias.
- [ ] Teste de preço por pagamento, com critério escrito antes; nenhum "preço ótimo" com menos de 200 respostas.
- [ ] SaaS: cobrança desde o dia 1, trial com cartão, entrada B2B ≥ US$ 25/mês, revisão por trimestre/20 vendas.
- [ ] Produto físico: markup ≥ 3× em loja própria, ≥ 4× em marketplace/TikTok Shop abaixo de R$ 50.
- [ ] Margem conferida pela skill de finanças.

## 6. Exceções

- **Piso > teto:** o preço não fecha. Voltar ao modelo (custo de entrega ou cliente errado) e não forçar desconto.
- **Prestador quer preço abaixo do piso** (para "entrar no mercado"): registrar como decisão do dono, com prazo para subir e uma premissa de que o cliente aceita o aumento.
- **Sem nenhuma referência de concorrente:** usar o custo de "fazer sozinho" e o de "não fazer" como alternativas.

## 7. Alimenta

- **Oferta (arkos-oferta):** preço e âncora.
- **Finanças:** a tabela de preços.
- **Banca-cliente:** os preços a julgar.
- **Retro:** preço testado × conversão real.

## 8. Regras duras

- Preço sempre por fórmula, nunca de cabeça.
- Mudança de preço no perfil exige confirmação do dono.
- Sem escassez nem desconto falso ("só hoje" que não é só hoje).
- No BR, deixar claro se o parcelamento tem juros (CDC).
