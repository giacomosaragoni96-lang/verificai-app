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
from prompts import prompt_leggi_verifica_completa, prompt_correggi_verifica, prompt_controlla_errori_verifica, prompt_descrivi_file

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


def leggi_verifica(model, immagini: list, materia: str = "", scuola: str = "", max_esercizi: int = MAX_ESERCIZI, on_progress=None) -> dict:
    """
    Legge le pagine e restituisce {"ok", "titolo", "punti_dichiarati", "esercizi", "messaggio"}.
    Ogni esercizio: titolo, latex, figura, dubbi, correzioni, ricontrollato. Qualsiasi errore diventa {"ok": False, "messaggio"}.
    """
    errore = ef.controlla_foto(immagini, MAX_FILE)
    if errore:
        return {"ok": False, "esercizi": [], "messaggio": errore}
    def _p(passo: str):
        if on_progress:
            try:
                on_progress(passo)
            except Exception:
                pass

    from docx_import import espandi_file
    esteso = espandi_file(immagini)
    if not esteso:
        return {"ok": False, "esercizi": [], "messaggio": "Non riesco a leggere il file Word: salvalo di nuovo come .docx oppure caricane il PDF."}
    parti = ef._parti(esteso)
    esercizi, problema, testo = [], None, ""
    _p("lettura")
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
    _p("controllo")
    # il secondo sguardo sulle pagine e la ricerca degli errori non dipendono l'uno dall'altra: si fanno insieme (meno attesa)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as _ex:
        _f1 = _ex.submit(ef.ricontrolla, model, parti, esercizi, True)
        _f2 = _ex.submit(_testo_errori, model, esercizi, materia)
        try:
            esercizi = _f1.result()
        except Exception:
            pass
        try:
            _grezzo_errori = _f2.result()
        except Exception:
            _grezzo_errori = ""
    _p("fine")
    dichiarati = _campo_globale(testo, "PUNTI_TOTALI")
    try:
        dichiarati = float(dichiarati.replace(",", ".")) if dichiarati else 0.0
    except ValueError:
        dichiarati = 0.0
    return {"ok": True, "titolo": titolo_pulito(_campo_globale(testo, "VERIFICA_TITOLO"), materia), "punti_dichiarati": dichiarati,
            "esercizi": esercizi, "messaggio": "", "note": trova_note(_grezzo_errori, esercizi)}


_RE_NOTA = re.compile(r"===\s*NOTA\s*===(.*?)(?:===\s*FINE\s*===|(?====\s*NOTA\s*===)|\Z)", re.DOTALL | re.IGNORECASE)
MAX_NOTE = 5


_SUB = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
_SUP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SIMBOLI = {r"\cdot": "·", r"\times": "×", r"\le": "≤", r"\leq": "≤", r"\ge": "≥", r"\geq": "≥", r"\neq": "≠", r"\pi": "π", r"\infty": "∞",
            r"\pm": "±", r"\to": "→", r"\rightarrow": "→", r"\Rightarrow": "⇒", r"\in": "∈", r"\mathbb{R}": "ℝ", r"\approx": "≈", r"\ldots": "…", r"\dots": "…",
            r"\alpha": "α", r"\beta": "β", r"\lambda": "λ", r"\Delta": "Δ", r"\displaystyle": "", r"\left": "", r"\right": "", r"\,": " ", r"\;": " "}


def descrivi_file(model, immagini: list) -> dict:
    """
    Lettura rapida (una chiamata breve, solo le prime pagine) di ciò che è stato caricato: {"ok", "materia", "argomento", "n_esercizi", "descrizione"}.
    Serve a far vedere al docente che il file è stato capito, prima della lettura completa. Qualsiasi problema = {"ok": False}.
    """
    try:
        errore = ef.controlla_foto(immagini, MAX_FILE)
        if errore:
            return {"ok": False}
        from docx_import import espandi_file
        esteso = espandi_file(immagini)
        if not esteso:
            return {"ok": False}
        parti = ef._parti(esteso)[:4]
        testo = ef._chiama(model, [prompt_descrivi_file()] + parti)
    except Exception:
        return {"ok": False}
    def campo(nome):
        m = re.search(rf"^\s*{nome}\s*:\s*(.+?)\s*$", testo, re.MULTILINE | re.IGNORECASE)
        return m.group(1).strip() if m else ""
    descr = campo("DESCRIZIONE")
    if not descr:
        return {"ok": False}
    try:
        n = int(re.sub(r"\D", "", campo("ESERCIZI")) or 0)
    except ValueError:
        n = 0
    materia = campo("MATERIA")
    return {"ok": True, "materia": "" if materia.lower().startswith("non chiar") else materia, "argomento": campo("ARGOMENTO"),
            "n_esercizi": n, "descrizione": descr[:300]}


def testo_leggibile(t: str) -> str:
    """Un testo con un po' di LaTeX (formule dentro \\( \\), x_1, \\frac…) in testo semplice da leggere in una nota."""
    t = t or ""
    for _ in range(3):
        t = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", lambda m: "(" + m.group(1) + ")/(" + m.group(2) + ")", t)
    t = re.sub(r"\\sqrt\{([^{}]*)\}", lambda m: "√(" + m.group(1) + ")", t)
    for k in sorted(_SIMBOLI, key=len, reverse=True):
        t = t.replace(k, _SIMBOLI[k])
    t = re.sub(r"\\[()\[\]]|\$", "", t)
    t = re.sub(r"_\{([^{}]+)\}", lambda m: m.group(1).translate(_SUB), t)
    t = re.sub(r"_([0-9]+)", lambda m: m.group(1).translate(_SUB), t)
    t = re.sub(r"\^\{([^{}]+)\}", lambda m: m.group(1).translate(_SUP), t)
    t = re.sub(r"\^([0-9n])", lambda m: m.group(1).translate(_SUP), t)
    t = re.sub(r"\\[a-zA-Z]+", "", t).replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", t).strip()


def bozza_leggibile(testo: str, massimo: int = 6, lunghezza: int = 120) -> list:
    """[(titolo, primo pezzo di testo)] degli esercizi scritti finora, in testo leggibile: serve a mostrare una bozza durante l'attesa."""
    out = []
    for blocco in re.split(r"(?=\\subsection\*\{)", testo or ""):
        m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", blocco, re.DOTALL)
        if not m:
            continue
        corpo = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?|\\item(?:\[[^\]]*\])?|\[\[.*?\]\]|%[^\n]*", " ", m.group(2), flags=re.DOTALL)
        corpo = re.sub(r"\(\s*\d+(?:[.,]\d+)?\s*pt\s*\)", "", corpo)
        corpo = testo_leggibile(corpo)
        out.append((testo_leggibile(m.group(1)), (corpo[:lunghezza] + ("…" if len(corpo) > lunghezza else "")).strip()))
        if len(out) >= massimo:
            break
    return out


def impronta(latex: str) -> str:
    """Un'impronta breve del testo di un esercizio: una nota vale solo finché l'esercizio è quello su cui è stata scritta."""
    import hashlib
    return hashlib.md5((latex or "").strip().encode("utf-8")).hexdigest()[:10]


def _trova_una_volta(latex: str, frammento: str):
    """(inizio, fine) del frammento nel testo se compare UNA sola volta (anche con spazi diversi), altrimenti None."""
    f = (frammento or "").strip()
    if len(f) < 2:
        return None
    if latex.count(f) == 1:
        i = latex.index(f)
        return i, i + len(f)
    pezzi = [re.escape(x) for x in f.split()]
    if not pezzi:
        return None
    trovati = list(re.finditer(r"\s+".join(pezzi), latex))
    return (trovati[0].start(), trovati[0].end()) if len(trovati) == 1 else None


def sostituisci_frammento(latex: str, da: str, a: str):
    """Il testo con il frammento `da` sostituito da `a` (solo se `da` compare una volta sola), altrimenti None."""
    pos = _trova_una_volta(latex or "", da)
    if pos is None:
        return None
    return latex[:pos[0]] + (a or "").strip() + latex[pos[1]:]


def differenze(prima: str, dopo: str, massimo: int = 4) -> list:
    """Le differenze tra due testi come [(prima, dopo)] in testo leggibile: serve a mostrare cosa è cambiato davvero."""
    import difflib
    ta, tb = testo_leggibile(prima).split(), testo_leggibile(dopo).split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        a1, b1 = max(0, i1 - 1), min(len(ta), i2 + 1)
        c1, d1 = max(0, j1 - 1), min(len(tb), j2 + 1)
        out.append((" ".join(ta[a1:b1]), " ".join(tb[c1:d1])))
        if len(out) >= massimo:
            break
    return out


def leggi_note(testo: str, esercizi: list) -> list:
    """
    Le note dalla risposta del modello: [{indice, problema, proposta, da, a, prima, dopo, su}]. Ogni nota è una SOSTITUZIONE di un frammento:
    vale solo se `da` compare una volta sola nell'esercizio e il testo resta LaTeX valido; mai una riscrittura dell'esercizio.
    """
    note = []
    for m in _RE_NOTA.finditer(re.sub(r"```(?:latex|tex)?", "", testo or "")):
        b = m.group(1)
        mi = re.search(r"^[ \t]*ESERCIZIO[ \t]*:[ \t]*(\d+)", b, re.MULTILINE | re.IGNORECASE)
        pr = re.search(r"^[ \t]*PROBLEMA[ \t]*:[ \t]*(.+?)[ \t]*$", b, re.MULTILINE | re.IGNORECASE)
        po = re.search(r"^[ \t]*PROPOSTA[ \t]*:[ \t]*(.+?)[ \t]*$", b, re.MULTILINE | re.IGNORECASE)
        ft = re.search(r"^[ \t]*DA[ \t]*:[ \t]*(.*?)\n[ \t]*A[ \t]*:[ \t]*(.*)$", b, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        if not (mi and pr and po and ft):
            continue
        idx = int(mi.group(1)) - 1
        if not (0 <= idx < len(esercizi)):
            continue
        da, a = ft.group(1).strip(), ft.group(2).strip()
        originale = (esercizi[idx].get("latex") or "").strip()
        nuovo = sostituisci_frammento(originale, da, a)
        if nuovo is None or nuovo.strip() == originale or ef.problemi_latex(nuovo) or abs(len(nuovo) - len(originale)) > 160:
            continue
        note.append({"indice": idx, "problema": testo_leggibile(pr.group(1).strip())[:300], "proposta": testo_leggibile(po.group(1).strip())[:300],
                     "da": da, "a": a, "prima": testo_leggibile(da)[:160], "dopo": testo_leggibile(a)[:160], "su": impronta(originale)})
        if len(note) >= MAX_NOTE:
            break
    return note


def _testo_errori(model, esercizi: list, materia: str = "") -> str:
    """La risposta grezza del controllo degli errori (vuota se qualcosa va storto)."""
    try:
        return ef._chiama(model, prompt_controlla_errori_verifica(_testo_numerato(esercizi), materia)) or ""
    except Exception:
        return ""


def trova_note(testo: str, esercizi: list) -> list:
    if not (testo or "").strip() or re.match(r"\s*NESSUNO\b", testo, re.IGNORECASE):
        return []
    return leggi_note(testo, esercizi)


def controlla_errori(model, esercizi: list, materia: str = "") -> list:
    """Un'ulteriore lettura del testo (senza foto) per segnalare errori oggettivi del docente. Mai bloccante: qualsiasi problema = nessuna nota."""
    return trova_note(_testo_errori(model, esercizi, materia), esercizi)


def applica_nota(esercizi: list, nota: dict) -> list:
    """Gli esercizi con la sostituzione della nota applicata (solo se l'esercizio è ancora quello della nota e il frammento è univoco)."""
    nuovi = [dict(e) for e in esercizi]
    i = nota.get("indice", -1)
    if 0 <= i < len(nuovi) and impronta(nuovi[i].get("latex")) == nota.get("su"):
        sost = sostituisci_frammento(nuovi[i].get("latex") or "", nota.get("da", ""), nota.get("a", ""))
        if sost is not None and not ef.problemi_latex(sost):
            nuovi[i]["latex"] = sost
            nuovi[i]["corretto_su_proposta"] = True
    return nuovi


def _senza_foto(latex: str):
    """(latex con segnaposto al posto delle figure-foto, blocchi): le immagini non vanno all'AI."""
    from latex_utils import proteggi_figure_foto
    return proteggi_figure_foto(latex or "")


def _testo_esercizi(esercizi: list) -> str:
    return "\n\n".join(f"===ESERCIZIO===\nTITOLO: {e.get('titolo', '')}\nTESTO:\n{_senza_foto(e['latex'])[0]}\n===FINE===" for e in esercizi)


def _testo_numerato(esercizi: list) -> str:
    """Gli esercizi con il loro numero (per le note: «Esercizio 2»)."""
    return "\n\n".join(f"ESERCIZIO {n} — {e.get('titolo', '')}\n{_senza_foto(e['latex'])[0]}" for n, e in enumerate(esercizi, 1))


def ripristina_figure_foto_(latex_ai: str, originale: dict) -> str:
    """Il testo restituito dall'AI con le figure-foto dell'originale rimesse (per confrontarlo con l'originale)."""
    from latex_utils import ripristina_figure_foto
    return ripristina_figure_foto(latex_ai, _senza_foto(originale.get("latex"))[1]).strip()


def numeri_citati(richiesta: str) -> set:
    """I numeri di esercizio nominati nella richiesta («nell'esercizio 2», «es. 3»): servono a limitare la correzione a quelli."""
    return {int(n) for n in re.findall(r"(?:esercizi[oi]?|es\.?|ex\.?)\s*(?:n[°.]?\s*)?(\d{1,2})", richiesta or "", re.IGNORECASE)}


def correggi_verifica(model, immagini: list, esercizi: list, richiesta: str) -> dict:
    """
    Il docente dice cosa non va; si riguardano le pagine e si corregge solo quello. Se nomina degli esercizi cambiano SOLO quelli (gli altri
    tornano com'erano comunque). Ritorna {"ok", "esercizi", "messaggio", "cambi": [(n, [(prima, dopo)])]}: i cambi si mostrano al docente.
    """
    richiesta = (richiesta or "").strip()
    if len(richiesta) < 3:
        return {"ok": False, "esercizi": esercizi, "messaggio": "Scrivi cosa non va (per esempio: «nell'esercizio 2 b) l'esponente è 3»)."}
    from docx_import import espandi_file
    parti = ef._parti(espandi_file(immagini))
    try:
        testo = ef._chiama(model, [prompt_correggi_verifica(_testo_esercizi(esercizi), richiesta[:600], len(parti))] + parti)
    except Exception as e:
        return {"ok": False, "esercizi": esercizi, "messaggio": f"Non sono riuscito a correggere ({str(e)[:120]}). Riprova."}
    nuovi, _ = ef.leggi_risposta(testo, tieni_punti=True, titolo_vuoto="")
    if len(nuovi) != len(esercizi):
        return {"ok": False, "esercizi": esercizi,
                "messaggio": "La correzione ha cambiato il numero di esercizi, quindi l'ho scartata: la verifica è rimasta com'era."}
    ammessi = numeri_citati(richiesta)
    risultato, cambi = [], []
    for n_idx, (n, o) in enumerate(zip(nuovi, esercizi), 1):
        if ammessi and n_idx not in ammessi:
            risultato.append(o)              # esercizio non nominato: resta com'era, qualunque cosa abbia risposto il modello
            continue
        if ripristina_figure_foto_(n["latex"], o) == (o.get("latex") or "").strip():
            risultato.append(o)
            continue
        from latex_utils import ripristina_figure_foto
        nuovo_latex = ripristina_figure_foto(n["latex"], _senza_foto(o.get("latex"))[1])
        risultato.append({**o, "titolo": n["titolo"], "figura": o.get("figura") if o.get("ha_figura_foto") else n["figura"], "latex": nuovo_latex, "dubbi": n["dubbi"],
                          "correzioni": [], "ricontrollato": True})
        cambi.append((n_idx, differenze(o.get("latex") or "", n["latex"])))
    if not cambi:
        return {"ok": False, "esercizi": esercizi, "messaggio": "Non ho trovato niente da cambiare: prova a dire più precisamente dove sta l'errore."}
    return {"ok": True, "esercizi": risultato, "messaggio": "", "cambi": cambi}


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
