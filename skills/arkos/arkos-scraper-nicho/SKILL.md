---
name: arkos-scraper-nicho
description: Lista de negócios de um nicho numa cidade, estado ou país com WhatsApp comercial público, e-mail, site, Instagram, endereço e CNPJ (BR), com prévia grátis, confirmação de custo com teto, validação offline de WhatsApp e registro de origem. Use quando o usuário pedir "nicho X em tal lugar", "minerar clientes", "lista de leads", "contatos de dentistas em BH", "lead list of gyms in Austin".
status: rascunho
versao: 0.1.0
modulos: [5, 9, K, 13]
depende_de: [arkos-intake, arkos-mercado, arkos-lead-merge, Apify MCP, radar-cnpj-mcp]
---

# arkos-scraper-nicho

Desenho completo na pesquisa 11 (§5). Aqui fica o roteiro operacional.

## 1. Entradas (via arkos-intake, nesta ordem)

nicho · local · mercado (BR/EUA; EU = EUA + GDPR) · quantidade (padrão 200) · canais pretendidos (padrão e-mail + DM) · motor (Apify padrão, gosom grátis, Outscraper volume) · destino (CSV padrão, CRM).

**Custo (decisão do usuário, 2026-11-21):** não há teto. A skill **estima o custo e pergunta**; quem decide gastar é o prestador. Plano Apify grátis ou pago, tanto faz.

## 2. Pipeline

`Maps → Site → Contato → (Instagram opcional) → WhatsApp offline → CNPJ (BR) → arkos-lead-merge → CSV/CRM`

| Etapa | Ferramenta padrão | Regra |
|---|---|---|
| Maps | `compass/crawler-google-places` + add-on "Company contacts enrichment" | **Desligar** add-ons de leads, verificação e social (US$ 0,10 cada no Free) |
| Site | `vdrmota/contact-info-scraper` (campo `whatsapps`), até 3 páginas, só para quem saiu sem e-mail ou sem wa.me | ou Jina Reader + regex `wa\.me/(\d+)`, `api\.whatsapp\.com/send\?phone=(\d+)` |
| Contato | regras determinísticas, sem LLM | tirar e-mail de plataforma (wix, sentry, exemplo@) |
| Instagram | `memo23/instagram-email-phone-scraper` (só cobra o contato achado) | opcional; só conta comercial |
| WhatsApp | `libphonenumber` local: E.164, MOBILE ou FIXED_LINE; selo `wa_fonte` = `publicado` / `celular_publicado` / `fixo` / `nenhum` | **consulta ao vivo desligada** |
| CNPJ (BR) | `radar-cnpj-mcp` | situação ATIVA, CNAE, porte, MEI; sem QSA, sem sócio |

## 3. Passo a passo

1. Entradas num bloco só.
2. Ficha do mercado (`arkos-mercado`).
3. **Prévia grátis**: Maps com `maxCrawledPlaces = 20` (< US$ 0,20). Mostrar amostra e taxa real de site, e-mail e celular; recalcular o custo.
4. **Informar o custo e perguntar (obrigatório):**
   > Vou buscar ~N negócios de <nicho> em <local>. Custo estimado: US$ X (plano Apify atual: <plano>). Etapas ligadas: … Consulta ao vivo de WhatsApp: **desligada**. Sigo? (Opções mais baratas: motor gosom grátis, sem Instagram, menos leads.)

   Sem "sim" explícito, nada pago roda. A decisão é do prestador.
5. Executar. Um contador entre as etapas mostra o custo real gasto; se o real passar de 1,5× a estimativa, pausar e perguntar de novo. `maxTotalChargeUsd` só é usado se o prestador pedir um limite.
6. `arkos-lead-merge` (dedup, score, base legal, supressão).
7. Entregar CSV + `resumo.md` + `run.json`. O resumo termina com o **bloco de uso permitido** (pesquisa 11 §6.5).
8. Registrar uma linha no histórico do projeto no Obsidian (fonte, data, custo, LIA).

## 4. Custo de referência (1.000 leads, preços de 2026-11-21)

BR padrão ~US$ 8,4 (Free) / 7,4 (Starter); com Instagram ~US$ 10,7; EUA ~US$ 8,4 sem verificação; gosom US$ 0. O Free cobre ~600 leads/mês. **Estimativa:** a taxa real sai do piloto.

## 5. Nunca

- Disparar mensagem (isso é `arkos-conversa` + `arkos-guarda-envio`).
- Buscar grupos de WhatsApp, usar dado vazado (`eduair94`), sessão de WhatsApp, sócio ou CPF.
- Ligar a consulta ao vivo de WhatsApp sem aceite escrito do risco (fica no `run.json`).
- Mandar dado de lead em prompt de serviço de busca (`redact()` + `ignore.txt`).

## Pendências

- Piloto: 20 lugares × 3 nichos × 2 cidades para medir a taxa real.
- Ler o texto exato dos termos do Google Maps.
- radar-cnpj: scanner + local de download no disco D (~7 GB).
