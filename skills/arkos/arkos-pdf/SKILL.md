---
name: arkos-pdf
description: Gera, junta, separa, carimba e lê PDF na pasta do cliente com bibliotecas livres (reportlab, pypdf) e Chrome headless sem janela — proposta, relatório, contrato em PDF, HTML virando PDF, marca d'água de rascunho, extrair páginas e ler o texto. Use em "gerar PDF", "juntar PDFs", "separar páginas do PDF", "marca d'água", "carimbo de rascunho", "transformar HTML em PDF", "ler o PDF", "PDF da proposta".
status: rascunho
versao: 0.1.0
modulos: [D, O]
depende_de: []
substitui: anthropic-skills:pdf (clone de sala limpa; texto e código escritos do zero)
---

# arkos-pdf

PDF por script (`scripts/pdf_arkos.py`). O mesmo spec do `arkos-docx` gera o PDF direto, sem precisar do Word.

## Pasta-casa

Saída em `workspace/<cliente>/<projeto>/documentos/<slug>-<AAAA-MM-DD>.pdf`; nome repetido vira `-v2`. **O arquivo de entrada nunca é sobrescrito**: juntar, separar e carimbar sempre geram um arquivo novo.

## Comandos

```bash
py -3 scripts/pdf_arkos.py gerar spec.json [--trocar chaves.json] --casa C --cliente X --projeto Y
py -3 scripts/pdf_arkos.py html pagina.html [--titulo T] [--spec spec.json] --casa C --cliente X --projeto Y
py -3 scripts/pdf_arkos.py juntar a.pdf b.pdf --titulo T --casa C --cliente X --projeto Y
py -3 scripts/pdf_arkos.py paginas a.pdf --faixa 1-3,5 --casa C --cliente X --projeto Y
py -3 scripts/pdf_arkos.py carimbar a.pdf --texto RASCUNHO --casa C --cliente X --projeto Y
py -3 scripts/pdf_arkos.py ler a.pdf
```

## Passos

1. Conteúdo novo: escrever o spec (formato do `arkos-docx`) e rodar `gerar`. Página web pronta (relatório, carrossel): `html`.
2. Arquivo do cliente: `ler` primeiro, para conferir o que tem e quantas páginas.
3. Versão para revisão vai com `carimbar --texto RASCUNHO`; a final sai sem carimbo.
4. Passar pelo `arkos-gate` antes de enviar.

## Identidade

Cabeçalho `ARKOS ENGINE · <CLIENTE>` com filete, rodapé com tipo, data e página, título Ink, tabela com cabeçalho Ink e nota em fundo papel com filete grafite. Volt não vai no papel. Usa Inter Tight / JetBrains Mono se estiverem instaladas como .ttf estático; senão, Helvetica e Courier.

## Regras duras

- Pasta-casa, data no nome e nada de sobrescrever.
- Metadados: título, autor `ARKOS Engine` e criador.
- PDF com `{{chave}}` sobrando não é entregue (o `gerar` devolve `amarelo` e a lista).
- O Chrome roda headless, sem janela (`CREATE_NO_WINDOW`) e com perfil temporário.
- Faixa de páginas fora do arquivo é erro de entrada, nunca um PDF vazio.

## Pronto quando

O comando devolve `status: ok`, o arquivo abre com o número de páginas esperado e passa nas regras acima (`_testes/aceitacao_clones.py`, T3).

## Exceções

- `entrada_incompleta`: spec sem `titulo`/`blocos`, arquivo inexistente, faixa fora do PDF ou `juntar` sem `--titulo` saem com código 2 e a lista do que falta, sem escrever nada.
- `fora_do_ar`: sem Chrome/Edge, o `html` usa o `--spec` pelo reportlab e marca `amarelo`. Sem spec, para com código 3 e diz o que instalar (ou `ARKOS_CHROME`).

## Pendências

- Preencher formulário PDF (AcroForm) e assinar.
- OCR de PDF escaneado.
