---
name: arkos-tiktok-ads
description: TikTok Ads na ARKOS. Monta a estrutura de campanha (manual ou Smart+), o portfólio de criativos nativos (gancho nos 2 primeiros segundos, depoimento com pessoa real falando com a câmera, Spark Ads com código de autorização do criador) e lê o export do Ads Manager por script, com uma decisão por anúncio (escalar, manter, pausar, trocar criativo, aguardar). Use em "TikTok Ads", "anunciar no TikTok", "campanha no TikTok", "Spark Ads", "impulsionar vídeo de criador", "ler métricas do TikTok", "hook rate", "TikTok ad structure", "Smart+ campaign", "TikTok export".
status: instalada (promovida em 2026-11-22)
versao: 0.1.0
modulos: [6, 7, E]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-gate, arkos-guarda-escrita, arkos-oferta, jev]
fontes_conferidas_em: 2026-11-22
---

# arkos-tiktok-ads

**Princípio:** no TikTok o criativo é a segmentação. A conta ganha com **portfólio de hipóteses** (ângulos diferentes que resolvem motivações diferentes), não com 10 variações de cor do mesmo vídeo. E a decisão de pausar ou escalar sai do **script**, nunca do olho.

## 1. Quando usar e quando não usar

**Usar:**
- Etapas de TikTok dos playbooks `campanha-nova`, `otimizar-campanha` e `lote-criativos`.
- Leitura semanal de uma conta TikTok a partir do export CSV do Ads Manager.
- Planejar Spark Ads com vídeo de criador ou do próprio perfil (vem do `arkos-motor-organico` quando um post orgânico vence).

**Não usar:**
- Venda dentro do próprio app/loja do TikTok: fora desta skill.
- Kwai: `arkos-kwai-ads`. Meta e Google: skills `*-meta-ads` e `*-google-ads`.
- Mexer na conta do cliente na fase 1: aqui só se **planeja e lê**. Criar, pausar ou mudar orçamento é escrita externa (seção 6).

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: cliente, pergunta: "Cliente (slug)", obrigatoria: true }
- { id: projeto, pergunta: "Projeto (slug, padrão tiktok-<AAAA-MM>)", obrigatoria: true }
- { id: modo, pergunta: "O que fazer?", opcoes: [estrutura-nova, ler-export, portfolio-criativo, spark-ads], obrigatoria: true }
- { id: objetivo, pergunta: "Objetivo", opcoes: [vendas, leads, trafego, app, alcance], obrigatoria: true }
- { id: cpa_alvo, pergunta: "CPA alvo (ou CPL) na moeda da conta", perfil: numeros.cpa_alvo, obrigatoria: true }
- { id: roas_alvo, pergunta: "ROAS alvo (se for venda)", obrigatoria: false }
- { id: export, pergunta: "Caminho do CSV exportado do Ads Manager (nível anúncio, últimos 7 ou 14 dias)", obrigatoria: "se modo = ler-export" }
- { id: verba, pergunta: "Verba diária ou mensal aprovada", obrigatoria: "se modo = estrutura-nova" }
- { id: pixel, pergunta: "Pixel/Events API do TikTok instalado e disparando o evento de conversão?", opcoes: [sim, nao, nao-sei], obrigatoria: true }
```

**Pasta das entregas:** `workspace/<cliente>/<projeto>/midia/tiktok/`.

## 3. O que a ARKOS sabe (conferido em 22/11/2026, Central de Ajuda TikTok Ads)

- **Spark Ads:** o criador gera o código de autorização nas configurações de anúncio do post, no app, e escolhe a duração (7, 30, 60 ou 365 dias). O anunciante cola o código no Ads Manager. Dá para autorizar até 20 códigos de uma vez. O Content Suite pede 365 dias por padrão.
- **Smart+:** a versão nova vale para os objetivos Vendas, Geração de leads e Promoção de app, com vários grupos de anúncio e orçamento no nível da campanha. A própria TikTok avisa que pode não estar liberado em todas as contas. **Histórico de conversão = 50+ eventos de conversão do pixel nos últimos 28 dias**; abaixo disso, campanha manual.
- **Os nomes dos menus mudam.** Conferir na Central antes de mandar o passo a passo ao prestador.
- **Os limiares de decisão do script são heurísticas da ARKOS**, não regra da plataforma. Ajustar por cliente com `--limiar`.
- **Teste é leitura de sinal, não campanha que escala.** A doc oficial pede orçamento de **10× o CPA** para um grupo sair da fase de aprendizado; **sem CPA histórico, o mínimo oficial é US$ 200/dia** na campanha de escala. O teste da ARKOS roda a **1–2× o CPA** só para, em 5–7 dias, separar o criativo que vende do que não vende; o CPA desse teste **não** é o CPA de escala (o grupo nunca saiu do aprendizado).
- **Escalar precisa de dado estável:** **25+ conversões** no grupo (doc oficial jun/2026: a oscilação cai depois de ~25 resultados ou 7 dias), ou 10+ conversões se o grupo tem **7+ dias** no ar (`--dias`). Antes disso, não escala.
- **Degrau de escala: 20–30%** a cada 48–72 h. O teto oficial é **50%** sem reentrar no aprendizado, com espera de **≥ 2 dias** entre mudanças; a ARKOS fica em 20–30% e só vai a 50% em data sazonal de intenção alta, com o grupo fora do aprendizado e registro do CPA de 24 h e 72 h depois de cada salto.
- **Pausar por CPA alto só fora da janela de aprendizado:** CPA > 1,5× o alvo pausa apenas com **7+ dias no ar ou 25+ resultados**; antes disso a decisão é **aguardar** (o aprendizado oscila ~7 dias). A regra de **0 conversão** (gasto ≥ 2× o CPA) continua sem prazo.
- **Gancho (taxa de 2 s):** mínimo **0,20**; com **10+ anúncios** no export, usa-se o relativo — abaixo de **0,75× a mediana da conta**.
- **Fadiga** = CTR ou taxa de 2 s caindo **≥ 30%** contra o export anterior (`--anterior`). A **frequência** é sinal **secundário**, só em retargeting (`--retargeting`, limite 2,0) e **experimental** até o `aprendizado.jsonl` confirmar. (O antigo `ctr_min` saiu: 0,6% era a própria mediana do e-commerce no TikTok.)
- **Virar Spark Ads (gatilho experimental):** vídeo no **top 10% de views em 48 h** da conta, com produto ligado, ou **10 mil+ views em 48 h**. Registrar o resultado para validar.

## 4. Passos

1. **Contexto:** ler perfil, oferta (`arkos-oferta`) e mecanismo (`arkos-mecanismo`). Sem oferta clara, parar e chamar a oferta: anúncio não conserta oferta. *Skill.*
2. **Rastreio antes de verba:** sem pixel ou Events API disparando o evento do objetivo, a etapa é `tracking-pixel`. Otimizar para clique "porque é mais barato" não é aceito. *Claude.*
3. **Estrutura** (modo `estrutura-nova`):
   - **Smart+** quando a conta tem histórico de conversão e o objetivo é venda, lead ou app;
   - **manual** quando a conta é nova, a verba é pequena ou é preciso isolar um teste;
   - 1 campanha por objetivo; teste de criativo em grupo separado do grupo que escala; não espalhar a verba em vários grupos pequenos.
   *Claude.*
4. **Portfólio de criativos** (modo `portfolio-criativo`):
   - de 3 a 5 **hipóteses** (ângulo + promessa + formato), cada uma ligada a uma motivação diferente do público;
   - cada hipótese tem de 2 a 3 execuções nativas (pessoa real falando com a câmera / depoimento, demonstração, antes e depois, reação, "3 erros");
   - gancho na fala **e** no texto da tela nos 2 primeiros segundos; legenda sempre; 9:16; sem cara de anúncio de TV;
   - roteiro por cena com o tempo. Os ganchos usam `hook-writing`, `hook-tactics` e `creative-mechanics`.
   *Claude.*
5. **Spark Ads** (modo `spark-ads`): lista de posts candidatos (os vencedores do `motor.py ler` ou do criador), o pedido de código ao criador com a duração, e o registro em `spark-codigos.md` (post, criador, duração, data de vencimento). Nunca pedir login ou senha do criador. *Claude.*
6. **Leitura do export** (modo `ler-export`):
   ```
   python ~/.claude/skills/arkos-tiktok-ads/scripts/anuncios.py ler <export.csv> --cpa-alvo <X> [--roas-alvo <Y>] \
     [--dias <N>] [--anterior <export-anterior.csv>] [--retargeting] \
     --out workspace/<cliente>/<projeto>/midia/tiktok/leitura-<AAAA-MM-DD>.json --md .../leitura-<AAAA-MM-DD>.md
   ```
   O script acha as colunas em português ou inglês, calcula CTR, CPM, CPA, ROAS, gancho de 2 s (views de 2 s ÷ impressões) e retenção de 6 s, e decide. *Script.*
7. **Explicar a decisão:** para cada "trocar criativo", dizer **qual hipótese** testar no lugar (passo 4). Para "escalar", subir **20–30%** da verba a cada 48 a 72 h na campanha de escala (orçamento ≥ 10× CPA); salto maior só na exceção sazonal da seção 3, com o registro de 24/72 h. O Claude não muda a decisão do script: quando discordar, escreve o porquê ao lado. *Claude.*
8. **Gate:** `anuncios.py pronto leitura.json` mais o checklist da seção 5, no `arkos-gate`. *Script + skill.*

## 5. Critério de pronto

- [ ] Pixel ou Events API confirmado, ou a etapa voltou para `tracking-pixel`.
- [ ] A estrutura diz por que é Smart+ ou manual, e o teste de criativo está separado do que escala.
- [ ] O portfólio tem de 3 a 5 hipóteses diferentes, cada uma com gancho nos 2 primeiros segundos e roteiro por cena.
- [ ] Na leitura, toda decisão veio do script e tem motivo; o `anuncios.py pronto` deu verde.
- [ ] Nenhum "escalar" com dado insuficiente.
- [ ] Os limiares aparecem como heurística.
- [ ] Tem "o que eu faria nesta semana" e "o que pode matar isto".

## 6. Exceções, custo e escrita externa

- **Custo:** ler e planejar é grátis. **Verba de mídia é custo**: nenhuma campanha nasce sem o portão `confirmacao_custo` com a verba diária por escrito.
- **Escrita na conta** (criar, pausar, mudar orçamento, por MCP ou à mão pelo prestador): passa pelo `arkos-guarda-escrita` com prévia do que muda. Antes de mudar, gravar o estado anterior em `midia/tiktok/antes-<data>.json` (status, orçamento, lance de cada item tocado).
- **Rollback:** reativar o que foi pausado, repor orçamento e lance do `antes-<data>.json`, pausar o que foi criado (nunca apagar sem OK). Spark Ads: o criador pode revogar o código no app.
- **Export sem coluna obrigatória** (`entrada_incompleta`): o script para e lista o que falta. Pedir o export no nível anúncio com custo, impressões, cliques e conversões, ou passar `--map`.
- **Dado insuficiente:** decisão `aguardar`. Não pausar "no feeling" um anúncio com 600 impressões.
- **MCP do TikTok fora do ar** (`fora_do_ar`): seguir com o CSV exportado à mão. O gate marca amarelo se a leitura usou export antigo.
- **Conta em revisão ou anúncio reprovado:** ler o motivo da política, reescrever o criativo; nunca tentar contornar a revisão.

## 7. Alimenta

- **Perfil do cliente:** CPA real e o ângulo vencedor (com confirmação).
- **Swipe (`arkos-swipe`):** os criativos vencedores, com hipótese, gancho e números.
- **Aprendizado:** `arkos.engine/aprendizado.jsonl` com a hipótese, a decisão e o resultado 7 dias depois.
- **Esteira:** `saida.json` com `campos.cpa_real`, `campos.vencedores` e `campos.proxima_leitura`.

## 8. Regras duras

- Decisão de pausar ou escalar vem do script. O modelo explica, não decide.
- Nada de verba sem portão de custo; nada de escrita na conta sem `arkos-guarda-escrita` e foto do antes.
- Nunca pedir senha nem login de criador ou de cliente.
- Nunca otimizar para clique quando o objetivo é venda ou lead.
- Promessa do anúncio passa pelo `mecanismo.py` (checagem de promessa) antes de ir para o roteiro.
