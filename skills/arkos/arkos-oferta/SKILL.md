---
name: arkos-oferta
description: Constrói, dá nota (0 a 10) e reescreve a oferta antes de qualquer copy, pela sequência do método ARKOS de oferta com diagnóstico honesto e vocabulário BR (Pix, parcelamento, garantia de 7 dias do CDC) ou EUA. Gera OFFER.md e a mensagem-núcleo. Use quando o usuário pedir oferta, "oferta irresistível", preço, bônus, garantia, "por que não vende", ou antes de página de vendas, anúncio e SDR.
status: rascunho
versao: 0.1.0
modulos: [10, 8, 13, P]
depende_de: [arkos-perfil, arkos-mercado, hundred-million-offers, offers, mechanism-ideation, jev]
---

# arkos-oferta

Premissa: **a oferta é a coisa, não a página** (coreyhaines `offers`). A copy só começa com oferta nota ≥ 8.

## Entradas

`arkos-perfil` (oferta, preço, ICP, dores, números, concorrentes, mecanismo) · tipo de negócio · mercado · opcional: swipe de ofertas concorrentes (`arkos-swipe`, `competitor-offer-analysis`).

## 12 passos

1. Ler o perfil e reescrever a oferta atual numa frase: nome, preço, o que recebe, garantia, prazo.
2. **Mercado (Starving Crowd):** nota 1–10 para dor, poder de compra, facilidade de alcançar, crescimento. Média < 6 = parar e sugerir outro nicho.
3. **Equação de valor:** nota 1–10 para resultado sonhado, probabilidade percebida, tempo e esforço. A pior nota é a restrição.
4. **Obstáculos** (antes, durante, depois) → solução + veículo (1:1, grupo, DIY, feito-para-você, software). **Trim & Stack** com matriz valor × custo de entrega.
5. **Preço por valor:** 10–20% do resultado; âncora de 3 números; parcelamento no BR. Margem conferida com `unit-economics`.
6. **Bônus:** 1 por objeção restante, com valor defensável (comparável real). Proibido inflar.
7. **Garantia:** escolher o tipo (incondicional, condicional, desempenho, anti-garantia) e dar nome. BR: respeitar o arrependimento de 7 dias (CDC art. 49) em venda online. OaaS: ligar à ficha de resultado da `arkos-oaas-proposta`.
8. **Escassez e urgência reais** (vagas, turma, prazo). Cronômetro falso bloqueado.
9. **Mecanismo:** `mechanism-ideation` (dtc) / `arkos-mecanismo`.
10. **Nome MAGIC:** 3–5 variações (avatar, objetivo, prazo, formato).
11. **Nota final 0–10** pelo diagnóstico de 7 linhas do `hundred-million-offers`. O Jev confere cada linha (sim/não). < 8 = voltar ao passo da alavanca mais fraca, **uma mudança por iteração**, ganho projetado de 10–40% (honesto, como no `offers`).
12. **Compliance:** vocabulário proibido do `offers` ("100% garantido" sem condição, "worth $X" sem comparável, escassez falsa) + regras BR (promessa de ganho em infoproduto financeiro; Meta e CONAR).

## Saída

- `workspace/<cliente>/<projeto>/oferta/OFFER.md` com estas seções: resumo, mercado, avatar, resultado, obstáculos, mapa de solução, stack com valores, preço, garantia, escassez, mecanismo, nome, **mensagem-núcleo**, nota e pendências.
- Campos-chave gravados no perfil (`arkos-perfil atualizar oferta|preco --fonte arkos-oferta`, com confirmação).
- Mensagem-núcleo (promessa + mecanismo + prova + oferta + CTA) entregue a `arkos-conversa`, `headline-formulas`, `hook-battery` e à copy.

## Regras duras

- Nunca inventar prova, depoimento ou número. Sem prova = campo "falta prova" na nota.
- Mudança de preço ou garantia no perfil pede confirmação do dono.
- Saída em pt-BR para BR; em inglês para EUA/EU (a conversa com o prestador segue em pt-BR).
