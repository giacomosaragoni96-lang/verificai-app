"""
impagina.py — la verifica che il docente ha già, scritta o impaginata male, impaginata bene da noi (senza Streamlit).

Il docente carica il PDF o le foto (anche un collage di screenshot). Come per l'esercizio da foto (esercizio_foto.py) il testo NON passa dal modello
che «scrive verifiche»: lo riscriverebbe. Si trascrivono tutti gli esercizi in LaTeX senza cambiare nulla, un secondo giro li ricontrolla sulle
pagine, il docente vede il risultato e conferma o corregge; poi il programma impagina con l'intestazione, il logo e lo stile di sempre. Il
risultato è una verifica normale: da lì si fa la Fila B, la versione BES/DSA, le soluzioni, il Word.

Le figure si trattano come nell'esercizio da foto: grafici di funzione, figure geometriche semplici e tabelle si ricostruiscono; una figura che non si
può riprodurre identica non si inventa: l'esercizio si toglie oppure si tiene con uno spazio vuoto al suo posto, a scelta del docente.
"""
import re

import esercizio_foto as ef
from prompts import prompt_leggi_verifica_completa, prompt_correggi_verifica, prompt_controlla_errori_verifica

MAX_FILE = 8            # pagine o foto per volta
MAX_ESERCIZI = 12

_RE_PUNTI = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*pt\s*\)")
_SPAZIO_FIGURA = ("\\begin{center}\\fbox{\\parbox[c][3.2cm][c]{0.55\\linewidth}{\\centering\\textit{(figura)}}}\\end{center}")


def _campo_globale(testo: str, nome: str) -> str:
    m = re.search(rf"^\s*{nome}\s*:\s*(.+?)\s*$", testo or "", re.MULTILINE | re.IGNORECASE)
    v = m.group(1).strip() if m else ""
    return "" if v.lower().strip(" .") in ("nessuno", "nessuna", "-", "—") else v


def titolo_pulito(t: str, materia: str = "") -> str:
    """Il titolo della verifica senza «Verifica di <materia> -» davanti (l'intestazione lo scrive già)."""
    t = re.sub(r"[{}\\$]", "", t or "").strip(" .:")
    t = re.sub(r"^(?:verifica|compito|prova)\s+(?:scritta\s+)?(?:(?:di|su|sulle|sulla|sullo|sugli|sui|sul|del|della|dei|delle)\b\s*)?", "", t, flags=re.IGNORECASE)
    if materia and t.lower().startswith(materia.lower()):
        t = t[len(materia):]
    t = re.sub(r"^[\s\-–—:,.]+", "", t)
    return t.strip(" .:")[:80]


def leggi_verifica(model, immagini: list, materia: str = "", scuola: str = "", max_esercizi: int = MAX_ESERCIZI) -> dict:
    """
    Legge le pagine e restituisce {"ok", "titolo", "punti_dichiarati", "esercizi", "messaggio"}.
    Ogni esercizio: titolo, latex, figura, dubbi, correzioni, ricontrollato. Qualsiasi errore diventa {"ok": False, "messaggio"}.
    """
    errore = ef.controlla_foto(immagini, MAX_FILE)
    if errore:
        return {"ok": False, "esercizi": [], "messaggio": errore}
    parti = ef._parti(immagini)
    esercizi, problema, testo = [], None, ""
    for _tentativo in range(2):
        try:
            testo = ef._chiama(model, [prompt_leggi_verifica_completa(materia, scuola, len(parti), max_esercizi)] + parti)
        except Exception as e:
            return {"ok": False, "esercizi": [], "messaggio": f"Non sono riuscito a leggere il file ({str(e)[:120]}). Riprova tra poco."}
        esercizi, problema = ef.leggi_risposta(testo, tieni_punti=True, titolo_vuoto="")
        if esercizi or problema:
            break
    if not esercizi:
        return {"ok": False, "esercizi": [],
                "messaggio": problema or "Non vedo esercizi in questo file. Controlla che le pagine siano leggibili e riprova."}
    esercizi = esercizi[:max_esercizi]
    for e in esercizi:
        e["ricontrollato"], e["correzioni"] = False, []
    esercizi = ef.ricontrolla(model, parti, esercizi, tieni_punti=True)
    dichiarati = _campo_globale(testo, "PUNTI_TOTALI")
    try:
        dichiarati = float(dichiarati.replace(",", ".")) if dichiarati else 0.0
    except ValueError:
        dichiarati = 0.0
    return {"ok": True, "titolo": titolo_pulito(_campo_globale(testo, "VERIFICA_TITOLO"), materia), "punti_dichiarati": dichiarati,
            "esercizi": esercizi, "messaggio": "", "note": controlla_errori(model, esercizi, materia)}


_RE_NOTA = re.compile(r"===\s*NOTA\s*===(.*?)(?:===\s*FINE\s*===|(?====\s*NOTA\s*===)|\Z)", re.DOTALL | re.IGNORECASE)
MAX_NOTE = 5


def impronta(latex: str) -> str:
    """Un'impronta breve del testo di un esercizio: una nota vale solo finché l'esercizio è quello su cui è stata scritta."""
    import hashlib
    return hashlib.md5((latex or "").strip().encode("utf-8")).hexdigest()[:10]


def leggi_note(testo: str, esercizi: list) -> list:
    """Le note dalla risposta del modello: [{indice, problema, proposta, testo_corretto, su}]. Scarta quelle incomplete, rotte o senza cambiamento."""
    note = []
    for m in _RE_NOTA.finditer(re.sub(r"```(?:latex|tex)?", "", testo or "")):
        b = m.group(1)
        mi = re.search(r"^[ \t]*ESERCIZIO[ \t]*:[ \t]*(\d+)", b, re.MULTILINE | re.IGNORECASE)
        pr = re.search(r"^[ \t]*PROBLEMA[ \t]*:[ \t]*(.+?)[ \t]*$", b, re.MULTILINE | re.IGNORECASE)
        po = re.search(r"^[ \t]*PROPOSTA[ \t]*:[ \t]*(.+?)[ \t]*$", b, re.MULTILINE | re.IGNORECASE)
        tc = re.search(r"^[ \t]*TESTO_CORRETTO[ \t]*:[ \t]*\n?(.*)$", b, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        if not (mi and pr and po and tc):
            continue
        idx = int(mi.group(1)) - 1
        if not (0 <= idx < len(esercizi)):
            continue
        corretto = ef.pulisci_latex_esercizio(tc.group(1), tieni_punti=True)
        originale = (esercizi[idx].get("latex") or "").strip()
        if not corretto.strip() or corretto.strip() == originale or ef.problemi_latex(corretto):
            continue
        if abs(len(corretto) - len(originale)) > max(80, len(originale) // 2):
            continue                      # una «correzione» che riscrive mezzo esercizio non è una correzione
        note.append({"indice": idx, "problema": pr.group(1).strip()[:300], "proposta": po.group(1).strip()[:300],
                     "testo_corretto": corretto, "su": impronta(originale)})
        if len(note) >= MAX_NOTE:
            break
    return note


def controlla_errori(model, esercizi: list, materia: str = "") -> list:
    """Un'ulteriore lettura del testo (senza foto) per segnalare errori oggettivi del docente. Mai bloccante: qualsiasi problema = nessuna nota."""
    try:
        testo = ef._chiama(model, prompt_controlla_errori_verifica(_testo_numerato(esercizi), materia))
    except Exception:
        return []
    if re.match(r"\s*NESSUNO\b", testo or "", re.IGNORECASE):
        return []
    return leggi_note(testo, esercizi)


def applica_nota(esercizi: list, nota: dict) -> list:
    """Gli esercizi con la correzione proposta applicata (solo se l'esercizio è ancora quello della nota)."""
    nuovi = [dict(e) for e in esercizi]
    i = nota.get("indice", -1)
    if 0 <= i < len(nuovi) and impronta(nuovi[i].get("latex")) == nota.get("su"):
        nuovi[i]["latex"] = nota["testo_corretto"]
        nuovi[i]["corretto_su_proposta"] = True
    return nuovi


def _testo_esercizi(esercizi: list) -> str:
    return "\n\n".join(f"===ESERCIZIO===\nTITOLO: {e.get('titolo', '')}\nTESTO:\n{e['latex']}\n===FINE===" for e in esercizi)


def _testo_numerato(esercizi: list) -> str:
    """Gli esercizi con il loro numero (per le note: «Esercizio 2»)."""
    return "\n\n".join(f"ESERCIZIO {n} — {e.get('titolo', '')}\n{e['latex']}" for n, e in enumerate(esercizi, 1))


def correggi_verifica(model, immagini: list, esercizi: list, richiesta: str) -> dict:
    """Il docente dice cosa non va; si riguardano le pagine e si corregge solo quello. {"ok", "esercizi", "messaggio"}."""
    richiesta = (richiesta or "").strip()
    if len(richiesta) < 3:
        return {"ok": False, "esercizi": esercizi, "messaggio": "Scrivi cosa non va (per esempio: «nell'esercizio 2 b) l'esponente è 3»)."}
    parti = ef._parti(immagini)
    try:
        testo = ef._chiama(model, [prompt_correggi_verifica(_testo_esercizi(esercizi), richiesta[:600], len(parti))] + parti)
    except Exception as e:
        return {"ok": False, "esercizi": esercizi, "messaggio": f"Non sono riuscito a correggere ({str(e)[:120]}). Riprova."}
    nuovi, _ = ef.leggi_risposta(testo, tieni_punti=True, titolo_vuoto="")
    if len(nuovi) != len(esercizi):
        return {"ok": False, "esercizi": esercizi,
                "messaggio": "La correzione ha cambiato il numero di esercizi, quindi l'ho scartata: la verifica è rimasta com'era."}
    if all(n["latex"].strip() == o["latex"].strip() for n, o in zip(nuovi, esercizi)):
        return {"ok": False, "esercizi": esercizi, "messaggio": "Non ho trovato niente da cambiare: prova a dire più precisamente dove sta l'errore."}
    risultato = []
    for n, o in zip(nuovi, esercizi):
        risultato.append({**o, "titolo": n["titolo"], "figura": n["figura"], "latex": n["latex"], "dubbi": n["dubbi"],
                          "correzioni": [], "ricontrollato": True})
    return {"ok": True, "esercizi": risultato, "messaggio": ""}


def punti_rilevati(esercizi: list) -> dict:
    """{"totale", "richieste", "con_punti"}: i punteggi trovati sul foglio (servono a decidere se tenerli)."""
    totale, richieste, con_punti = 0.0, 0, 0
    for e in esercizi:
        t = e.get("latex") or ""
        voci = len(re.findall(r"\\item\b", t)) or 1
        richieste += voci
        trovati = [float(x) for x in _RE_PUNTI.findall(t)]
        con_punti += min(len(trovati), voci)
        totale += sum(trovati)
    return {"totale": totale, "richieste": richieste, "con_punti": con_punti}


def punti_del_foglio(esercizi: list):
    """
    Gli esercizi con i punteggi del foglio portati a numeri interi (la tabella dei punteggi li vuole interi): se hanno decimali (0.5, 1.5)
    si moltiplicano tutti per 2, 4, 10, 20 o 100 (es. 1.5 su 10 → 15 su 100). Ritorna (esercizi, totale, fattore); fattore 1 = invariati.
    """
    valori = [float(x) for e in esercizi for x in _RE_PUNTI.findall(e.get("latex") or "")]
    if not valori:
        return esercizi, 0, 1
    fattore = 1
    for f in (1, 2, 4, 10, 20, 100):
        if all(abs(v * f - round(v * f)) < 1e-9 for v in valori):
            fattore = f
            break
    if fattore == 1:
        return esercizi, int(round(sum(valori))), 1
    nuovi = []
    for e in esercizi:
        lat = _RE_PUNTI.sub(lambda m: "(" + str(int(round(float(m.group(1)) * fattore))) + " pt)", e.get("latex") or "")
        nuovi.append({**e, "latex": lat})
    return nuovi, int(round(sum(valori) * fattore)), fattore


def senza_punti(esercizi: list) -> list:
    """Gli stessi esercizi senza i punteggi del foglio (si assegnano poi in automatico)."""
    return [{**e, "latex": re.sub(r"[ \t]*" + _RE_PUNTI.pattern, "", e.get("latex") or "")} for e in esercizi]


def problemi_per_esercizio(esercizi: list) -> list:
    """[(indice da 0, motivo)] per gli esercizi che non si possono includere così come sono (figura non riproducibile, LaTeX rotto)."""
    out = []
    for i, e in enumerate(esercizi):
        st = ef.stato_esercizio(e)
        if not st["utilizzabile"]:
            out.append((i, st["motivo"], e.get("figura") == "non_riproducibile" or "[[FIGURA NON RIPRODUCIBILE]]" in (e.get("latex") or "").upper()))
    return out


def _blocchi(esercizi: list, con_spazio_figura: set) -> str:
    parti = []
    for n, e in enumerate(esercizi, 1):
        corpo = (e.get("latex") or "").strip()
        if n - 1 in con_spazio_figura:
            corpo = re.sub(r"\[\[\s*FIGURA NON RIPRODUCIBILE\s*\]\]", lambda m: _SPAZIO_FIGURA, corpo, flags=re.IGNORECASE)
        titolo = ef._titolo_pulito(e.get("titolo", ""), "")
        parti.append("\\subsection*{Esercizio " + str(n) + (": " + titolo if titolo else "") + "}\n" + corpo + "\n")
    return "\n".join(parti) + "\n\\end{document}"


def genera_da_trascrizione(esercizi: list, titolo: str, materia: str, mostra_punteggi: bool, punti_totali: int, con_griglia: bool,
                           stile=None, con_spazio_figura: set | None = None, richiesta: str = "", model=None, on_progress=None,
                           punti_fedeli: bool = False) -> dict:
    """
    Impagina gli esercizi trascritti e restituisce lo stesso dizionario di generation.genera_verifica (titolo, A, B, R, RB, S), così il resto
    dell'app (anteprima, modifica, Fila B, BES/DSA, Word) funziona come per una verifica creata da zero. Con `richiesta` (facoltativa) il
    docente può chiedere cambiamenti: si applicano dopo, con la stessa funzione della «modifica rapida».
    """
    from generation import _costruisci_preambolo, _assembla_e_compila, modifica_verifica_libera
    from latex_utils import reconstruct_latex

    def _avanza(t):
        if on_progress:
            on_progress(t)

    e_mat = any(k in (materia or "").lower() for k in ["matem", "fis", "chim", "inform", "elettr", "meccan"])
    titolo = titolo_pulito(titolo, materia)
    pre, _ = _costruisci_preambolo(materia, titolo, "", e_mat, stile)
    if not titolo:
        pre = pre.replace(": }", "}", 1)             # senza titolo l'intestazione resta «Verifica di Materia»
    corpo = _blocchi(esercizi, con_spazio_figura or set())
    _avanza("Compilazione PDF…")
    latex_a, pdf_a = _assembla_e_compila(pre, corpo, mostra_punteggi, punti_totali, con_griglia, fedele=True, punti_fedeli=punti_fedeli)

    if (richiesta or "").strip() and model is not None and latex_a:
        _avanza("Applico le tue richieste…")
        try:
            r = modifica_verifica_libera(model, materia, titolo or materia, latex_a, richiesta, mostra_punteggi, punti_totali)
        except Exception:
            r = {"ok": False}
        if r.get("ok"):
            nuovo = reconstruct_latex(r["preambolo"], r["blocchi"])
            corpo2 = nuovo[len(r["preambolo"]):]
            lat2, pdf2 = _assembla_e_compila(r["preambolo"], corpo2, mostra_punteggi, punti_totali, con_griglia, fedele=True,
                                             punti_fedeli=punti_fedeli)
            if pdf2:
                latex_a, pdf_a = lat2, pdf2

    vuoto = {"latex": "", "pdf": None}
    return {"titolo": titolo or materia, "A": {"latex": latex_a, "pdf": pdf_a}, "B": dict(vuoto), "R": dict(vuoto), "RB": dict(vuoto),
            "S": {"latex": "", "pdf": None, "testo": ""}, "_impaginata": True}
