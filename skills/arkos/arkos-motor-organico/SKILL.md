---
name: arkos-motor-organico
description: Motor de conteúdo orgânico da ARKOS ligado aos fluxos. Define pilares e mix de funil, gera por script o calendário (Reels, TikTok, carrossel, stories) em que todo post tem um CTA apontando para um fluxo da ARKOS (isca no site-landing, conversa no agente-sdr, loja/vitrine), escreve ganchos e roteiros e lê as métricas para achar os vencedores, que viram Spark Ads ou anúncio. Use em "conteúdo orgânico", "calendário de posts", "o que postar", "crescer o perfil", "motor de conteúdo", "Reels e TikTok", "linha editorial", "organic content engine", "content calendar".
status: instalada (promovida em 2026-11-22)
versao: 0.1.0
modulos: [5, 7, 8, E]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-gate, arkos-guarda-escrita, arkos-mecanismo, jev]
fontes_conferidas_em: 2026-11-22
---

# arkos-motor-organico

**Princípio:** conteúdo que não leva a lugar nenhum é hobby. No motor da ARKOS **todo post tem um próximo passo** que cai num fluxo que já existe (isca, conversa, loja, agenda), e o que funciona no orgânico vira anúncio. O calendário sai do script; o Claude escreve.

## 1. Quando usar e quando não usar

**Usar:**
- Playbook `conteudo-organico` (o `social-content` faz a etapa e este motor dá o calendário e o elo com os fluxos).
- Toda esteira que precisa de demanda sem verba (serviço local BR, infoproduto, agência OaaS) e a vitrine de loja.
- Leitura mensal das métricas do perfil para decidir o que repetir e o que vira anúncio.

**Não usar:**
- Post avulso: `post-writer-sms`, `caption-writer-sms` ou `carousel-writer-sms` direto.
- Gestão de comunidade e resposta de DM em tempo real: é atendimento (`agente-sdr`).
- Publicação automática sem aprovação: publicar é escrita externa (seção 6).

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: cliente, pergunta: "Cliente (slug)", obrigatoria: true }
- { id: projeto, pergunta: "Projeto (slug, padrão organico-<AAAA-MM>)", obrigatoria: true }
- { id: plataformas, pergunta: "Plataformas", opcoes: [instagram, tiktok, youtube-shorts, linkedin, kwai], obrigatoria: true }
- { id: capacidade, pergunta: "Quantos posts por semana o cliente consegue gravar e aprovar de verdade?", padrao: 3, obrigatoria: true }
- { id: semanas, pergunta: "Horizonte do calendário em semanas", padrao: 4, obrigatoria: true }
- { id: fluxos, pergunta: "Para onde cada etapa leva: topo (seguir/salvar), meio (isca/landing), fundo (conversa/loja/agenda)", obrigatoria: true }
- { id: metricas, pergunta: "Export de métricas dos últimos 30 a 90 dias (CSV), se houver", obrigatoria: false }
```

**Pasta das entregas:** `workspace/<cliente>/<projeto>/organico/` (`plano.json`, `calendario.csv`, `calendario.json`, `roteiros.md`, `leitura-<data>.json`).

## 3. Passos

1. **Ler o que já existe:** com métricas, rodar `motor.py ler` primeiro e usar os pilares e formatos vencedores. Sem métricas, partir do perfil (ICP, dores, mecanismo) e de 3 perfis de referência (`creator-profile-teardown`). *Script + skill.*
2. **Pilares:** de 3 a 5, cada um ligado a uma dor ou desejo do ICP e a uma prova que o cliente tem (bastidor, antes e depois, dúvida frequente, opinião contra o mercado, caso). Peso maior para o que já performa. *Claude.*
3. **Mix de funil:** padrão topo 60%, meio 30%, fundo 10%. Fundo nunca passa de 25% (heurística do script: perfil que só vende para de crescer). *Claude.*
4. **Ligar cada etapa a um fluxo** (obrigatório, o script recusa sem isso):
   - topo: seguir, salvar ou compartilhar (fluxo `conteudo-organico`);
   - meio: palavra-chave no comentário ou link para a isca (fluxo `site-landing` ou `lead-magnets`);
   - fundo: direct, WhatsApp ou loja (fluxos `agente-sdr`, `conversa-abordagem` ou o fluxo de loja).
   *Claude.*
5. **Calendário:**
   ```
   python ~/.claude/skills/arkos-motor-organico/scripts/motor.py calendario workspace/<cliente>/<projeto>/organico/plano.json \
     --out .../organico/calendario.csv --json .../organico/calendario.json
   ```
   O script distribui pilares, formatos, plataformas e etapas sem repetir pilar 3 vezes seguidas e respeitando a capacidade. *Script.*
6. **Gancho e roteiro:** para cada post, gancho (`hook-writing`, `hook-tactics`), roteiro por cena com o tempo para vídeo, texto por lâmina para carrossel, e o CTA do fluxo. Promessa passa pela checagem do `mecanismo.py`. Gravar no `calendario.json` (campos `gancho` e `roteiro`). *Claude.*
7. **Pronto:** `motor.py pronto calendario.json` (todo post com CTA e fluxo, com gancho, vídeo com roteiro, fundo dentro do limite). *Script.*
8. **Aprovação e agenda:** o cliente aprova o lote. Agendar (instaflow ou manual) só depois do `arkos-guarda-escrita`. *Skill.*
9. **Leitura mensal:**
   ```
   python ~/.claude/skills/arkos-motor-organico/scripts/motor.py ler <metricas.csv> --out .../organico/leitura-<AAAA-MM-DD>.json
   ```
   Nota por post: salvos + compartilhamentos pesam mais que curtida. Os 20% de cima são vencedores: repetir o ângulo em outro formato e mandar ao `lote-criativos` como Spark Ads (TikTok) ou impulsionamento. *Script + Claude.*

## 4. Critério de pronto

- [ ] Pilares ligados a dor do ICP e a prova existente.
- [ ] Todo post do calendário tem etapa, CTA e fluxo da ARKOS; o calendário saiu do script.
- [ ] A cadência cabe na capacidade que o cliente declarou.
- [ ] Todo vídeo tem gancho e roteiro; todo carrossel tem texto por lâmina.
- [ ] O `motor.py pronto` deu verde.
- [ ] Com métricas: os vencedores foram listados e encaminhados ao `lote-criativos`.
- [ ] Tem "o que eu faria nesta semana" e "o que pode matar isto".

## 5. Exceções, custo e escrita externa

- **Etapa sem fluxo ou fundo acima de 25%** (`entrada_incompleta`): o script recusa. Definir o fluxo ou rebalancear o mix.
- **Menos de 5 posts com alcance no export:** a leitura não roda; montar o calendário pelo passo 1 sem métricas.
- **Cliente não grava:** reduzir a cadência (o script usa a capacidade) e trocar para formatos sem rosto (carrossel, tela gravada, depoimento de cliente com autorização).
- **Publicar ou agendar** (instaflow, Meta Business Suite, TikTok): passa pelo `arkos-guarda-escrita` com a prévia do lote. Regra da casa no Instagram: Reels com legenda feita a partir do conteúdo do vídeo, mostrada antes de subir.
- **Rollback:** cancelar o agendamento (`cancel-pst` no instaflow) ou arquivar o post publicado. Apagar post só com OK.
- **Custo:** o motor é grátis. Ferramenta de agendamento paga ou impulsionamento passam pelo portão `confirmacao_custo`.
- **Comentário com dado pessoal** num post: não copiar para o relatório (LGPD/GDPR).

## 6. Alimenta

- **Perfil:** pilares vencedores e a cadência real.
- **Swipe:** posts vencedores com gancho e números.
- **Anúncios:** os vencedores vão para `arkos-tiktok-ads` (Spark Ads), `arkos-kwai-ads` e o `lote-criativos`.
- **Aprendizado:** pilar × formato × nota em `arkos.engine/aprendizado.jsonl`.
- **Esteira:** `saida.json` com `campos.calendario`, `campos.vencedores` e `campos.proxima_leitura`.

## 7. Regras duras

- Post sem CTA ligado a fluxo não entra.
- Calendário e classificação de vencedores vêm do script.
- Nada publicado sem aprovação e sem `arkos-guarda-escrita`.
- Nada de comprar seguidor, engajamento ou view, nem grupo de engajamento.
- Rosto, voz ou caso de cliente só com autorização por escrito.
