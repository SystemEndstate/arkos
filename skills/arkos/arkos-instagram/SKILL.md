---
name: arkos-instagram
description: Publica e agenda no Instagram pela Meta Graph API usando o token do PRÓPRIO cliente (conta IG Business/Creator ligada a uma Página). Avisa do custo/limite e de qual conta vai postar antes. Padrão da casa é Reels. Não envia sozinha: entrega o lote como rascunho ao arkos-guarda-envio. Use em "postar no Instagram", "agendar Reels", "subir o criativo no IG", "publicar pela conta do cliente".
status: rascunho
versao: 0.1.0
modulos: [organico]
depende_de: [arkos-guarda-envio, arkos-decisor]
---

# arkos-instagram

Clone de sala limpa do publicador de IG: fala direto com a **Meta Graph API** (método público), com o token do cliente, em vez de usar qualquer serviço/MCP pessoal. Monta o pedido e o entrega travado; quem libera o envio é o `arkos-guarda-envio`. Regra da casa: sempre Reels, legenda pelo conteúdo do vídeo.

## Quando usar e quando não usar

- **Usar:** publicar/agendar Reels ou post pela conta do cliente.
- **Não usar:** conta que não é Business/Creator ligada a Página; sem token do cliente.

## Entradas

- `IG_USER_ID` e `ACCESS_TOKEN` do cliente (env/config; nunca embutidos).
- `media_url` (vídeo/imagem público), `caption`, `agendar_em` (opcional).
- A conta destino (confirmada com o usuário).

## Passos

1. **Validar:** token e IG_USER_ID presentes, `media_url` http(s), legenda ≤ 2200 chars, hashtags ≤ 30.
2. **Avisar antes:** qual conta, que é Reels, e o limite da API (cota de publicação/24h). Confirmar a conta certa (`arkos-decisor` só se houver 2 candidatas).
3. **Montar o pedido** (`instagram.py preparar`): passo 1 `POST /{ig}/media` (container, `media_type=REELS`, `video_url`, `caption`); passo 2 `POST /{ig}/media_publish` (`creation_id`).
4. **Entregar travado** ao `arkos-guarda-envio`: ele mostra o diff (conta, legenda, mídia) e só então chama a API.
5. **Registrar** o `media_id` publicado e o horário.

## Saída

JSON: `{conta, tipo:"REELS", aviso, requisicoes:[{metodo,url,campos}], agendado?}`. A publicação real só ocorre após a trava.

## Critério de pronto

- [ ] A conta foi confirmada e aparece no aviso.
- [ ] O envio passou pelo `arkos-guarda-envio` (não publicou direto).
- [ ] Legenda e hashtags dentro do limite; mídia é URL pública.

## Exceções

- **Sem token:** recusar e pedir a conexão da conta (não chamar a API).
- **Mídia inválida / legenda longa:** apontar e parar antes de montar o pedido.
- **Cota estourada (API 4/9007):** avisar e reagendar; não insistir.

## Alimenta

- `arkos-guarda-envio` (libera) e `arkos-motor-organico` (vencedor orgânico vira Spark Ad).

## Regras duras

- Token é sempre do cliente; o pacote não traz token nem conta.
- Nunca publicar sem passar pela trava de envio.
- Avisar custo/conta antes; post publicado não se desfaz sem OK do dono.
