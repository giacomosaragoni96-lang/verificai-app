"""
prova_confronto_modelli.py — confronto Gemini / Claude sulla generazione delle verifiche (strumento di sviluppo).

Fa girare la STESSA pipeline dell'app (`generation.genera_verifica`) con quattro modelli su cinque materie:
Gemini Flash-Lite e Flash (come i piani free e Pro) e Claude Haiku 5.5 e Sonnet 5.5, con la stessa divisione dei compiti
(`config.COMPITI_AI`: titolo, piano, controlli = modello leggero; corpo, autoverifica = modello forte o del piano).
Chiavi dal file .env (GOOGLE_API_KEY e ANTHROPIC_API_KEY): non vengono stampate.

    python prova_confronto_modelli.py                          # 5 materie x 4 modelli = 20 generazioni (circa 25-40 minuti)
    python prova_confronto_modelli.py --scenari fisica         # un solo scenario
    python prova_confronto_modelli.py --modelli haiku sonnet   # solo alcuni modelli
    python prova_confronto_modelli.py --riprendi prove_confronto/2026-11-02_1530   # continua una prova interrotta

Risultati in prove_confronto/<data>/ (ignorata da git): un PDF e un .tex per ogni coppia materia/modello, results.json,
resoconto.md, resoconto.html (tabella con costi, tempi, controlli e link ai PDF) e tutte_le_verifiche.pdf (con segnalibri).
Le generazioni girano una dopo l'altra, così i costi di ognuna non si mescolano. Costi = stime dai token (prezzi in listino).
"""
import argparse
import base64
import html
import json
import os
import re
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

for _flusso in (sys.stdout, sys.stderr):
    try:
        _flusso.reconfigure(encoding="utf-8")
    except Exception:
        pass

import ai_client                                    # noqa: E402
import config                                       # noqa: E402
from generation import genera_verifica              # noqa: E402
from latex_utils import conta_punti_latex           # noqa: E402

# Prezzi di listino Claude (USD per milione di token: input, output). Gemini è già in config.PREZZI_USD_PER_MILIONE.
PREZZI_CLAUDE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}
config.PREZZI_USD_PER_MILIONE.update(PREZZI_CLAUDE)      # lo stesso dizionario che usa ai_client per stimare i costi

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"


# ── ADATTATORE CLAUDE ─────────────────────────────────────────────────────────

class _Risposta:
    def __init__(self, testo: str):
        self.text = testo or ""


class ModelloClaude:
    """Stessa forma di ai_client.ModelloAI (`per`, `generate_content`), ma chiama Claude.

    Il modello del «piano» fa da `corpo`; i compiti leggeri vanno a Haiku, quelli «flash» (autoverifica…) a Sonnet:
    stessa logica di config.scegli_modello_per_compito, con Haiku al posto di Flash-Lite e Sonnet al posto di Flash."""

    def __init__(self, piano: str, model_id: str | None = None, livello: str = "basso", client=None):
        self.piano = piano
        self.model_id = model_id or piano
        self.livello = livello
        self.compito = None
        self._client = client

    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(max_retries=3, timeout=600.0)
        return self._client

    def per(self, compito: str) -> "ModelloClaude":
        tipo, rag = config.COMPITI_AI.get(compito, ("piano", None))
        if tipo == "veloce":
            mid = HAIKU
        elif tipo == "flash":
            mid = SONNET
        elif tipo == "medio":
            mid = HAIKU if self.piano == HAIKU else SONNET
        else:
            mid = self.piano
        if rag == 0:
            livello = "spento"
        elif rag == "alto" or (isinstance(rag, int) and rag > 1024):
            livello = "medio"
        else:
            livello = "basso"
        m = ModelloClaude(self.piano, mid, livello, self._client)
        m.compito = compito
        return m

    def _parametri(self, contenuto, generation_config) -> dict:
        if isinstance(contenuto, str):
            blocchi = [{"type": "text", "text": contenuto}]
        else:
            blocchi = []
            for x in contenuto:
                if isinstance(x, dict) and "data" in x:
                    blocchi.append({"type": "image", "source": {
                        "type": "base64", "media_type": x.get("mime_type", "image/png"),
                        "data": base64.standard_b64encode(x["data"]).decode("ascii")}})
                else:
                    blocchi.append({"type": "text", "text": str(x)})
        kw = {"model": self.model_id, "max_tokens": 32000, "messages": [{"role": "user", "content": blocchi}]}
        if isinstance(generation_config, dict) and generation_config.get("json"):
            kw["system"] = "Rispondi esclusivamente con un oggetto JSON valido, senza testo attorno e senza backtick."
        # Ragionamento: spento dove l'app lo spegne, basso o medio altrove (stessa idea dei tetti di Gemini)
        if self.livello == "spento":
            kw["thinking"] = {"type": "disabled"} if self.model_id == HAIKU else {"type": "between_tools"}
        else:
            kw["thinking"] = {"type": "adaptive"}
            kw["output_config"] = {"effort": "low" if self.livello == "basso" else "medium"}
        return kw

    def _registra(self, messaggio, t0: float):
        u = messaggio.usage
        uso = {"input": int(u.input_tokens or 0), "output": int(u.output_tokens or 0), "pensiero": 0}
        ai_client._registra(self.model_id, self.compito, uso, time.time() - t0)

    def generate_content(self, contenuto, generation_config=None, stream: bool = False):
        kw = self._parametri(contenuto, generation_config)
        t0 = time.time()
        if stream:
            return self._flusso(kw, t0)
        with self.client.messages.stream(**kw) as s:
            msg = s.get_final_message()
        self._registra(msg, t0)
        return _Risposta("".join(b.text for b in msg.content if b.type == "text"))

    def _flusso(self, kw: dict, t0: float):
        with self.client.messages.stream(**kw) as s:
            for testo in s.text_stream:
                yield _Risposta(testo)
            msg = s.get_final_message()
        self._registra(msg, t0)


# ── MODELLI E SCENARI ─────────────────────────────────────────────────────────

MODELLI = {
    "flashlite": dict(etichetta="Gemini Flash-Lite", casa="Google", crea=lambda: ai_client.crea_modello(config.MODEL_FAST_ID)),
    "flash":     dict(etichetta="Gemini Flash",      casa="Google", crea=lambda: ai_client.crea_modello(config.MODEL_FLASH_ID)),
    "haiku":     dict(etichetta="Claude Haiku 5.5",      casa="Anthropic", crea=lambda: ModelloClaude(HAIKU)),
    "sonnet":    dict(etichetta="Claude Sonnet 5.5",     casa="Anthropic", crea=lambda: ModelloClaude(SONNET)),
}

SCENARI = {
    "matematica": dict(
        etichetta="Matematica", materia="Matematica", scuola="Liceo Scientifico",
        argomento="Equazioni di secondo grado e parabola\n- 4 esercizi, difficoltà crescente\n"
                  "- includi un grafico da leggere (senza scrivere l'equazione sul grafico)\n- usa numeri interi",
        esercizi=4, grafico=True),
    "fisica": dict(
        etichetta="Fisica", materia="Fisica", scuola="Liceo Scientifico",
        argomento="Cinematica: moto rettilineo uniformemente accelerato\n- un problema con grafico velocità-tempo da leggere\n"
                  "- un vero/falso e un problema di sorpasso tra due auto",
        esercizi=4, grafico=True),
    "chimica": dict(
        etichetta="Chimica", materia="Chimica", scuola="Istituto Tecnico",
        argomento="Stechiometria e bilanciamento delle reazioni\n- niente tabelle periodiche da consultare\n- una scelta multipla",
        esercizi=4, grafico=False),
    "italiano": dict(
        etichetta="Italiano", materia="Italiano", scuola="Scuola Secondaria di Primo Grado",
        argomento="Analisi del testo narrativo: narratore, personaggi, tempo e luogo\n- un breve brano inventato incluso nella verifica",
        esercizi=3, grafico=False),
    "storia": dict(
        etichetta="Storia", materia="Storia", scuola="Liceo Scientifico",
        argomento="La Rivoluzione francese: cause, fasi principali e conseguenze\n- una domanda a risposta aperta breve, "
                  "un'analisi di una fonte inventata (breve citazione) e un esercizio di cronologia",
        esercizi=4, grafico=False),
}


# ── ESECUZIONE ────────────────────────────────────────────────────────────────

def esegui(sc_id: str, mod_id: str, cartella: str) -> dict:
    sc, md = SCENARI[sc_id], MODELLI[mod_id]
    base = f"{sc_id}__{mod_id}"
    ris = {"scenario": sc_id, "modello": mod_id, "etichetta": md["etichetta"], "casa": md["casa"],
           "materia": sc["etichetta"], "ok": False, "errore": None}
    ai_client.azzera_uso()
    t0 = time.time()
    try:
        r = genera_verifica(
            model=md["crea"](), materia=sc["materia"], argomento=sc["argomento"], difficolta=sc["scuola"],
            calibrazione="", durata="1 ora", num_esercizi=sc["esercizi"], punti_totali=100,
            mostra_punteggi=True, con_griglia=True, doppia_fila=False, bes_dsa=False, perc_ridotta=None,
            bes_dsa_b=False, genera_soluzioni=False, note_generali="", istruzioni_esercizi="",
            immagini_esercizi=[], piano_struttura={"primo_base": False, "eccellenza": True},
        )
    except Exception as e:                           # noqa: BLE001
        ris["errore"] = f"{type(e).__name__}: {str(e)[:300]}"
        ris["secondi"] = round(time.time() - t0, 1)
        _riepilogo_uso(ris)
        return ris
    ris["secondi"] = round(time.time() - t0, 1)
    latex = (r.get("A") or {}).get("latex") or ""
    pdf = (r.get("A") or {}).get("pdf")
    _riepilogo_uso(ris)
    ris["esercizi"] = len(re.findall(r"\\subsection\*", latex))
    ris["esercizi_richiesti"] = sc["esercizi"]              # il totale richiesto comprende «Per l'eccellenza»
    ris["punti"] = conta_punti_latex(latex)
    ris["grafico"] = bool(re.search(r"\\begin\{(?:tikzpicture|axis)\}", latex))
    ris["grafico_richiesto"] = sc["grafico"]
    ris["caratteri"] = len(latex)
    ris["pdf_ok"] = bool(pdf)
    if latex:
        with open(os.path.join(cartella, base + ".tex"), "w", encoding="utf-8") as f:
            f.write(latex)
    if pdf:
        ris["pdf"] = base + ".pdf"
        with open(os.path.join(cartella, ris["pdf"]), "wb") as f:
            f.write(pdf)
    ris["ok"] = bool(pdf)
    return ris


def _riepilogo_uso(ris: dict):
    uso = ai_client.riepilogo_uso()
    ris["costo_usd"] = round(sum(u["costo_usd"] for u in uso), 5)
    ris["chiamate"] = sum(u["chiamate"] for u in uso)
    ris["token_in"] = sum(u["input"] for u in uso)
    ris["token_out"] = sum(u["output"] + u["pensiero"] for u in uso)
    ris["per_modello"] = {u["modello"]: 0.0 for u in uso}
    for u in uso:
        ris["per_modello"][u["modello"]] = round(ris["per_modello"][u["modello"]] + u["costo_usd"], 5)


def _riga_console(r: dict):
    if r.get("errore"):
        print(f"   ERRORE: {r['errore']}")
        return
    print(f"   {r['secondi']:.0f}s | chiamate {r['chiamate']} | token {r['token_in']}/{r['token_out']} | ${r['costo_usd']:.4f} | "
          f"esercizi {r.get('esercizi')}/{r.get('esercizi_richiesti')} | punti {r.get('punti')}/100 | "
          f"PDF {'sì' if r.get('pdf_ok') else 'NO'} | grafico {'sì' if r.get('grafico') else 'no'}"
          f"{' (richiesto!)' if r.get('grafico_richiesto') and not r.get('grafico') else ''}")


# ── RESOCONTO ─────────────────────────────────────────────────────────────────

def _eur(usd: float) -> str:
    return f"${usd:.4f}"


def _totali(risultati: list, modelli: list) -> dict:
    t = {}
    for m in modelli:
        rr = [r for r in risultati if r["modello"] == m]
        ok = [r for r in rr if r["ok"]]
        t[m] = {
            "n": len(rr), "ok": len(ok), "costo": sum(r.get("costo_usd", 0) for r in rr),
            "secondi": sum(r.get("secondi", 0) for r in rr),
            "costo_medio": (sum(r.get("costo_usd", 0) for r in ok) / len(ok)) if ok else 0,
            "secondi_medi": (sum(r.get("secondi", 0) for r in ok) / len(ok)) if ok else 0,
            "punti100": sum(1 for r in ok if r.get("punti") == 100),
            "esercizi_ok": sum(1 for r in ok if r.get("esercizi") == r.get("esercizi_richiesti")),
            "grafici": sum(1 for r in ok if r.get("grafico_richiesto") and r.get("grafico")),
            "grafici_richiesti": sum(1 for r in rr if r.get("grafico_richiesto")),
        }
    return t


def _effettivi(risultati: list, modelli: list) -> dict:
    """Quali modelli hanno risposto davvero (Gemini sostituisce da solo quelli ritirati)."""
    e = {}
    for m in modelli:
        nomi = set()
        for r in risultati:
            if r["modello"] == m:
                nomi |= set((r.get("per_modello") or {}).keys())
        e[m] = ", ".join(sorted(nomi))
    return e


def scrivi_resoconti(cartella: str, risultati: list, scenari: list, modelli: list):
    tot = _totali(risultati, modelli)
    eff = _effettivi(risultati, modelli)
    idx = {(r["scenario"], r["modello"]): r for r in risultati}

    def cella_md(r):
        if not r:
            return "—"
        if r.get("errore"):
            return "ERRORE"
        return (f"{_eur(r['costo_usd'])} · {r['secondi']:.0f}s · {r.get('esercizi')}/{r.get('esercizi_richiesti')} es. · "
                f"{r.get('punti')} pt · PDF {'✓' if r.get('pdf_ok') else '✗'}")

    # Markdown
    L = [f"# Confronto modelli — {datetime.now():%d/%m/%Y %H:%M}", "",
         "Stessa pipeline dell'app, stessi prompt. Costi stimati dai token a prezzo di listino (USD). "
         "«es.» = esercizi ottenuti/richiesti (compreso «Per l'eccellenza»); «pt» = somma dei punti (dovrebbe essere 100).", ""]
    L.append("## Costo, tempo e controlli per ogni generazione\n")
    L.append("| Materia | " + " | ".join(MODELLI[m]["etichetta"] for m in modelli) + " |")
    L.append("|---|" + "---|" * len(modelli))
    for s in scenari:
        L.append(f"| {SCENARI[s]['etichetta']} | " + " | ".join(cella_md(idx.get((s, m))) for m in modelli) + " |")
    L.append("\n## Totali per modello\n")
    L.append("| Modello | Riuscite | Costo totale | Costo medio | Tempo medio | Punti = 100 | Esercizi giusti | Grafici richiesti presenti |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m in modelli:
        t = tot[m]
        L.append(f"| {MODELLI[m]['etichetta']} | {t['ok']}/{t['n']} | {_eur(t['costo'])} | {_eur(t['costo_medio'])} | "
                 f"{t['secondi_medi']:.0f}s | {t['punti100']}/{t['ok']} | {t['esercizi_ok']}/{t['ok']} | "
                 f"{t['grafici']}/{t['grafici_richiesti']} |")
    L.append("\n## Modelli che hanno risposto davvero\n")
    L += [f"- {MODELLI[m]['etichetta']}: {eff[m]}" for m in modelli]
    errori = [r for r in risultati if r.get("errore")]
    if errori:
        L.append("\n## Errori\n")
        L += [f"- {SCENARI[r['scenario']]['etichetta']} · {r['etichetta']}: {r['errore']}" for r in errori]
    L.append("\nI PDF (versione A) sono in questa cartella: `<materia>__<modello>.pdf`; `tutte_le_verifiche.pdf` li raccoglie con i segnalibri.")
    with open(os.path.join(cartella, "resoconto.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # HTML
    def cella_html(r):
        if not r:
            return "<td class='vuota'>—</td>"
        if r.get("errore"):
            return f"<td class='err'>ERRORE<br><small>{html.escape(r['errore'][:120])}</small></td>"
        avv = []
        if r.get("punti") != 100:
            avv.append(f"punti {r.get('punti')}")
        if r.get("esercizi") != r.get("esercizi_richiesti"):
            avv.append(f"esercizi {r.get('esercizi')}/{r.get('esercizi_richiesti')}")
        if r.get("grafico_richiesto") and not r.get("grafico"):
            avv.append("manca il grafico")
        if not r.get("pdf_ok"):
            avv.append("PDF non compilato")
        pdf = f"<a href='{html.escape(r['pdf'])}' target='_blank'>apri PDF</a>" if r.get("pdf") else ""
        classe = "ok" if not avv else "avv"
        note = f"<div class='note'>⚠ {', '.join(avv)}</div>" if avv else ""
        return (f"<td class='{classe}'><div class='costo'>{_eur(r['costo_usd'])}</div>"
                f"<div>{r['secondi']:.0f} s · {r['chiamate']} chiamate</div>"
                f"<div>{r['token_in']:,} in / {r['token_out']:,} out</div>{note}<div>{pdf}</div></td>".replace(",", "."))

    H = ["<!doctype html><html lang='it'><head><meta charset='utf-8'><title>Confronto modelli</title><style>",
         "body{font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#1c2330;background:#f6f7f9}",
         "h1{margin:0 0 4px}p.sotto{color:#5b6475;margin:0 0 24px;max-width:900px}",
         "table{border-collapse:collapse;background:#fff;box-shadow:0 1px 3px #0001;margin-bottom:32px}",
         "th,td{border:1px solid #dde1e8;padding:10px 14px;text-align:left;vertical-align:top;font-size:14px}",
         "th{background:#eef1f6}td.ok{background:#f3fbf5}td.avv{background:#fff8e8}td.err{background:#fdeeee}",
         ".costo{font-weight:700;font-size:16px}.note{color:#9a5b00;font-size:12px;margin-top:4px}",
         "small{color:#a33}a{color:#2563eb;text-decoration:none}a:hover{text-decoration:underline}",
         "th.g{background:#e8f0fe}th.a{background:#fdf0e6}</style></head><body>",
         "<h1>Confronto Gemini / Claude</h1>",
         f"<p class='sotto'>{datetime.now():%d/%m/%Y %H:%M} · stessa pipeline e stessi prompt dell'app · costi stimati dai token a prezzo di listino (USD).</p>",
         "<h2>Per ogni generazione</h2><table><tr><th>Materia</th>"]
    for m in modelli:
        H.append(f"<th class='{'g' if MODELLI[m]['casa'] == 'Google' else 'a'}'>{MODELLI[m]['etichetta']}<br><small style='color:#5b6475'>{MODELLI[m]['casa']} · {eff[m]}</small></th>")
    H.append("</tr>")
    for s in scenari:
        H.append(f"<tr><th>{SCENARI[s]['etichetta']}</th>" + "".join(cella_html(idx.get((s, m))) for m in modelli) + "</tr>")
    H.append("</table><h2>Totali per modello</h2><table><tr><th>Modello</th><th>Riuscite</th><th>Costo totale</th><th>Costo medio</th>"
             "<th>Tempo medio</th><th>Punti = 100</th><th>Esercizi giusti</th><th>Grafici presenti</th></tr>")
    for m in modelli:
        t = tot[m]
        H.append(f"<tr><th>{MODELLI[m]['etichetta']}</th><td>{t['ok']}/{t['n']}</td><td>{_eur(t['costo'])}</td><td>{_eur(t['costo_medio'])}</td>"
                 f"<td>{t['secondi_medi']:.0f} s</td><td>{t['punti100']}/{t['ok']}</td><td>{t['esercizi_ok']}/{t['ok']}</td>"
                 f"<td>{t['grafici']}/{t['grafici_richiesti']}</td></tr>")
    H.append("</table><p class='sotto'>La qualità didattica (correttezza dei calcoli, difficoltà, chiarezza) si giudica leggendo i PDF: "
             "i controlli qui sopra sono solo quelli automatici.</p></body></html>")
    with open(os.path.join(cartella, "resoconto.html"), "w", encoding="utf-8") as f:
        f.write("".join(H))


def unisci_pdf(cartella: str, risultati: list, scenari: list, modelli: list):
    """Un solo PDF con tutte le versioni A, con segnalibri per materia e modello (se pypdf c'è)."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("pypdf non installato: salto tutte_le_verifiche.pdf (i PDF singoli ci sono).")
        return
    idx = {(r["scenario"], r["modello"]): r for r in risultati if r.get("pdf")}
    w = PdfWriter()
    for s in scenari:
        padre = None
        for m in modelli:
            r = idx.get((s, m))
            if not r:
                continue
            pagina = len(w.pages)
            for p in PdfReader(os.path.join(cartella, r["pdf"])).pages:
                w.add_page(p)
            if padre is None:
                padre = w.add_outline_item(SCENARI[s]["etichetta"], pagina)
            w.add_outline_item(f"{MODELLI[m]['etichetta']} ({_eur(r['costo_usd'])})", pagina, parent=padre)
    if len(w.pages):
        with open(os.path.join(cartella, "tutte_le_verifiche.pdf"), "wb") as f:
            w.write(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenari", nargs="+", choices=sorted(SCENARI), default=list(SCENARI))
    ap.add_argument("--modelli", nargs="+", choices=sorted(MODELLI), default=list(MODELLI))
    ap.add_argument("--rigenera", help="cartella di una prova finita: rifà solo resoconti e PDF unico dai dati salvati (nessuna chiamata)")
    ap.add_argument("--riprendi", help="cartella di una prova interrotta: salta le coppie già riuscite")
    a = ap.parse_args()
    if a.rigenera:
        with open(os.path.join(a.rigenera, "results.json"), encoding="utf-8") as f:
            ris = json.load(f)
        for r in ris:                                   # etichette e conteggio come nella versione attuale
            r["etichetta"] = MODELLI[r["modello"]]["etichetta"]
            r["esercizi_richiesti"] = SCENARI[r["scenario"]]["esercizi"]
        with open(os.path.join(a.rigenera, "results.json"), "w", encoding="utf-8") as f:
            json.dump(ris, f, ensure_ascii=False, indent=1)
        sc = [s for s in SCENARI if any(r["scenario"] == s for r in ris)]
        mo = [m for m in MODELLI if any(r["modello"] == m for r in ris)]
        scrivi_resoconti(a.rigenera, ris, sc, mo)
        unisci_pdf(a.rigenera, ris, sc, mo)
        return print("Resoconti rifatti in", a.rigenera)
    for chiave in ("GOOGLE_API_KEY", "ANTHROPIC_API_KEY"):
        if not os.getenv(chiave):
            sys.exit(f"Manca {chiave} nel file .env.")
    ai_client.configura()
    cartella = a.riprendi or os.path.join("prove_confronto", f"{datetime.now():%Y-%m-%d_%H%M}")
    os.makedirs(cartella, exist_ok=True)
    percorso_json = os.path.join(cartella, "results.json")
    risultati = []
    if a.riprendi and os.path.exists(percorso_json):
        with open(percorso_json, encoding="utf-8") as f:
            risultati = [r for r in json.load(f) if r.get("ok")]
    fatti = {(r["scenario"], r["modello"]) for r in risultati}
    totale = len(a.scenari) * len(a.modelli)
    print(f"Cartella: {cartella}\n{totale} generazioni ({len(a.scenari)} materie x {len(a.modelli)} modelli)\n")
    n = 0
    for s in a.scenari:
        for m in a.modelli:
            n += 1
            if (s, m) in fatti:
                print(f"[{n}/{totale}] {s} · {MODELLI[m]['etichetta']}: già fatta, salto")
                continue
            print(f"[{n}/{totale}] {s} · {MODELLI[m]['etichetta']}")
            r = esegui(s, m, cartella)
            _riga_console(r)
            risultati.append(r)
            with open(percorso_json, "w", encoding="utf-8") as f:
                json.dump(risultati, f, ensure_ascii=False, indent=1)
    scrivi_resoconti(cartella, risultati, a.scenari, a.modelli)
    unisci_pdf(cartella, risultati, a.scenari, a.modelli)
    tot = sum(r.get("costo_usd", 0) for r in risultati)
    print(f"\nFatto. Costo totale stimato ${tot:.3f}. Apri: {os.path.join(cartella, 'resoconto.html')}")
    sost = ai_client.modelli_sostituiti()
    if sost:
        print("Modelli Gemini sostituiti perché ritirati:", sost)


if __name__ == "__main__":
    main()
