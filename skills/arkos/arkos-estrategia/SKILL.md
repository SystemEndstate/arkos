---
name: arkos-estrategia
description: Porta de entrada da suíte de estratégia de negócio da ARKOS. Entende a pergunta (ideia nova, validar, lançar, precificar, crescer, destravar um negócio que já roda), escolhe quais skills arkos-estrategia-* rodar e em que ordem, mantém a tese e o registro de premissas e consolida tudo num relatório com a banca. Use quando pedirem "estratégia", "plano de negócio", "modelo de negócio", "vale a pena?", "por onde começo?", "como crescer", "business strategy", "should I build this", ou no playbook estrategia-negocio e no lancar-saas.
status: rascunho
versao: 0.1.0
modulos: [9, 10, 11, B]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia-premissas, arkos-estrategia-relatorio, jev]
---

# arkos-estrategia

Não analisa sozinha: decide o **caminho** pela suíte, guarda a **tese** e garante que nenhuma recomendação saia sem premissas explícitas e sem banca.

## 1. Quando usar e quando não usar

**Usar:**
- Pergunta estratégica aberta ("o que faço com esse negócio?", "vale lançar X?").
- Início do `lancar-saas`, do `estrategia-negocio` e de qualquer esteira que comece sem oferta definida.

**Não usar:**
- Pergunta fechada de uma área só. Ir direto à skill: preço → `arkos-estrategia-preco`; projeção → `arkos-estrategia-financas`.
- Copy, anúncio ou site. Isso é dos outros módulos, que leem a tese daqui.

## 2. Entradas

Lê o perfil (sem os campos `privado` quando o relatório for para o cliente), `tese.md` e `premissas.yaml`, se já existirem.

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: pergunta, pergunta: "Qual decisão você precisa tomar? (uma frase)", obrigatoria: true }
- { id: estagio, pergunta: "Estágio", opcoes: [ideia, validando, já fatura, escalando], obrigatoria: true }
- { id: prazo_decisao, pergunta: "Até quando precisa decidir?", padrao: "7 dias", obrigatoria: false }
- { id: restricoes, pergunta: "O que está fora de questão? (dinheiro, tempo, canal, sócio)", perfil: restricoes, obrigatoria: false }
- { id: numeros, pergunta: "Números que já existem (faturamento, clientes, CAC, margem)", perfil: numeros, obrigatoria: false }
```

## 3. Passos

1. **Reescrever a pergunta** como uma decisão sim/não ou de escolha ("lançar o plano anual a R$ X: sim ou não?"). Confirmar com o prestador. *Claude.*
2. **Escolher o caminho** pelo estágio (tabela abaixo). O Jev confirma (`decide` entre os caminhos, aceita com prob > 0,6; abaixo disso, pergunta ao prestador). *Jev.*
3. **Abrir ou carregar** `workspace/<cliente>/<projeto>/estrategia/` e escrever a `tese.md` provisória: pergunta, resposta-hipótese em 5 linhas e data. *Claude.*
4. **Rodar as skills do caminho** em ordem. Cada uma acrescenta premissas no `premissas.yaml`. *Skills.*
5. **Banca:** independente, cada persona sem ler as outras. No caminho curto, só o cético. *Skills da banca.*
6. **Consolidar:** atualizar a tese com o veredito, os riscos críticos (`scripts/criticos.py`) e as 3 ações da semana. *Script + Claude.*
7. **Relatório:** chamar `arkos-estrategia-relatorio`. *Skill.*
8. **Agendar a retro** (`arkos-estrategia-retro`) para a data em que o teste mais arriscado termina. *Claude.*

| Estágio | Caminho |
|---|---|
| ideia | ideia → premissas → banca-cetico |
| validando | premissas → modelo → preco → gtm → banca (cético + cliente) |
| lançando | modelo → preco → gtm → financas → produto → banca (4) |
| já fatura | diagnostico → premissas → (a skill do gargalo) → banca (operador + investidor) |
| escalando | diagnostico → financas → gtm → banca (4) |

## 4. Saída

- `workspace/<cliente>/<projeto>/estrategia/tese.md` com pergunta, veredito, resposta em 5 linhas, riscos críticos, 3 ações da semana, data da retro e links para os arquivos da suíte.
- O `saida.json` da execução leva os campos `tese`, `oferta` (se houver), `nome_produto`, `problema` e `mvp`, que as esteiras usam.

## 5. Critério de pronto

- [ ] A pergunta virou uma decisão explícita, confirmada.
- [ ] Toda recomendação aponta para uma premissa do registro.
- [ ] Os riscos críticos estão no topo da tese.
- [ ] A banca do caminho rodou, com independência registrada.
- [ ] Há no máximo 3 ações da semana, cada uma com dono e data.
- [ ] A retro está agendada.

## 6. Exceções

- **Sem número nenhum:** seguir com `estimativa` e faixa. Cada estimativa vira premissa de confiança ≤ 0,3, e o relatório avisa no topo.
- **A banca dá "parar":** a tese registra o motivo. Propor a troca da premissa que matou (pivô) ou encerrar. Nunca esconder o veredito.
- **Pergunta grande demais** ("como ficar rico com isso"): quebrar em até 3 decisões e começar pela de maior risco.

## 7. Alimenta

- **Perfil:** `oferta`, `icp` e `mecanismo` atualizados pelo `arkos-perfil atualizar`, com confirmação.
- **Premissas:** todas.
- **Relatório:** a tese.
- **Retro:** data e teste.
- **Aprendizado:** caminho escolhido × veredito final, no `arkos.engine/aprendizado.jsonl`.

## 8. Regras duras

- Recomendação sem premissa por trás não sai.
- Os campos `numeros` e `privado` não entram em relatório de cliente.
- A suíte é autoral, em sala limpa: nada do money-* (CC BY-NC).
