---
name: arkos-estrategia-produto
description: Produto na suíte arkos-estrategia. Define o escopo do MVP pelo trabalho que o cliente quer fazer (JTBD), prioriza com RICE ou ICE (conta por script), monta o roadmap Agora/Próximo/Depois e fixa a North Star, a métrica de ativação e a de retenção, mais o teste dos 40% de "muito decepcionado". Use quando pedirem "o que entra no MVP", "priorizar features", "roadmap", "o que construir primeiro", "métrica de ativação", "product-market fit", "MVP scope", "prioritize backlog", "north star".
status: rascunho
versao: 0.1.0
modulos: [1, 11, 9]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-estrategia-premissas, arkos-estrategia-modelo, arkos-estrategia-gtm, arkos-gate, jev]
---

# arkos-estrategia-produto

A pergunta é: **qual é a menor coisa que entrega o trabalho principal do cliente, e como saberemos que funcionou?** Um MVP que não tem métrica de ativação definida antes de ser construído não é MVP: é palpite caro.

## 1. Quando usar e quando não usar

**Usar:**
- No playbook `lancar-saas` depois de modelo e GTM, ou antes, quando o dono já tem a lista de features.
- Quando o backlog cresceu e ninguém sabe o que vem primeiro.
- Quando o produto já existe e a retenção está ruim. Nesse caso esta skill entra depois do `arkos-estrategia-diagnostico`.

**Não usar:**
- Para arquitetura e código, que são do módulo 1 (superpowers, backend-design).
- Para interface e telas, que são do módulo 2 (taste-skill, impeccable).
- Para serviço puro sem componente de produto (ex.: agência OaaS). Aí o "produto" é a oferta: `arkos-oferta`.

## 2. Entradas

Lê do perfil `icp`, `dores`, `oferta` e `mecanismo`. Do estado da suíte lê `modelo.md` (proposta de valor), `gtm.md` (ICP e canal) e `premissas.yaml` (categorias `cliente` e `problema`).

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: job, pergunta: "Em uma frase: quando [situação], o cliente quer [motivação] para [resultado]", perfil: oferta.promessa, obrigatoria: true }
- { id: alternativa, pergunta: "Como o cliente resolve isso hoje (planilha, WhatsApp, concorrente, não resolve)?", obrigatoria: true }
- { id: backlog, pergunta: "Lista de features ou ideias que você já tem (pode colar)", obrigatoria: false }
- { id: evidencia, pergunta: "Conversas com clientes já feitas: quantas e o que ouviu (sem nomes)", obrigatoria: false }
- { id: prazo, pergunta: "Prazo até ter alguém usando", padrao: "6 semanas", obrigatoria: true }
- { id: time, pergunta: "Quem constrói e quantas horas por semana", obrigatoria: true }
- { id: estagio, pergunta: "Estágio", opcoes: [ideia, prototipo, beta-com-usuarios, pagantes], obrigatoria: true }
```

## 3. Passos

1. **Escrever o job principal** no formato JTBD, mais 2–4 jobs relacionados. Depois listar os *resultados desejados* do job principal: "diminuir o tempo de…", "reduzir a chance de…". *Claude.*
2. **Mapear a alternativa atual** e o custo dela para o cliente: tempo, dinheiro, erro, vergonha. O MVP precisa ganhar da alternativa em pelo menos um resultado que importa, não em tudo. *Claude.*
3. **Ler as evidências.** Sem conversa com cliente, o primeiro item do roadmap é o roteiro de entrevista no estilo Mom Test:
   - perguntas sobre o passado e o comportamento, nunca "você usaria?";
   - de 10 a 15 conversas antes de escrever código.
   O roteiro vai como `teste` da premissa de problema. *Claude.*
4. **Montar o backlog:** juntar o que o dono já tem com o que sai dos resultados desejados. Cada item leva o job que atende. Item sem job vai para "Depois" ou sai. *Claude.*
5. **Triar com o Jev** (`decide_many`), uma pergunta sim/não por item: "sem isto, o cliente consegue completar o job principal?". Os itens com "não" são candidatos ao núcleo do MVP. *Jev.*
6. **Pontuar com RICE.** Alcance, impacto (0,25 / 0,5 / 1 / 2 / 3), confiança (0,5 / 0,8 / 1) e esforço em semanas-pessoa são estimados pelo Claude, com a justificativa de uma linha. A conta (A × I × C ÷ E) e a ordenação são feitas pelo `scripts/rice.py`. Com menos de 10 itens ou sem dado de alcance, usar ICE com a mesma regra. *Script.*
7. **Cortar até caber no prazo:** somar o esforço do topo da lista até o limite de `prazo × time`. O que passar do limite vai para "Próximo". *Script.*
8. **Definir as métricas:**
   - **North Star:** uma métrica que cresce quando o cliente recebe valor (ex.: SaaS de agenda para salões: "horários marcados pelo app por semana", não "cadastros").
   - **Ativação:** a ação que mostra que o cliente viu o valor, com o prazo (ex.: "marcou 5 horários nos primeiros 7 dias").
   - **Retenção:** a coorte semanal ou mensal que continua fazendo a ação-núcleo.
   - **Teste dos 40%:** a pergunta dos 40% de "muito decepcionado", aplicada a partir de 30–40 usuários ativos.
   *Claude.*
9. **Critérios de parada:** o número que, se não for atingido até a data X, faz voltar à premissa ou mudar o escopo (ex.: "ativação < 25% depois de 50 contas = rever o onboarding antes de nova feature"). *Claude.*
10. **Escrever `produto.md`** e passar pelo `arkos-gate`. *Skill.*

## 4. Saída

Em `workspace/<cliente>/<projeto>/estrategia/produto.md`:
- **Job e alternativa:** o job principal, os resultados desejados e a alternativa atual com o custo dela.
- **Escopo do MVP:** o que entra, cada item com o job e o RICE; e o que fica de fora, com o porquê.
- **Roadmap:** Agora (até o prazo), Próximo e Depois. Sem datas falsas além do "Agora".
- **Métricas:** North Star, ativação, retenção, teste dos 40% e os critérios de parada.
- **Roteiro de entrevista** (Mom Test), quando faltar evidência.
- **"O que eu faria nesta semana"** e **"o que pode matar isto"**.

Também gera `produto-rice.json` com a entrada e o resultado do script, e linhas novas em `premissas.yaml`.

## 5. Critério de pronto

- [ ] O job principal está escrito no formato "quando…, quero…, para…".
- [ ] A alternativa atual do cliente está nomeada.
- [ ] Todo item do MVP aponta para um job.
- [ ] A ordem do RICE ou do ICE veio do script, e o `produto-rice.json` existe.
- [ ] O esforço do "Agora" cabe em `prazo × time`.
- [ ] North Star, ativação (com prazo) e retenção estão definidas, e nenhuma é métrica de vaidade (cadastro, pageview).
- [ ] Existe pelo menos um critério de parada com número e data.
- [ ] Sem evidência de cliente, o roteiro Mom Test está na saída e a premissa de problema está `aberta`.
- [ ] Tem "o que eu faria nesta semana" e "o que pode matar isto".

## 6. Exceções

- **Não há backlog:** gerar a lista a partir dos resultados desejados, com no máximo 15 itens.
- **Não há evidência:** não cortar escopo "no feeling". Rodar a priorização com confiança 0,5 em tudo e pôr as entrevistas como primeiro item do "Agora".
- **O MVP não cabe no prazo nem com o núcleo mínimo:**
  - propor um MVP "concierge" (feito à mão por trás) ou "mágico de Oz" para testar o valor antes do código;
  - ou pedir ao dono para mudar o prazo.
  Nunca esconder o excesso.
- **Produto já com usuários e retenção ruim:** não adicionar feature. Ler o diagnóstico, achar onde a coorte cai e priorizar só o que mexe na ativação.

## 7. Alimenta

- **Perfil:** `mecanismo.como_funciona` quando o núcleo do MVP o define, com confirmação.
- **Premissas:**
  - "o cliente completa o job com só o núcleo" (categoria `problema`);
  - "a taxa de ativação chega a X" (categoria `cliente`).
- **Relatório:** o escopo, o roadmap e as métricas.
- **Banca:** o operador ataca o esforço e o cliente ataca o job.
- **Retro:** as métricas e os critérios de parada são o que a retro mede.

## 8. Regras duras

- Nenhuma feature entra no MVP sem job ligado.
- A conta de priorização é do script. O Claude só estima e justifica cada fator.
- Ativação e retenção são definidas **antes** de construir.
- Pergunta "você usaria?" não conta como evidência.
- Não usar nome de cliente nem dado pessoal nas evidências: só o padrão do que foi ouvido.
