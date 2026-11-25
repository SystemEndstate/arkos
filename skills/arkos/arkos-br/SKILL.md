---
name: arkos-br
description: Camada de contexto Brasil que as skills globais (em inglês e centradas nos EUA) leem antes de produzir para o mercado brasileiro - Pix, parcelamento, boleto, CPA em real, sazonalidade (Black Friday, 11.11, Dia das Mães, 13º), LGPD em pixel e CAPI, CDC, CONAR, CNAE e Simples, tom pt-BR. Use sempre que o mercado do perfil for BR e a tarefa for copy, anúncio, oferta, e-commerce, conteúdo, SEO local ou finanças.
status: rascunho
versao: 0.1.0
modulos: [6, 7, 8, J, M, 10, 4]
depende_de: [arkos-mercado]
---

# arkos-br

Não substitui as skills do pacote: **adapta** o que elas produzem. Ordem de uso: skill global faz o rascunho → `arkos-br` revisa com o checklist abaixo → gate (humanizer-pt-br + antislop).

## Checklist de adaptação

| Tema | Regra |
|---|---|
| Moeda e números | R$ com vírgula decimal (R$ 1.297,00); nunca "$"; CPA e ROAS em real |
| Pagamento como argumento | Pix (à vista com desconto), parcelamento no cartão ("12x de R$ 108,08"), boleto; deixar claro se tem juros |
| Garantia | Venda online: arrependimento de 7 dias (CDC art. 49) é direito, não bônus. A garantia da oferta vai **além** disso |
| Linguagem | Informal sem gíria forçada; "você"; sem tradução literal ("game changer", "no-brainer"); passar por `humanizer-pt-br` |
| Infoproduto | Vocabulário: lançamento semente, interno e perpétuo; low ticket; "fundo de funil"; aula gratuita; CPL |
| Sazonalidade | Black Friday (novembro, CPM alto), 11.11, Dia das Mães (maio), Dia dos Namorados (12/06), Natal, 13º salário (nov/dez), volta às aulas (jan/fev), Carnaval (vale de B2B) |
| Anúncio | Meta reprova no BR: promessa de renda, antes/depois, saúde, "você" apontando atributo pessoal. CONAR: não enganar, identificar publicidade |
| Tracking | LGPD em pixel e CAPI: aviso de cookies, base legal, minimização; hash do e-mail e telefone no CAPI |
| WhatsApp | É o canal de fechamento, mas só com opt-in (ver arkos-mercado). CTA "chama no WhatsApp" aponta para wa.me da empresa (o lead inicia) |
| Empresa | CNAE, Simples Nacional (anexos e faixas), MEI (limite de faturamento), nota fiscal de serviço; suporte por WhatsApp esperado |
| SEO local | Google Business Profile em pt-BR, Reclame Aqui, diretórios (Apontador, TeleListas, Guia Mais), iFood/Doctoralia conforme o nicho |

## Conteúdo exclusivo

Benchmarks de CAC no Brasil, sazonalidade de CPM por nicho e o padrão da casa ficam no `arkos-base` (consulta por trecho). Esta skill local só tem as regras públicas acima.

## Pendências

- Popular a base com os benchmarks (buraco de conteúdo do MAPA).
- Confirmar com o dono a lista de nichos e as particularidades que a casa já domina.
