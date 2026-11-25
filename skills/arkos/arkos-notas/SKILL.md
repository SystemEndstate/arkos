---
name: arkos-notas
description: Sistema de notas da ARKOS. Pontua um objeto (criativo, SaaS, oferta, projeto OaaS, nicho de cliente, produto a vender, cold-email, copy, prospect) contra uma régua de critérios com peso e evidência, por script, e devolve nota 0–100, veredito (aprovar ≥ 75 · ajustar 50–74 · descartar < 50), nota por critério e as 3 correções que mais sobem a nota. O Jev pontua cada critério; o Claude revisa e escreve a justificativa. Use em "dar nota", "isso é bom?", "vale a pena?", "avaliar oferta/criativo/nicho/produto/copy", "score", "aprovar ou não", "qualificar prospect".
status: instalada (promovida em 2026-11-23)
versao: 0.1.0
modulos: [auditoria]
depende_de: [arkos-perfil, arkos-gate, jev]
fontes_conferidas_em: 2026-11-23
---

# arkos-notas

**Princípio:** nota sem evidência é opinião. Cada critério só pontua com prova, a nota final é ponderada e **sai do script**, e o corte é fixo. O Jev dá o Sistema 1 (pontua cada critério); o Claude revisa e escreve o porquê. Imparcialidade: a nota segue os dados, não o que o usuário quer ouvir.

## 1. As 9 réguas

Uma régua por tipo de objeto, cada uma num JSON em `reguas/<id>.json` (formato em `reguas/README.md`):

| id | objeto | acesso |
|---|---|---|
| `criativo` | anúncio/criativo | todos (critérios UGC e criativo de loja só VIP) |
| `saas` | ideia/produto SaaS | todos |
| `oferta` | oferta | todos (oferta de e-commerce só VIP) |
| `projeto-oaas` | projeto OaaS | todos |
| `nicho-cliente` | nicho de cliente | todos |
| `produto-vender` | produto a vender | todos (produto físico de loja só VIP) |
| `cold-email` | sequência de cold-email | todos |
| `copy` | peça de copy | todos (VSL/advertorial só VIP) |
| `prospect` | lead/prospect | todos |

Nicho de cliente e produto a vender são **duas réguas separadas** (decisão do usuário).

## 2. Entrada

```yaml
- { id: regua, pergunta: "Qual régua?", opcoes: [criativo, saas, oferta, projeto-oaas, nicho-cliente, produto-vender, cold-email, copy, prospect], obrigatoria: true }
- { id: plano, pergunta: "Plano da licença", opcoes: [vip, membro], padrao: membro, obrigatoria: true }
- { id: objeto, pergunta: "O que está sendo avaliado (nome/slug)", obrigatoria: true }
- { id: evidencias, pergunta: "Para cada critério da régua: a nota 0–100 e a evidência que a sustenta", obrigatoria: true }
```

O Claude monta o `aval.json`:

```json
{"objeto": "garantia-30-dias",
 "criterios": {"garantia": {"nota": 80, "evidencia": "texto literal da garantia incondicional de 30 dias"},
               "preco": {"nota": 60, "evidencia": "preço R$ 97 vs. margem 70%"}}}
```

## 3. Passos

1. **Escolher a régua** pelo tipo de objeto e **o plano** pela licença (`arkos-licenca`). Régua ou critério de acesso `vip` não existe para membro: o script tira do cálculo e renormaliza os pesos. *Skill.*
2. **Levantar evidência de cada critério.** Sem evidência o critério **não pontua** (conta 0). Se mais de 40% do peso ativo ficar sem evidência, a nota é `insuficiente` e não vale. *Claude.*
3. **Pontuar cada critério** (0–100) pelas faixas da régua. Com `--jev`, o Jev pontua primeiro (Sistema 1) e o Claude revisa; sem Jev ou se ele falhar, o Claude dá a nota direto (o script não trava). *Jev + Claude.*
4. **Rodar o script:**
   ```
   python ~/.claude/skills/arkos-notas/scripts/notas.py pontuar \
     --regua <id> --plano <vip|membro> --entrada aval.json \
     --aprendizado arkos.engine/aprendizado.jsonl [--jev] --out nota.json
   ```
   Devolve nota ponderada, veredito, nota por critério com evidência e **o que sobe a nota** (3 correções por impacto = peso × (100 − nota)). *Script.*
5. **Escrever o veredito:** nota no topo do relatório, as 3 correções em ordem de impacto e, quando discordar do script, o porquê ao lado (não muda o número). *Claude.*
6. **Gate:** `notas.py pronto nota.json` antes do `arkos-gate`. Nos fluxos, a etapa `nota` roda antes do portão: a etapa seguinte só anda com veredito `aprovar` (≥ 75) ou com aceite registrado. *Script + skill.*

## 4. Corte (fixo, decisão do usuário)

- **aprovar** nota ≥ 75
- **ajustar** 50 ≤ nota < 75
- **descartar** nota < 50
- **insuficiente** mais de 40% do peso ativo sem evidência (nota não confiável; nem aprova, nem descarta — falta prova)

Dois portões além da soma:
- **veto** (`"veto": true` no critério): critério-portão (política, lei, teste observável/atribuível). Nota efetiva < 25 — inclui sem evidência (= 0) — **reprova** (veredito `descartar`) seja qual for a nota final. Política e lei são portão, não parcela da soma.
- **não aplicável** (`"nao_aplica": [ids]` na entrada): critério que não cabe no objeto (ex.: autenticidade UGC numa peça que não é UGC; VSL numa landing comum) **sai do cálculo** e os pesos renormalizam sobre os aplicáveis — não conta 0.

## 5. Critério de pronto

- [ ] A régua certa para o tipo de objeto e o plano certo pela licença.
- [ ] Todo critério pontuado tem evidência; nenhum critério VIP apareceu em avaliação de membro.
- [ ] A nota, o veredito e as 3 correções vieram do script.
- [ ] `notas.py pronto` deu verde (sem pendente, sem `insuficiente`).
- [ ] A pontuação foi registrada em `aprendizado.jsonl`.

## 6. Exceções e imparcialidade

- **Régua VIP pedida por membro** (`bloqueada`): resposta "Isso faz parte do plano VIP"; não revelar o critério.
- **Jev fora do ar:** o Claude pontua e marca a origem `claude`; a nota não trava.
- **Número não comprovado / viés de sobrevivência:** marcar ao lado da evidência; a nota não sobe por promessa sem prova.
- **Nota baixa não trava o gate por si** — quem decide seguir é o fluxo (ex.: oferta só segue com ≥ 75 ou aceite registrado).

## 7. Alimenta

- **Aprendizado:** `arkos.engine/aprendizado.jsonl` com régua × objeto × nota × veredito; o `resultado_real` entra depois para a retro recalibrar os pesos.
- **Gate/fluxos:** a etapa `nota` roda antes do `arkos-gate` (mapa em `engine/fluxos/notas.mjs`).

## 8. Regras duras

- Critério sem evidência conta 0. Nunca pontuar por impressão.
- Corte fixo 75/50; não afrouxar por pedido.
- Régua e critério de acesso `vip` nunca entram para membro, e o nome da régua não vaza (limite B).
- Origem oculta (limite A): `docs_base` e `base_peso` da régua são internos — o script não os põe na saída e nunca vão ao usuário.
- O número sai do script; o Claude explica, não muda.
