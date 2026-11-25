---
name: arkos-garimpo-x
description: Garimpa no X (Twitter) posts de empresas e empresários PEDINDO um prestador — "preciso de alguém que programe", "procuro editor de vídeo", "alguém indica dev", "looking for a developer", "hiring a video editor" — em português e inglês. Confere cada post no dado público do próprio X, classifica serviço, urgência, sinal de orçamento, porte e recência, descarta recrutador, agência revendendo, prestador se oferecendo e spam, dá nota 0-100 (rubrica do first-customer-finder) e escreve um rascunho de abordagem. Nunca envia, curte, segue nem responde. Use em "achar cliente no X", "quem está pedindo dev/editor", "garimpo no Twitter", "leads no X", "pedidos de freelancer".
status: instalada (2026-11-23)
versao: 1.1.0
modulos: [growth, oferta, operacao]
depende_de: [first-customer-finder]
---

# arkos-garimpo-x

## Passos

1. **Escolher os serviços** que o prestador vende: `dev`, `video`, `design`, `trafego`, `social` (um ou mais).
2. **Rodar** (as chaves só passam pelo `chaves.py` da pasta `_tools`):
   `python scripts/garimpo_x.py buscar --tools <pasta _tools da ARKOS> --servicos dev,video --saida workspace/<cliente>/<projeto>/garimpo-x/`
   Janela padrão: **7 dias** quando o Apify (`x.py`) trouxe post, 30 dias só com o Google; `--dias N` manda.
   O script chama `pesq.py google <mod> "<consulta>" x.com` (Google `site:x.com`, últimos 12 meses) e `x.py` (Apify). Com o Apify travado no plano grátis, use `--sem-x`: o Google sozinho já traz os links.
3. **Ler `garimpo.md`**: tabela por nota, o post citado, as dimensões da nota, o rascunho e os descartados com o motivo.
4. **O dono decide** post a post se responde. Responder, mandar DM ou seguir é ação dele, fora desta skill.

## Como decide

- **Conferência no original.** Cada link passa pelo dado público do embed do X (`cdn.syndication.twimg.com/tweet-result`): texto, autor e data. Post apagado, privado ou com autor diferente do link sai da lista. Trecho de busca nunca conta como prova.
- **Data exata pelo id.** O id do post já carrega a data (snowflake do X); não depende do que o Google mostra.
- **Filtros:** pergunta retórica ("why are companies hiring editors?"), recrutador ou vaga (CLT, salário, full-time), frase negativa ("não precisa de dev"), "developer" de imóvel (incorporadora), verbo de pedido longe do serviço, agência revendendo (white label, "para nossos clientes"), prestador se oferecendo ("estou disponível", "hire me"), spam (cripto, sorteio, renda extra), pedido sem verbo de pedido e serviço fora dos escolhidos.
- **Nota 0-100** (first-customer-finder): dor 25 (pedido explícito; 5 com urgência ou orçamento), fit 25 (serviço único casado), timing 20 (até 3 dias = 5, 7 = 4, 14 = 3; **mais de 14 dias perde nota**: 1 até 45 dias, 0 depois), alcance 15 (empresa = 5, criador = 4, pessoa = 2) e evidência 15 (conferido = 5). Abaixo de 50 não entra. Faixas: 80+ forte, 65-79 promissor, 50-64 plausível.
- **Alvo é empresa/empresário:** consultas próprias ("minha empresa", "meu negócio", "for my startup/agency/store", "my saas") e porte "empresa" (fundador, dono de negócio, loja, SaaS, agência, clínica, empreendedor) com alcance 5; pessoa sem sinal fica com 2.
- **Criador de conteúdo é categoria separada** (meu canal, cortes, podcast, streamer), com tabela e ordem próprias abaixo das empresas (alcance 4).
- **Rascunho personalizado:** cita o trecho do post que diz o que a pessoa procura, acrescenta o detalhe pedido (cortes, motion, site da loja, app, automação, MVP, Shopify...) e só fala de prazo ou orçamento se o post falou.

## Regras duras

1. **Nunca envia.** Nenhuma chamada de escrita no X: sem resposta, DM, curtida, follow ou lista.
2. **Só dado público**, sem login, sem contornar bloqueio. Nada de e-mail ou telefone pessoal.
3. **Rascunho com menos de 90 palavras**, só com o que está no post; nada de intimidade fingida. Rótulo: "potencial cliente por sinal público".
4. **Custo:** Oxylabs por busca no Google (1 por consulta) e Apify no `x.py` (grátis trava com `noResults`). Sem chave, o script para com código 3.
5. A entrega vai para `workspace/`, nunca para `arkos.engine/`.

## Pronto quando

- todo post da lista tem link conferido, data, nota com as dimensões e rascunho;
- todo descartado tem motivo;
- `garimpo.md` diz "Nada foi enviado".

## Exceções

- **entrada_incompleta:** serviço fora da lista. Devolve código 3 e pergunta.
- **fora_do_ar:** sem a pasta `_tools` (chaves.py + pesq.py). Código 3.
- **resultado_ruim:** lista vazia. Amplie `--dias`, acrescente o idioma ou outro serviço; não baixe a nota mínima.

## Testes

`python -m unittest discover -s scripts/tests`: 8 testes sem rede, com conferência simulada. Cobrem pedido real com urgência e orçamento (nota 80+), post em inglês com rascunho em inglês, recência acima de 14 dias, recrutador, prestador se oferecendo, spam, agência revendendo, serviço fora, frase negativa ("you don't need a developer"), "developer" de imóvel, vaga com salário, link não conferido, autor trocado, data pelo id, serviço inválido, falta de `_tools` a recusa de saída no engine, a ordem empresa > pessoa > criador, o rascunho que cita o pedido (trecho com o serviço, em 2ª pessoa), a pergunta retórica descartada e a janela de 7 dias com Apify.
