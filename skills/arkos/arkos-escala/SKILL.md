---
name: arkos-escala
description: Decide o que pausar, manter e escalar nos conjuntos e campanhas de Meta, Google ou TikTok a partir do export de métricas (CSV ou JSON), por uma regra fixa e auditável. Protege a fase de aprendizado, não decide com pouco dado e limita o aumento de budget por execução. Não planeja a verba do mês nem a distribuição entre canais (isso é o budget-ads). Só propõe; a mudança na conta passa pela arkos-guarda-escrita. Use em "o que pausar", "o que escalar", "posso aumentar o budget", "qual conjunto está ruim", "decisão de otimização", e na etapa decisao do playbook otimizar-campanha.
status: instalada (2026-11-22)
versao: 1.2.0
modulos: [D, 6]
depende_de: [arkos-guarda-escrita]
---

# arkos-escala

## Passos

1. **Exportar as métricas dos últimos 7 dias**, no nível em que o budget mora (campanha em CBO, conjunto em ABO): nome, gasto, conversões, receita, dias ativo, aprendizado, budget diário e, se der, dias desde o último ajuste de budget. Os nomes de coluna da Meta e do Google são aceitos e a vírgula decimal também.
2. **Pegar a meta** do `metas.yaml` do cliente: CPA meta e, se houver, ROAS meta. Sem meta, pergunte; não invente.
3. **Rodar.** Lead ou SKU único, por CPA: `python scripts/escala.py decidir --dados export.csv --meta-cpa 50 [--meta-roas 3] [--intervalo-dias 3] --saida .../escala/`. **Loja** (AOV varia, decisão por ROAS): `python scripts/escala.py decidir --dados export.csv --modo loja --break-even 2.5 [--meta-roas R] [--cpa-break-even C] --saida .../escala/`.
4. **Mostrar a tabela** (`decisao.md`) com a ação e o motivo de cada linha.
5. **Para cada PAUSAR, REDUZIR ou ESCALAR aceito**, chamar a `arkos-guarda-escrita`, que monta o diff, pede aprovação e registra.

## A regra (nessa ordem)

1. Em aprendizado ou com menos de 7 dias: **MANTER**. Mexer reinicia o aprendizado.
2. Gasto abaixo de 2 × CPA meta e menos de 10 conversões: **MANTER_COLETAR**. Não há dado para decidir.
3. CPA acima de 1,5 × meta, ou ROAS abaixo da metade da meta, com gasto de pelo menos 2 × CPA meta: **PAUSAR**.
4. **Folga** = (CPA-alvo − CPA médio dos últimos 7 dias) ÷ CPA-alvo. Com folga de pelo menos 10%, ROAS na meta (se houver) e 10+ conversões: **ESCALAR em até METADE DA FOLGA**, nunca acima do teto (20%). Folga de 10% dá 5%; folga de 30% dá 15%. Assim, se a verba nova não trouxer nenhuma conversão a mais, o CPA ainda fica abaixo do alvo. Ajuste de budget há menos de `intervalo_dias`: **MANTER**.
5. O resto: **MANTER**.

Substitui a tabela fixa antiga (gatilho 0,8 × meta, passo de 20%): ela deixava subir 20% com 20% de folga, e sem conversão extra o CPA ia a 0,96 × alvo e a folga zerava. Base: `trafego/meta/escala-por-folga-headroom.md` e `trafego/meta/escala-meta.md` da base de conhecimento.

### Modo loja (`--modo loja`, decisão por ROAS × break-even)

Para loja de e-commerce, em que o AOV varia e o CPA engana (mix de SKU). A decisão vai no **conjunto/campanha**, nunca no anúncio (ponto 3 da auditoria de e-commerce). Precisa do **break-even** (ROAS de equilíbrio).

1. Em aprendizado ou com menos de 7 dias: **MANTER**.
2. Pouco dado (gasto abaixo de 2 × CPA de equilíbrio, quando informado, ou menos de 10 conversões): **MANTER_COLETAR**.
3. **ROAS 7d < 0,8 × equilíbrio**: **PAUSAR**. Entre **0,8× e 1,0×**: **REDUZIR** o budget à metade e reler em 7 dias.
4. **ROAS-meta** = `--meta-roas`, ou o **break-even × 1,25** por padrão (precaução). **Folga = 1 − meta ÷ ROAS 7d**. Folga ≥ 10%: **ESCALAR** em até **metade da folga**, teto **20%** — ou **até 50%** quando a folga ≥ 40% (regra "sem reaprendizado" da Meta). **Passo acima de 5% espera 72 h** desde o último ajuste.
5. O resto: **MANTER**.

**PMax/Shopping** (ponto 18): a meta inicial é o **ROAS real de 30 dias**, nunca abaixo de equilíbrio × 1,25, e se ajusta ao real **antes** de escalar; a leitura do gatilho usa **14 dias** (`--periodo-dias 14`). Some o "alerta a 70% da meta": o gatilho é ROAS < 0,8 × equilíbrio com gasto ≥ 2 × CPA de equilíbrio. Base: auditoria de e-commerce 2026-11-23, pontos 1-4 e 18.

### Intervalo entre aumentos (`travas.intervalo_dias`, padrão 3)

- Padrão: **3 dias** entre aumentos na mesma linha.
- **Escala diária** (`--intervalo-dias 1` ou 2) só com as três condições: **30+ conversões por dia** na linha, **atribuição confiável** (CAPI + qualidade de evento boa; `--atribuicao-confiavel`) e **registro da decisão do dono** (`--registro-dono <id ou caminho no ledger>`). Sem as duas flags o script recusa (código 2). Linha com menos de 30 conversões/dia continua com 3 dias, mesmo com as flags.
- Com 3–5 conversões por dia, o CPA de ontem é ruído: subir todo dia vira subir no acaso.

Os limiares são padrão e saem do `config.travas` do perfil (`min_conv`, `min_gasto_fator`, `teto_aumento`, `dias_aprendizado`, `folga_min`, `intervalo_dias`). **A CONFIRMAR com o dono.**

## Regras duras

1. **Só propõe.** Nenhuma chamada de escrita sai daqui.
2. **Teto de aumento:** acima de 50% por execução o script recusa. Entre 20% e 50%, a guarda-escrita pede uma segunda confirmação.
3. **Não pausar em aprendizado** só porque está caro.
4. **Sem número inventado:** linha sem gasto ou sem conversões vira MANTER_COLETAR.
5. A decisão vai para `workspace/`, nunca para `arkos.engine/`.

## Pronto quando

- toda linha do export tem ação e motivo;
- PAUSAR e ESCALAR têm `guarda: arkos-guarda-escrita` e rollback;
- `decisao.md` diz "Nada foi alterado na conta".

## Exceções

- **entrada_incompleta:** sem meta de CPA (modo cpa), sem `--break-even` (modo loja) ou export vazio. Devolve código 3 e pergunta.
- **resultado_ruim:** tudo em PAUSAR. Volte ao `lote-criativos` ou à `oferta-irresistivel` antes de gastar mais.
- **rollback:** reativar o conjunto ou voltar o budget anterior. Está em cada linha.

## Testes

`python -m unittest discover -s scripts/tests`: 9 testes. Modo CPA: export sintético da Meta (`;` e vírgula decimal), as 5 ações, o passo de metade da folga (10% → 5%, 30% → 15%, 5% → não sobe), o intervalo entre ajustes, a escala diária só com atribuição confiável + registro do dono + 30 conv./dia, pausar em aprendizado, sem meta, linha quebrada e a recusa de saída no engine. Modo loja: PAUSAR/REDUZIR/ESCALAR por ROAS × break-even, teto 50% com folga ≥ 40%, espera de 72 h no passo > 5%, ROAS-meta = equilíbrio × 1,25 e o `--break-even` obrigatório.
