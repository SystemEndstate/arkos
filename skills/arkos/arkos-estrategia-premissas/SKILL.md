---
name: arkos-estrategia-premissas
description: Registro único das premissas de um negócio - extrai as afirmações que precisam ser verdade para o plano funcionar, dá nota de impacto e confiança, marca os riscos críticos (impacto alto e confiança abaixo de 0,5), desenha o teste mais barato de cada um e atualiza a confiança só por evidência, com regra fixa. Use para "quais são os riscos", "o que preciso validar", "premissas", "hipóteses", "assumptions", "o que tem que ser verdade", e sempre que outra skill da suíte criar ou mudar premissa.
status: rascunho
versao: 0.1.0
modulos: [9, 10, 11, G]
depende_de: [arkos-perfil, jev]
---

# arkos-estrategia-premissas

**Princípio:** todo plano é uma pilha de apostas. Esta skill deixa as apostas **escritas**, **ranqueadas** e **testáveis**, e só deixa a confiança subir quando há evidência.

## 1. Quando usar e quando não usar

**Usar:**
- Depois de qualquer análise da suíte.
- Antes de gastar dinheiro.
- Na retro.
- Quando alguém disser "tenho certeza que...".

**Não usar:**
- Para guardar fato já comprovado e auditado (faturamento fechado, contrato assinado). Isso vai para o perfil.

## 2. Entradas

Lê `premissas.yaml`, `tese.md` e os arquivos da suíte que existirem.

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: modo, pergunta: "O que fazer", opcoes: [extrair do plano, revisar existentes, registrar evidência nova], obrigatoria: true }
- { id: texto, pergunta: "Plano, conversa ou evidência (cole ou dê o caminho)", obrigatoria: false }
```

## 3. Passos

### Modo "extrair"

1. **Ler o plano** e listar cada afirmação que, se for falsa, muda a decisão. Formato: sujeito + verbo + número ou condição ("dentistas de BH **pagam** R$ 400/mês **por** agenda cheia"). *Claude.*
2. **Categorizar:** cliente, problema, canal, preço, custo, operação, mercado ou regulatório. *Jev (`decide_many`).*
3. **Impacto** (alto, médio ou baixo): "se estiver errada, o negócio cai, encolhe ou só atrasa?". *Jev + revisão humana dos "alto".*
4. **Confiança inicial:**
   - sem evidência: ≤ 0,3;
   - evidência indireta (pesquisa, concorrente): até 0,5;
   - evidência direta (pagamento, pedido, contrato): até 0,8.
   - Nunca 1. *Regra fixa no script.*
5. **Taxa-base:** para as de impacto alto, perguntar "quantos negócios parecidos conseguem isso?". Se a resposta for "poucos", a confiança desce ao teto de 0,3. *Claude.*
6. **Teste mais barato** para cada risco crítico: o que fazer, critério de passar e de falhar escrito **antes**, custo e prazo. *Claude.*
7. **Gravar** pelo `scripts/premissas.py validar`. O id é sequencial (`P-001`) e o script recusa duplicatas por semelhança (o Jev confirma). *Script.*

### Modo "registrar evidência"

1. Ligar a evidência a uma ou mais premissas. *Claude.*
2. **O Jev classifica:** `sobe`, `mantem`, `baixa` ou `refuta`. *Jev.*
3. **O script aplica a regra comum da suíte:**
   - `sobe` +0,15, `mantem` 0, `baixa` −0,20, sempre entre 0,05 e 0,95;
   - `refuta`: status `refutada` e confiança 0,05;
   - o status vira `validada` quando a confiança ≥ 0,8 **e** houver evidência direta. *Script.*
4. Premissa de impacto alto refutada: avisar na hora e sugerir rodar a `arkos-estrategia` de novo (pivô). *Claude.*

### Modo "revisar"

- Listar os críticos (`arkos-estrategia/scripts/criticos.py`), os testes vencidos e as premissas sem atualização há mais de 30 dias.

## 4. Saída

- `workspace/<cliente>/<projeto>/estrategia/premissas.yaml` (formato validado por `scripts/premissas.py` da arkos-estrategia).
- Resumo com a lista dos riscos críticos, ordenada por impacto e confiança, e os testes desta semana.

## 5. Critério de pronto

- [ ] Toda premissa tem afirmação testável (com número ou condição), categoria, impacto e confiança.
- [ ] Todo risco crítico tem teste com critério de passar e de falhar, custo e prazo.
- [ ] Nenhuma confiança foi alterada fora do script.
- [ ] Nenhuma premissa duplicada.

## 6. Exceções

- **Plano sem nada testável** ("vamos ser os melhores"): devolver pedindo números ou condições. Cada frase vaga vira uma pergunta.
- **Evidência ambígua:** o Jev dá `mantem` e a premissa ganha nota "evidência ambígua: precisa de teste melhor".
- **Mais de 15 riscos críticos:** o plano tem apostas demais. Propor cortar escopo antes de testar.

## 7. Alimenta

- **Todas as skills da suíte e a banca:** os críticos.
- **Relatório:** a matriz de impacto × confiança.
- **Retro:** a foto das premissas antes e depois.
- **Aprendizado:** premissas refutadas por categoria e nicho, em `arkos.engine/aprendizado.jsonl`. Quando o padrão se repete entre clientes, vira conhecimento da base (com aprovação do dono).

## 8. Regras duras

- A confiança só muda pelo script e com evidência ligada.
- Nada de dado pessoal na evidência: descrever ("3 de 10 dentistas disseram..."), sem nome nem telefone.
- Premissa refutada não se apaga: muda de status, e o histórico fica.
