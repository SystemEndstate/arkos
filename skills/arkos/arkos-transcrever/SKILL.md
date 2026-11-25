---
name: arkos-transcrever
description: Transcreve áudio e vídeo localmente, sem API paga, com faster-whisper (MIT) na CPU — gera texto, legenda SRT e VTT com tempo, segmentos com a confiança de cada trecho e a lista do que precisa ser ouvido de novo. Serve para reunião, depoimento, vídeo do cliente, roteiro a partir de gravação e legenda de Reels. Use em "transcrever", "transcrição", "legenda do vídeo", "gerar SRT", "o que foi dito no áudio", "tirar o texto da reunião", "transcribe".
status: rascunho
versao: 0.1.0
modulos: [C, V, O]
depende_de: []
substitui: whisper-transcribe (sem licença; implementação própria, escrita do zero)
---

# arkos-transcrever

Transcrição na máquina do prestador: o áudio do cliente não sai do computador e não há custo por minuto. Modelo Whisper rodando pelo `faster-whisper` (CTranslate2), int8 na CPU.

## Pasta-casa

`workspace/<cliente>/<projeto>/transcricoes/<nome-do-arquivo>-<data>/` (repetido no dia: `-v2`), com `texto.txt`, `legenda.srt`, `legenda.vtt`, `segmentos.json` (início, fim, texto, confiança média e chance de não ser fala) e `conferir.txt`.

## Comandos

```bash
py -3 scripts/transcrever.py transcrever reuniao.m4a [--modelo small] [--idioma pt] --casa C --cliente X --projeto Y
py -3 scripts/transcrever.py checar <pasta> [--referencia texto-certo.txt]
```

Modelos: `base` (rápido, ~150 MB), `small` (padrão, ~480 MB), `medium`/`large-v3`/`turbo` (melhores e mais pesados). Na primeira vez o modelo é baixado para o cache; depois funciona sem internet. Aceita wav, mp3, m4a, ogg, opus, flac, webm, mp4, mov, mkv e avi.

Instalação: `py -3 -m pip install faster-whisper "av>=11,<16"` (o PyAV 16+ quebrou a chamada que o faster-whisper usa).

## Passos

1. Pegar o arquivo original (não o áudio comprimido de novo pelo WhatsApp, se houver o original).
2. `transcrever`. Idioma explícito (`--idioma pt`) evita a troca de idioma em trecho curto.
3. Ler o `conferir.txt` e ouvir esses trechos antes de citar.
4. Nome de marca, nome próprio e termo em inglês: conferir no áudio. O modelo erra nisso com confiança alta (ver Limites).
5. Legenda de vídeo: o `legenda.srt` entra no editor; o texto vai para o `arkos-gate` se virar copy.

## Regras duras

- Nada sai do computador: sem API paga, sem upload.
- Citação entre aspas só de trecho conferido no áudio.
- Trecho de baixa confiança (confiança média abaixo de −1,0 ou chance de não ser fala acima de 0,6) vai para o `conferir.txt`.
- Áudio de terceiro só com autorização de quem gravou (reunião com o cliente: avisar no começo da chamada).
- Subprocesso oculto, sem janela.

## Pronto quando

`checar` verde: os 5 arquivos existem, a transcrição não está vazia, os tempos crescem sem sobreposição, a legenda cobre pelo menos 60% da duração e o SRT tem um bloco por segmento. Com `--referencia`, o WER tem que ficar em até 15% (números normalizados: "6h" e "seis" contam igual).

## Exceções

- `entrada_incompleta`: arquivo inexistente, formato não aceito ou modelo inválido. Código 2.
- `fora_do_ar`: faster-whisper não instalado, ou modelo sem cache e sem internet. Código 3 e o comando para resolver.
- `resultado_ruim`: `checar` vermelho (vazio, sem fala ou WER alto). Tentar um modelo maior; se o áudio for ruim, dizer ao cliente o que dá e o que não dá para aproveitar.

## Limites

- O teste com voz sintética em PT-BR deu WER de 9,5%. O erro foi "WhatsApp" virar "vinhetepe" com confiança alta, então **não** caiu no `conferir.txt`. Termo estrangeiro e nome de marca sempre se conferem de ouvido.
- Sem separação de quem fala (diarização). Fica como pendência.
