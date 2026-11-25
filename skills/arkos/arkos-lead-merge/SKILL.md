---
name: arkos-lead-merge
description: Junta leads de qualquer fonte (Apify, gosom, Outscraper, Serper, Apollo, Hunter, first-customer-finder, sellbird, CNPJ) num formato único da ARKOS, com dedup, normalização, score, base legal, origem, data, canais permitidos e lista de supressão. Use depois de qualquer coleta de leads e antes de mandar para CRM ou para arkos-conversa.
status: rascunho
versao: 0.1.0
modulos: [5, K, 13]
depende_de: [arkos-mercado]
---

# arkos-lead-merge

Script determinístico (`scripts/merge.py`, sem LLM no caminho principal) + esta skill que explica como chamar e como ler o resultado. Segue `guarda-regressao`: o script tem testes antes de entrar.

## Entrada

Uma ou mais pastas de bruto (`arkos.engine/execucoes/<id>/bruto/*.json|csv`) com `fonte` declarada, mais o mercado e a LIA da campanha.

## Passos (todos no script)

1. **Normalizar**: telefone → E.164 (`libphonenumber`, região do mercado); domínio do site sem `www` e sem caminho; e-mail em minúsculas; tipo de e-mail `dominio` ou `generico`.
2. **Dedup**, nesta ordem de chave: `place_id` → CNPJ → domínio → telefone E.164. Ao juntar, manter todos os valores em `fonte` (separados por `;`).
3. **Classificar pessoa física provável**: MEI, empresário individual ou nome próprio na razão social → `pessoa_fisica_provavel = true`.
4. **Score 0–100** (regra fixa da pesquisa 11 §5.2; ajuste só no retune com o Jev):
   +30 `wa_fonte=publicado` · +15 `celular_publicado` · +20 e-mail no domínio · +5 e-mail genérico · +10 site · +10 IG comercial · +10 CNPJ ATIVO · +5 nota ≥ 4 com ≥ 20 avaliações · −20 pessoa física provável (vai para revisão) · −100 opt-out.
5. **Canais permitidos** (da ficha do mercado): BR → `email,ligacao,dm`; WhatsApp só vira `whatsapp_template_optin` quando houver registro de opt-in. EUA → `email,ligacao_humana`.
6. **Base legal**: `legitimo_interesse:<id da LIA>`; sem LIA informada, o script para.
7. **Supressão**: aplicar `arkos.engine/supressao.csv` (e a da nuvem). Quem está lá sai do arquivo final e conta no resumo.
8. **Nicho ambíguo** (opcional): Jev `decide_many` "este negócio é mesmo do nicho X?" → `nicho_ok` com a probabilidade.

## Saída

`leads_<nicho>_<local>_<AAAA-MM-DD>.csv` (UTF-8 com BOM) com os campos da pesquisa 11 §5.4: `lead_id`, `nome`, `categoria_maps`, `nicho_ok`, endereço completo, `telefone_e164`, `whatsapp_e164`, `wa_fonte`, `wa_link`, `email`, `email_tipo`, `site`, `instagram`, CNPJ (`cnpj`, `razao_social`, `situacao`, `cnae`, `porte`, `mei`), `pessoa_fisica_provavel`, `score`, `canais_permitidos`, `fonte`, `coletado_em`, `base_legal`, `optout`.

Mais `resumo.md` (contagens, taxa de preenchimento por campo, removidos por dedup e por supressão) e o bloco de uso permitido.

## Regras duras

- Nunca guardar sócio, CPF, foto ou dado de vazamento.
- `lead_id` estável entre execuções (hash da chave de dedup).
- Lead sem `fonte` ou `coletado_em` não entra.

## Pendências

- Formato de importação para os CRMs do módulo K (HubSpot, Pipedrive, RD).
- Testes com dados sintéticos (nunca leads reais no repositório).
