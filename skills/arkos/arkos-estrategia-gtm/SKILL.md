---
name: arkos-estrategia-gtm
description: Go-to-market - define o ICP afiado (o primeiro público, estreito), o canal principal (um, não cinco), o motor de aquisição (outbound, pago, orgânico, parceria, indicação, produto), a mensagem-núcleo, as metas do funil e o plano de 90 dias em sprints de 2 semanas, já apontando os playbooks da ARKOS que executam cada parte. Use para "go-to-market", "como vender", "primeiros 100 clientes", "plano de lançamento", "qual canal", "GTM", ou no lancar-saas e no lancar-infoproduto.
status: rascunho
versao: 0.1.0
modulos: [5, 6, 9, B]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia-modelo, arkos-estrategia-preco, arkos-estrategia-premissas, arkos-roteador, jev]
---

# arkos-estrategia-gtm

**Princípio:** um público estreito, um canal, uma mensagem e uma métrica. Abrir para mais só depois que o primeiro funcionar.

## 1. Quando usar e quando não usar

**Usar:**
- Depois do modelo e do preço.
- Quando o negócio "não decola" e há canais demais.
- Para montar o plano dos primeiros 90 dias.

**Não usar:**
- Executar campanha, lista ou conteúdo. O plano aponta os playbooks que fazem isso: `campanha-nova`, `mineracao-clientes`, `conteudo-organico`, `cold-email-eua`, `agente-sdr`.

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: icp, pergunta: "Para quem você vende primeiro? (quanto mais estreito, melhor)", perfil: icp, obrigatoria: true }
- { id: recursos, pergunta: "Recursos para aquisição: dinheiro/mês e horas/semana", obrigatoria: true }
- { id: ativos, pergunta: "O que já existe: audiência, lista, parceiros, cases, site", obrigatoria: false }
- { id: meta, pergunta: "Meta de 90 dias (clientes ou faturamento)", obrigatoria: true }
- { id: ticket, pergunta: "Ticket e ciclo de venda", opcoes: [baixo e rápido, médio, alto e consultivo], obrigatoria: true }
```

## 3. Passos

1. **Afinar o ICP:**
   - um segmento que se conhece entre si (indica um ao outro);
   - alcançável;
   - com dor alta.
   - Persona com cargo, gatilho de compra ("quando..."), objeções e onde está.
   - Teste: dá para listar 100 nomes reais desse ICP? Se não, estreitar. *Claude.*
2. **Canal pelo método Bullseye:**
   - listar os canais possíveis;
   - escolher 3 para teste barato;
   - escolher 1 principal pelo critério CAC provável × volume × velocidade.

   Coerência com o ticket:
   - **ticket baixo: comunidade, busca e diretórios primeiro** (o 1º pagante de ticket baixo quase nunca vem de anúncio); pago só **com demanda de busca já existente** ou **depois de 10+ pagantes** (aí serve para testar mensagem);
   - ticket alto: outbound, parceria e indicação;
   - BR local: Meta + WhatsApp inbound;
   - EUA B2B: cold email + LinkedIn manual.

   O Jev confere a coerência ticket × canal (sim/não). *Claude + Jev.*
3. **Mensagem-núcleo:** promessa + mecanismo + prova + oferta + CTA, vinda da `arkos-oferta` quando existir. *Skill.*
4. **Funil e metas:** North Star + metas por etapa (alcance → lead → conversa → proposta → cliente). As taxas são de referência do mercado, marcadas como estimativa e viram premissas. O script calcula de trás para frente, a partir da meta de 90 dias: quantos leads, conversas e propostas. *Script + premissas.*
5. **Plano de 90 dias**, com a **janela de julgamento por tipo de canal** (não cortar antes):
   - **canal de resposta rápida** (anúncio, outbound): julgar em **2 semanas**;
   - **canal de presença** (comunidade, conteúdo, SEO, diretório): **4 a 6 semanas**, com a **cota diária escrita antes** (quantos posts/mensagens/dia) — a mediana até o 1º cliente nesses canais foi ~28 dias;
   - depois da janela: dobrar o vencedor e montar o segundo canal.

   Cada item aponta o playbook e a esteira da ARKOS que o executa (`arkos-roteador`). *Claude.*
6. **Regras de corte:** quando parar um canal. O limiar "CAC > 1,5× o máximo depois de N tentativas" fica como premissa escrita antes, **marcada "sem estudo"**, e é recalibrado pela retro; antes dele, respeitar a janela do passo 5. *Claude.*

## 4. Saída

`workspace/<cliente>/<projeto>/estrategia/gtm.md` com:
- ICP e persona;
- canal principal e os de teste, com notas;
- mensagem-núcleo;
- funil com as metas (de trás para frente);
- plano de 90 dias com os playbooks;
- regras de corte;
- premissas.

O `saida.json` leva `icp`, `canal_principal` e `plano_90d`, para as esteiras.

## 5. Critério de pronto

- [ ] ICP estreito o bastante para listar 100 nomes reais.
- [ ] Um canal principal, com justificativa e coerência ticket × canal (ticket baixo começa em comunidade/busca/diretório).
- [ ] Janela de julgamento por tipo de canal (2 semanas resposta rápida; 4-6 semanas presença, com cota diária).
- [ ] Funil calculado por script a partir da meta.
- [ ] Cada item do plano ligado a um playbook da ARKOS.
- [ ] Regras de corte escritas antes.

## 6. Exceções

- **Recursos não cobrem o funil** (a meta pede 3.000 leads e só há verba para 500): mostrar a conta, propor meta menor ou canal mais barato. Nunca esconder.
- **Canal principal bloqueado por regra** (WhatsApp frio, SMS nos EUA, LinkedIn automático): o canal sai da lista, e a regra fica registrada.
- **ICP muito amplo, e o prestador não quer estreitar:** rodar o plano mesmo assim, mas criar a premissa crítica "mensagem genérica converte" e um teste com prazo curto.

## 7. Alimenta

- **Esteiras e playbooks:** o plano de 90 dias.
- **Finanças:** o CAC estimado.
- **Banca-investidor e banca-operador:** a capacidade de execução.
- **Retro:** meta × real por etapa do funil e por canal.
- **Perfil:** `icp`, com confirmação.

## 8. Regras duras

- Um canal principal por vez. Os de teste têm prazo e critério.
- Nenhum canal que dependa de contato sem opt-in (WhatsApp) ou de automação proibida (LinkedIn).
- Toda taxa de conversão sem dado próprio é estimativa e vira premissa.
