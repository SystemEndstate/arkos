---
name: arkos-outbound-eua
description: Outbound para o mercado dos EUA pela ARKOS, dentro do CAN-SPAM. Monta a infraestrutura (domínio secundário, SPF, DKIM, DMARC, aquecimento), limpa a lista por script (supressão, sem fonte, endereço de função, fora dos EUA, duplicado), escreve a sequência em inglês americano e confere cada e-mail por script (cabeçalho, assunto, endereço postal, opt-out, identificação comercial). Nunca envia: entrega o lote como rascunho ao arkos-guarda-envio. Use em "outbound EUA", "cold email americano", "prospectar nos Estados Unidos", "CAN-SPAM", "cold email US", "outbound to US", "email sequence for American prospects".
status: instalada (promovida em 2026-11-22)
versao: 0.1.0
modulos: [5, 8, 13, K]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-gate, arkos-guarda-envio, arkos-lead-merge, cold-email, coldoutbound, jev]
fontes_conferidas_em: 2026-11-22
---

# arkos-outbound-eua

**Princípio:** nos EUA o cold e-mail B2B é permitido (opt-out, não opt-in), mas **cada e-mail fora da regra pode custar até US$ 53.088** e queima o domínio. A ARKOS escreve, limpa e confere. Quem libera o envio é o `arkos-guarda-envio`, com o "sim" de uma pessoa.

## 1. Quando usar e quando não usar

**Usar:**
- Apoio da etapa `sequencia` do playbook `cold-email-eua` e da esteira `outbound-eua`.
- Cliente brasileiro vendendo para empresas americanas (serviço, software, agência OaaS).

**Não usar:**
- Leads na Europa: GDPR e ePrivacy, base legal por país (o próprio playbook trata). Canadá: CASL, que é opt-in.
- Consumidor final (B2C) em massa: risco alto e baixa resposta; usar mídia paga.
- SMS ou ligação automática: TCPA, fora do escopo; ligação só humana.
- Lista comprada sem fonte: não entra (o script tira quem não tem `fonte`).

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: cliente, pergunta: "Cliente (slug)", obrigatoria: true }
- { id: projeto, pergunta: "Projeto (slug, padrão outbound-eua-<AAAA-MM>)", obrigatoria: true }
- { id: icp, pergunta: "ICP: cargo, porte, setor, estado dos EUA", perfil: icp, obrigatoria: true }
- { id: leads, pergunta: "CSV de leads (email, nome, empresa, fonte, pais) ou rodar mineracao-clientes", obrigatoria: true }
- { id: endereco, pergunta: "Endereço postal físico válido do remetente (rua ou caixa postal registrada, cidade, UF, ZIP)", obrigatoria: true }
- { id: dominio, pergunta: "Domínio secundário de envio (nunca o principal) e quantas caixas", obrigatoria: true }
- { id: dia_aquecimento, pergunta: "Dia do aquecimento das caixas (1 = caixa nova)", padrao: 1, obrigatoria: true }
- { id: ferramenta, pergunta: "Ferramenta de envio", opcoes: [Instantly, Smartlead, sellbird, outra], padrao: Instantly, obrigatoria: true }
```

**Pasta das entregas:** `workspace/<cliente>/<projeto>/outbound/`.

## 3. O que a ARKOS sabe (conferido em 22/11/2026, guia da FTC)

O CAN-SPAM vale para toda mensagem comercial, B2B incluído:
1. **Cabeçalho verdadeiro:** From, To, Reply-To e domínio identificam quem envia.
2. **Assunto que não engana:** nada de "Re:" falso, "invoice", "your order".
3. **Identificar como anúncio** de forma clara (a exceção é quem deu consentimento antes).
4. **Endereço postal físico válido** em todo e-mail (rua, caixa postal ou caixa privada registrada).
5. **Forma clara de sair**, que funcione por pelo menos 30 dias depois do envio.
6. **Atender o opt-out em até 10 dias úteis**, sem cobrar nem pedir dado além do e-mail. Regra da ARKOS: no mesmo dia.
7. **Quem contrata o envio também responde** pelo que o fornecedor faz.

**Multa:** até US$ 53.088 por e-mail (ajuste da FTC de 17/01/2025; conferir em janeiro de cada ano). **Gmail e Yahoo** (desde 2024): SPF, DKIM e DMARC no domínio, unsubscribe de um clique para quem envia em massa e taxa de spam abaixo de 0,3%.

## 4. Passos

1. **Infraestrutura** (com o `coldoutbound`): domínio secundário parecido com o principal, SPF, DKIM e DMARC (`p=none` no começo), **2 a 3 caixas por domínio** com nome de pessoa, e **2 semanas só de aquecimento** antes de qualquer e-mail frio. *Skill.*
2. **Limpar a lista:**
   ```
   python ~/.claude/skills/arkos-outbound-eua/scripts/canspam.py lote <leads.csv> --supressao <casa>/arkos.engine/supressao.csv \
     --caixas <N> --dia <D> --out .../outbound/lote-<AAAA-MM-DD>.csv --relatorio .../outbound/lote-<AAAA-MM-DD>.json
   ```
   Tira supressão (e-mail ou `@dominio`), duplicado, sem fonte, endereço de função (info@, sales@), fora dos EUA e inválido. Aplica o teto do dia pelo aquecimento (heurística: sobe no warmup das 2 primeiras semanas e estabiliza em **15-20 por caixa por dia, teto 25**). *Script.*
3. **Sequência em inglês americano** (com o `cold-email`): de 3 a 5 toques em 2 a 3 semanas; primeiro e-mail com até 90 palavras, uma pergunta só, sem link nem anexo; personalização de verdade (um fato da empresa), não `{{first_name}}` solto; tom direto, sem "I hope this email finds you well". *Claude.*
4. **Rodapé fixo:** nome da empresa, endereço postal, "This is a promotional message" (ou a decisão registrada do dono de não usar) e a forma de sair ("Reply STOP" ou link). *Claude.*
5. **Conferir cada e-mail** da sequência:
   ```
   python ~/.claude/skills/arkos-outbound-eua/scripts/canspam.py checar .../outbound/email-<n>.json
   ```
   Violação reprova; aviso vai para o dono decidir. *Script.*
6. **Entregar ao `arkos-guarda-envio`:** o lote (`lote-<data>.csv`), os e-mails aprovados pelo script e o relatório. O guarda mostra a prévia, pede o "sim" e só então libera a ferramenta. *Skill.*
7. **Resposta e opt-out:** quem pediu para sair vai para `arkos.engine/supressao.csv` no mesmo dia (também na ferramenta). Respostas são lidas pelo `write-outreach-reply-reader`. *Skill.*
8. **Entrega (todo dia que enviar):** ler da ferramenta o bounce e a taxa de spam e passar pelo script.
   ```
   python ~/.claude/skills/arkos-outbound-eua/scripts/canspam.py bounce --hard <frac> --plataforma <frac> --spam <frac>
   ```
   **Hard bounce real > 2% pausa o lote** e manda limpar a lista; **bounce total da plataforma > 3% pausa a caixa** (o número da plataforma infla, conferir o hard real); **spam ≥ 0,3% pausa** (teto oficial do Gmail/Yahoo). *Script.*
9. **Gate:** checklist da seção 5 no `arkos-gate`. *Skill.*

## 5. Critério de pronto

- [ ] SPF, DKIM e DMARC conferidos no domínio secundário; o domínio principal não envia.
- [ ] O lote saiu do script, com o relatório de quem ficou de fora e o motivo.
- [ ] Houve 2 semanas de aquecimento antes do primeiro e-mail frio, com 2-3 caixas por domínio.
- [ ] O volume do dia respeita o teto do aquecimento (15-20/caixa, teto 25).
- [ ] Bounce e spam conferidos pelo `canspam.py bounce` no dia de envio (nenhum gatilho de pausa ativo).
- [ ] Todo e-mail da sequência passou no `canspam.py checar` sem violação.
- [ ] Os avisos (ex.: identificação como anúncio) têm a decisão do dono registrada.
- [ ] O lote está como rascunho no `arkos-guarda-envio`; nada foi enviado por esta skill.
- [ ] O processo de opt-out no mesmo dia está escrito para o prestador.

## 6. Exceções, custo e envio externo

- **Custo:** domínio secundário, caixas de e-mail (Google Workspace ou Microsoft 365) e a ferramenta de envio têm mensalidade. Estimar e passar pelo portão `confirmacao_custo` antes de comprar.
- **Envio:** nunca daqui. Só o `arkos-guarda-envio` libera, com aprovação explícita (hook `PreToolUse` bloqueia a ferramenta sem `aprovacao_id`).
- **Rollback:** pausar a campanha na ferramenta, tirar o lote da fila e pôr os contatos já tocados na supressão se o problema foi de conteúdo. E-mail enviado não volta: por isso a checagem vem antes.
- **Lote vazio ou quase todo fora** (`resultado_ruim`): a lista é ruim; voltar ao `mineracao-clientes` com outro ICP ou fonte.
- **Coluna email faltando** (`entrada_incompleta`): o script para.
- **Entrega ruim:** hard bounce real acima de 2% pausa o lote e limpa a lista; bounce total da plataforma acima de 3% pausa a caixa para reaquecer; spam a partir de 0,3% para o domínio. Investigar lista e conteúdo, não trocar de domínio para continuar igual.
- **Lead de fora dos EUA na lista:** sai do lote e vai para o fluxo do mercado certo.

## 7. Alimenta

- **Supressão:** `arkos.engine/supressao.csv` (compartilhada por todos os clientes do prestador).
- **Perfil do cliente:** ICP que respondeu, ângulo que respondeu.
- **Aprendizado:** taxa de resposta por ângulo e por setor em `arkos.engine/aprendizado.jsonl`.
- **Esteira:** `saida.json` com `campos.lote`, `campos.respostas` e `campos.reunioes`.

## 8. Regras duras

- Nada enviado por esta skill. Nunca.
- Todo e-mail com endereço postal físico, forma de sair e cabeçalho verdadeiro.
- Opt-out atendido no mesmo dia e para sempre.
- Nada de lista sem fonte, de assunto que engana nem de domínio principal no cold.
- SMS e ligação automática para os EUA: fora (TCPA).
