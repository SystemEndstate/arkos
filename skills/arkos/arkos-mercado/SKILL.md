---
name: arkos-mercado
description: Ficha por mercado (Brasil, EUA, Europa) com canais permitidos, leis (LGPD, CAN-SPAM, TCPA, GDPR), idioma, tom, fuso, moeda e horário de envio. Use sempre que um módulo de aquisição, copy, conversa, anúncio ou scraping precisar saber o que pode e o que não pode naquele mercado, e logo depois da pergunta "Mercado?" do arkos-intake.
status: rascunho
versao: 0.1.0
modulos: [5, 6, 8, 13, J, K, M, P]
depende_de: []
---

# arkos-mercado

Uma ficha por mercado, para que nenhuma skill repita regra. A ficha **não é aconselhamento jurídico**: é o padrão operacional da casa, montado a partir das pesquisas 07, 08, 10 e 11.

## Uso

`arkos-mercado ficha BR|EUA|EU [--pais DE|FR|...]` devolve o bloco abaixo. Skills que leem a ficha: arkos-intake, arkos-roteador, arkos-conversa, arkos-oferta, arkos-scraper-nicho, arkos-lead-merge, arkos-guarda-envio, arkos-br.

## Ficha BR

| Campo | Valor |
|---|---|
| Idioma e tom | pt-BR, caloroso, apresentação curta ("aqui é o X da Y"), "faz sentido?" |
| Moeda e pagamento | R$, Pix, parcelamento no cartão, boleto |
| Fuso e horário | America/Sao_Paulo; envio em dia útil, 9h–18h |
| Canal principal | Conversa: WhatsApp (**só com opt-in**) e Instagram DM (só para quem interagiu) |
| Canal secundário | E-mail com opt-out, ligação humana, LinkedIn (humano envia) |
| Lei | LGPD: legítimo interesse (art. 7º IX + art. 10) com LIA por campanha; origem e data por lead (art. 37); opt-out atendido (art. 18). Dado de MEI/autônomo é dado pessoal |
| WhatsApp | Opt-in obrigatório; abrir só com template aprovado; janela de 24 h; escalonamento para humano; agente de função de negócio (regra contra IA de uso geral desde 15/01/2026); só Cloud API ou BSP (Wame) |
| Consumidor | CDC art. 49: arrependimento de 7 dias em venda online; CONAR e políticas da Meta em anúncio |
| Fontes de lead | Apify Maps → site → CNPJ (radar-cnpj) |

## Ficha EUA

| Campo | Valor |
|---|---|
| Idioma e tom | en-US, direto, curto, sem hype; assunto de 2 a 4 palavras; CTA de interesse ("worth a look?") |
| Moeda | USD |
| Fuso e horário | fuso do lead; envio em dia útil, 8h–17h locais |
| Canal principal | **Cold email** com infraestrutura (domínio secundário, SPF/DKIM/DMARC, warmup) |
| Canal secundário | LinkedIn (humano envia), Instagram DM (só quem interagiu) |
| Lei | CAN-SPAM: cabeçalho verdadeiro, assunto que não engana, endereço postal válido, opt-out atendido em 10 dias úteis, sem exceção B2B, até US$ 53.088 por e-mail. TCPA: SMS e ligação automática para celular **desligados** (US$ 500 por violação); ligação só humana, conferindo a DNC. Leis estaduais (mini-TCPA) **não conferidas** |
| Fontes de lead | Apollo, Exa, Apify → Hunter → sellbird ou cold-email |

## Ficha EU

Igual à dos EUA, mais:

| Campo | Valor |
|---|---|
| Idioma | o local (DE, FR, ES, IT…); nada de inglês por padrão |
| Lei | GDPR + ePrivacy **por país**; legítimo interesse com LIA, ou consentimento quando o país exigir (ex.: Alemanha mais restritiva); lista de supressão; Consent Mode v2 antes de pixel e CAPI |
| Ferramenta | preferir lemlist (UE, OAuth) |
| Aviso | a matriz por país **precisa de validação jurídica** antes de virar regra |

## Regras duras

- Mercado sem ficha = a skill para e pergunta.
- Quando a ficha disser "desligado" (SMS e ligação automática nos EUA, WhatsApp sem opt-in no BR), nenhum playbook liga sem aceite escrito do dono, registrado no `run.json`.
- A ficha é lida, nunca editada, por skills de execução. Mudança de regra = mudança nesta skill, com data e fonte.

## Pendências

- Mini-TCPA estaduais e DNC (pesquisa 11, §7).
- Matriz GDPR por país (pesquisa 08, `arkos-outbound-europa`).
- Tabela atual de preço de template do WhatsApp no Brasil.
- Mover as fichas para a base na nuvem quando ela existir; a skill local só consulta.
