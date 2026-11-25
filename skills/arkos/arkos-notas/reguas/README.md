# Réguas de nota da ARKOS

Uma régua por tipo de objeto, um arquivo `<id>.json` nesta pasta. Ids:
`criativo`, `saas`, `oferta`, `projeto-oaas`, `nicho-cliente`, `produto-vender`,
`cold-email`, `copy`, `prospect` (as 9 são escritas pelo Oboé).

## Formato

```json
{
  "regua": "oferta",
  "versao": "1.0.0",
  "atualizado": "2026-11-23",
  "acesso": "todos",
  "objeto": "o que é avaliado",
  "criterios": [
    {
      "id": "garantia",
      "nome": "garantia",
      "acesso": "todos",
      "peso": 0.15,
      "base_peso": "doc id + número que justifica o peso",
      "pergunta": "pergunta fechada para o Jev pontuar",
      "como_medir": "como se chega à nota",
      "evidencia_exigida": ["o que precisa estar presente"],
      "faixas": [
        {"min": 0,  "max": 24,  "descricao": "...", "exemplo": "..."},
        {"min": 25, "max": 49,  "descricao": "...", "exemplo": "..."},
        {"min": 50, "max": 74,  "descricao": "...", "exemplo": "..."},
        {"min": 75, "max": 89,  "descricao": "...", "exemplo": "..."},
        {"min": 90, "max": 100, "descricao": "...", "exemplo": "..."}
      ],
      "docs_base": ["oferta.garantias.xxx"]
    }
  ]
}
```

## Campos que o script lê (`scripts/notas.py`)

- `regua` (str), `acesso` (`todos|vip`: se `vip`, a régua inteira é bloqueada para membro).
- `criterios[]`: `id`, `peso` (float), `acesso` (`todos|vip`: critério `vip` sai do cálculo
  do membro), `pergunta` (para o Jev), `evidencia_exigida` (lista), `faixas` (5), `nome`.
- `criterios[].veto` (bool, opcional): critério-portão (política, lei, teste observável). Nota
  efetiva < 25 (inclui sem evidência = 0) reprova: veredito `descartar`, qualquer que seja a nota final.
- `criterios[].aplica_se` (texto, opcional): quando o critério se aplica (ex.: só peça UGC, só VSL).
  É documentação; na avaliação, o Claude/Jev marca o que não cabe via `nao_aplica: [ids]` no `aval.json`
  (critério inaplicável sai do cálculo e os pesos renormalizam — não conta 0).
- `criterios[].veto_abaixo` (número, opcional, padrão 25): limiar próprio do veto
  (ex.: prospect `encaixe_icp` veta abaixo de 50).
- `perfis` (opcional): `{"<nome>": {"pesos": {id: peso}, "veto": {id: limiar | null}}}`. Só vale
  quando o `aval.json` traz `"perfil": "<nome>"`; troca pesos e liga/desliga vetos (null desliga).
  Hoje: saas `pre_lancamento`/`no_ar`, oferta `loja`, produto-vender `loja`/`loja_consumivel`.
  `descricao`, `soma_1` e `inclui_vip` são documentação/teste. Perfil desconhecido = erro.
- `vetos_duros` (opcional): `[{"id", "descricao"}]`. Se o `aval.json` traz `"bandeiras": [id]`,
  veredito `descartar` (ex.: criativo `ia_efeito_categoria_vetada`, `persona_ia_sem_rotulo`).
  Bandeira desconhecida = erro.
- `aval.json` pode trazer `contexto` (vertical, canal, AOV, CM2...) que vai para o aprendizado.

## Aprendizado (`--aprendizado PATH`)

Linha `tipo: nota` com `id`, perfil, nota por critério (`notas_criterios`), vetos, bandeiras,
`nao_aplica` e `contexto`. O resultado real entra depois, append-only, por
`notas.py resultado --aprendizado PATH --id ID --gasto N --pedidos N --lucro-d30 N --lucro-d60 N
--decisao TEXTO --override-dono TEXTO` (linha `tipo: resultado` com o mesmo id). Com 30+ casos:
Spearman critério × lucro D60 antes de mexer em peso; corte recalibrado onde "lucro D60 > 0" passa de 50%.
- O resto (`base_peso`, `como_medir`, `docs_base`, `objeto`, `versao`, `atualizado`) é
  documentação e contexto para o Jev/Claude; o script os repassa, não os usa no cálculo.

## Regras de peso

- Critérios de acesso `todos` somam **1.0**.
- Critérios `vip` têm peso próprio (além do 1.0); para o plano VIP os pesos são
  renormalizados sobre todos os ativos (todos + vip); para membro, só os `todos`.

## Regras fixas (não vão no JSON; estão no script)

- Corte: aprovar ≥ 75 · ajustar 50–74 · descartar < 50 (decisão do usuário).
- Critério sem evidência conta 0. Mais de 40% do peso ativo sem evidência = `insuficiente`.
- "O que sobe a nota" = 3 correções por impacto = peso × (100 − nota).
