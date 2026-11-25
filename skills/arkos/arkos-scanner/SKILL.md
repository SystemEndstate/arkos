---
name: arkos-scanner
description: Varredura estática de uma skill (SKILL.md + scripts) ANTES de instalar no pacote da ARKOS. Procura shell destrutivo, código que baixa e executa da rede, segredo no código, git destrutivo, janela visível no Windows (regra da casa) e ofuscação. Use antes de instalar qualquer skill nova, quando o arkos-roteador sugerir algo de fora, e na etapa de homologação do arkos-atualizar.
status: rascunho
versao: 0.1.0
modulos: [dev]
depende_de: [arkos-decisor]
---

# arkos-scanner

Clone de sala limpa do scanner de skills: lê o conteúdo de uma pasta de skill e aponta padrões perigosos por regra determinística, sem executar nada. Regra fixa fica em análise estática; a triagem do que é falso positivo passa pelo `arkos-decisor` (Sistema 1). Não instala: só decide se é seguro instalar.

## Quando usar e quando não usar

- **Usar:** antes de instalar skill nova; ao homologar versão (`arkos-atualizar`); quando o roteador topar algo de fora do pacote.
- **Não usar:** como antivírus geral de código de aplicação (é para pacote de skill).

## Entradas

- Caminho da pasta da skill (SKILL.md + `scripts/`).
- Opcional: lista de regras extra do perfil da casa.

## Passos

1. `scanner.py scan <pasta>` varre os arquivos de texto e casa cada linha com as regras.
2. Classifica por severidade: **alto** (rede→exec, shell destrutivo, segredo no código, git destrutivo) e **médio** (lê `.env`/segredo, janela visível no Windows, ofuscação).
3. Achado de severidade duvidosa vai ao `arkos-decisor` para triar falso positivo (não baixa a severidade sozinho).
4. Veredito: **bloquear** se houver qualquer alto; **revisar** se só médios; **liberar** se limpo.

## Saída

JSON: `{veredito, resumo:{alto,medio}, achados:[{arquivo,linha,regra,severidade,trecho}]}`. Exit 0 limpo, 1 só médios, 2 com alto.

## Critério de pronto

- [ ] Todo arquivo de texto da pasta foi lido.
- [ ] Nenhum alto ficou sem aparecer no resumo.
- [ ] A regra de janela visível (DETACHED_PROCESS, Start-Process sem -WindowStyle Hidden) foi conferida.

## Exceções

- **Pasta inexistente/vazia:** erro claro, exit 2.
- **Arquivo binário/grande:** pula o binário; trunca a leitura por tamanho.
- **Só médios:** veredito `revisar`, nunca `liberar` automático.

## Alimenta

- `arkos-atualizar` (gate de homologação) e `arkos-roteador` (não roteia para o que o scanner bloqueou).

## Regras duras

- Nunca executar o código escaneado.
- Qualquer `alto` bloqueia; o humano decide a exceção, não o script.
- A regra de janela visível no Windows é obrigatória (ordem do usuário).
