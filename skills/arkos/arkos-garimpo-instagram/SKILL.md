---
name: arkos-garimpo-instagram
description: Acha empresas de um nicho numa cidade pelo Instagram (dado público, sem login) e mede sinais de oportunidade — posta muito com pouco engajamento, bio sem link de venda, site ruim ou sem site, nenhum anúncio ativo na Biblioteca de Anúncios da Meta, comentários sem resposta. Dá nota 0-100, diagnóstico e o que oferecer a cada uma. Avisa o custo antes de gastar (Apify grátis é limitado) e nunca contata ninguém. Use em "achar clientes no Instagram", "empresas de <nicho> em <cidade>", "prospecção local", "quem precisa de site/tráfego", "garimpo no Instagram".
status: instalada (2026-11-23)
versao: 1.1.0
modulos: [growth, oferta, trafego, design]
depende_de: []
---

# arkos-garimpo-instagram

## Passos

1. **Nicho e cidade** (ex.: "clínica odontológica", "Campinas") e, se der, sinônimos (`--sinonimos "dentista,odontologia"`), ou uma lista pronta de perfis (`--perfis a,b`). **Amostra mínima: 20 perfis** por nicho (`--n` abaixo disso sobe para 20); se o Google não render 20, o relatório avisa.
2. **Ver o custo:** `python scripts/garimpo_ig.py buscar --tools <pasta _tools> --nicho "..." --cidade "..." --n 10 --saida workspace/<cliente>/<projeto>/garimpo-instagram/`. Sem `--confirmar-custo` o script só imprime a estimativa e para (código 3).
3. **Mostrar a estimativa ao usuário** e, com o OK, rodar de novo com `--confirmar-custo` (e `--comentarios` se ele quiser medir comentários sem resposta, que custa mais).
4. **Ler `garimpo.md`**: tabela por nota, diagnóstico por perfil, o que oferecer e os descartados.

## De onde vem cada sinal

| Sinal | Fonte | Observação |
|---|---|---|
| Perfis do nicho | `pesq.py google` com `site:instagram.com` | pega `instagram.com/<perfil>/` e o `(@perfil)` do título |
| Seguidores, posts, link da bio, categoria | `apify~instagram-profile-scraper` (12 posts recentes) | ator oficial da Apify |
| Engajamento | (curtidas + comentários) ÷ seguidores, média dos posts recentes | |
| Site | GET público no link da bio: status, https, viewport (mobile), tempo | sem formulário, sem login |
| Anúncios ativos | Biblioteca de Anúncios da Meta, busca pelo nome (sem letra estilizada nem emoji), via `pesq.py adlib` | busca por palavra-chave: "0" entra na nota; número maior pode ser de outras empresas e não entra |
| Comentários sem resposta | `apify~instagram-comment-scraper` em até 3 posts (só com `--comentarios`) | conta resposta aninhada do perfil ou comentário dele marcando o cliente; se o ator não trouxer respostas, fica "não medido" e não entra na nota |

## Nota de oportunidade (0-100)

Sem link na bio **25** · site com problema (fora do ar, sem https, sem mobile, mais de 4 s) **25** · bio só com WhatsApp ou agregador **15** · nenhum anúncio ativo **20** · posta muito (8+ em 30 dias) com engajamento abaixo de 0,5% **20** (só engajamento baixo: 10) · 70%+ dos comentários recentes sem resposta **10** · conta ativa (post nos últimos 90 dias) **10** · **conta parada (sem post em 90 dias) perde 20** (piso 0).

Os limiares (`LIM` no script) são cortes operacionais padrão, **a confirmar com o dono**; não são benchmark de mercado. Descarta conta privada, perfil que não abriu, marca grande (mais de 100 mil seguidores, fora do porte) e **conta minúscula** (menos de 300 seguidores; `--min-seguidores N` muda).

**O que oferecer** sai do diagnóstico: sem site ou site ruim → site/landing (`arkos-site`); só WhatsApp ou agregador → landing de oferta; sem anúncio → tráfego pago Meta; engajamento baixo → conteúdo e criativos; comentários sem resposta → atendimento e resposta automática.

## Regras duras

1. **Custo antes.** Nada de Apify ou Oxylabs sem `--confirmar-custo`, e esse só depois do OK do usuário.
2. **Só dado público**, sem login. Nada de curtir, seguir, comentar, mandar DM ou extrair e-mail ou telefone pessoal.
3. **Sem número inventado:** sinal que não deu para medir fica "-" e não soma nota.
4. A entrega vai para `workspace/`, nunca para `arkos.engine/`.

## Pronto quando

- todo perfil tem nota, diagnóstico e o que oferecer, com os sinais medidos;
- todo descartado tem motivo;
- `garimpo.md` diz "Ninguém foi contatado".

## Exceções

- **aguardando_confirmacao:** sem `--confirmar-custo`. Mostra a estimativa e para (código 3).
- **entrada_incompleta:** sem nicho e cidade nem `--perfis`. Código 3.
- **fora_do_ar:** sem a pasta `_tools`. Código 3.
- **resultado_ruim:** nenhum perfil achado. Troque o nicho (singular, termo do cliente) ou a cidade.

## Testes

`python -m unittest discover -s scripts/tests`: 6 testes sem rede, com perfis no formato do Apify. Cobrem a nota e o diagnóstico de cada sinal (sem link, site ruim, sem anúncio, posta muito com engajamento baixo, comentários sem resposta, conta parada), o descarte de marca grande, conta privada e perfil quebrado, a leitura dos perfis no resultado do Google, o nome limpo para a Biblioteca de Anúncios, o comentário "não medido" fora da nota, o "nada gasto sem confirmar custo", a falta de nicho, a recusa de saída no engine, a conta parada perdendo nota, a conta minúscula (limiar configurável) e a amostra mínima de 20.
