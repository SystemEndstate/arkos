---
name: arkos-regressao
description: Trava de regressão em toda mudança de código que já funciona na ARKOS — grava a linha de base dos testes que passam, mostra o raio de impacto dos arquivos mudados, registra contratos (comportamentos que não podem mudar) e, antes de entregar, roda tudo e reprova se algum teste que passava passou a falhar, sumiu ou quebrou contrato. Lê pytest, node --test e go test. Use em "corrigir bug", "mudar o código", "adicionar feature", "refatorar", "não quebrar o que funciona", "teste de regressão", "check antes de entregar".
status: rascunho
versao: 0.1.0
modulos: [2, O]
depende_de: [arkos-impacto, arkos-grafo]
substitui: guarda-regressao (ferramenta pessoal do usuário, sem repo público; implementação própria, escrita do zero)
---

# arkos-regressao

Corrigir uma coisa e quebrar outra é o erro mais caro de entregar. Esta skill não confia no "testei a minha mudança": compara a suíte **inteira** com o que passava antes.

## Fases

1. **Linha de base** (uma vez por repositório): `init` roda os testes e grava os que passam. Teste que já falha não entra: é dívida, não regressão. Sem teste nenhum: escrever o primeiro do comportamento que funciona hoje.
2. **Raio de impacto** (antes de mexer): `raio <arquivos>` lista quem importa cada arquivo e quais testes cobrem. Arquivo sem teste no raio: escrever o teste **antes** da mudança.
3. **Contrato** (o que não pode mudar): `contrato --id --descricao --teste` liga um comportamento a testes da base. Contrato quebrado reprova mesmo que outro teste cubra.
4. **Teste da mudança:** a correção ou a feature ganha o seu teste, que tem que passar.
5. **Check antes de entregar:** `check`. Verde com `--aceitar` põe os testes novos na base.

## Comandos

```bash
py -3 scripts/regressao.py init <repo> [--comando "npm test"]
py -3 scripts/regressao.py raio <repo> [arquivo ...]      # sem arquivo: usa o git diff
py -3 scripts/regressao.py contrato <repo> --id total-com-desconto --descricao "..." --teste "tests.test_preco::test_desconto"
py -3 scripts/regressao.py check <repo> [--aceitar]       # código 1 = regressão
py -3 scripts/regressao.py ler <repo>
```

Estado em `<repo>/.arkos-regressao/` (`config.json`, `base.json`, `contratos.json`, `historico.jsonl`). Pode ir para o git do repositório: é o registro do que estava garantido.

## Regras duras

- **Vermelho em qualquer um destes:** teste da base falhando (regressão), teste da base sumido (apagado ou renomeado), teste novo falhando, contrato quebrado.
- Nunca apagar, pular (`skip`) ou afrouxar teste para o check passar. Teste errado se corrige com o motivo escrito no commit e passa pela revisão.
- `--aceitar` só soma testes novos à base; nunca tira nenhum.
- Com `--comando` genérico só o código de saída conta: o máximo é amarelo.
- Os testes rodam ocultos (`CREATE_NO_WINDOW`).

## Pronto quando

`check` sai com código 0 depois da última mudança, com o histórico registrado. Isso vem antes do commit e antes do gate de entrega.

## Exceções

- `entrada_incompleta`: pasta inexistente, nenhum teste encontrado, `check` antes do `init`, contrato apontando teste fora da base. Código 2.
- `fora_do_ar`: executor de teste ausente (pytest, node, go). Código 3 e o comando de instalação.
- `resultado_ruim`: vermelho. Corrigir o código (não o teste) e rodar de novo; com 3 vermelhos seguidos na mesma mudança, voltar à fase 2 e escalar.
