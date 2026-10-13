"""
importa_esercizi.py — legge un PDF (scheda, appunti, libro) e ne estrae gli esercizi catalogati.

Non tocca il sito né il database: produce un file JSON e una pagina HTML da rivedere a occhio.

    python importa_esercizi.py materiale/scheda.pdf
    python importa_esercizi.py materiale/libro.pdf --materia Matematica --pagine 3

Il PDF resta sul tuo computer (la cartella materiale/ è ignorata da git). Usa la chiave
GOOGLE_API_KEY del file .env. Ogni blocco di pagine è una chiamata all'AI: un libro da 300 pagine
costa nell'ordine di 1 dollaro.
"""
import argparse
import html
import json
import os
import re
import sys
import time

from dotenv import load_dotenv

load_dotenv()

for _flusso in (sys.stdout, sys.stderr):          # la console di Windows non stampa tutti i simboli
    try:
        _flusso.reconfigure(encoding="utf-8")
    except Exception:
        pass

import fitz                                       # noqa: E402  (PyMuPDF, già nelle dipendenze)

import ai_client                                  # noqa: E402
from config import MODEL_FLASH_ID, livello_normalizzato  # noqa: E402
from prompts import prompt_importa_esercizi      # noqa: E402


def blocchi_di_pagine(percorso: str, per_blocco: int):
    """Taglia il PDF in blocchi di poche pagine: [(prima_pagina, byte_del_pdf), ...]."""
    doc = fitz.open(percorso)
    for inizio in range(0, len(doc), per_blocco):
        fine = min(inizio + per_blocco, len(doc)) - 1
        parte = fitz.open()
        parte.insert_pdf(doc, from_page=inizio, to_page=fine)
        yield inizio + 1, parte.tobytes()


def leggi_json(testo: str) -> dict:
    testo = re.sub(r"^```(?:json)?|```$", "", (testo or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(testo)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", testo, re.DOTALL)
        return json.loads(m.group(0)) if m else {"esercizi": []}


def estrai_blocco(modello, materia: str, pdf_bytes: bytes, tentativi: int = 2) -> list:
    prompt = prompt_importa_esercizi(materia)
    ultimo = None
    for t in range(tentativi):
        try:
            r = modello.generate_content(
                [prompt, {"mime_type": "application/pdf", "data": pdf_bytes}],
                generation_config={"json": True, "temperature": 0.1},
            )
            return leggi_json(r.text).get("esercizi", [])
        except Exception as e:                    # noqa: BLE001
            ultimo = e
            if ai_client.errore_definitivo(e):
                break
            time.sleep(2 * (t + 1))
    print(f"   ⚠️  blocco non letto: {str(ultimo)[:200]}")
    return []


def normalizza(esercizi: list) -> list:
    """Porta tutte le difficoltà su 1-3 (★) mantenendo il livello originale."""
    L = max([int(e["livelli_totali"]) for e in esercizi if isinstance(e.get("livelli_totali"), int)] or
            [int(e["livello_numero"]) for e in esercizi if isinstance(e.get("livello_numero"), int)] or [0])
    for e in esercizi:
        if isinstance(e.get("livello_numero"), int) and L:
            e["difficolta"] = livello_normalizzato(e["livello_numero"], L)
            e["difficolta_origine"] = f"livello {e['livello_numero']} di {L}"
        else:
            e["difficolta"] = max(1, min(3, int(e.get("difficolta_stimata") or 2)))
            e["difficolta_origine"] = "stimata dall'AI (la fonte non indica livelli)"
    return esercizi


def pagina_html(esercizi: list, titolo: str) -> str:
    righe = []
    for e in esercizi:
        tecniche = ", ".join(e.get("tecniche") or [])
        figura = "⚠️ figura" if e.get("ha_figura") else ""
        sol = f"<div class='sol'>Soluzione: {html.escape(e['soluzione_latex'])}</div>" if e.get("soluzione_latex") else ""
        righe.append(
            f"<tr><td>{html.escape(str(e.get('numero', '')))}</td><td>p. {e.get('pagina', '')}</td>"
            f"<td class='st{e['difficolta']}'>{'★' * e['difficolta']}<br><small>{html.escape(e['difficolta_origine'])}</small></td>"
            f"<td>{html.escape(e.get('testo_latex', '')).replace(chr(10), '<br>')}{sol}</td>"
            f"<td>{html.escape(e.get('argomento', ''))}<br><small>{html.escape(tecniche)}</small></td>"
            f"<td>{html.escape(e.get('tipo', ''))} {figura}</td></tr>"
        )
    return (
        "<!doctype html><meta charset='utf-8'><title>" + html.escape(titolo) + "</title>"
        "<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'>"
        "<script defer src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'></script>"
        "<script defer src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js' "
        "onload=\"renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false},{left:'\\\\(',right:'\\\\)',display:false}]})\"></script>"
        "<style>body{font-family:system-ui,sans-serif;margin:1.5rem}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #d0d5dd;padding:.45rem .6rem;vertical-align:top;font-size:.92rem}"
        "th{background:#f2f4f7;text-align:left}small{color:#667085}.st1{background:#ecfdf3}.st2{background:#fffaeb}"
        ".st3{background:#fef3f2}.sol{margin-top:.4rem;color:#344054}</style>"
        f"<h1>{html.escape(titolo)}</h1><p>{len(esercizi)} esercizi. Controlla formule, livelli e tecniche.</p>"
        "<table><tr><th>N.</th><th>Pag.</th><th>Livello</th><th>Esercizio</th><th>Argomento / tecniche</th>"
        "<th>Tipo</th></tr>" + "".join(righe) + "</table>"
    )


def main():
    ap = argparse.ArgumentParser(description="Estrae gli esercizi da un PDF in un file da rivedere.")
    ap.add_argument("pdf", help="percorso del PDF (consiglio: nella cartella materiale/)")
    ap.add_argument("--materia", default="", help="materia, se vuoi guidare la lettura")
    ap.add_argument("--pagine", type=int, default=4, help="pagine per chiamata all'AI (default 4)")
    ap.add_argument("--uscita", default=os.path.join("materiale", "estratti"), help="cartella di uscita")
    a = ap.parse_args()
    if not os.path.isfile(a.pdf):
        sys.exit(f"File non trovato: {a.pdf}")
    if not os.getenv("GOOGLE_API_KEY"):
        sys.exit("Manca GOOGLE_API_KEY: mettila nel file .env e riprova.")

    ai_client.configura()
    modello = ai_client.crea_modello(MODEL_FLASH_ID).per("importazione")
    ai_client.azzera_uso()
    os.makedirs(a.uscita, exist_ok=True)
    nome = os.path.splitext(os.path.basename(a.pdf))[0]

    tutti = []
    for prima, dati in blocchi_di_pagine(a.pdf, a.pagine):
        print(f"Leggo le pagine da {prima}…")
        for e in estrai_blocco(modello, a.materia, dati):
            e["pagina"] = prima + int(e.get("pagina_nel_blocco") or 1) - 1
            e["fonte"] = os.path.basename(a.pdf)
            tutti.append(e)
    tutti = normalizza(tutti)

    base = os.path.join(a.uscita, nome)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(tutti, f, ensure_ascii=False, indent=1)
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(pagina_html(tutti, nome))

    uso = ai_client.riepilogo_uso()
    costo = sum(u["costo_usd"] for u in uso)
    per_livello = {k: sum(1 for e in tutti if e["difficolta"] == k) for k in (1, 2, 3)}
    print(f"\n{len(tutti)} esercizi estratti | ★1: {per_livello[1]}  ★2: {per_livello[2]}  ★3: {per_livello[3]} | ~${costo:.3f}")
    print(f"→ {base}.html (aprilo nel browser per controllare)\n→ {base}.json")
    sost = ai_client.modelli_sostituiti()
    if sost:
        print("Modelli sostituiti perché ritirati:", sost)


if __name__ == "__main__":
    main()
