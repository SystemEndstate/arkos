---
name: arkos-swipe
description: Biblioteca de referências (swipe file) da ARKOS - coleta anúncios, páginas, VSLs e e-mails vencedores (ad-library-teardown, apify, defuddle), cataloga numa ficha padrão (nicho, formato, gancho, ângulo, mecanismo, oferta, prova, CTA, por que funciona) e consulta pelo MCP arkos-base, que devolve só trechos. Use antes de escrever copy, criativo, roteiro ou abordagem ("me dá referências", "o que funciona no nicho X", "swipe"), e para cadastrar uma referência nova.
status: rascunho
versao: 0.1.0
modulos: [C, 7, 8, 13, J]
depende_de: [arkos-base (MCP), ad-library-teardown, obsidian:defuddle]
---

# arkos-swipe

O acervo é **conteúdo exclusivo**: ele vive no `arkos-base` e nunca vai inteiro para a máquina do prestador.

## Consultar (prestador e skills)

`swipe_buscar` (ferramenta do MCP `arkos-base`) com `nicho`, `formato` (anuncio, vsl, pagina, email, dm) e `angulo` opcional. Volta só a ficha resumida e **trechos relevantes**, nunca o original completo. Tamanho de trecho, quantidade e conteúdo **a definir** na pesquisa da base (decisão do usuário).

Uso pelas skills: `arkos-oferta`, `arkos-conversa`, copy e criativo chamam a busca **antes** de escrever e citam o `swipe_id` de cada referência usada. Copiar a estrutura, nunca o texto.

## Cadastrar (só o dono ou quem tiver papel `curador`)

1. Coletar: Meta Ad Library (`ad-library-teardown`), página (`defuddle`/`raspar`), funil de concorrente (`reverse-engineer-marketing`).
2. Preencher a ficha:

| Campo | Exemplo |
|---|---|
| `nicho`, `mercado` | odontologia estética, BR |
| `formato` | anúncio vídeo 9:16 |
| `gancho` | "Seu sorriso some na foto?" |
| `angulo` | vergonha social → solução rápida |
| `mecanismo` | lente de resina em 1 sessão |
| `oferta`, `prova`, `cta` | avaliação grátis · antes/depois com consentimento · "chama no WhatsApp" |
| `por_que_funciona` | 2–3 frases |
| `metricas_conhecidas` | tempo no ar, se for público |
| `fonte`, `capturado_em` | URL da biblioteca, data |

3. `swipe_cadastrar` no MCP (papel curador). A ficha passa pelo `clarity-gate` antes de entrar no RAG.

## Regras duras

- Nunca baixar o acervo, nem pedir "todas as fichas do nicho".
- Respeitar direito autoral: o swipe guarda análise e trechos curtos, não o criativo inteiro de terceiros.
- Sem dado pessoal de anunciante pessoa física.
