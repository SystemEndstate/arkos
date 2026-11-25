---
name: arkos-kwai-ads
description: Kwai for Business (Kwai Ads) no Brasil pela ARKOS. Decide se o Kwai faz sentido para o cliente, monta a campanha (In-Feed, Eyemax, desafio de hashtag, criadores), adapta o criativo ao público do Kwai e lê o export do painel por script com uma decisão por anúncio. Use em "Kwai", "Kwai Ads", "Kwai for Business", "anunciar no Kwai", "campanha no Kwai", "tráfego no Kwai", "ler métricas do Kwai", "Kwai export".
status: instalada (promovida em 2026-11-22)
versao: 0.1.0
modulos: [6, 7, E]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-gate, arkos-guarda-escrita, arkos-tiktok-ads, jev]
fontes_conferidas_em: 2026-11-22
---

# arkos-kwai-ads

**Princípio:** o Kwai é canal de teste barato com público diferente do Instagram, não "TikTok de segunda". Entra quando o público do cliente está lá e o rastreio está de pé. A decisão sai do mesmo leitor do TikTok, com as heurísticas próprias do Kwai.

## 1. Quando usar e quando não usar

**Usar:**
- Mercado **BR** (o Kwai for Business é forte no Brasil), em `campanha-nova`, `otimizar-campanha` e `lote-criativos`.
- Público de massa, popular, fora das capitais, ofertas de ticket baixo ou médio, app e geração de lead em volume.
- Teste de criativo vertical que já rodou no TikTok ou no Reels, com adaptação.

**Não usar:**
- Mercado EUA ou Europa: o Kwai não é canal prioritário lá; ir de TikTok, Meta ou Google.
- B2B de ticket alto ou nicho técnico: o público raramente está lá. Dizer isso ao prestador em vez de gastar verba.
- Sem pixel (site) ou SDK (app) disparando conversão: primeiro `tracking-pixel`.

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: cliente, pergunta: "Cliente (slug)", obrigatoria: true }
- { id: projeto, pergunta: "Projeto (slug, padrão kwai-<AAAA-MM>)", obrigatoria: true }
- { id: modo, pergunta: "O que fazer?", opcoes: [avaliar-canal, estrutura-nova, ler-export, criativo], obrigatoria: true }
- { id: objetivo, pergunta: "Objetivo", opcoes: [conversao, leads, instalacao-app, trafego, alcance], obrigatoria: true }
- { id: cpa_alvo, pergunta: "CPA ou CPL alvo (R$)", perfil: numeros.cpa_alvo, obrigatoria: true }
- { id: export, pergunta: "CSV exportado do painel Kwai for Business (nível anúncio)", obrigatoria: "se modo = ler-export" }
- { id: publico, pergunta: "Quem compra (idade, região, renda) em uma frase", perfil: icp, obrigatoria: true }
```

**Pasta das entregas:** `workspace/<cliente>/<projeto>/midia/kwai/`.

## 3. O que a ARKOS sabe (conferido em 22/11/2026)

Fontes: guias públicos em pt-BR e material do Kwai Summit. A documentação oficial atualizada **não foi encontrada** na conferência: o que está marcado com ⚠ é **incerto** e precisa de confirmação no painel ou com o gerente de conta.

- **Formatos:** In-Feed (vertical 9:16, entre os vídeos), Eyemax (tela cheia na abertura do app, compra de alcance), desafio de hashtag, Magic Face (efeito de rosto) e ações com criadores. ⚠ Eyemax e desafio costumam ser vendidos pelo time comercial, não pelo autoatendimento.
- **Objetivos:** alcance, tráfego, instalação de app, geração de leads e conversão. ⚠ Os nomes e agrupamentos mudam entre versões do painel.
- **Rastreio:** pixel no site e SDK no app alimentam a otimização por conversão.
- ⚠ **Custo:** blogs falam em CPC muito menor que Meta e Google. É afirmação de marketing sem dado verificável: a ARKOS só usa o CPA real do teste.
- ⚠ **Colunas do export:** variam. O leitor procura nomes em pt-BR e inglês (custo total, impressões, cliques, resultados, reproduções de 3 s e 5 s) e para pedindo `--map` quando não acha.

## 4. Passos

1. **Avaliar o canal** (sempre, antes de verba): o Jev responde, com o ICP e a oferta, "o público deste cliente está no Kwai em volume?" (sim/não com probabilidade). Abaixo de 0,5: recomendar não entrar e dizer por quê. *Jev.*
2. **Rastreio:** confirmar pixel ou SDK com o evento do objetivo. Sem isso, `tracking-pixel`. *Claude.*
3. **Estrutura:** 1 campanha por objetivo; teste com 3 a 5 criativos de hipóteses diferentes num grupo; verba de teste = pelo menos 2× o CPA alvo por criativo (heurística). Eyemax e desafio só com verba de marca aprovada. *Claude.*
4. **Criativo para o Kwai:**
   - linguagem direta, popular e brasileira, com humor ou depoimento; fala logo no 1º segundo;
   - mostrar o preço ou a condição quando for ticket baixo (o público compara rápido);
   - reaproveitar vídeo do TikTok ou Reels só depois de trocar o gancho e o texto da tela;
   - hipóteses como no `arkos-tiktok-ads` passo 4.
   *Claude.*
5. **Leitura do export:**
   ```
   python ~/.claude/skills/arkos-kwai-ads/scripts/kwai.py ler <export.csv> --cpa-alvo <X> \
     --out workspace/<cliente>/<projeto>/midia/kwai/leitura-<AAAA-MM-DD>.json --md .../leitura-<AAAA-MM-DD>.md
   ```
   Mesmo leitor do TikTok (`arkos-tiktok-ads/scripts/anuncios.py`, pasta irmã), com heurísticas do Kwai (mais impressões antes de decidir, gancho e retenção com mínimos menores). *Script.*
6. **Comparar com os outros canais:** CPA do Kwai × TikTok × Meta no mesmo período, sem misturar janela de atribuição. *Claude.*
7. **Gate:** `kwai.py pronto leitura.json` e o checklist da seção 5. *Script + skill.*

## 5. Critério de pronto

- [ ] A avaliação do canal foi feita e registrada (entra ou não entra, com o porquê).
- [ ] Pixel ou SDK confirmado antes de verba de conversão.
- [ ] De 3 a 5 hipóteses de criativo adaptadas ao público do Kwai.
- [ ] A leitura veio do script, com decisão e motivo por anúncio, e o `pronto` deu verde.
- [ ] Todo fato marcado ⚠ que foi usado na decisão foi confirmado no painel, ou aparece como incerto no relatório.
- [ ] Tem "o que eu faria nesta semana" e "o que pode matar isto".

## 6. Exceções, custo e escrita externa

- **Custo:** verba de mídia passa pelo portão `confirmacao_custo`. Eyemax e desafio de hashtag são compra grande: portão do **dono**, além do cliente.
- **Escrita na conta:** pelo `arkos-guarda-escrita`, com a foto do antes em `midia/kwai/antes-<data>.json`.
- **Rollback:** reativar o pausado e repor orçamento do `antes-<data>.json`; pausar o criado. Nada se apaga sem OK.
- **Export com coluna diferente** (`entrada_incompleta`): o script para; pedir o export certo ou montar o `--map`.
- **Canal reprovado na avaliação:** não é falha. Registrar no aprendizado e seguir com os outros canais.
- **Painel fora do ar ou login expirado** (`fora_do_ar`): pedir re-login ao prestador; nunca pedir senha no chat.

## 7. Alimenta

- **Perfil do cliente:** se o Kwai entra no mix e o CPA real.
- **Aprendizado:** canal × nicho × CPA em `arkos.engine/aprendizado.jsonl` (é o dado que mais falta no mercado).
- **Swipe:** criativos vencedores com a adaptação feita.
- **Esteira:** `saida.json` com `campos.cpa_real` e `campos.canal_aprovado`.

## 8. Regras duras

- Não entrar no Kwai sem avaliar o canal e sem rastreio.
- Nada de verba sem portão; nada de escrita na conta sem guarda e foto do antes.
- Fato incerto (⚠) nunca vira promessa ao cliente.
- A decisão por anúncio vem do script.
