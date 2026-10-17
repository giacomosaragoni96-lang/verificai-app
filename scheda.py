# scheda.py — VerificAI
# Scheda di allenamento: ~40 esercizi graduati (★ ★★ ★★★) sugli stessi argomenti della verifica
# di una verifica già generata, da dare alla classe prima della verifica.
# Una sezione per ogni esercizio della verifica, una chiamata all'AI per sezione (in parallelo).
# Nessun import di streamlit: resta testabile in isolamento (CLAUDE.md).

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import CALIBRAZIONE_SCUOLA, SCHEDA, sequenza_difficolta
from latex_utils import (
    aggiungi_spaziatura_grafici_tabelle, clean_tikz_spoilers, compila_pdf, compila_pdf_sicuro,
    extract_blocks, extract_preambolo, limita_altezza_grafici, rimuovi_logo_b64, rimuovi_vspace_corpo,
)
from prompts import SEPARATORE_SCHEDA, prompt_scheda_sezione, titolo_pulito

logger = logging.getLogger("verificai.scheda")

_STELLE = {1: r"$\bigstar$", 2: r"$\bigstar\bigstar$", 3: r"$\bigstar\bigstar\bigstar$"}
_LIVELLI_SCHEDA = r"Difficolt\`a: $\bigstar$ base \quad $\bigstar\bigstar$ media \quad $\bigstar\bigstar\bigstar$ sfida."


def _nota_scheda(materia: str) -> str:
    """«Mostrando i passaggi» solo per le materie scientifiche."""
    from config import MATERIE_STEM
    inizio = ("Svolgi gli esercizi sul quaderno, mostrando i passaggi. " if materia in MATERIE_STEM
              else "Svolgi gli esercizi sul quaderno. ")
    return inizio + _LIVELLI_SCHEDA
_MAX_CARATTERI_ESERCIZIO = 1500   # testo dell'esercizio della verifica passato all'AI


# ── 1. Dalla verifica alle sezioni ────────────────────────────────────────────

def _sezioni_dalla_verifica(latex_verifica: str) -> list:
    """Esercizi della verifica → [{"titolo", "corpo"}] senza punteggi e senza logo."""
    _, blocchi = extract_blocks(rimuovi_logo_b64(latex_verifica))
    sezioni = []
    for b in blocchi:
        corpo = re.sub(r"\s*\(\s*\d+(?:[.,]\d+)?\s*pt\s*\)", "", b["body"])
        corpo = re.sub(r"\n{3,}", "\n\n", corpo).strip()
        if not corpo:
            continue
        sezioni.append({
            "titolo": titolo_pulito(b["title"]) or "Esercizi",
            "corpo": corpo[:_MAX_CARATTERI_ESERCIZIO],
        })
    return sezioni


def _piano_sezioni(sezioni: list, scuola: str, totale: int) -> list:
    """Quanti esercizi per sezione e con quali livelli. Con troppi esercizi si raggruppano a coppie."""
    massimo = SCHEDA["max_sezioni"]
    while len(sezioni) > massimo:
        sezioni = [
            ({"titolo": f"{sezioni[i]['titolo']} · {sezioni[i + 1]['titolo']}",
              "corpo": (sezioni[i]["corpo"] + "\n\n" + sezioni[i + 1]["corpo"])[:_MAX_CARATTERI_ESERCIZIO]}
             if i + 1 < len(sezioni) else sezioni[i])
            for i in range(0, len(sezioni), 2)
        ]
    n = len(sezioni)
    base, extra = divmod(totale, n)
    piano = []
    for i, s in enumerate(sezioni):
        k = base + (1 if i < extra else 0)
        k = max(SCHEDA["min_per_sezione"], min(SCHEDA["max_per_sezione"], k))
        piano.append({**s, "livelli": sequenza_difficolta(scuola, k)})
    return piano


# ── 2. Chiamata all'AI e lettura della risposta ───────────────────────────────

def _blocchi_da_risposta(testo: str) -> list:
    """Risposta dell'AI → lista di esercizi (testo LaTeX), scartando i blocchi non utilizzabili."""
    t = (testo or "").replace("```latex", "").replace("```", "")
    esercizi = []
    for blocco in re.split(rf"^\s*{re.escape(SEPARATORE_SCHEDA)}+\s*$", t, flags=re.MULTILINE):
        b = blocco.strip()
        # via numerazione, stelle e risposte che l'AI mette di sua iniziativa
        b = re.sub(r"^\s*(?:\\textbf\{)?\s*(?:Esercizio\s*)?\d+\s*[.):\-]\s*\}?\s*", "", b)
        b = re.sub(r"\s*\(\s*\d+(?:[.,]\d+)?\s*pt\s*\)", "", b)
        if len(b) < 12 or re.search(r"\\(?:subsection|section|documentclass|begin\{document\})", b):
            continue
        esercizi.append(b)
    return esercizi


def _chiedi_sezione(modello, sez: dict, materia: str, scuola: str, argomento: str) -> list:
    """Gli esercizi di una sezione; se ne mancano troppi si riprova una volta sola."""
    k = len(sez["livelli"])
    prompt = prompt_scheda_sezione(
        materia, scuola, argomento, sez["titolo"], sez["corpo"], sez["livelli"],
        CALIBRAZIONE_SCUOLA.get(scuola, ""),
    )
    migliore = []
    for tentativo in range(2):
        risposta = modello.generate_content([prompt], generation_config={"temperature": 0.9})
        esercizi = _blocchi_da_risposta(risposta.text)
        if len(esercizi) > len(migliore):
            migliore = esercizi
        if len(migliore) >= max(1, int(0.6 * k)):
            break
        logger.warning("Sezione «%s»: %d esercizi su %d, riprovo", sez["titolo"], len(migliore), k)
    return migliore[:k]


# ── 3. Assemblaggio e compilazione ────────────────────────────────────────────

def _preambolo_scheda(latex_verifica: str, materia: str) -> str:
    """Intestazione della verifica (logo compreso) con titolo e nota della scheda."""
    pre = extract_preambolo(latex_verifica)   # con il logo: i dati restano nel commento della verifica
    if not pre:
        from generation import _costruisci_preambolo   # intestazione standard se la verifica non ne ha una riconoscibile
        pre, _ = _costruisci_preambolo(materia, "", "", False)
    pre = pre.replace("Verifica di ", "Allenamento di ", 1)
    pre = re.sub(r"(?:Svolgere tutti gli esercizi mostrando i passaggi|Rispondere a tutte le richieste in modo chiaro e completo)\.",
                 lambda _m: _nota_scheda(materia), pre, count=1)
    return pre


def _corpo_sezione(indice: int, titolo: str, esercizi: list, livelli: list, primo_numero: int) -> str:
    righe = [
        f"\\subsection*{{Parte {indice} · {titolo}}}",
        "\\begin{enumerate}\\setlength{\\itemsep}{6pt}",
    ]
    for j, testo in enumerate(esercizi):
        stelle = _STELLE.get(livelli[j] if j < len(livelli) else 2, _STELLE[2])
        righe.append(f"\\item[\\textbf{{{primo_numero + j}.}}] {{\\footnotesize {stelle}}}\\ {testo}")
    righe.append("\\end{enumerate}\n")
    return "\n".join(righe)


def _pulisci(latex: str) -> str:
    latex = clean_tikz_spoilers(latex)
    latex = aggiungi_spaziatura_grafici_tabelle(latex)
    latex = limita_altezza_grafici(latex)
    return rimuovi_vspace_corpo(latex)


def _assembla(preambolo: str, sezioni: list) -> str:
    """sezioni: [{"titolo", "esercizi", "livelli"}] → LaTeX completo, numerazione continua."""
    corpo, numero = [], 1
    for i, s in enumerate(sezioni, 1):
        if not s["esercizi"]:
            continue
        corpo.append(_corpo_sezione(i, s["titolo"], s["esercizi"], s["livelli"], numero))
        numero += len(s["esercizi"])
    return _pulisci(preambolo + "\n".join(corpo) + "\n\\end{document}\n")


def _compila_isolando(preambolo: str, sezioni: list, avvisi: list):
    """La compilazione completa è fallita: si scartano le sole sezioni che non compilano."""
    buone = []
    for i, s in enumerate(sezioni):
        if not s["esercizi"]:
            continue
        pdf, _ = compila_pdf(_assembla(preambolo, [s]))
        if pdf:
            buone.append(s)
        else:
            avvisi.append(f"La parte «{s['titolo']}» non si è impaginata ed è stata tolta.")
    if not buone:
        return None, None
    latex = _assembla(preambolo, buone)
    pdf, _err, latex = compila_pdf_sicuro(latex)
    return (latex, pdf) if pdf else (None, None)


# ── API ───────────────────────────────────────────────────────────────────────

def genera_scheda(modello, materia: str, scuola: str, argomento: str, latex_verifica: str,
                  on_progress=None, totale: int | None = None) -> dict:
    """
    Crea la scheda di allenamento a partire dalla verifica (la Fila A attuale).

    modello      : ModelloAI del piano dell'utente (si usa .per("scheda"); nessun ID scritto a mano)
    on_progress  : callback(testo) chiamato dal thread principale a ogni sezione completata
    Restituisce {"latex", "pdf", "n_esercizi", "avvisi"}; "pdf" è None solo se nulla compila.
    Solleva ValueError se la verifica non ha esercizi riconoscibili.
    """
    totale = totale or SCHEDA["esercizi_totali"]
    avvisi: list = []
    sezioni = _sezioni_dalla_verifica(latex_verifica)
    if not sezioni:
        raise ValueError("La verifica non contiene esercizi da cui partire.")
    piano = _piano_sezioni(sezioni, scuola, totale)

    mod = modello.per("scheda")
    risultati: list = [None] * len(piano)
    fatti = 0
    with ThreadPoolExecutor(max_workers=max(1, SCHEDA["parallelo"])) as pool:
        futuri = {pool.submit(_chiedi_sezione, mod, sez, materia, scuola, argomento): i
                  for i, sez in enumerate(piano)}
        for fut in as_completed(futuri):
            i = futuri[fut]
            try:
                risultati[i] = fut.result()
            except Exception as e:   # una sezione che fallisce non ferma le altre
                logger.error("Sezione «%s» non riuscita: %s", piano[i]["titolo"], e)
                risultati[i] = []
                avvisi.append(f"Non sono riuscito a preparare la parte «{piano[i]['titolo']}».")
            fatti += 1
            if on_progress:
                on_progress(f"Preparo gli esercizi: parte {fatti} di {len(piano)}")

    sezioni_finali = [
        {"titolo": p["titolo"], "esercizi": risultati[i] or [], "livelli": p["livelli"]}
        for i, p in enumerate(piano)
    ]
    for s in sezioni_finali:
        previsti = len(s["livelli"])
        if s["esercizi"] and len(s["esercizi"]) < previsti:
            avvisi.append(f"Nella parte «{s['titolo']}» ci sono {len(s['esercizi'])} esercizi invece di {previsti}.")
    n_esercizi = sum(len(s["esercizi"]) for s in sezioni_finali)
    if n_esercizi == 0:
        raise RuntimeError("L'assistente non ha prodotto esercizi utilizzabili.")

    if on_progress:
        on_progress("Impagino la scheda")
    preambolo = _preambolo_scheda(latex_verifica, materia)
    latex = _assembla(preambolo, sezioni_finali)
    pdf, err, latex = compila_pdf_sicuro(latex)
    if not pdf:
        logger.warning("Compilazione della scheda fallita (%s): isolo le sezioni", str(err)[:200])
        latex2, pdf = _compila_isolando(preambolo, sezioni_finali, avvisi)
        latex = latex2 or latex
        if pdf:
            n_esercizi = len(re.findall(r"\\item\[\\textbf\{\d+\.\}\]", latex))
    return {"latex": latex, "pdf": pdf, "n_esercizi": n_esercizi, "avvisi": avvisi}
