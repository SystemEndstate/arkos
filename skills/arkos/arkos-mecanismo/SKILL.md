---
name: arkos-mecanismo
description: Ideação do mecanismo único da oferta na ARKOS. Acha a causa do problema (o vilão), gera de 5 a 8 candidatos a mecanismo (o "como" que só esta oferta tem), pontua por script (dor, credibilidade, novidade, especificidade, provabilidade), veta promessa proibida ou sem prova, dá nome e define o teste de prova. Use em "mecanismo único", "mecanismo da oferta", "diferencial da oferta", "por que o meu funciona", "USP", "big idea", "unique mechanism", "nome do método", "mecanismo do problema".
status: instalada (promovida em 2026-11-22)
versao: 0.1.0
modulos: [10, 8, 7]
depende_de: [arkos-perfil, arkos-mercado, arkos-intake, arkos-oferta, arkos-gate, jev]
fontes_conferidas_em: 2026-11-22
---

# arkos-mecanismo

**Princípio:** mercado sofisticado já ouviu toda promessa. O que ainda convence é **por que o problema existe** (mecanismo do problema) e **por que esta solução funciona quando as outras falharam** (mecanismo da solução). Mecanismo sem prova é só nome bonito: não entra.

## 1. Quando usar e quando não usar

**Usar:**
- Passo 9 do `arkos-oferta` (mecanismo), no `oferta-irresistivel` e no `copy-venda`.
- Quando os anúncios cansam rápido e todos os concorrentes prometem a mesma coisa (sofisticação alta).
- Para dar nome a um método, serviço ou produto que já funciona mas é descrito de forma genérica.

**Não usar:**
- Sem oferta definida (para quem, resultado, preço): primeiro `arkos-oferta`.
- Para inventar diferença que o produto não tem. Se o "como" é igual ao dos concorrentes, o mecanismo é de **comunicação** (a explicação mais clara do mercado), e isso é dito ao dono.
- Mercado inconsciente do problema (consciência baixa): o trabalho é educação, não mecanismo.

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: cliente, pergunta: "Cliente (slug)", obrigatoria: true }
- { id: projeto, pergunta: "Projeto (slug)", obrigatoria: true }
- { id: oferta, pergunta: "Oferta em uma frase (para quem, resultado, prazo)", perfil: oferta.promessa, obrigatoria: true }
- { id: como_funciona, pergunta: "Como o produto ou serviço entrega o resultado, passo a passo, sem marketing", obrigatoria: true }
- { id: tentativas, pergunta: "O que o cliente já tentou antes e por que não deu certo", perfil: dores, obrigatoria: true }
- { id: concorrentes, pergunta: "Como os 3 principais concorrentes explicam o que fazem", perfil: concorrentes, obrigatoria: false }
- { id: provas, pergunta: "Provas que existem hoje: números, casos, demonstração, estudo, certificação", obrigatoria: true }
```

**Pasta das entregas:** `workspace/<cliente>/<projeto>/oferta/` (`mecanismo.md`, `mecanismo-candidatos.json`, `mecanismo-pontos.json`).

## 3. Passos

1. **Nível de consciência e sofisticação:** o Jev classifica o mercado (consciência: inconsciente, do problema, da solução, do produto, mais consciente; sofisticação de 1 a 5). Consciência baixa: avisar e sugerir conteúdo educativo antes. *Jev.*
2. **Mecanismo do problema:** escrever a **causa** que o cliente ainda não enxerga, em uma frase ("as faltas não acontecem por esquecimento, e sim porque a confirmação chega quando o paciente já remarcou de cabeça"). Ela explica por que as tentativas anteriores falharam. *Claude.*
3. **Candidatos:** de 5 a 8 mecanismos da solução, de famílias diferentes:
   - **processo** (passos com nome),
   - **ingrediente ou componente** (o que tem dentro),
   - **sequência ou tempo** (quando cada coisa acontece),
   - **tecnologia ou ferramenta** (o que faz a parte difícil),
   - **inversão** (o contrário do que o mercado faz),
   - **critério** (o que se mede e os outros não).
   Cada um com: `nome`, `como_funciona`, `causa` que ele resolve, `prova` existente (ou vazio), `promessa`. *Claude.*
4. **Notas:** de 1 a 5 em dor, credibilidade, novidade, especificidade e provabilidade, cada nota com uma linha de justificativa no `mecanismo-candidatos.json`. *Claude.*
5. **Pontuar e vetar:**
   ```
   python ~/.claude/skills/arkos-mecanismo/scripts/mecanismo.py pontuar workspace/<cliente>/<projeto>/oferta/mecanismo-candidatos.json \
     --out workspace/<cliente>/<projeto>/oferta/mecanismo-pontos.json
   ```
   Pesos fixos (dor 0,25 · credibilidade 0,25 · novidade 0,20 · especificidade 0,15 · provabilidade 0,15). Mínimo 3,5. Vetos: sem prova, sem causa, promessa proibida (cura, garantido, sem esforço, milagre, renda garantida...) e afirmação que exige prova sem prova citada (%, "comprovado", "em X dias", "o melhor"). *Script.*
6. **Nome:** de 3 a 5 nomes para o escolhido: concretos, fáceis de dizer em voz alta, sem marca de terceiro e sem promessa proibida. O Jev escolhe o mais claro para o ICP (escolha múltipla). *Claude + Jev.*
7. **Teste de prova:** o que mostrar em 30 dias para provar o mecanismo (demo gravada, antes e depois com permissão, número de clientes, estudo). Vai como premissa com `teste` e `prazo_teste`. *Claude.*
8. **Escrever `mecanismo.md`** com as seções do `pronto` e rodar:
   ```
   python ~/.claude/skills/arkos-mecanismo/scripts/mecanismo.py pronto .../oferta/mecanismo.md .../oferta/mecanismo-pontos.json
   ```
   *Script.*
9. **Gate:** `arkos-gate`, com o sub-gate de copy (antislop e humanizer-pt-br no BR). *Skill.*

## 4. Saída

`mecanismo.md` com: **Mecanismo escolhido**, **Como funciona** (3 a 5 passos), **Por que o problema existe**, **Prova** (a que existe e o teste de 30 dias), **Nome** (o escolhido e os outros), **Candidatos** (tabela com notas e vetos, vinda do script), **O que eu faria nesta semana** e **O que pode matar isto**. Mais a frase-núcleo: "[Resultado] sem [dor das tentativas] porque [mecanismo]".

## 5. Critério de pronto

- [ ] O mecanismo do problema (a causa) está escrito e explica as tentativas que falharam.
- [ ] Pelo menos 5 candidatos de pelo menos 3 famílias diferentes.
- [ ] Toda nota tem justificativa; o ranking e os vetos vieram do script.
- [ ] O escolhido tem prova existente ou um teste de prova com prazo.
- [ ] O `mecanismo.py pronto` deu verde (seções completas, escolhido = o do script, nenhuma promessa proibida).
- [ ] O `arkos-perfil` recebeu `mecanismo.nome`, `como_funciona` e `prova`, com confirmação.

## 6. Exceções

- **Nenhum candidato passa** (`resultado_ruim`): voltar ao passo 3 com outra família, ou rodar primeiro o teste de prova do melhor. Nunca baixar o mínimo nem tirar o veto para passar.
- **Menos de 3 candidatos ou nota sem justificativa** (`entrada_incompleta`): o script para e lista o que falta.
- **O produto não tem nada diferente:** registrar "mecanismo de comunicação" e dizer ao dono que a diferença real precisa ser criada (garantia, processo, bônus) no `arkos-oferta`.
- **Prova depende de dado de cliente:** só com permissão por escrito; sem nome nem foto de pessoa sem autorização (LGPD, GDPR).
- **Retrabalho** depois da entrega: nova versão do `mecanismo.md`; a anterior fica.

## 7. Alimenta

- **Perfil:** `mecanismo.nome`, `mecanismo.como_funciona`, `mecanismo.prova`.
- **Oferta e copy:** a frase-núcleo vai para `arkos-oferta`, `arkos-conversa`, `hook-writing`, `arkos-tiktok-ads` e `arkos-kwai-ads`.
- **Premissas:** "o público acredita no mecanismo X" (categoria `cliente`), com o teste de prova.
- **Aprendizado:** mecanismo × CTR e conversão dos anúncios que o usaram.

## 8. Regras duras

- A conta e os vetos são do script; o Claude só gera, justifica e nomeia.
- Sem prova, sem mecanismo: o candidato fica como hipótese a testar.
- Nenhuma promessa de cura, resultado garantido, enriquecimento ou "sem esforço", em nenhum mercado.
- Nunca usar nome ou marca de terceiro no nome do mecanismo.
