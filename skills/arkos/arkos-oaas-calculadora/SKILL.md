---
name: arkos-oaas-calculadora
description: Calculadora determinística de preço por resultado (OaaS) - preço por unidade de resultado, piso mensal, volume mínimo, teto, margem por cenário (pessimista, base, otimista), break-even e ROI do cliente, a partir do custo humano atual, volume, baseline, custo de IA e operação e taxa de sucesso. Use ao precificar proposta OaaS, retainer + success fee, gain-share, ou quando perguntarem "quanto cobrar por resultado".
status: rascunho
versao: 0.1.0
modulos: [P, 10, N]
depende_de: [arkos-perfil, jev]
---

# arkos-oaas-calculadora

Script Python (`scripts/calc.py`, sem LLM, com testes pelo guarda-regressao) + esta skill. A conta é determinística; o Jev só dá a nota de risco.

## Entradas (`calc.json`)

```json
{ "unidade": "reuniao_qualificada",
  "custo_humano_por_unidade": 180.0, "moeda": "BRL",
  "volume_mes": { "pessimista": 20, "base": 35, "otimista": 50 },
  "taxa_sucesso": { "pessimista": 0.5, "base": 0.7, "otimista": 0.85 },
  "custo_ia_por_tentativa": 4.0, "custo_operacao_mes": 3000.0,
  "baseline_mes": 12, "risco_dependencia": "medio",
  "margem_minima": 0.35 }
```

## Regras de cálculo

1. **Faixa de preço por resultado:** custo humano ÷ 10 a custo humano ÷ 3 (como os exemplos de mercado: Fin, Sierra, HubSpot). Ponto sugerido: o menor preço da faixa que mantém a margem mínima no cenário **pessimista**.
2. **Custo por resultado** = (custo IA por tentativa ÷ taxa de sucesso) + (operação ÷ resultados do mês).
3. **Piso mensal** = custo de operação × (1 + margem mínima). Cobre o custo mesmo com zero resultado.
4. **Volume mínimo** = piso ÷ preço por resultado (arredondado para cima).
5. **Teto** = volume otimista × 1,5 × preço (o cliente sabe o máximo que pode pagar).
6. **Margem por cenário** = (receita − custo) ÷ receita, nos três cenários.
7. **Break-even** = resultados por mês para a receita cobrir o custo.
8. **ROI do cliente** = (custo humano evitado − preço pago) ÷ preço pago; incremental sobre a baseline quando for gain-share.
9. **Alerta:** margem pessimista < margem mínima → o modelo recomendado vira **híbrido** (subir o piso) ou **fixo por marco**.

## Saída

Tabela no relatório (`engine/report/`) e `calc-resultado.json`: faixa, preço sugerido, piso, mínimo, teto, margem × 3 cenários, break-even, ROI do cliente, modelo recomendado e nota de risco do Jev (`decide`: "risco de dependência do cliente alto, médio ou baixo?").

## Regras duras

- Não inventar custo humano: sem dado do cliente, usar uma faixa pedida ao dono e marcar como **estimativa**.
- Números do perfil marcados `privado` não saem no relatório do cliente.
