---
name: arkos-estrategia-banca-cliente
description: Banca da suíte arkos-estrategia na lente do cliente-alvo. Simula o comprador do ICP diante da oferta - compraria? por quanto? o que trava (confiança, troca, preço, tempo, aprovação)? - pelo trabalho que ele quer fazer e pela alternativa atual, e devolve o roteiro para validar com clientes reais. Parecer padrão da banca (nota 0–10, veredito seguir / seguir com condições / parar, 3 exigências, premissas atacadas). Use quando pedirem "o cliente compraria?", "como o cliente vê isto", "objeções", "banca do cliente", "customer review", "would they buy", ou no playbook lancar-saas.
status: rascunho
versao: 0.1.0
modulos: [11, G, 9, 8]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia-premissas, arkos-estrategia-preco, arkos-oferta, arkos-gate, jev]
---

# arkos-estrategia-banca-cliente

**Persona:** o comprador do ICP, ocupado, com o dinheiro contado e uma solução ruim que ele já conhece. Ex.: a dona de um salão de bairro que marca horário pelo WhatsApp e no caderno. A pergunta é: **por que eu largaria o que faço hoje para pagar por isto?**

## 1. Quando usar e quando não usar

**Usar:**
- Depois de existir oferta e preço (`arkos-oferta` ou `arkos-estrategia-preco`).
- Antes da página de vendas e do anúncio, para afiar as objeções.
- No `lancar-saas`, como uma das 4 personas.

**Não usar:**
- Como prova de demanda. Esta banca é uma **simulação**: a evidência que ela gera tem peso zero no registro de premissas, até ser confirmada com clientes reais.
- Sem ICP definido. Primeiro vem `arkos-estrategia-gtm` ou o `perfil.icp`.

## 2. Entradas

Lê do perfil `icp`, `dores`, `oferta`, `preco` e `concorrentes`. Do estado da suíte lê `preco.md`, `gtm.md`, `produto.md` (job e alternativa) e `premissas.yaml` (categorias `cliente`, `problema` e `preco`). Lê o `OFFER.md` do `arkos-oferta`, se existir.

**Independência:** não lê os pareceres das outras bancas antes de escrever o seu.

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: persona, pergunta: "Qual cliente simular: o decisor, o usuário ou os dois?", padrao: "o decisor do ICP", perfil: icp.cargo_decisor, obrigatoria: true }
- { id: ouvido, pergunta: "Frases reais que você já ouviu de clientes (sem nomes)", obrigatoria: false }
- { id: alternativa, pergunta: "O que esse cliente usa hoje no lugar", obrigatoria: false }
```

## 3. Passos

1. **Riscos críticos primeiro:** as premissas de impacto alto e confiança < 0,5, pelo `arkos-estrategia/scripts/criticos.py`, com destaque para as das categorias `cliente`, `problema` e `preco`. *Script.*
2. **Vestir a persona:** escrever um dia comum do cliente em 5 linhas, com o momento em que o problema aparece. Usar só o que está no perfil, nas frases ouvidas e na pesquisa pública do nicho. Lacuna vira "não sei", não detalhe inventado. *Claude.*
3. **Forças do progresso (JTBD):**
   - **empurrão:** o que incomoda hoje;
   - **atração:** o que a oferta promete;
   - **ansiedade:** o medo de trocar;
   - **hábito:** o apego ao que já usa.
   A compra só acontece quando empurrão + atração > ansiedade + hábito. Dizer qual lado ganha e por quê. *Claude.*
4. **Ler a oferta como o cliente:** reescrever a promessa nas palavras dele. Se a reescrita não fizer sentido para o cliente, a oferta está falando com o dono, não com o cliente. Dar nota às 4 partes da equação de valor (resultado, probabilidade, tempo, esforço) do ponto de vista dele. *Claude.*
5. **Preço:** simular as 4 perguntas de Van Westendorp (barato demais, barato, caro, caro demais) **como hipótese**, com a lógica de cada faixa. Comparar com o preço atual e com o custo da alternativa. O resultado vira premissa de preço com `confianca` ≤ 0,3 e o teste real. *Claude.*
6. **Objeções:** listar as 5 objeções mais prováveis, em 5 tipos: confiança ("e se não funcionar?"), troca ("dá trabalho mudar"), preço, tempo ("agora não") e aprovação ("preciso falar com meu sócio"). O Jev (`decide_many`) responde por objeção "a oferta atual responde a isto?". *Claude + Jev.*
7. **Pontuar a rubrica** (0–10 por critério, com a justificativa de uma linha):

   | Critério | Peso |
   |---|---|
   | Dor real e frequente (empurrão) | 0,25 |
   | Clareza da promessa nas palavras do cliente | 0,20 |
   | Preço frente à alternativa | 0,20 |
   | Ansiedade e hábito superáveis | 0,20 |
   | Objeções respondidas pela oferta | 0,15 |

   A nota sai do `arkos-estrategia/scripts/banca_nota.py`, o mesmo das 4 bancas. *Claude + script.*
8. **Roteiro de validação real** no estilo Mom Test:
   - de 6 a 8 perguntas sobre o passado e o comportamento, sem pitch e sem "você compraria?";
   - mais o sinal de compromisso a pedir no fim: pré-venda, lista de espera com Pix de reserva ou uma segunda reunião.
   *Claude.*
9. **Checar o parecer com o Jev:** "o parecer usa detalhe da persona que não está no estado nem na pesquisa?", "as exigências pedem evidência de cliente real?", "o veredito segue a regra?". Gravar o parecer e as premissas novas. *Jev.*

## 4. Saída

O arquivo é `workspace/<cliente>/<projeto>/estrategia/banca/cliente.md`, no **formato comum da banca**:

```markdown
---
persona: cliente
nota: 0.0            # do banca_nota.py
veredito: seguir | seguir com condições | parar
rubrica: { dor: 0, clareza: 0, preco: 0, ansiedade_habito: 0, objecoes: 0 }
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
## Forças do progresso
## Objeções (e se a oferta responde)
## Roteiro para conversar com clientes reais
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
- [ ] A nota veio do `banca_nota.py`, e o veredito bate com a regra comum.
- [ ] As 4 forças do progresso estão escritas, e o lado que ganha está dito.
- [ ] As 5 objeções estão listadas, cada uma com sim/não para "a oferta responde?".
- [ ] A faixa de preço está marcada como hipótese e virou premissa com confiança ≤ 0,3.
- [ ] O roteiro de validação tem de 6 a 8 perguntas sobre o passado, sem pitch.
- [ ] Pelo menos 1 das 3 exigências pede evidência de cliente real.
- [ ] Nenhum detalhe da persona foi inventado fora do estado e da pesquisa.
- [ ] O parecer foi escrito sem ler os das outras bancas.

## 6. Exceções

- **Sem ICP claro:** não simular um cliente genérico. A primeira exigência vira definir o ICP, e a nota fica parcial.
- **Já existem conversas reais:** usar as frases como base da persona, e a evidência delas entra no registro com o peso real. A simulação continua com peso zero.
- **B2B com decisor e usuário diferentes:** simular os dois. A nota usa o decisor, e as objeções do usuário entram como risco de adoção.
- **Mercado EUA ou EU:** a persona segue os hábitos do mercado (canal, meio de pagamento, ciclo de compra) e o parecer sai em pt-BR. O roteiro de entrevista sai no idioma do cliente.

## 7. Alimenta

- **Perfil:** `dores`, só com confirmação e só as que vieram de conversa real, nunca da simulação.
- **Premissas:** as premissas de preço (Van Westendorp hipotético), as de objeção e as de adoção, cada uma com o teste real.
- **Relatório:** a linha da banca e as 3 objeções principais.
- **Copy e oferta:** as objeções sem resposta vão para o `arkos-oferta` (bônus e garantia) e para a copy (módulo 8).
- **Retro:** o resultado das conversas reais confirma ou derruba esta banca.

## 8. Regras duras

- Simulação não é evidência: peso zero no registro até haver cliente real, e o parecer diz isso na primeira linha.
- Nada de "você compraria?" no roteiro.
- Não inventar depoimento, frase de cliente nem dado demográfico.
- A nota sai do script, e o veredito sai da regra.
- Não usar nome nem dado pessoal de cliente real nas frases ouvidas.
