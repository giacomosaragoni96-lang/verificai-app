"""
importa_esercizi.py — legge schede, verifiche e appunti (PDF o LaTeX) e ne ricava gli esercizi catalogati.

Per ogni file produce un JSON e una pagina HTML da rivedere; con --salva li mette anche nella banca
su Supabase come «in attesa di revisione» (li approvi dalla pagina Banca dell'app).

    python importa_esercizi.py materiale/scheda.pdf
    python importa_esercizi.py materiale/verifica.tex
    python importa_esercizi.py materiale                      # tutti i .tex e .pdf della cartella
    python importa_esercizi.py materiale --senza-ai           # solo lettura del codice, niente AI
    python importa_esercizi.py materiale --salva --materia Matematica --scuola "Istituto Professionale"

La logica sta in banca_import.py (la usa anche la pagina Banca). I file restano sul tuo computer
(la cartella materiale/ è ignorata da git). Usa GOOGLE_API_KEY del .env; per --salva servono anche
SUPABASE_URL e SUPABASE_SERVICE_KEY nel .env.
"""
import argparse
import glob
import html
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

for _flusso in (sys.stdout, sys.stderr):          # la console di Windows non stampa tutti i simboli
    try:
        _flusso.reconfigure(encoding="utf-8")
    except Exception:
        pass

import ai_client                                  # noqa: E402
import banca                                      # noqa: E402
import banca_import                               # noqa: E402
from config import CATEGORIE_SCUOLA, MODEL_FLASH_ID  # noqa: E402


def _h(x) -> str:
    return html.escape(str(x if x is not None else ""))


def pagina_html(titolo: str, esercizi: list, modello: dict | None, nota: str = "") -> str:
    struttura = (f"<p style='background:#fffaeb;border:1px solid #fec84b;padding:.6rem .8rem'>{_h(nota)}</p>" if nota else "")
    if modello:
        righe = "".join(
            f"<tr><td>{_h(s['nome'])}</td><td>{_h(s['tipo'])}</td><td>{s['n_quesiti']}</td>"
            f"<td>{_h(' · '.join(str(p) if p is not None else '—' for p in s['punti']))}</td>"
            f"<td>{_h(', '.join(s['facoltativi']) or '—')}</td></tr>" for s in modello["sezioni"])
        struttura += (
            f"<h2>Struttura della verifica</h2><p>{_h(modello['titolo'])} — <b>{_h(modello['argomento'])}</b><br>"
            f"Punti base <b>{modello['punti_base']}</b> + facoltativi <b>{modello['punti_extra']}</b> = "
            f"<b>{modello['totale']}</b>"
            + (f" · base PDP/DSA indicata: {modello['base_pdp_dsa']}" if modello.get("base_pdp_dsa") else "")
            + ("" if modello["punti_letti"] else " · <span style='color:#b42318'>punti non letti dalla tabella</span>")
            + f"<br>Stile: {_h(modello['stile'])}</p>"
            "<table><tr><th>Sezione</th><th>Tipo</th><th>Quesiti</th><th>Punti</th><th>Facoltativi</th></tr>"
            + righe + "</table><h2>Esercizi</h2>")
    righe = []
    for e in esercizi:
        opz = ""
        if e.get("opzioni"):
            opz = "<ul>" + "".join(f"<li>{_h(o)}</li>" for o in e["opzioni"]) + "</ul>"
        sol = f"<div class='sol'>Soluzione: {_h(e['soluzione_latex'])}</div>" if e.get("soluzione_latex") else ""
        flag = " ".join(x for x in (
            "<b>(*) facoltativo</b>" if e.get("facoltativo") else "",
            f"{e['punti']} pt" if e.get("punti") is not None else "",
            "⚠️ figura" if e.get("ha_figura") else "",
            "esempio svolto" if e.get("ruolo") == "esempio_svolto" else "") if x)
        pos = e.get("sezione") or e.get("titolo_sezione") or ""
        riga_pagina = f"p. {e['pagina']}" if e.get("pagina") is not None else ""
        righe.append(
            f"<tr><td>{_h(e.get('numero'))}<br><small>{_h(pos)} {riga_pagina}</small></td>"
            f"<td class='st{e['difficolta']}'>{'★' * e['difficolta']}<br><small>{_h(e['difficolta_origine'])}</small></td>"
            f"<td>{_h(e.get('testo_latex', '')).replace(chr(10), '<br>')}{opz}{sol}</td>"
            f"<td>{_h(e.get('argomento'))}<br><small>{_h(', '.join(e.get('tecniche') or []))}</small></td>"
            f"<td>{_h(e.get('tipo'))}<br><small>{flag}</small></td></tr>")
    return (
        "<!doctype html><meta charset='utf-8'><title>" + _h(titolo) + "</title>"
        "<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'>"
        "<script defer src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'></script>"
        "<script defer src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js' "
        "onload=\"renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false},{left:'\\\\(',right:'\\\\)',display:false}],throwOnError:false})\"></script>"
        "<style>body{font-family:system-ui,sans-serif;margin:1.5rem}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #d0d5dd;padding:.45rem .6rem;vertical-align:top;font-size:.92rem}"
        "th{background:#f2f4f7;text-align:left}small{color:#667085}.st1{background:#ecfdf3}.st2{background:#fffaeb}"
        ".st3{background:#fef3f2}.sol{margin-top:.4rem;color:#344054}li{list-style:none}</style>"
        f"<h1>{_h(titolo)}</h1>{struttura}<p>{len(esercizi)} esercizi. Controlla formule, livelli e tecniche.</p>"
        "<table><tr><th>N. / posizione</th><th>Livello</th><th>Esercizio</th><th>Argomento / tecniche</th>"
        "<th>Tipo / punti</th></tr>" + "".join(righe) + "</table>"
    )


def elabora_file(percorso: str, a, modello, sb):
    nome_file = os.path.basename(percorso)
    ext = os.path.splitext(percorso)[1].lower().strip(".")
    print(f"\n▶ {nome_file}")
    with open(percorso, "rb") as f:
        contenuto = f.read()
    ris = banca_import.analizza_file(
        nome_file, contenuto, materia=a.materia, modello=modello, livelli=a.livelli,
        senza_ai=a.senza_ai, pagine=a.pagine, on_progress=lambda m: print("   " + m))
    if ris is None:
        print("   (saltato)")
        return None
    for av in ris["avvisi"]:
        print("   ⚠️ ", av)
    if ris["nota_livelli"]:
        print("   " + ris["nota_livelli"] + " Se è sbagliato rilancia con --livelli argomenti|difficolta.")
    esercizi = ris["esercizi"]

    os.makedirs(a.uscita, exist_ok=True)
    base = os.path.join(a.uscita, f"{os.path.splitext(nome_file)[0]}.{ext}")   # PDF e .tex omonimi non si sovrascrivono
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"fonte": ris["fonte"], "modello_verifica": ris["modello_verifica"],
                   "nota_livelli": ris["nota_livelli"], "esercizi": esercizi}, f, ensure_ascii=False, indent=1)
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(pagina_html(ris["fonte"]["titolo"], esercizi, ris["modello_verifica"], ris["nota_livelli"]))
    per = {k: sum(1 for e in esercizi if e["difficolta"] == k) for k in (1, 2, 3)}
    print(f"   → {ris['fonte']['tipo']}: {len(esercizi)} esercizi | ★1: {per[1]}  ★2: {per[2]}  ★3: {per[3]} | {base}.html")

    if sb is not None:
        esito = banca.salva_analisi(sb, ris, a.materia, a.scuola)
        print("   già in banca, non ricaricato" if esito["gia_presente"]
              else f"   salvati in banca: {esito['nuovi']} esercizi in attesa di approvazione")
    return {"file": nome_file, "esercizi": len(esercizi)}


def main():
    ap = argparse.ArgumentParser(description="Estrae e cataloga gli esercizi da PDF e LaTeX.")
    ap.add_argument("percorsi", nargs="+", help="file .tex/.pdf oppure cartelle (consiglio: materiale/)")
    ap.add_argument("--materia", default="", help="materia (consigliato con --salva)")
    ap.add_argument("--scuola", default="", choices=[""] + CATEGORIE_SCUOLA,
                    help="scuola a cui è destinato il materiale, con --salva (" + ", ".join(CATEGORIE_SCUOLA) + ")")
    ap.add_argument("--pagine", type=int, default=4, help="pagine per chiamata all'AI per i PDF (default 4)")
    ap.add_argument("--livelli", choices=["auto", "difficolta", "argomenti"], default="auto",
                    help="nelle schede, le sezioni «Livello N» sono difficoltà o argomenti? (auto: lo capisce)")
    ap.add_argument("--senza-ai", action="store_true", help="solo lettura del codice: nessuna etichetta dell'AI")
    ap.add_argument("--salva", action="store_true", help="salva anche nella banca su Supabase (da approvare)")
    ap.add_argument("--uscita", default=os.path.join("materiale", "estratti"), help="cartella di uscita")
    a = ap.parse_args()

    file = []
    for p in a.percorsi:
        if os.path.isdir(p):
            file += sorted(glob.glob(os.path.join(p, "*.tex")) + glob.glob(os.path.join(p, "*.pdf")))
        elif os.path.isfile(p):
            file.append(p)
        else:
            sys.exit(f"Non trovato: {p}")

    modello = None
    if os.getenv("GOOGLE_API_KEY") and not a.senza_ai:
        ai_client.configura()
        modello = ai_client.crea_modello(MODEL_FLASH_ID).per("importazione")
        ai_client.azzera_uso()
    elif not a.senza_ai:
        print("⚠️  GOOGLE_API_KEY non trovata nel .env: leggo solo il codice delle verifiche e schede, senza etichette.")

    sb = None
    if a.salva:
        url, chiave = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
        if not (url and chiave):
            sys.exit("Per --salva servono SUPABASE_URL e SUPABASE_SERVICE_KEY nel file .env.")
        from supabase import create_client
        sb = create_client(url, chiave)
        if not banca.tabelle_pronte(sb):
            sys.exit("Le tabelle della banca non esistono ancora: esegui banca_esercizi.sql su Supabase.")

    riepilogo = [r for r in (elabora_file(f, a, modello, sb) for f in file) if r]
    uso = ai_client.riepilogo_uso()
    costo = sum(u["costo_usd"] for u in uso)
    print(f"\n{len(riepilogo)} file elaborati | {sum(r['esercizi'] for r in riepilogo)} esercizi | ~${costo:.3f} di AI")
    sost = ai_client.modelli_sostituiti()
    if sost:
        print("Modelli sostituiti perché ritirati:", sost)


if __name__ == "__main__":
    main()
