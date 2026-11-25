---
name: arkos-monitor
description: Monitoramento do que a ARKOS colocou no ar (site, landing, API, webhook). Confere status HTTP, tempo de resposta, se o texto esperado está na página (pega domínio estacionado e página errada que respondem 200) e quantos dias faltam para o HTTPS vencer. Alerta só na 2ª falha seguida e aponta o rollback do deploy-infra. Só lê, não reinicia nem mexe em servidor. Use em "o site está no ar?", "monitorar o site", "checar se a landing caiu", "certificado vencendo", "uptime", e na etapa monitor do playbook deploy-infra.
status: instalada (2026-11-22)
versao: 1.0.0
modulos: [I, O]
depende_de: []
---

# arkos-monitor

## Passos

1. **Listar os alvos** em `workspace/<cliente>/<projeto>/monitor/alvos.json`:
   `[{"nome": "landing", "url": "https://...", "esperar_status": 200, "contem": "Agende", "max_ms": 3000, "tls_min_dias": 14}]`
   O `contem` é obrigatório na prática: escolha um texto que só existe na página certa.
2. **Checar:** `python scripts/monitor.py checar --alvos alvos.json --estado estado.json --saida workspace/<cliente>/<projeto>/monitor/`
3. **Agendar** (opcional, com OK do prestador): uma rotina local de 15 em 15 minutos com o mesmo comando, oculta (sem janela).
4. **Vermelho com `alertar: true`:** avise o prestador. O próximo passo vem no campo `proximo`: rollback pelo `deploy-infra`.

## Cores

- **verde:** status certo, texto presente, rápido e HTTPS com folga.
- **amarelo:** lento, sem HTTPS, ou certificado vencendo em menos de 14 dias.
- **vermelho:** fora do ar, status errado, texto ausente ou certificado vencendo em menos de 3 dias ou quebrado.

## Regras duras

1. **Só GET.** Nunca reinicia, faz redeploy ou mexe em DNS por conta própria. Correção é no `deploy-infra`, com a guarda-escrita.
2. **"Deu 200" não basta:** sem o texto esperado é vermelho.
3. **Alerta só na 2ª falha seguida**, para não gerar alarme falso por soluço de rede. Recuperou, zera.
4. **Só `http(s)`.** Outro esquema é recusado.
5. Aviso ao cliente sobre queda passa pela `arkos-guarda-envio`.

## Pronto quando

- todo alvo do projeto aparece com cor e problemas listados;
- o resultado está salvo em `monitor/`.

## Exceções

- **fora_do_ar:** porta fechada ou DNS sem resposta. Sai vermelho com `proximo` apontando o rollback do `deploy-infra`, e alerta na 2ª vez.
- **rollback:** é o do `deploy-infra` (voltar a última versão que funcionava). O monitor só confirma a volta na checagem seguinte.

## Testes

`python -m unittest discover -s scripts/tests`: 3 testes contra um servidor HTTP local de verdade, cobrindo o verde, a página estacionada com 200, o 500, o esquema inválido, o sem HTTPS, a porta fechada, a histerese de 2 falhas e a recuperação.
