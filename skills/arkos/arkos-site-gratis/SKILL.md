---
name: arkos-site-gratis
description: Põe o site do cliente no ar com domínio e hospedagem grátis, usando o nome do projeto (DigitalPlat FreeDomain + Cloudflare Pages), ou com domínio próprio quando o cliente paga. Cuida do DNS, do HTTPS e do aviso honesto de riscos. Use em "colocar o site no ar", "publicar o site", "domínio grátis", "hospedagem grátis", "subir a landing", "free domain", "deploy site", e na etapa dominio/publicar do playbook site-landing.
status: instalada (promovida em 2026-11-22)
versao: 0.1.0
modulos: [2, O, D]
depende_de: [arkos-perfil, arkos-mercado, arkos-guarda-escrita, arkos-gate, cloudflare-pages]
fontes_conferidas_em: 2026-11-22
---

# arkos-site-gratis

**Princípio:** um site de MVP sai do ar para o mundo sem gastar nada. Mas o grátis tem preço em confiança, e o prestador precisa saber disso **antes**. Para cliente pagante, o padrão é o domínio próprio.

## 1. Quando usar e quando não usar

**Usar:**
- Etapas `dominio` e `publicar` do playbook `site-landing`, que entra nas esteiras de agência OaaS, lançamento de SaaS e serviço local BR.
- Landing de teste, validação de nicho (`validar-nicho-48h`), MVP ou página de evento.

**Não usar:**
- App com backend, banco ou login: vai para a VPS pelo `deploy-infra` (Easypanel).
- Loja com pagamento em domínio grátis: compre o domínio.
- Quando o cliente já tem domínio e hospedagem funcionando: só publique lá.

## 2. Entradas

```yaml
- { id: mercado, pergunta: "Mercado: Brasil, EUA ou Europa?", opcoes: [BR, EUA, EU], perfil: mercado, obrigatoria: true }
- { id: hospedagem, pergunta: "Onde o site vai ficar no ar?", opcoes: ["grátis: domínio com o nome do projeto + Cloudflare Pages", "domínio próprio (pago) + Cloudflare Pages", "VPS do usuário (Easypanel)"], obrigatoria: true }
- { id: nome, pergunta: "Nome para o domínio (padrão: o slug do projeto)", padrao: "<projeto>", obrigatoria: true }
- { id: titular, pergunta: "Em nome de quem fica o domínio e a conta?", opcoes: [cliente, prestador], padrao: cliente, obrigatoria: true }
- { id: pasta, pergunta: "Pasta do site pronto (build estático)", padrao: "workspace/<cliente>/<projeto>/site/", obrigatoria: true }
```

**Regra da titularidade:** o domínio do cliente fica **em nome do cliente**, na conta dele. A DigitalPlat permite **1 domínio por conta** e pede dados reais. Com o domínio no nome do prestador, o cliente fica preso a ele.

## 3. O que a ARKOS sabe (conferido em 22/11/2026)

**Domínio grátis: DigitalPlat FreeDomain**
- Fonte: `github.com/DigitalPlatDev/FreeDomain`, com ~209 mil estrelas, AGPL-3.0 e último push em 12/08/2026. O código do painel está em `DigitalPlatDev/Domain-OSS`. A ARKOS só segue o tutorial e não copia código.
- Sufixos atuais: `.dpdns.org`, `.us.kg`, `.qzz.io`, `.xx.kg` e `.qd.je`. Ex.: `clinica-lumiere.dpdns.org`.
- Limite: **1 domínio por conta**. Subdomínios embaixo dele são livres (`lp.clinica-lumiere.dpdns.org`).
- A DigitalPlat **não tem editor de DNS**: ela só delega os nameservers para fora (Cloudflare). Os registros A, CNAME, MX e TXT ficam na Cloudflare.
- Os sufixos, as pausas de cadastro, a exigência de "slot", a cobrança e a janela de renovação **podem mudar**. Ler sempre os avisos do painel (`dash.domain.digitalplat.org`) antes. Se o painel mostrar cobrança ou slot, **parar e perguntar**.
- O cadastro exige nome, e-mail, telefone e endereço **reais**, e a fonte proíbe dado fictício. A denúncia de abuso é tratada por e-mail. O canal antigo no Telegram foi invadido, então não confiar em mensagem vinda dele.

**Alternativas de domínio grátis**
- `eu.org`: grátis, aprovação manual e lenta (semanas).
- `is-a.dev`: só para projeto pessoal de desenvolvedor. **Não serve para cliente.**

Essas duas não foram conferidas na fonte hoje. Conferir antes de usar.

**Hospedagem**

| Opção | Grátis | Uso comercial | Notas |
|---|---|---|---|
| **Cloudflare Pages** (padrão) | sim | não está proibido nas páginas oficiais consultadas. **Confirmar nos termos self-serve antes do 1º cliente** | 500 builds/mês, 1 build por vez, 20 min por build, 100 domínios por projeto, 20 mil arquivos, SSL automático, endereço `<nome>.pages.dev` |
| **Netlify Free** (reserva) | sim, 300 créditos/mês, sem cartão | **permitido** (blog oficial) | Créditos acabaram = espera o mês ou paga |
| **Vercel Hobby** | sim | **proibido**: só uso pessoal e não comercial (termos e fair use) | Avisar o prestador; site de cliente exige o plano Pro |
| **GitHub Pages** | sim | não serve para loja ou transação comercial | Só estático simples, de projeto ou portfólio |

**Domínio de verdade não é grátis:**
- `.com.br`: cerca de **R$ 40/ano** no registro.br, valor citado por terceiros e a conferir no registro.br. Exige CPF ou CNPJ.
- `.com`: a Cloudflare Registrar cobra o preço de custo, sem margem.

Para cliente pagante, recomendar **sempre** o domínio próprio. O grátis é para MVP, teste e validação.

## 4. Passos

1. **Avisar e decidir.** Mostrar ao prestador os riscos do grátis (§6) e o custo do próprio. O prestador escolhe a `hospedagem`. *Claude.*
2. **Perguntar antes de criar conta.** Dizer quais contas serão criadas (DigitalPlat e Cloudflare), em nome de quem e quais dados cada uma pede. **Nunca** preencher os dados pessoais do prestador ou do cliente sem um "sim" explícito. O cadastro é feito pela própria pessoa: a ARKOS guia, não digita senha. Portão `guarda_escrita`. *Claude.*
3. **Criar a zona na Cloudflare.** Plano Free, "Add a site", com o domínio completo (ex.: `clinica-lumiere.dpdns.org`). Copiar **os dois** nameservers que ela der. *Pessoa, com guia.*
4. **Registrar o domínio grátis.** No painel da DigitalPlat:
   - Register → nome + sufixo → Check availability;
   - conferir a grafia, o sufixo e a cobrança ou slot mostrados;
   - colar os 2 nameservers da Cloudflare;
   - enviar **uma vez**.
   Se a resposta for ambígua, olhar a Domain List antes de reenviar. *Pessoa, com guia.*
5. **Conferir a delegação.** `nslookup -type=NS <dominio>` ou `dig NS <dominio>`. A resposta tem que trazer os mesmos NS da Cloudflare. A propagação pode levar de minutos a horas. *Script (Bash, em segundo plano).*
6. **Publicar.**
   - **Pages direto** (detalhes na skill `cloudflare-pages`): `npx wrangler pages project create <projeto>` e depois `npx wrangler pages deploy <pasta> --project-name <projeto>`. O login no wrangler é feito pela pessoa (`! npx wrangler login`).
   - **Pages pelo git:** repositório ligado no painel.
   - **Netlify:** `npx netlify deploy --prod --dir <pasta>`.
   - **VPS:** passar para o `o-maestro-vps` / Easypanel. **Não criar projeto no Easypanel**: o usuário cria.
   - Anotar a URL `*.pages.dev`. *Script + portão.*
7. **Ligar o domínio.** Pages → projeto → Custom domains → adicionar o domínio. Como a zona está na mesma conta, a Cloudflare cria o CNAME sozinha. *Pessoa ou API, com portão.*
8. **Conferir o HTTPS.** `curl -sI https://<dominio>` deve responder 200 ou 3xx, com certificado válido. Conferir também o `*.pages.dev`. Abrir no portal do O Maestro, de 360 a 1800 px. *Script.*
9. **Registrar.** Gravar `workspace/<cliente>/<projeto>/site/no-ar.md` com:
   - domínio, sufixo, titular e data de expiração (vista no painel);
   - provedor, URL `pages.dev` e conta dona (sem senha);
   - lembretes de renovação em 90, 60, 30 e 7 dias.
   No `saida.json` vão o domínio e a URL em `campos`, e a escolha grátis × próprio em `decisoes`. *Claude.*

## 5. Critério de pronto

- [ ] O prestador viu os riscos do grátis e escolheu a hospedagem por escrito.
- [ ] Nenhuma conta criada sem "sim", e os dados pessoais foram digitados só pela pessoa.
- [ ] O domínio está no nome de quem vai ser dono (o cliente, por padrão).
- [ ] Os NS respondem com os nameservers da Cloudflare.
- [ ] O HTTPS é válido no domínio e no `*.pages.dev`.
- [ ] A Vercel Hobby não foi usada para site comercial.
- [ ] O `no-ar.md` tem a data de expiração e os lembretes.

## 6. Exceções e riscos

- **Riscos do grátis** (sempre avisar):
  - menos confiança do visitante e dos anúncios: a Meta e o Google podem tratar o sufixo grátis com desconfiança;
  - e-mail no domínio grátis tem entregabilidade ruim: não usar para disparo;
  - o provedor pode suspender ou mudar as regras;
  - 1 domínio por conta;
  - SEO fraco para marca.
- **Domínio pendente ou recusado:** ler o motivo no painel (nome indisponível, NS inválido, dado incompleto, sufixo pausado). O site segue no `*.pages.dev` enquanto isso.
- **Suspensão ou expiração:** corrigir o DNS não resolve. Ver o status no painel. O prestador decide entre outro sufixo e o domínio próprio, e o `*.pages.dev` segue no ar.
- **Cobrança ou slot no painel:** parar. É custo, então entra o portão `confirmacao_custo`.
- **Builds no limite (500/mês):** publicar pelo `wrangler deploy` do build local ou juntar os commits.
- **Rollback:**
  - Pages: promover o deploy anterior;
  - domínio: tirar o domínio do projeto e repor os NS anteriores;
  - conta, zona e domínio **só se apagam com OK**.

## 7. Alimenta

- **Perfil do cliente** (`workspace/<cliente>/_cliente/perfil.md`): domínio, hospedagem e data de renovação.
- **Relatório:** URL, HTTPS e a decisão grátis × próprio com o motivo.
- **Retro:** conversão com domínio grátis × próprio, em `arkos.engine/aprendizado.jsonl`.
- **Esteira:** a URL fica em `campos.url` do `saida.json`, para o próximo elo (campanha, tracking).

## 8. Regras duras

- Perguntar **antes** de criar qualquer conta. Nunca usar dados pessoais do prestador ou do cliente sem OK. Nunca guardar senha, token ou código de recuperação.
- Nunca inventar dado de cadastro: a fonte exige dado real.
- Site comercial nunca na Vercel Hobby.
- Para cliente pagante, recomendar o domínio próprio. O grátis é para MVP e teste.
- Nada de nome que imite marca de terceiro (política da DigitalPlat).
- Nada de janela visível: comandos em segundo plano. Browser só para mostrar o resultado.
