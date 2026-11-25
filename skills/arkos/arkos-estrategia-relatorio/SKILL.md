---
name: arkos-estrategia-relatorio
description: Consolida o estado da suíte arkos-estrategia (tese, premissas, modelo, preço, GTM, finanças, produto, diagnóstico, banca, retro) num relatório executivo local pelo gerador engine/report e num one-pager de uma página, em duas versões (interna e para cliente, sem dado privado). Riscos críticos sempre no topo. Use quando pedirem "relatório", "resumo da estratégia", "one-pager", "apresentar para o sócio", "o que decidimos", "executive summary", "strategy report", ou no fim de qualquer playbook da suíte.
status: rascunho
versao: 0.1.0
modulos: [N, G]
depende_de: [arkos-perfil, arkos-mercado, arkos-estrategia, arkos-estrategia-premissas, arkos-gate, engine/report (arkos-report.mjs), jev]
---

# arkos-estrategia-relatorio

A pergunta é: **o que o dono precisa ler em 2 minutos para decidir, e onde está o resto para quem quiser conferir?** A resposta vem primeiro e o detalhe depois. O relatório não cria conteúdo novo: só organiza o que as outras skills já gravaram.

## 1. Quando usar e quando não usar

**Usar:**
- No fim de todo playbook da suíte (`lancar-saas`, `lancar-infoproduto`, `validar-nicho-48h`, diagnóstico).
- Quando o dono pede "me mostra onde estamos", ou quer levar a estratégia a um sócio ou cliente.
- Depois de uma retro, para atualizar o relatório com o que mudou.

**Não usar:**
- No meio de uma skill, para mostrar resultado parcial: cada skill tem a própria saída.
- Para proposta comercial (módulo N, `arkos-oaas-proposta`) ou relatório de campanha (módulo 6).
- Quando o estado está vazio: sem ao menos `tese.md` e `premissas.yaml` não há o que consolidar.

## 2. Entradas

Lê a pasta `workspace/<cliente>/<projeto>/estrategia/` inteira, o perfil (respeitando `privado`) e a ficha do mercado (idioma da versão para cliente).

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa? (define o idioma da versão para cliente)", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: empresa, pergunta: "Para qual empresa ou projeto?", perfil: slug, obrigatoria: true }
- { id: publico, pergunta: "Para quem é", opcoes: [interno, cliente, socio-ou-investidor, as-duas-versoes], padrao: as-duas-versoes, obrigatoria: true }
- { id: formato, pergunta: "Formato", opcoes: [relatorio-e-one-pager, so-relatorio, so-one-pager], padrao: relatorio-e-one-pager, obrigatoria: false }
- { id: decisao, pergunta: "Qual decisão este relatório precisa apoiar?", padrao: "a pergunta do tese.md", obrigatoria: false }
```

## 3. Passos

1. **Inventário** com o `scripts/inventario.py`: listar quais arquivos do estado existem e a data de cada um, e copiar nota e veredito de `banca/*.md`. Arquivo com mais de 30 dias, ou mais antigo que uma retro posterior, entra marcado "desatualizado". *Script.*
2. **Riscos críticos:** filtrar em `premissas.yaml` as premissas com `impacto: alto` e `confianca < 0,5` e status diferente de `validada`. A filtragem é feita pelo `arkos-estrategia/scripts/criticos.py`, não pelo modelo. Elas vão para o topo, sempre. *Script.*
3. **Conclusão primeiro:** escrever a resposta à pergunta do `tese.md` em até 3 frases, seguida de 3 argumentos e da evidência de cada um. *Claude.*
4. **Consolidar a banca:** montar a tabela com persona, nota, veredito e a exigência principal de cada uma. As notas e os vereditos são copiados dos arquivos `banca/*.md`, nunca recalculados nem suavizados. Se uma persona disse `parar`, isso aparece no lead. *Script + Claude.*
5. **Montar o JSON do relatório** no formato de `engine/report/SCHEMA.md`, com `kind: "Relatório"` e estas seções, na ordem e cada uma só se houver dado:
   1. "A resposta" (`callout` + `text`);
   2. "Riscos críticos" (`table`);
   3. "O negócio em uma página" (`split`: modelo, preço, canal);
   4. "Os números" (`kpis` e `table` vindos do `financas-resultado.json`);
   5. "Produto e métricas";
   6. "O que a banca disse";
   7. "Todas as premissas" (`table`: id, afirmação, confiança, status);
   8. "Plano das próximas semanas" (`steps` com `owner` e `status`);
   9. "Fontes" (`sources`).
   *Claude.*
6. **Versão para cliente:**
   - remover todo campo `privado` e os `numeros` do perfil;
   - trocar valores absolutos por taxas quando o número for privado;
   - traduzir para o idioma do mercado (EUA: en-US; EU: o idioma local).
   Depois o Jev confere, linha a linha: "contém número privado do perfil?". Um "sim" bloqueia. *Claude + Jev.*
7. **Gerar os sites:** `node engine/report/arkos-report.mjs relatorio-<versao>.json --out workspace/<cliente>/<projeto>/estrategia/relatorio/<versao>`. *Script.*
8. **One-pager:**
   - um segundo JSON, com no máximo 4 seções: a resposta, os 3 números, os riscos críticos e as próximas 3 ações;
   - mesmo gerador;
   - PDF por Chrome headless (`--print-to-pdf`, processo com `CREATE_NO_WINDOW`, nenhuma janela);
   - conferir que o PDF tem 1 página.
   *Script.*
9. **Gate:** `arkos-gate` com o sub-gate de copy (antislop e humanizer-pt-br no BR), o checklist da §5 e o responsivo de 360 a 1800 px no portal do Maestro. *Skill.*
10. **Abrir:** `maestro open` na versão interna. Avisar o caminho da versão para cliente. *Skill.*

## 4. Saída

Em `workspace/<cliente>/<projeto>/estrategia/relatorio/`:
- `interno/index.html`: o relatório completo, com tudo.
- `cliente/index.html`: sem dado privado, no idioma do mercado.
- `one-pager.pdf` e `one-pager/index.html`.
- `relatorio-interno.json` e `relatorio-cliente.json`, as fontes, para refazer.
- `inventario.json`: o que entrou, a data de cada arquivo e o que estava desatualizado.

O lead de todo relatório termina com "o que eu faria nesta semana" (até 3 ações) e "o que pode matar isto" (o risco crítico de maior impacto).

## 5. Critério de pronto

- [ ] Os riscos críticos (impacto alto e confiança < 0,5) estão na primeira seção depois da resposta, e a lista veio do script.
- [ ] A resposta à pergunta do `tese.md` está nas 3 primeiras frases.
- [ ] As notas e os vereditos da banca batem, um a um, com os arquivos `banca/*.md`.
- [ ] Todo número do relatório tem origem num arquivo do estado (nenhum número novo).
- [ ] A versão para cliente passou pela checagem do Jev, com zero número privado.
- [ ] Os arquivos desatualizados estão marcados como tal.
- [ ] O one-pager tem exatamente 1 página.
- [ ] O site abre do disco e passou no responsivo de 360 a 1800 px.
- [ ] Tem "o que eu faria nesta semana" e "o que pode matar isto".

## 6. Exceções

- **Falta um arquivo do estado:** a seção não entra. O inventário diz o que faltou e qual skill o produz. Nunca preencher uma seção ausente com texto genérico.
- **A banca não rodou:** a seção "O que a banca disse" vira um aviso: "sem revisão da banca; recomendado antes de decidir".
- **Arquivos se contradizem** (ex.: o preço do `preco.md` difere do usado em `financas-entrada.json`):
  - mostrar a contradição num `callout` com `tone: warn`;
  - não escolher um lado;
  - devolver ao `arkos-estrategia`.
- **O resultado é "parar":** o relatório diz isso na primeira frase. Não suavizar.

## 7. Alimenta

- **Perfil:** nada. O relatório só lê.
- **Premissas:** nada novo. Só aponta contradições.
- **Relatório:** é a própria saída. O `report.json` fica ao lado para a próxima versão.
- **Retro:** o relatório anterior é a foto do "antes" que a retro compara.
- **Painel de execuções** (quando existir): o relatório entra no histórico da execução.

## 8. Regras duras

- O relatório não inventa nem recalcula: copia o que as skills gravaram e cita o arquivo.
- Riscos críticos sempre no topo, mesmo que o dono peça para tirar. Ele pode pedir um resumo à parte, sem remover a seção.
- Dado privado nunca na versão para cliente nem no one-pager.
- Nenhuma janela visível: gerador e Chrome rodam em segundo plano.
- Nota e veredito da banca não são editados aqui.
