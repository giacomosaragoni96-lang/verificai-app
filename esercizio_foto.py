"""
esercizio_foto.py — un esercizio del libro, da una foto, dentro la verifica (senza Streamlit).

Il docente fotografa un esercizio e lo vuole IDENTICO nella verifica. Per questo l'esercizio non passa dal modello che scrive la
verifica (lo riscriverebbe): si legge una volta, si ricontrolla con un secondo sguardo indipendente, lo vede il docente accanto
alla foto e, solo se lo conferma, il programma lo inserisce al suo posto nella verifica già scritta.

Catena: leggi_esercizi_da_foto (trascrizione) → ricontrolla (confronto con la foto) → il docente conferma, o corregge con
correggi_esercizio → blocco_latex / inserisci_esercizi (inserimento deterministico, rinumerazione).

Figure: grafici di funzioni (riga [[GRAFICO: …]], disegnata dal programma), figure geometriche semplici (TikZ) e tabelle si
riproducono; un quadro, una fotografia, una cartina o uno schema complesso NO: l'esercizio viene segnalato come non utilizzabile
invece di inventare una figura «simile». Il LaTeX scritto dall'AI è input non fidato: si tolgono i comandi che leggono file o
cambiano il documento.
"""
import re

from config import MAX_ESERCIZI_DA_FOTO
from prompts import (
    prompt_leggi_esercizi_foto, prompt_ricontrolla_trascrizione, prompt_correggi_trascrizione,
)

FIGURE_VALIDE = ("nessuna", "grafico_funzione", "figura_geometrica", "tabella", "non_riproducibile")
MAX_FOTO = 6                       # foto o pagine per volta
MAX_BYTE_FOTO = 12 * 1024 * 1024   # oltre questa dimensione non si manda al modello

_RE_BLOCCO = re.compile(r"===\s*ESERCIZIO\s*===(.*?)(?:===\s*FINE\s*===|(?====\s*ESERCIZIO\s*===)|\Z)", re.DOTALL | re.IGNORECASE)
_RE_PROBLEMA = re.compile(r"^\s*PROBLEMA\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_RE_SPEC_GRAFICO = re.compile(r"\[\[\s*GRAFICO\s*:\s*(.*?)\]\]", re.DOTALL | re.IGNORECASE)

# Comandi che un esercizio non deve mai contenere: leggono o scrivono file, cambiano il documento, ridefiniscono LaTeX.
_RE_VIETATI = re.compile(
    r"\\(?:documentclass|usepackage|RequirePackage|begin\{document\}|end\{document\}|input|include|includegraphics|"
    r"includepdf|openin|openout|read|readline|write|immediate|catcode|def|edef|gdef|xdef|let|newcommand|renewcommand|"
    r"providecommand|newenvironment|csname|expandafter|loop|special|pdfliteral|pdfshellescape|directlua|subsection\*?|section\*?)\b"
)


# ── LETTURA DELLA RISPOSTA DEL MODELLO ──────────────────────────────────────────────────────────────

def _campo(blocco: str, nome: str) -> str:
    m = re.search(rf"^[ \t]*{nome}[ \t]*:[ \t]*(.*?)[ \t]*$", blocco, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _testo_del_blocco(blocco: str) -> str:
    m = re.search(r"^\s*TESTO\s*:\s*\n?(.*)$", blocco, re.DOTALL | re.MULTILINE | re.IGNORECASE)
    return m.group(1) if m else ""


def _dubbi(valore: str, blocco: str) -> list:
    """Righe di DUBBI: sulla stessa riga del campo e, se continuano, sulle righe successive fino a TESTO."""
    m = re.search(r"^\s*DUBBI\s*:\s*(.*?)^\s*TESTO\s*:", blocco, re.DOTALL | re.MULTILINE | re.IGNORECASE)
    grezzo = m.group(1) if m else valore
    righe = [re.sub(r"^\s*[-•*]\s*", "", r).strip() for r in grezzo.splitlines()]
    righe = [r for r in righe if r and r.lower().strip(" .") not in ("nessuno", "nessun dubbio", "nessuna")]
    return righe[:8]


_RE_RITAGLIO = re.compile(r"pagina\s*=\s*(\d+)\D+x0\s*=\s*(\d+)\D+y0\s*=\s*(\d+)\D+x1\s*=\s*(\d+)\D+y1\s*=\s*(\d+)", re.IGNORECASE)


def _ritaglio(valore: str):
    """{pagina, x0, y0, x1, y1} (millesimi) dal campo RITAGLIO, oppure None se manca o non ha senso."""
    m = _RE_RITAGLIO.search(valore or "")
    if not m:
        return None
    pagina, x0, y0, x1, y1 = (int(v) for v in m.groups())
    x0, x1 = sorted((min(1000, x0), min(1000, x1)))
    y0, y1 = sorted((min(1000, y0), min(1000, y1)))
    if pagina < 1 or x1 - x0 < 40 or y1 - y0 < 40:
        return None
    return {"pagina": pagina, "x0": x0, "y0": y0, "x1": x1, "y1": y1}


def leggi_risposta(testo: str, tieni_punti: bool = False, titolo_vuoto: str = "Esercizio dal libro") -> tuple:
    """(lista di esercizi, problema o None) dalla risposta in formato a marcatori."""
    testo = re.sub(r"```(?:latex|tex)?", "", testo or "")
    esercizi = []
    for m in _RE_BLOCCO.finditer(testo):
        b = m.group(1)
        corpo = pulisci_latex_esercizio(_testo_del_blocco(b), tieni_punti)
        if not corpo.strip():
            continue
        figura = _campo(b, "FIGURA").lower().replace(" ", "_")
        figura = figura if figura in FIGURE_VALIDE else ("non_riproducibile" if "non_riprod" in figura else "nessuna")
        esercizi.append({
            "titolo": _titolo_pulito(_campo(b, "TITOLO"), titolo_vuoto),
            "figura": figura,
            "dubbi": _dubbi(_campo(b, "DUBBI"), b),
            "ritaglio": _ritaglio(_campo(b, "RITAGLIO")),
            "latex": corpo,
            "differenze": _campo_multi(b, "DIFFERENZE"),
            "esito": _campo(b, "ESITO").lower(),
        })
    problema = None
    if not esercizi:
        mp = _RE_PROBLEMA.search(testo)
        problema = mp.group(1).strip() if mp else None
    return esercizi, problema


def _campo_multi(blocco: str, nome: str) -> list:
    m = re.search(rf"^\s*{nome}\s*:\s*(.*?)^\s*TESTO\s*:", blocco, re.DOTALL | re.MULTILINE | re.IGNORECASE)
    if not m:
        return []
    righe = [re.sub(r"^\s*[-•*]\s*", "", r).strip() for r in m.group(1).splitlines()]
    return [r for r in righe if r and r.lower().strip(" .") not in ("nessuna", "nessuno", "nessuna differenza")][:10]


def _titolo_pulito(t: str, vuoto: str = "Esercizio dal libro") -> str:
    t = re.sub(r"^\s*(esercizio|es\.?)\s*\d*\s*[:.\-–—]?\s*", "", t or "", flags=re.IGNORECASE)
    t = re.sub(r"[{}\\$]", "", t).strip(" .:")
    return (t[:60] or vuoto)


def pulisci_latex_esercizio(testo: str, tieni_punti: bool = False) -> str:
    """Toglie ciò che non è il corpo dell'esercizio: recinti di codice, numeri del libro in testa, comandi vietati."""
    t = re.sub(r"```(?:latex|tex)?", "", testo or "").strip()
    t = re.sub(r"^\s*===.*$", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*(?:ESERCIZIO|Esercizio)\s+\d+\s*[\u2014\u2013:\-].*\n", "", t.lstrip("\n"), count=1)     # «ESERCIZIO 2 — titolo» in testa
    righe = []
    for r in t.splitlines():
        if _RE_VIETATI.search(r):
            r = _RE_VIETATI.sub("", r)
        righe.append(r.rstrip())
    t = "\n".join(righe).strip()
    # punteggi che il modello avesse scritto lo stesso: li aggiunge il programma (non per la verifica completa, dove sono quelli del docente)
    if not tieni_punti:
        t = re.sub(r"\s*\(\s*\d+(?:[.,]\d+)?\s*pt\s*\)", "", t)
    return t


# ── CONTROLLI SUL LATEX ─────────────────────────────────────────────────────────────────────────────

def problemi_latex(latex: str) -> list:
    """Difetti che renderebbero l'esercizio inutilizzabile (liste vuota = va bene)."""
    p = []
    t = latex or ""
    aperti = re.findall(r"\\begin\{([a-zA-Z*]+)\}", t)
    chiusi = re.findall(r"\\end\{([a-zA-Z*]+)\}", t)
    if sorted(aperti) != sorted(chiusi):
        p.append("gli ambienti LaTeX non sono chiusi bene")
    if t.count("\\(") != t.count("\\)") or t.count("\\[") != t.count("\\]"):
        p.append("una formula non è chiusa")
    if t.count("{") != t.count("}") and not re.search(r"\\[{}]", t):
        p.append("le parentesi graffe non tornano")
    if "[[FIGURA NON RIPRODUCIBILE]]" in t.upper():
        p.append("la figura dell'esercizio non si può riprodurre")
    try:
        from latex_utils import _tikz_da_specifica
        for spec in _RE_SPEC_GRAFICO.findall(t):
            if _tikz_da_specifica(spec) is None:
                p.append("un grafico non è stato interpretato")
                break
    except Exception:
        pass
    return p


def stato_esercizio(ex: dict) -> dict:
    """{'utilizzabile': bool, 'motivo': str}: se l'esercizio può entrare nella verifica senza inventare niente."""
    if ex.get("figura") == "non_riproducibile" or "[[FIGURA NON RIPRODUCIBILE]]" in (ex.get("latex") or "").upper():
        return {"utilizzabile": False,
                "motivo": "Contiene una figura che non so riprodurre in modo identico (un quadro, una fotografia, una cartina o uno schema "
                          "complesso). Preferisco non inserirlo piuttosto che mettere una figura inventata."}
    pl = problemi_latex(ex.get("latex"))
    if pl:
        return {"utilizzabile": False, "motivo": "Non riesco a scriverlo in modo pulito (" + "; ".join(pl) + "). Prova a correggerlo o a rifare la foto."}
    if len((ex.get("latex") or "").strip()) < 15:
        return {"utilizzabile": False, "motivo": "Il testo letto è troppo corto per essere un esercizio."}
    return {"utilizzabile": True, "motivo": ""}


def riassunto_per_prompt(ex: dict) -> str:
    """Poche parole sul contenuto (per dire a chi scrive la verifica cosa c'è già), senza comandi LaTeX."""
    t = re.sub(r"^%IMG_B64:[^\n]*\n", "", ex.get("latex") or "", flags=re.MULTILINE)
    t = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", " ", t, flags=re.DOTALL)
    t = re.sub(r"\[\[.*?\]\]", " ", t, flags=re.DOTALL)
    t = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?|\\item|\\displaystyle|\\[()\[\]]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:220]


# ── CHIAMATE ALL'AI ─────────────────────────────────────────────────────────────────────────────────

def _parti(immagini: list) -> list:
    """Le parti da dare al modello: testo (da un file Word) oppure immagine/PDF."""
    return [i["testo"] if "testo" in i else {"mime_type": i.get("mime_type") or "image/jpeg", "data": i["data"]} for i in immagini]


def _chiama(model, contenuto) -> str:
    risposta = model.generate_content(contenuto)
    try:
        return (risposta.text or "").strip()
    except Exception:
        return ""


def controlla_foto(immagini: list, massimo: int = MAX_FOTO) -> str | None:
    """Messaggio d'errore se le foto non vanno bene (troppe, troppo grandi, formato strano), None se vanno."""
    if not immagini:
        return "Carica almeno una foto."
    if len(immagini) > massimo:
        return f"Carica al massimo {massimo} file per volta."
    for i in immagini:
        d = i.get("data") or b""
        if len(d) > MAX_BYTE_FOTO:
            return "Una foto è troppo pesante: riducila o ritagliala sull'esercizio."
        if len(d) < 1500:
            return "Una foto sembra vuota o rovinata: riprova a caricarla."
        if (i.get("mime_type") or "") not in ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "application/pdf", "") and not (i.get("name") or "").lower().endswith(".docx"):
            return "Formato non supportato: usa una foto JPG o PNG, oppure un PDF."
    return None


def leggi_esercizi_da_foto(model, immagini: list, materia: str = "", scuola: str = "",
                           max_esercizi: int = MAX_ESERCIZI_DA_FOTO, ricontrolla_con_foto: bool = True) -> dict:
    """
    Legge le foto e restituisce {"ok": bool, "esercizi": [...], "messaggio": str}.
    Ogni esercizio: {titolo, figura, dubbi, latex, ricontrollato, correzioni}. Qualsiasi errore diventa {"ok": False, "messaggio"}.
    """
    errore = controlla_foto(immagini)
    if errore:
        return {"ok": False, "esercizi": [], "messaggio": errore}
    parti = _parti(immagini)
    esercizi, problema = [], None
    for _tentativo in range(2):          # una seconda lettura se la risposta non è nel formato atteso
        try:
            testo = _chiama(model, [prompt_leggi_esercizi_foto(materia, scuola, len(parti), max_esercizi)] + parti)
        except Exception as e:           # chiamata fallita (rete, chiave, limite): messaggio chiaro, mai un'eccezione fino all'interfaccia
            return {"ok": False, "esercizi": [], "messaggio": f"Non sono riuscito a leggere la foto ({str(e)[:120]}). Riprova tra poco."}
        esercizi, problema = leggi_risposta(testo)
        if esercizi or problema:
            break
    if not esercizi:
        return {"ok": False, "esercizi": [],
                "messaggio": problema or "Non vedo un esercizio in questa foto. Inquadra bene l'esercizio, con buona luce, e riprova."}
    esercizi = esercizi[:max_esercizi]
    for e in esercizi:
        e["ricontrollato"] = False
        e["correzioni"] = []
    if ricontrolla_con_foto:
        esercizi = ricontrolla(model, parti, esercizi)
    return {"ok": True, "esercizi": esercizi, "messaggio": ""}


def _testo_da_ricontrollare(esercizi: list) -> str:
    return "\n\n".join(f"===ESERCIZIO===\nTITOLO: {e['titolo']}\nTESTO:\n{e['latex']}\n===FINE===" for e in esercizi)


def ricontrolla(model, parti: list, esercizi: list, tieni_punti: bool = False) -> list:
    """
    Secondo sguardo indipendente: il modello confronta la trascrizione con la foto. Se corregge qualcosa si prende la versione corretta
    e si ricordano le differenze (il docente le vede). Se la risposta non è coerente (numero di esercizi diverso, testo vuoto o
    con problemi) si tiene la prima lettura e si segnala che il controllo non è riuscito.
    """
    try:
        testo = _chiama(model, [prompt_ricontrolla_trascrizione(_testo_da_ricontrollare(esercizi), len(parti), tieni_punti)] + parti)
        riletti, _ = leggi_risposta(testo, tieni_punti)
    except Exception:
        return esercizi
    if len(riletti) != len(esercizi):
        return esercizi
    for e, r in zip(esercizi, riletti):
        e["ricontrollato"] = True
        diff = r.get("differenze") or []
        e["correzioni"] = [d for d in diff if "dubbio" not in d.lower()]
        e["dubbi"] = list(dict.fromkeys(e.get("dubbi", []) + [d for d in diff if "dubbio" in d.lower()]))
        nuovo = r.get("latex") or ""
        if (r.get("esito") or "").startswith("corretto") and nuovo.strip() and not problemi_latex(nuovo):
            e["latex"] = nuovo
        elif diff and nuovo.strip() and not problemi_latex(nuovo) and e["correzioni"]:
            e["latex"] = nuovo
        if r.get("figura") in FIGURE_VALIDE and r["figura"] == "non_riproducibile":
            e["figura"] = "non_riproducibile"
    return esercizi


def correggi_esercizio(model, immagini: list, ex: dict, richiesta: str) -> dict:
    """Il docente dice cosa non va; l'AI riguarda la foto e corregge. Restituisce {"ok", "esercizio", "messaggio"}."""
    richiesta = (richiesta or "").strip()
    if len(richiesta) < 3:
        return {"ok": False, "esercizio": ex, "messaggio": "Scrivi cosa non va (per esempio: «nella b) l'esponente è 3, non 2»)."}
    parti = _parti(immagini)
    try:
        testo = _chiama(model, [prompt_correggi_trascrizione(ex.get("latex", ""), richiesta[:600], len(parti))] + parti)
    except Exception as e:
        return {"ok": False, "esercizio": ex, "messaggio": f"Non sono riuscito a correggerlo ({str(e)[:120]}). Riprova."}
    nuovi, _ = leggi_risposta(testo)
    if not nuovi:
        return {"ok": False, "esercizio": ex, "messaggio": "La correzione non è andata a buon fine: l'esercizio è rimasto com'era."}
    n = nuovi[0]
    if n["latex"].strip() == (ex.get("latex") or "").strip():
        return {"ok": False, "esercizio": ex, "messaggio": "Non ho trovato niente da cambiare: prova a dire più precisamente dove sta l'errore."}
    corretto = {**ex, "titolo": n["titolo"] or ex.get("titolo"), "figura": n["figura"], "latex": n["latex"],
                "dubbi": n["dubbi"], "correzioni": [], "ricontrollato": True, "corretto_dal_docente": True}
    return {"ok": True, "esercizio": corretto, "messaggio": ""}


# ── INSERIMENTO NELLA VERIFICA ──────────────────────────────────────────────────────────────────────

def blocco_latex(ex: dict, numero: int = 1) -> str:
    """L'esercizio come blocco della verifica: \\subsection*{Esercizio N: Titolo} seguito dal corpo."""
    titolo = _titolo_pulito(ex.get("titolo", ""))
    return "\\subsection*{Esercizio " + str(numero) + ": " + titolo + "}\n" + (ex.get("latex") or "").strip() + "\n"


def rinumera_blocchi(blocchi: list) -> list:
    """Porta i titoli «Esercizio N: …» a 1, 2, 3… nell'ordine in cui compaiono."""
    out = []
    for i, b in enumerate(blocchi, 1):
        out.append(re.sub(r"^(\s*\\subsection\*\{\s*)(?:Esercizio|Es\.?)\s*\d+\s*", lambda m: m.group(1) + f"Esercizio {i}", b, count=1))
    return out


def inserisci_esercizi(blocchi: list, fissi: list) -> list:
    """
    Inserisce gli esercizi del docente tra i blocchi scritti dall'AI. `fissi` = [{"blocco": str, "posizione": int}] con la posizione
    1-based nella verifica FINALE (1 = primo; oltre la fine = ultimo). Due esercizi con la stessa posizione: il secondo va subito dopo.
    Rinumera tutto.
    """
    risultato = list(blocchi)
    totale = len(risultato) + len(fissi)
    precedente = 0
    for f in sorted(fissi, key=lambda f: int(f.get("posizione") or 1)):
        pos = min(max(int(f.get("posizione") or 1), precedente + 1), totale)
        risultato.insert(min(pos - 1, len(risultato)), f["blocco"])
        precedente = pos
    return rinumera_blocchi(risultato)


# ── figure ritagliate dalla foto ───────────────────────────────────────────────────────────────────

def pagine_da_file(immagini: list, lato_max: int = 1600) -> list:
    """Le pagine delle foto/PDF caricati come PNG (lato massimo `lato_max`), nell'ordine in cui il modello le ha viste."""
    import io as _io
    from PIL import Image
    from docx_import import espandi_file
    out = []
    for f in espandi_file(immagini):
        dati = f.get("data") or b""
        if not dati:
            continue
        pezzi = []
        if (f.get("mime_type") or "").startswith("application/pdf"):
            try:
                from latex_utils import pdf_to_images_bytes
                pezzi, _ = pdf_to_images_bytes(dati)
                pezzi = pezzi or []
            except Exception:
                pezzi = []
        else:
            pezzi = [dati]
        for p in pezzi:
            try:
                im = Image.open(_io.BytesIO(p))
                im.load()
                im = im.convert("RGB")
                if max(im.size) > lato_max:
                    k = lato_max / max(im.size)
                    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
                b = _io.BytesIO()
                im.save(b, "PNG", optimize=True)
                out.append(b.getvalue())
            except Exception:
                continue
    return out


def ritaglia(pagina_png: bytes, x0: int, y0: int, x1: int, y1: int, lato_max: int = 900, peso_max: int = 200_000):
    """Ritaglia il riquadro (millesimi della pagina) e lo restituisce come PNG leggero; None se non si riesce o l'area è troppo piccola."""
    import io as _io
    from PIL import Image
    try:
        im = Image.open(_io.BytesIO(pagina_png)).convert("RGB")
        w, h = im.size
        box = (int(w * min(x0, x1) / 1000), int(h * min(y0, y1) / 1000), int(w * max(x0, x1) / 1000), int(h * max(y0, y1) / 1000))
        if box[2] - box[0] < 20 or box[3] - box[1] < 20:
            return None
        im = im.crop(box)
        for lato in (lato_max, 700, 520, 380):
            r = im
            if max(r.size) > lato:
                k = lato / max(r.size)
                r = r.resize((max(1, int(r.width * k)), max(1, int(r.height * k))), Image.LANCZOS)
            b = _io.BytesIO()
            r.save(b, "PNG", optimize=True)
            if len(b.getvalue()) <= peso_max:
                return b.getvalue()
        return None
    except Exception:
        return None


def con_figura(ex: dict, png: bytes) -> dict:
    """L'esercizio con la figura ritagliata al posto del segnaposto (se non c'è il segnaposto la figura va in testa, sotto la consegna)."""
    from latex_utils import blocco_figura
    marca = re.compile(r"\[\[\s*FIGURA NON RIPRODUCIBILE\s*\]\]", re.IGNORECASE)
    latex = ex.get("latex") or ""
    blocco = blocco_figura(png)
    nuovo = marca.sub(lambda m: blocco, latex, count=1) if marca.search(latex) else latex.rstrip() + "\n" + blocco
    return {**ex, "latex_senza_figura": latex, "latex": nuovo, "figura": "foto", "ha_figura_foto": True, "png_figura": png}


def senza_figura(ex: dict) -> dict:
    """Toglie la figura inserita e rimette com'era l'esercizio."""
    if not ex.get("ha_figura_foto"):
        return ex
    base = {k: v for k, v in ex.items() if k not in ("latex_senza_figura", "ha_figura_foto", "png_figura")}
    base["latex"] = ex.get("latex_senza_figura") or ex.get("latex")
    base["figura"] = "non_riproducibile"
    return base
