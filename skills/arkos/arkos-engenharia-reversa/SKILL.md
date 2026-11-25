---
name: arkos-engenharia-reversa
description: Entender como um sistema, site ou app de referência funciona por fora — comportamento, fluxo, API, estrutura — para reconstruir o equivalente de forma legítima (sem copiar código nem violar termos). Usa ferramentas de análise (rea/MCP, portal, captura de rede) e um ledger de obrigações de reconstrução com cobertura. Use em "como esse sistema funciona", "engenharia reversa de", "replicar o comportamento de", "mapear a API de", "entender o fluxo do concorrente".
status: rascunho
versao: 0.1.0
modulos: [dev]
depende_de: [arkos-portal]
---

# arkos-engenharia-reversa

Clone de sala limpa do "entender qualquer coisa": observa o comportamento público do alvo e mantém um **ledger de obrigações** — o que precisa ser reconstruído e com que evidência — medindo a cobertura. Não copia código nem burla termos; reconstrói o equivalente a partir do comportamento observado. Método público (caixa-preta + evidência).

## Quando usar e quando não usar

- **Usar:** entender um sistema/site/app de referência para construir o nosso equivalente.
- **Não usar:** copiar código protegido, burlar paywall/DRM ou violar os termos do alvo.

## Entradas

- O alvo (URL, app, binário público) e o objetivo da reconstrução.
- As evidências coletadas (o que se observou: tela, requisição de rede, string, comportamento).

## Passos

1. **Listar obrigações:** cada comportamento/recurso a reconstruir vira uma obrigação (`er.py obrigacao add`).
2. **Coletar evidência** por obrigação: estática (artefato público), dinâmica (comportamento via `arkos-portal`/observação) ou de rede (requisição/resposta). O ledger guarda o tipo e a referência.
3. **Medir cobertura:** obrigações com ≥1 evidência / total. As sem evidência ficam `em_aberto`.
4. **Reconstruir** só o que tem evidência; o que está em aberto não vira feature por suposição.
5. **Checar legitimidade:** nada de código copiado, nada de burlar termos; registrar a fonte de cada evidência.

## Saída

JSON: `{obrigacoes:[{id,descricao,evidencias:[{tipo,ref}],status}], cobertura, em_aberto:[...]}`.

## Critério de pronto

- [ ] Toda feature reconstruída tem obrigação com evidência (não suposição).
- [ ] A cobertura foi medida e as lacunas estão declaradas.
- [ ] Nenhuma evidência veio de código protegido ou de burlar termos.

## Exceções

- **Sem evidência para uma obrigação:** fica `em_aberto`, não entra na reconstrução.
- **Alvo bloqueia análise (termos/DRM):** parar nessa parte e declarar; não burlar.
- **Comportamento ambíguo:** registrar as hipóteses e o teste que decide.

## Alimenta

- O plano de construção do nosso equivalente; o `arkos-impacto` usa as obrigações como contrato a cobrir.

## Regras duras

- Nunca copiar código protegido nem burlar termos de uso/DRM.
- Feature só entra com evidência registrada; suposição fica em aberto.
- Registrar a fonte de cada evidência.
