---
name: arkos-estrategia-retro
description: Retrospectiva da suíte arkos-estrategia depois de N semanas. Compara premissa com realidade e o projetado com o realizado, atualiza status e confiança no registro de premissas, mede o erro da projeção financeira e fecha com uma decisão (perseverar, ajustar, pivotar ou parar) e a data da próxima retro. Use quando disserem "retro", "revisão do mês", "o que aprendemos", "deu certo o que planejamos?", "atualizar premissas", "retrospective", "what did we learn", "check assumptions", ou na data agendada pelo diagnóstico ou pelo GTM.
status: rascunho
versao: 0.1.0
modulos: [E, B, 11]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-estrategia-premissas, arkos-estrategia-financas, arkos-estrategia-relatorio, arkos-gate, jev]
---

# arkos-estrategia-retro

A pergunta é: **o que achávamos que era verdade, o que de fato aconteceu e o que muda agora?** A retro é o motivo de existir o `premissas.yaml`. Sem ela, as premissas viram uma lista de desejos.

## 1. Quando usar e quando não usar

**Usar:**
- Na data marcada pelo diagnóstico, pelo GTM (fim dos 90 dias) ou pelo produto (critério de parada).
- A cada 4 semanas num negócio que roda (padrão; ajustável).
- Quando um número importante mudou muito, para mais ou para menos, fora do esperado.

**Não usar:**
- Antes de existir `premissas.yaml` com pelo menos uma premissa em `testando`.
- Com menos de 2 semanas desde a última retro, a menos que um critério de parada tenha disparado.
- Para culpar pessoas. A retro olha premissas e decisões, não quem errou.

## 2. Entradas

Lê `premissas.yaml`, `financas-resultado.json`, `produto.md` (métricas e critérios de parada), `diagnostico.md` (plano de 30 dias), o último `retro/*.md` e o perfil (`numeros`, privado).

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: periodo, pergunta: "Período desta retro", padrao: "desde a última retro", obrigatoria: true }
- { id: realizados, pergunta: "Números reais do período (os mesmos da projeção: clientes novos, CAC, ticket, churn, caixa) ou arquivo", perfil: numeros, obrigatoria: true }
- { id: testes, pergunta: "Resultado de cada teste em andamento (conversas, pré-vendas, anúncios de teste)", obrigatoria: true }
- { id: surpresas, pergunta: "O que aconteceu que ninguém previu?", obrigatoria: false }
- { id: decisoes, pergunta: "Decisões tomadas no período fora do plano", obrigatoria: false }
```

## 3. Passos

1. **Foto do antes:** carregar as premissas com status `testando` ou `aberta` e os valores projetados para o período, a partir do `financas-resultado.json` e das métricas do produto. *Script.*
2. **Projetado × realizado** com o `scripts/retro.py`:
   - para cada métrica: o projetado (cenário base), o realizado, a diferença absoluta e a percentual;
   - em que cenário o realizado caiu (abaixo do pessimista, entre o pessimista e o base, entre o base e o otimista, acima do otimista);
   - o erro médio da projeção.
   Grava `retro-dados.json`. *Script.*
3. **Julgar cada premissa** com a evidência do período:
   - `validada`: o teste passou no critério combinado antes;
   - `refutada`: o teste falhou no critério;
   - `testando`: ainda sem evidência suficiente;
   - `sem dado`: o teste não rodou, e a retro registra por quê.
   O critério é o que estava escrito no campo `teste`, nunca um novo inventado depois. *Claude.*
4. **Calibrar a confiança:** o Jev (`decide_many`) responde, por premissa, "a evidência do período aumenta, mantém ou reduz a confiança?". A nova confiança sai da regra comum (`retro.py premissas`, que usa `arkos-estrategia/scripts/premissas.py`): +0,15, 0 ou −0,20, com limites entre 0,05 e 0,95; evidência que refuta manda o status para `refutada` e a confiança para 0,05. Nunca chega a 1. *Jev + script.*
5. **Novos riscos críticos:** reaplicar o filtro de impacto alto com confiança < 0,5. Uma premissa que entrou no filtro é destacada como "virou crítica nesta retro". *Script.*
6. **Surpresas:** cada surpresa relevante vira premissa nova, com `origem: arkos-estrategia-retro`. *Claude.*
7. **O que aprendemos:** de 3 a 5 frases, cada uma ligada a uma premissa ou a uma métrica. "Aprendemos que precisamos nos esforçar mais" não conta. *Claude.*
8. **Decisão:** perseverar, ajustar, pivotar ou parar, com a regra:
   - **pivotar ou parar:** uma premissa de impacto alto foi refutada;
   - **ajustar:** o realizado ficou abaixo do pessimista em 2 métricas da North Star, ou um critério de parada disparou;
   - **perseverar:** os demais casos.
   O Claude pode recomendar outra coisa, mas tem de dizer que contrariou a regra e por quê. *Claude.*
9. **Plano até a próxima retro:** até 3 ações, os testes das premissas críticas e a data da próxima retro. Quando a decisão mexe em preço, modelo ou GTM, chamar a skill correspondente pelo `arkos-estrategia`. *Claude.*
10. **Gravar e gate:** atualizar `premissas.yaml` (status, confiança, evidência e `atualizado_em`), escrever a retro, passar pelo `arkos-gate` e pedir ao `arkos-estrategia-relatorio` a nova versão. *Skill.*

## 4. Saída

- `workspace/<cliente>/<projeto>/estrategia/retro/<AAAA-MM-DD>.md`, com:
  - o período e a decisão em uma linha;
  - a tabela projetado × realizado;
  - a tabela de premissas (id, antes → depois, status e evidência);
  - as premissas que viraram críticas;
  - o que aprendemos;
  - o plano e a data da próxima retro;
  - "o que eu faria nesta semana" e "o que pode matar isto".
- `retro-dados.json` ao lado.
- `premissas.yaml` atualizado. A versão anterior fica em `retro/<data>-premissas-antes.yaml` para o diff.

Exemplo (infoproduto de preparação para concurso, BR, ilustrativo): "Previmos CAC de R$ 45 e veio R$ 112. A premissa P-004 ('o público compra no primeiro anúncio') foi refutada: 80% das vendas vieram de quem viu a aula gratuita. Decisão: ajustar. O canal passa a ser aula gratuita → e-mail → oferta, e a projeção é refeita."

## 5. Critério de pronto

- [ ] Toda premissa `testando` do início do período tem um status novo ou o motivo de seguir `testando`.
- [ ] O julgamento usou o critério escrito no `teste` de cada premissa.
- [ ] A tabela projetado × realizado veio do script, e o `retro-dados.json` existe.
- [ ] A confiança mudou pela regra fixa, e nenhuma ficou em 1.
- [ ] A cópia `premissas-antes.yaml` existe.
- [ ] Há uma decisão, e se ela contraria a regra o motivo está escrito.
- [ ] A próxima retro tem data.
- [ ] "O que aprendemos" tem de 3 a 5 itens, cada um ligado a premissa ou métrica.
- [ ] Tem "o que eu faria nesta semana" e "o que pode matar isto".

## 6. Exceções

- **Nenhum teste rodou no período:** a retro não inventa aprendizado. Registra "sem dado" com o motivo, recomenda reduzir o número de testes para 1 e remarca em 2 semanas.
- **Faltam os números reais:** comparar só as premissas com evidência qualitativa e pedir a coleta (mesmo plano de 2 semanas do diagnóstico).
- **O realizado ficou muito acima do otimista:**
  - conferir primeiro se o dado está certo (duplicado, mês parcial);
  - se estiver, tratar como surpresa e criar a premissa "o que causou isto se repete?". Ganho também se testa.
- **O dono discorda da decisão:** registrar as duas posições na retro. A decisão final é do dono, e a retro seguinte mede quem tinha razão.

## 7. Alimenta

- **Perfil:** `numeros`, com os valores realizados, sempre com confirmação e `privado: true`.
- **Premissas:** status, confiança, evidência e as premissas novas.
- **Relatório:** uma nova versão, com a seção "O que mudou desde a última retro".
- **Finanças:** quando o erro médio passa de 30%, a retro pede para refazer a projeção com os drivers reais.
- **Retro seguinte:** a data, o plano e a lista do que conferir.

## 8. Regras duras

- Não mudar o critério de um teste depois de ver o resultado.
- Confiança nunca chega a 1, nem cai a 0. Premissa refutada fica no registro como `refutada`, não é apagada.
- Toda mudança de confiança sai da regra fixa, com o motivo.
- A retro não culpa pessoas: fala de premissas, decisões e dados.
- Números privados não vão para o Jev: ele recebe só a direção (subiu, desceu, igual) e o texto da premissa.
