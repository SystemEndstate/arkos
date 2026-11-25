---
name: arkos-prospeccao-local
description: Montar uma lista de negócios locais (nicho + cidade) a partir de fontes públicas permitidas, respeitando os termos de uso de cada fonte. Normaliza, deduplica e enriquece o básico (nome, categoria, telefone, endereço, site), e deixa claro que achar um número público NÃO autoriza contato — só depois do opt-in. Use em "prospectar negócios locais", "lista de leads do nicho", "empresas de X na cidade Y", "montar base de prospecção".
status: rascunho
versao: 0.1.0
modulos: [prospeccao]
depende_de: [arkos-lead-merge, arkos-guarda-envio]
---

# arkos-prospeccao-local

Clone de sala limpa (substitui o sellbird, que é AGPL): monta a lista de negócios locais a partir de fontes **públicas e permitidas**, respeitando os termos de cada uma. Não raspa o que o termo proíbe e não trata número achado como permissão de contato. O método é público (coleta permitida + dedup + opt-in).

## Quando usar e quando não usar

- **Usar:** levantar negócios de um nicho numa cidade, de fontes cujo uso é permitido.
- **Não usar:** fonte que proíbe raspagem nos termos; disparar mensagem sem opt-in (isso é bloqueado pelo `arkos-guarda-envio`).

## Entradas

- `nicho`, `cidade`, e a **fonte** com a confirmação de que o uso é permitido (`fonte_permitida`).
- O export/dados já coletados da fonte permitida (a coleta em si respeita robots/ToS).

## Passos

1. **Trava de termos:** sem `fonte_permitida=true`, recusar (não processar).
2. **Normalizar** cada registro: nome, categoria, telefone (dígitos), endereço, site.
3. **Deduplicar** por nome+telefone normalizados.
4. **Marcar consentimento:** cada lead sai com `contato_autorizado=false` e o aviso de que número público não autoriza contato (só opt-in, por template, pela Cloud API — regra da casa).
5. **Entregar** ao `arkos-lead-merge` (importa pro CRM); o envio, quando houver, passa pelo `arkos-guarda-envio`.

## Saída

JSON: `{fonte, permitida, leads:[{nome,categoria,telefone,endereco,site,contato_autorizado:false}], descartados_dup, aviso}`.

## Critério de pronto

- [ ] A fonte estava marcada como permitida (termos respeitados).
- [ ] Duplicados foram removidos.
- [ ] Todo lead saiu com `contato_autorizado=false` e o aviso de opt-in.

## Exceções

- **Fonte não permitida:** recusar e explicar; não processar.
- **Registro sem telefone/endereço:** manter com o campo vazio, marcado `incompleto`.
- **Pedido de disparo direto:** barrar — contato só após opt-in (pelo `arkos-guarda-envio`).

## Alimenta

- `arkos-lead-merge` (CRM) e, depois do opt-in, `arkos-conversa`.

## Regras duras

- Respeitar robots/ToS de cada fonte; sem `fonte_permitida`, não processa.
- Número público nunca autoriza contato: opt-in obrigatório antes de qualquer envio.
- Sem dado sensível além do básico de negócio público.
