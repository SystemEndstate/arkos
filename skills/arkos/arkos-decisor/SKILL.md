---
name: arkos-decisor
description: Decisão fechada barata (sim/não, múltipla escolha, nota numa escala, triagem em lote) com limiar. Pede probabilidades a um provedor OpenAI-compatível configurável, com a chave do próprio prestador; sem chave ou com o provedor fora do ar, devolve o controle para o Claude decidir. Use antes de toda decisão fechada e repetida dentro do `arkos`, para gastar o modelo caro só na lista curta.
status: rascunho
versao: 0.1.0
modulos: [todos]
depende_de: []
---

# arkos-decisor

Sistema 1 da ARKOS: escolhe rápido e barato nas decisões fechadas; o Claude (Sistema 2) só recebe a lista curta ou decide quando o provedor não responde. Não gera texto nem escreve código — só devolve probabilidades e a decisão do limiar. Clone de sala limpa: não usa nenhum código, endpoint, modelo ou formato de ferramenta pessoal de terceiros; método público (classificação por LLM + limiar).

## Quando usar e quando não usar

- **Usar:** sim/não repetido, múltipla escolha fechada, nota numa escala, triagem/classificação em lote.
- **Não usar:** quando a saída é texto, código ou raciocínio aberto (fica com o Claude), e quando a regra é determinística (fica em análise estática, ex.: `arkos-scanner`).

## Entradas

- `pergunta` (texto), `opcoes` (lista fechada) e `texto` (o caso a decidir).
- `limiar` (0–1, padrão 0,6).
- Config do provedor, nesta ordem: variáveis de ambiente (`ARKOS_DECISOR_PROVIDER`, `ARKOS_DECISOR_BASE_URL`, `ARKOS_DECISOR_MODEL`, `ARKOS_DECISOR_KEY`) ou `~/.arkos/decisor.json`. A chave é **do prestador**, nunca embutida no pacote.

## Passos

1. `redigir()` mascara segredos e dado pessoal do `texto` antes de qualquer envio (chaves `sk-…`, tokens, e-mails, CPF/CNPJ).
2. Sem chave/provedor configurado: devolver `{fonte:"fallback", decidir_com_claude:true, motivo:"sem chave"}` e parar. O chamador decide com o Claude.
3. Com chave: `POST {base_url}/chat/completions` (dialeto OpenAI), pedindo ao modelo um JSON com uma probabilidade por opção. Tempo limite curto; 1 tentativa extra.
4. Erro, tempo esgotado ou JSON inválido do provedor: mesma saída de fallback (`decidir_com_claude:true`, `motivo:"provedor"`). Nunca travar o fluxo (regra do Sistema 1).
5. Normalizar as probabilidades (soma 1). Aplicar o limiar:
   - maior prob `> limiar` e sem empate: `{fonte:"provedor", escolha, prob, acima_limiar}`;
   - abaixo do limiar ou empate técnico (diferença < 0,05): `{fonte:"provedor", decidir_com_claude:true, top:[2 melhores]}`.
6. Lote (`decide-lote`): mesma regra item a item; devolve lista e um resumo `{decididos, para_claude}`.

## Saída

- JSON no stdout (uma linha). Nada é escrito em disco pela skill.
- Log opcional de auditoria em `arkos.engine/execucoes/<id>/decisor.jsonl` (pergunta redigida, opções, fonte, limiar — sem o texto cru), quando `--log <id>`.

## Critério de pronto

- [ ] A saída sempre tem `fonte` e, quando não decidiu, `decidir_com_claude:true`.
- [ ] Nenhuma decisão fechada do fluxo chamou o Claude direto sem passar por aqui.
- [ ] Nenhum segredo ou dado pessoal saiu no corpo enviado (conferível no log redigido).
- [ ] Sem chave, o fluxo segue pelo Claude sem erro.

## Exceções

- **Sem chave:** fallback para o Claude (não é erro).
- **Provedor fora do ar / resposta inválida:** 1 retry, depois fallback; registrar a falha numa linha.
- **Opções vazias ou com 1 item:** não há o que decidir — `decidir_com_claude:true`, `motivo:"opcoes_insuficientes"`.
- **Texto todo mascarado (só segredo):** avisar e pedir reformulação ao chamador.

## Alimenta

- A lista curta sobe para o Claude. O `retune` lê o log para calibrar o `limiar` por tipo de decisão.
- `arkos-roteador`, `arkos-scanner` (triagem de achados) e as bancas de estratégia usam esta skill como Sistema 1.

## Regras duras

- Nunca enviar segredo nem dado pessoal: `redigir()` é obrigatório antes do envio.
- A chave é sempre do prestador; o pacote não traz chave nem provedor fixo.
- Falha do provedor nunca trava o fluxo: cai para o Claude.
- A skill não gera texto nem código; só decide o fechado.
