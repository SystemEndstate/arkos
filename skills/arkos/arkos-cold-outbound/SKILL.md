---
name: arkos-cold-outbound
description: Cold outbound B2B no Brasil (e geral, fora dos EUA) pela ARKOS, dentro da LGPD — avaliação de legítimo interesse (LIA) registrada, lista limpa por script (supressão, sem fonte, endereço de função, e-mail pessoal, duplicado, lead dos EUA ou da UE separado), infraestrutura do domínio de envio (SPF, DMARC, aquecimento), sequência em PT-BR conferida por script e rascunhos montados lead a lead. Nunca envia: entrega ao arkos-guarda-envio. Use em "cold email", "prospecção por e-mail", "outbound no Brasil", "sequência de abordagem", "limpar a lista de leads", "legítimo interesse", "LIA".
status: rascunho
versao: 0.1.0
modulos: [5, 8, K]
depende_de: [arkos-outbound-eua, arkos-guarda-envio, arkos-intake, arkos-perfil, arkos-lead-merge, arkos-gate]
substitui: coldoutbound (sem fonte livre; implementação própria, escrita do zero)
---

# arkos-cold-outbound

**Divisão com a `arkos-outbound-eua`:** esta é dona de **Brasil e geral** (LGPD, PT-BR); a da Flauta é dona dos **EUA** (CAN-SPAM, inglês). Lead dos EUA que aparecer aqui sai num arquivo separado para lá; a sequência com `mercado: EUA` é delegada. União Europeia fica fora (GDPR, base legal por país). As duas **nunca enviam**: o lote vai como rascunho ao `arkos-guarda-envio`.

Reusa da irmã (`arkos-outbound-eua/scripts/canspam.py`): leitor de CSV, validação de e-mail, endereços de função e a rampa de aquecimento por caixa. A regra legal aqui é outra, então os filtros de mercado e a LIA são próprios.

## Pasta-casa

`workspace/<cliente>/<projeto>/outbound/`: `lote-<data>.csv` (pode enviar hoje), `-fora.csv` (com o motivo), `-para-outbound-eua.csv`, `-lia.json` e `rascunhos-<data>.csv`. Supressão comum: `arkos.engine/supressao.csv` da casa (ou `--supressao`).

## Comandos

```bash
py -3 scripts/outbound_br.py lote leads.csv --lia lia.json --caixas 2 --dia 1 --casa C --cliente X --projeto Y
py -3 scripts/outbound_br.py conferir sequencia.json
py -3 scripts/outbound_br.py montar sequencia.json <lote.csv> --casa C --cliente X --projeto Y
py -3 scripts/outbound_br.py dns dominio-de-envio.com.br
```

Exemplos em `_comum/`: `leads-br.csv`, `lia.json`, `sequencia-br.json`.

## Passos

1. **LIA** (avaliação de legítimo interesse), uma por campanha: `finalidade`, `necessidade` (só os dados mínimos), `expectativa_do_titular` (o contato é sobre a empresa dele, no e-mail da empresa) e `salvaguardas` (frequência, saída, supressão). Sem LIA o `lote` não roda.
2. **Infraestrutura:** domínio secundário parecido com o principal, nunca o principal; SPF, DKIM e DMARC (`p=none` no começo); caixas com nome de pessoa; aquecimento pela rampa da irmã. `dns` confere SPF e DMARC.
3. **Lote:** `lote` limpa a lista e corta no teto do dia.
4. **Sequência:** 3 a 5 toques (os principais por e-mail) ao longo de **3 a 5 semanas**; o **2º e-mail vem de 7 a 14 dias** depois do 1º. O 1º e-mail tem **de 25 a 75 palavras** (76 a 90 ainda passa com aviso; acima de 90 reprova), **uma** pergunta, sem link, diz de onde veio o contato (`{{fonte}}`) e traz personalização real além do nome (`{{gancho}}`); os follow-ups ficam **em até 90 palavras**. `conferir` até ficar verde.
5. **Rascunhos:** `montar` gera um rascunho por lead e por toque. Lead com campo faltando fica em `pendentes`, nunca sai com `{{campo}}` aberto.
6. **Envio:** só pelo `arkos-guarda-envio`, com o "sim" de uma pessoa. Quem pede para sair entra na supressão no mesmo dia.

## Regras duras

- Sem LIA preenchida, sem lote.
- Fora do lote: e-mail inválido, duplicado, na supressão (inclusive `@dominio`), sem `fonte`, endereço de função (`contato@`, `vendas@`, `info@`…), EUA e UE.
- **E-mail pessoal** (`gmail`, `hotmail`…) fica de fora, **salvo** se o próprio titular o publicou como contato do negócio (site, Perfil da Empresa, cartão de CNPJ/MEI): aí o CSV traz `publicado_titular` (URL) e `data_publicacao`, e a base **não pode** ser comprada nem de enriquecimento (`apollo`, `lusha`, raspagem…). Fora disso é pessoa física e o legítimo interesse B2B não cobre.
- Todo toque: remetente com nome e empresa, assunto até 50 caracteres sem `Re:`/`Enc:`/"boleto" falso, e a saída fácil ("se não quiser mais receber, responda SAIR"), que atende o direito de oposição da LGPD (art. 18).
- WhatsApp só com opt-in registrado e dentro da janela de 24 h (regra do `arkos-guarda-envio`).
- Nunca envia. Nunca compra lista.

## Pronto quando

`conferir` verde na sequência, `lote` com status `ok` e `montar` sem `pendentes`. O lote e os rascunhos estão na pasta-casa, prontos para o `arkos-guarda-envio`.

## Exceções

- `entrada_incompleta`: sem CSV, sem coluna `email`, LIA incompleta ou sequência sem `remetente`/`toques`. Código 2 e a lista; nenhum arquivo escrito.
- `fora_do_ar`: sem a skill irmã `arkos-outbound-eua` (o reuso some), ou `nslookup` falhou. Código 3.
- `delegar`: sequência com `mercado: EUA` vai para a `arkos-outbound-eua`.

## Pendências

- Ligar nos playbooks (Flauta, `vinculos.mjs`): `mineracao-clientes`, `conversa-abordagem`, `primeiros-clientes`.
- DKIM depende do seletor da ferramenta de envio: conferir no painel dela.
