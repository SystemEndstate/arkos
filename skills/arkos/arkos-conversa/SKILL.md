---
name: arkos-conversa
description: Copy de contato e conversa que desperta interesse e leva à reunião sem soar robô, por canal (WhatsApp, Instagram DM, LinkedIn, e-mail) e mercado (BR, EUA). Gera primeira mensagem, cadência, qualificação, objeções e o prompt de sistema do agente atendente, com a política de cada canal embutida. Substitui o arkos-sdr-segmentado. Use para abordagem, follow-up, SDR, agente de WhatsApp, resposta a lead, reativação de base.
status: rascunho
versao: 0.1.0
modulos: [8.6, 13, K, 5]
depende_de: [arkos-perfil, arkos-oferta, arkos-mercado, arkos-guarda-envio, jev]
semente: Mia (meuanuncio)
---

# arkos-conversa

Método: Josh Braun (pergunta neutra sobre o processo, "pare no não"), Becc Holland (premissa não transferível), 30MPC (uma dor por mensagem, prova de par, CTA de interesse). Fluxo: `chatbot-flow-design` + `build-agent`. **Esta skill escreve. Quem envia é o canal, depois do `arkos-guarda-envio`.**

## Entradas

perfil + `OFFER.md` · tipo de venda e ICP · canal · mercado · **origem do contato** (inbound, opt-in, base própria, frio) · voz do dono (3–5 mensagens reais) · link de agenda e regras de handoff.

## 0. Porteiro de política (antes de escrever)

O Jev classifica origem × canal. Bloqueia: WhatsApp sem opt-in · DM de IG para quem não interagiu · LinkedIn automatizado. Bloqueado = propor o canal permitido (ex.: e-mail que pede o opt-in: "posso te mandar pelo WhatsApp?").

## 1. Primeira mensagem

- **Premissa** verificada sobre a pessoa ou a empresa. Sem fato, não inventa: pergunta.
- **Uma** dor provável do cargo ou do nicho.
- **Uma** pergunta neutra sobre o processo atual.
- Sem pitch, sem link, sem pedir reunião no 1º toque.

| Canal | Formato |
|---|---|
| WhatsApp | template aprovado (marketing/utilidade), ~300 caracteres, variável de premissa, botão de resposta rápida; áudio de 20–30 s só depois da 1ª resposta |
| Instagram | resposta à palavra-chave ou story: entregar primeiro o prometido, perguntar depois; nunca elogio + pitch juntos |
| LinkedIn | conexão ≤ 300 caracteres ou sem nota; DM só depois do aceite; **humano envia** |
| E-mail EUA | direto, assunto de 2–4 palavras, prova com número, "worth a look?" |
| BR | caloroso, "aqui é o X da Y", "faz sentido?" |

## 2. Cadência

- WhatsApp: D0 template → conversa livre na janela de 24 h → sem resposta, **no máximo 2 templates** (D3, D7) com valor novo e saída clara → encerrar. Cada template custa: o Jev decide se vale.
- IG: só dentro de 24 h; fora disso, só humano (`HUMAN_AGENT`, até 7 dias).
- LinkedIn: conexão → D+1 → D+5 → D+12, com comentário em post no meio.
- Reativação: reconhecer o sumiço sem vender → oferta só se responder → parar se houver reclamação.
- Break-up: última mensagem que deixa o "não" fácil.

## 3. Qualificação

Uma pergunta por mensagem, alternando com observação. B2B/high-ticket: BANT/MEDDIC lite · serviço local/imóvel: necessidade, prazo, região, faixa · infoproduto: momento, consciência, dinheiro para a parcela. Memória por turno: qualificação, compromissos, objeções, próxima ação. Jev: quente/morno/frio → agendar, nutrir ou desqualificar com elegância.

## 4. Objeções (ACRC)

Reconhecer → esclarecer com uma pergunta → responder com prova **do perfil** → confirmar. Categorias: preço, "agora não", "já tenho fornecedor", "manda material", "vou pensar", autoridade, desconfiança de IA. **"Não" explícito = parar e registrar opt-out.**

## 5. Prompt do agente (um por canal × mercado)

Blocos fixos: identidade e escopo (função de negócio; recusa conversa geral, pela regra do WhatsApp contra IA de uso geral) · transparência (diz que é assistente virtual da empresa) · voz · base (OFFER.md + FAQ + preços; sem resposta = "vou confirmar com a equipe") · fluxo (saudação → descoberta → qualificação → oferta → objeção → agendamento → confirmação) · regras do canal · escalonamento para humano (pedido, reclamação, negociação fora da tabela, lead quente, 2 falhas seguidas) · mercado (R$/Pix/Brasília/LGPD ou USD/fuso/TCPA/CAN-SPAM) · saída JSON por turno `{intencao, nota_lead, proxima_acao, flags_politica}`.

## Saída

`workspace/<cliente>/<projeto>/conversa/`: `primeira-mensagem.md`, `cadencia.md`, `qualificacao.md`, `objecoes.md`, `prompt-agente-<canal>-<mercado>.md`, `politica-canal.md`.

## Teste obrigatório antes de entregar

10 conversas simuladas (satisfeito, curioso, cético, "tá caro", "não"). O Jev responde sim/não: parece humano? inventou dado? pediu reunião sem interesse? respeitou o "não"? violou a política? **Qualquer reprovação = volta.** Relatório no `arkos-gate`.
