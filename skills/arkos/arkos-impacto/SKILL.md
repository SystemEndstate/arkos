---
name: arkos-impacto
description: Pensamento futuro antes de mexer em código. Em toda criação, alteração, correção ou release dentro do `arkos`, antecipa os bugs de impacto que a mudança costuma gerar — raio de impacto, contrato quebrado, cenários prováveis — mitiga já na geração e prova o cenário previsto antes de entregar. Use em "criar sistema", "fazer app", "site", "adicionar feature", "corrigir", "lançar", "release" ou qualquer mudança que pode quebrar outra coisa.
status: rascunho
versao: 0.1.0
modulos: [dev]
depende_de: []
---

# arkos-impacto

Clone de sala limpa da antecipação de impacto: antes de codar, mapeia o que a mudança pode quebrar e exige a prova do bug previsto antes da entrega. Não gera o código final sozinho — orienta a geração e o gate. Método público (blast radius + contrato + pré-mortem).

## Quando usar e quando não usar

- **Usar:** antes de qualquer mudança em sistema que já funciona (feature, fix, refactor, release).
- **Não usar:** rascunho isolado sem consumidores (nada depende dele ainda).

## Entradas

- `descricao` da mudança (o que muda e por quê).
- `simbolos`/`arquivos` tocados (funções, módulos, rotas, tabelas).
- `repo` (opcional): raiz para medir o raio de impacto de verdade.

## Passos

1. **Raio de impacto:** `impacto.py radar --repo <dir> --simbolos a,b` varre quem referencia os símbolos/arquivos tocados (quem quebra se o contrato mudar).
2. **Contrato:** listar as assinaturas públicas afetadas (parâmetros, retorno, forma do JSON, schema de tabela, evento). Mudança de contrato é o maior risco.
3. **Pré-mortem por categoria:** casar a mudança com os padrões de bug de impacto (estado compartilhado, migração/schema, forma de API, concorrência, nulo/vazio, encoding/i18n, limite/overflow, cache, retrocompatibilidade). Cada categoria vem com "como provar".
4. **Mitigar na geração:** escrever o código já tratando o cenário previsto (guardas, default, migração reversível, compat).
5. **Provar antes de entregar:** criar o teste que reproduz exatamente o bug previsto e rodá-lo; só entrega com ele verde.

## Saída

JSON: `{raio_de_impacto:[arquivos], contrato:[assinaturas], cenarios:[{categoria, risco, como_provar}], checklist:[itens para o gate]}`. Sem escrever em disco (a não ser `--log`).

## Critério de pronto

- [ ] O raio de impacto foi medido (não só suposto) quando havia repo.
- [ ] Cada cenário de risco alto tem um teste que o reproduz, rodado e verde.
- [ ] Nenhuma assinatura pública mudou sem compat ou sem aviso no checklist.

## Exceções

- **Sem repo:** usar os `deps` informados; marcar o raio como "declarado, não medido".
- **Símbolo não encontrado:** raio vazio para ele; avisar (pode ser nome errado).
- **Mudança grande demais:** recomendar fatiar antes de codar.

## Alimenta

- O `arkos-gate` (o checklist vira sub-gate) e a `guarda-regressao` da casa, quando existir.

## Regras duras

- Nunca entregar sem rodar o teste do bug previsto de risco alto.
- Mudança de contrato público sempre aparece no checklist, com compat ou aviso.
- Não baixar o limiar nem apagar teste para passar.
