---
name: arkos-gate
description: Portão de qualidade único da ARKOS antes de entregar qualquer coisa - encadeia jev, guarda-regressao, ciber-diff, verification-before-completion e browse/webapp-testing para código e site, mais sub-gates de vídeo (legenda, loudness, safe zone, 3 s iniciais), tracking (evento de teste no Events Manager, GA4, GTM), copy (antislop, humanizer-pt-br, nota Jev) e lead/OaaS, e gera um relatório único em engine/report. Use ao fim de toda etapa de playbook, antes de "pronto", "entregar", "publicar" ou "subir".
status: rascunho
versao: 0.1.1
modulos: [G, 1, 2, 3, 7, 8, E, I, P]
depende_de: [jev, guarda-regressao, central-ciber, superpowers:verification-before-completion, earshot]
---

# arkos-gate

As peças existem; esta skill é a **cola** e o relatório. Nada é entregue com o gate vermelho.

## Escolha dos sub-gates (pelo tipo da entrega)

| Entrega | Sub-gates, nesta ordem |
|---|---|
| Código | `jev review.py` → `guarda-regressao gate.py check` → `ciber-diff` → `verification-before-completion` (rodar os testes e mostrar a saída) |
| Site / interface | Código + `browse.py goal <url>` (Jev) + gate da taste-skill + responsivo 360–1800 px no portal do Maestro |
| Vídeo | earshot `measure` (−14 LUFS ±1, pico ≤ −1 dBTP) e `critique` · legenda legível e dentro da safe zone (9:16 em 1080×1920: fora dos 270 px de cima e dos 672 px de baixo, 14% e 35% do guia da Meta para Stories/Reels) · gancho nos 3 s iniciais · selo/marca presentes · formato e duração certos (ffprobe) |
| Tracking | disparar evento de teste → conferir no Events Manager (Meta MCP), GA4 (DebugView/Realtime) e GTM (Stape MCP) → deduplicação pixel × CAPI por `event_id` → UTM consistente |
| Copy | `antislop` + `humanizer-pt-br` (BR) + Jev sim/não: "inventa dado?", "promete o que a oferta não entrega?", "viola política do canal?" + nota 0–10 (limiar 8) |
| Oferta | nota do `arkos-oferta` ≥ 8 |
| Leads | `arkos-lead-merge`: 100% com `fonte`, `coletado_em`, `base_legal`; zero opt-out no arquivo |
| OaaS | ficha de resultado completa; ledger sem linha cobrável sem evidência |
| SOP / prestador | checklist do SOP (`.jev/checklist.json` do papel) |
| Relatório local (toda entrega) | `python scripts/relatorio_completo.py resultado.json --plano <membro\|vip>` antes de gerar o site: os 7 papéis de `engine/report/SCHEMA.md` (diagnóstico com números, plano passo a passo, material pronto, números e cortes, riscos e plano B, cronograma 7/30/90 com checklist, medição), sem seção genérica, sem "procure um especialista", sem origem do método (limite A) e, para membro, sem nome técnico de skill (limite B) nem tema do plano VIP. Reprovado volta para completar. Testes: `python -m unittest discover -s scripts/tests` |

## Passos

1. Detectar o tipo da entrega (pelo playbook ou pelos arquivos).
2. Rodar os sub-gates em ordem. **O primeiro vermelho para a fila**, a menos que o usuário peça o relatório completo.
3. Para cada item: `verde` / `amarelo` (passa com aviso) / `vermelho` (bloqueia), com a evidência (saída de comando, print, número).
4. Gerar o relatório no formato de `engine/report/SCHEMA` (título, sumário, seções, passos, status) e abrir com `maestro open`.
5. Devolver ao playbook: `{status: aprovado|reprovado, vermelhos: [], relatorio: caminho}`.

## Regras duras

- Nunca dizer "pronto" sem evidência executada nesta sessão (verification-before-completion).
- Gate reprovado não se contorna apagando teste, baixando limiar ou pulando sub-gate. Corrigir e rodar de novo.
- Um sub-gate que falha por ferramenta indisponível = `amarelo` com o motivo, nunca `verde`.

## Pendências

- Valores da safe zone por plataforma (Reels, TikTok, Shorts) no padrão da casa.
- Integração com o painel de execuções do terminal.
