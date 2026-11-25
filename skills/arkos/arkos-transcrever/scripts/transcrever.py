"""arkos-transcrever: transcrição local (sem API paga) com faster-whisper (MIT; modelos Whisper, MIT).

  transcrever <audio|video> [--modelo small] [--idioma pt] --casa C --cliente X --projeto Y
  checar <pasta-da-transcricao> [--referencia texto.txt]

Saída em workspace/<cliente>/<projeto>/transcricoes/<nome>-<data>/:
  texto.txt, legenda.srt, legenda.vtt, segmentos.json (com confiança por trecho) e conferir.txt
  (trechos de baixa confiança que uma pessoa precisa ouvir antes de usar como citação).
Roda na CPU (int8). Primeira vez baixa o modelo (base ~150 MB, small ~480 MB) para o cache do Hugging Face.
"""
import argparse
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arkos_casa as C  # noqa: E402

EXT = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".webm", ".mp4", ".mov", ".mkv", ".avi"}
MODELOS = {"tiny", "base", "small", "medium", "large-v3", "turbo"}
BAIXA = -1.0  # avg_logprob abaixo disso: trecho para conferir de ouvido
SEM_FALA = 0.6


def _t(seg, sep):
    h, r = divmod(seg, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s - int(s)) * 1000)) % 1000:03d}"


def transcrever(a):
    falta = []
    if not os.path.isfile(a.arquivo):
        falta.append(f"arquivo não existe: {a.arquivo}")
    elif os.path.splitext(a.arquivo)[1].lower() not in EXT:
        falta.append(f"formato {os.path.splitext(a.arquivo)[1]} (aceitos: {', '.join(sorted(EXT))})")
    if a.modelo not in MODELOS:
        falta.append(f"modelo '{a.modelo}' (use {', '.join(sorted(MODELOS))})")
    if falta:
        C.saida("aguardando", excecao="entrada_incompleta", falta=falta)
        sys.exit(C.ENTRADA_INCOMPLETA)
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        C.saida("bloqueada", excecao="fora_do_ar", motivo="faster-whisper não instalado",
                como_resolver=f"{sys.executable} -m pip install faster-whisper")
        sys.exit(C.FORA_DO_AR)
    try:
        modelo = WhisperModel(a.modelo, device="cpu", compute_type="int8")
    except Exception as e:  # noqa: BLE001  sem rede e sem cache: não há modelo
        C.saida("bloqueada", excecao="fora_do_ar", motivo=f"modelo '{a.modelo}' indisponível: {type(e).__name__}: {str(e)[:160]}",
                como_resolver="conectar à internet uma vez para baixar o modelo, ou usar um modelo já baixado")
        sys.exit(C.FORA_DO_AR)
    segs, info = modelo.transcribe(a.arquivo, language=a.idioma or None, vad_filter=True, beam_size=5)
    lista = []
    for s in segs:
        lista.append({"inicio": round(s.start, 2), "fim": round(s.end, 2), "texto": s.text.strip(),
                      "confianca_media": round(s.avg_logprob, 3), "sem_fala": round(s.no_speech_prob, 3),
                      "conferir": s.avg_logprob < BAIXA or s.no_speech_prob > SEM_FALA})
    base = C.pasta_casa(a.casa, a.cliente, a.projeto, "transcricoes")
    raiz = os.path.join(base, f"{C.slug(os.path.splitext(os.path.basename(a.arquivo))[0])}-{C.hoje()}")
    pasta, n = raiz, 1
    while os.path.exists(pasta):
        n += 1
        pasta = f"{raiz}-v{n}"
    os.makedirs(pasta)
    with open(os.path.join(pasta, "texto.txt"), "w", encoding="utf-8") as f:
        f.write(" ".join(s["texto"] for s in lista).strip() + "\n")
    with open(os.path.join(pasta, "legenda.srt"), "w", encoding="utf-8") as f:
        for i, s in enumerate(lista, 1):
            f.write(f"{i}\n{_t(s['inicio'], ',')} --> {_t(s['fim'], ',')}\n{s['texto']}\n\n")
    with open(os.path.join(pasta, "legenda.vtt"), "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n" + "".join(f"{_t(s['inicio'], '.')} --> {_t(s['fim'], '.')}\n{s['texto']}\n\n" for s in lista))
    meta = {"origem": os.path.abspath(a.arquivo), "modelo": a.modelo, "idioma": info.language,
            "prob_idioma": round(info.language_probability, 3), "duracao": round(info.duration, 2), "segmentos": lista}
    with open(os.path.join(pasta, "segmentos.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    duvida = [s for s in lista if s["conferir"]]
    with open(os.path.join(pasta, "conferir.txt"), "w", encoding="utf-8") as f:
        f.write("".join(f"{_t(s['inicio'], ',')}  {s['texto']}\n" for s in duvida) or "nenhum trecho de baixa confiança\n")
    probs = _checar(pasta)
    C.saida("ok" if not probs else "reprovado", pasta=pasta, idioma=info.language, duracao=meta["duracao"],
            segmentos=len(lista), para_conferir=len(duvida), problemas=probs)


NUM = ["zero", "um", "dois", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
       "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove", "vinte"]


def _norm(t):
    """Minúsculas, sem acento, sem pontuação; '6h' e '6' viram 'seis' (0 a 20), para a grafia do número não contar como erro."""
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\b(\d{1,2})h\b", r"\1", t)
    out = []
    for w in re.findall(r"[a-z0-9]+", t):
        out.append(NUM[int(w)] if w.isdigit() and int(w) <= 20 else w)
    return out


def wer(ref, hip):
    r, h = _norm(ref), _norm(hip)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        ant, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            ant, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, ant + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(len(r), 1)


def _checar(pasta, referencia=None):
    probs = []
    for f in ("texto.txt", "legenda.srt", "legenda.vtt", "segmentos.json", "conferir.txt"):
        if not os.path.isfile(os.path.join(pasta, f)):
            probs.append(f"falta {f}")
    if probs:
        return probs
    meta = json.load(open(os.path.join(pasta, "segmentos.json"), encoding="utf-8"))
    segs = meta["segmentos"]
    if not segs or not open(os.path.join(pasta, "texto.txt"), encoding="utf-8").read().strip():
        return ["transcrição vazia (sem fala detectada?)"]
    fim = 0.0
    for i, s in enumerate(segs, 1):
        if s["fim"] <= s["inicio"]:
            probs.append(f"segmento {i}: fim antes do início")
        if s["inicio"] < fim - 0.05:
            probs.append(f"segmento {i}: sobrepõe o anterior")
        if not s["texto"]:
            probs.append(f"segmento {i}: sem texto")
        fim = s["fim"]
    if meta["duracao"] and segs[-1]["fim"] < meta["duracao"] * 0.6:
        probs.append(f"legenda cobre até {segs[-1]['fim']}s de {meta['duracao']}s (menos de 60%)")
    blocos = open(os.path.join(pasta, "legenda.srt"), encoding="utf-8").read().strip().split("\n\n")
    if len(blocos) != len(segs):
        probs.append(f"SRT com {len(blocos)} blocos para {len(segs)} segmentos")
    if referencia:
        w = wer(open(referencia, encoding="utf-8").read(), open(os.path.join(pasta, "texto.txt"), encoding="utf-8").read())
        if w > 0.15:
            probs.append(f"WER {w:.1%} contra a referência (máximo 15%)")
    return probs


def checar(a):
    if not os.path.isdir(a.pasta):
        C.saida("aguardando", excecao="entrada_incompleta", falta=[f"pasta não existe: {a.pasta}"])
        sys.exit(C.ENTRADA_INCOMPLETA)
    p = _checar(a.pasta, a.referencia)
    extra = {}
    if a.referencia and os.path.isfile(os.path.join(a.pasta, "texto.txt")):
        extra["wer"] = round(wer(open(a.referencia, encoding="utf-8").read(),
                                 open(os.path.join(a.pasta, "texto.txt"), encoding="utf-8").read()), 3)
    C.saida("verde" if not p else "vermelho", pasta=a.pasta, problemas=p, **extra)
    sys.exit(0 if not p else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("transcrever")
    t.add_argument("arquivo")
    t.add_argument("--modelo", default="small")
    t.add_argument("--idioma", default="pt")
    t.add_argument("--casa")
    t.add_argument("--cliente")
    t.add_argument("--projeto")
    c = sub.add_parser("checar")
    c.add_argument("pasta")
    c.add_argument("--referencia")
    a = ap.parse_args()
    {"transcrever": transcrever, "checar": checar}[a.cmd](a)


if __name__ == "__main__":
    main()
