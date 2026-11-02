"""
agente.py — l'agente conversazionale di VerificAI (senza Streamlit).

Il docente scrive liberamente («equazioni di secondo grado per la 3B, con fila B e soluzioni»); l'AI decide UNA azione e i suoi parametri
(prompt in prompts.py), il codice li controlla e li riporta a valori che l'app conosce (materie, scuole, classi del docente, intervalli).
Lo scopo è compilare al posto del docente tutto ciò che il modulo chiederebbe e chiedere solo ciò che manca davvero.

L'agente NON scrive verifiche e non esegue nulla: restituisce una decisione. Le azioni le esegue main.py con le funzioni che già esistono.
Qualsiasi problema (risposta non valida, errore dell'AI) = ripiego prudente, mai un'eccezione.
"""
import json
import logging
import re

from config import AGENTE_MAX_DOMANDE, DURATA_DEFAULT, DURATE, MATERIE, SCUOLE
from prompts import prompt_agente

logger = logging.getLogger(__name__)

# ── Azioni ────────────────────────────────────────────────────────────────────
AZIONI_HOME = {
    "crea": "crea una verifica nuova (anche con «versioni» aggiuntive da preparare subito dopo)",
    "impagina": "il docente ha GIÀ una verifica scritta (PDF, foto, Word) e vuole solo impaginarla o sistemarla (se l'ha allegata, la impagino subito)",
    "libro": "il docente vuole inserire nella verifica un esercizio preso da una foto del suo libro",
    "storico": "il docente vuole ritrovare o riaprire una verifica già creata",
    "aiuto": "domande su come funziona l'app, o richieste che l'app non sa fare: rispondi in «messaggio»",
    "domanda": "ti manca un'informazione essenziale: fai UNA domanda (campi «domanda» e «opzioni»)",
}
AZIONI_FINAL = {
    "operazioni": "azioni su ESERCIZI PRECISI della verifica aperta (rifai/semplifica/complica il 3, togli il 4, cambia i numeri, punti, aggiungi, annulla): elencale in «operazioni»",
    "modifica": "cambio generale della verifica aperta, che non si riduce a operazioni su singoli esercizi: scrivi la richiesta in «modifica»",
    "versioni": "crea documenti aggiuntivi della verifica aperta (Fila B, BES/DSA, soluzioni, recupero…): elencali in «versioni»",
    "crea": "il docente vuole una verifica NUOVA e diversa da quella aperta",
    "storico": "il docente vuole ritrovare un'altra verifica già creata",
    "aiuto": "domande su come funziona l'app, o richieste che l'app non sa fare: rispondi in «messaggio»",
    "domanda": "ti manca un'informazione essenziale: fai UNA domanda (campi «domanda» e «opzioni»)",
}
VERSIONI = {"B": "Fila B", "C": "Fila C", "D": "Fila D", "E": "Fila E", "R": "Versione BES/DSA", "L": "Alta leggibilità (DSA)",
            "REC": "Versione di recupero", "S": "Soluzioni", "SC": "Scheda di allenamento", "G": "Griglia di valutazione", "W": "File Word"}
_ORDINE_VERSIONI = ["B", "C", "D", "E", "R", "L", "REC", "S", "SC", "G", "W"]
_ALIAS_VERSIONI = {"FILA B": "B", "FILA C": "C", "FILA D": "D", "FILA E": "E", "BES": "R", "DSA": "R", "BES/DSA": "R", "RECUPERO": "REC",
                   "SOLUZIONI": "S", "SCHEDA": "SC", "GRIGLIA": "G", "WORD": "W", "LEGGIBILITA": "L", "LEGGIBILITÀ": "L"}


# Operazioni su singoli esercizi: tipo → (richiede un indice, usa l'AI)
OPERAZIONI = {"riscrivi": (True, True), "piu_facile": (True, True), "piu_difficile": (True, True), "numeri": (True, True), "sostituisci": (True, True),
              "aggiungi": (False, True), "porta_a": (False, True), "elimina": (True, False), "punti": (True, False), "intestazione": (False, False), "annulla": (False, False), "ripristina": (False, False)}
MAX_OPERAZIONI = 8


def azioni_per(stage: str) -> dict:
    return AZIONI_FINAL if stage == "final" else AZIONI_HOME


def _azioni_testo(stage: str) -> str:
    return "".join(f"- {k}: {v}\n" for k, v in azioni_per(stage).items())


# ── Contesto per il prompt ────────────────────────────────────────────────────
def contesto_testo(ctx: dict) -> str:
    """Ciò che l'agente sa, in righe brevi. `ctx` lo prepara main.py (chiavi tutte facoltative)."""
    r = []
    r.append("Materie ammesse: " + ", ".join(m for m in ctx.get("materie") or MATERIE if m != "Altra materia") + ".")
    r.append("Scuole ammesse: " + "; ".join(ctx.get("scuole") or SCUOLE) + ".")
    pre = ctx.get("predefiniti") or {}
    if pre.get("scuola") or pre.get("materia"):
        r.append(f"Valori abituali del docente: materia «{pre.get('materia') or '—'}», scuola «{pre.get('scuola') or '—'}».")
    classi = ctx.get("classi") or []
    if classi:
        r.append("Classi del docente:")
        for c in classi[:20]:
            r.append(f"  - {c.get('nome')}" + (f" (scuola: {c['scuola']})" if c.get("scuola") else "") + (f" — note: {c['note'][:120]}" if c.get("note") else ""))
    else:
        r.append("Il docente non ha ancora salvato classi.")
    ult = ctx.get("ultime") or []
    if ult:
        r.append("Ultime verifiche create (la più recente per prima):")
        for u in ult[:5]:
            r.append("  - " + " · ".join(x for x in (u.get("argomento"), u.get("materia"), u.get("scuola"), u.get("classe")) if x))
    if ctx.get("preferenze"):
        r.append("Preferenze fisse del docente (le applica già l'app, non ripeterle): " + "; ".join(ctx["preferenze"][:6]) + ".")
    al = ctx.get("allegato")
    if al:
        r.append(f"Allegato caricato ora: {al.get('nome')} ({al.get('tipo') or 'file'}" + (f", {al['n']} file" if (al.get("n") or 0) > 1 else "") + ").")
    else:
        r.append("Nessun allegato caricato.")
    v = ctx.get("verifica")
    if v:
        r.append("VERIFICA APERTA ORA: " + " · ".join(x for x in (v.get("argomento"), v.get("materia"), v.get("scuola"), v.get("classe")) if x)
                 + (f" (totale {v['punti_totali']} punti)" if v.get("punti_totali") else "") + ".")
        if v.get("esercizi"):
            r.append("  Esercizi: " + " | ".join(f"{i + 1}) {t}" for i, t in enumerate(v["esercizi"][:12])))
        if v.get("pronte"):
            r.append("  Già create: " + ", ".join(VERSIONI.get(k, k) for k in v["pronte"]) + ".")
    if ctx.get("bloccate"):
        r.append("Funzioni non disponibili per ora a questo docente: " + ", ".join(VERSIONI.get(k, k) for k in ctx["bloccate"]) + ".")
    b = ctx.get("bozza")
    if b:
        r.append("BOZZA GIÀ PROPOSTA al docente (parti da qui se la corregge): " + json.dumps(b, ensure_ascii=False))
    return "\n".join(r)


def conversazione_testo(chat: list, stage: str, ultimi: int = 8) -> str:
    righe = []
    for m in [m for m in chat if m.get("stage", stage) == stage][-ultimi:]:
        righe.append(("Docente: " if m.get("ruolo") == "utente" else "Assistente: ") + (m.get("testo") or "").strip())
    return "\n".join(righe)


# ── Controllo delle risposte ──────────────────────────────────────────────────
def _chiave(s) -> str:
    return re.sub(r"[^a-z0-9àèéìòù]", "", str(s or "").lower().replace("ª", "").replace("°", "").replace("º", ""))


def _da_elenco(valore, elenco, escludi=()):
    if not valore:
        return None
    k = _chiave(valore)
    for x in elenco:
        if x not in escludi and _chiave(x) == k:
            return x
    return None


def _scuola_da_testo(valore):
    """Scuola dell'elenco: nome esatto, oppure una voce che contiene (o è contenuta nel) testo dato dall'AI."""
    esatta = _da_elenco(valore, SCUOLE)
    if esatta or not valore:
        return esatta
    k = _chiave(valore)
    for s in SCUOLE:
        if len(k) >= 5 and (k in _chiave(s) or _chiave(s) in k):
            return s
    return None


def _intero(v, lo, hi):
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return None
    return max(lo, min(hi, n))


def _bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "si", "sì", "vero"):
        return True
    if isinstance(v, str) and v.strip().lower() in ("false", "no", "falso"):
        return False
    return None


def _testo(v, massimo):
    t = re.sub(r"[ \t]+", " ", str(v or "")).strip()
    return t[:massimo] if t and t.lower() not in ("null", "none") else ""


def pulisci_versioni(lista) -> list:
    out = []
    for x in lista if isinstance(lista, list) else []:
        k = str(x or "").strip().upper()
        k = _ALIAS_VERSIONI.get(k, k)
        if k in VERSIONI and k not in out:
            out.append(k)
    return sorted(out, key=_ORDINE_VERSIONI.index)


def pulisci_crea(grezzo, classi: list) -> dict:
    """I parametri di una nuova verifica, riportati a valori validi per l'app. Ciò che non è chiaro resta None."""
    g = grezzo if isinstance(grezzo, dict) else {}
    nomi_classi = [c.get("nome") for c in classi or [] if c.get("nome")]
    classe = _da_elenco(g.get("classe"), nomi_classi) or (_testo(g.get("classe"), 24) or None)
    scuola = _scuola_da_testo(g.get("scuola"))
    if not scuola and classe:
        c = next((c for c in classi or [] if c.get("nome") == classe), None)
        scuola = _scuola_da_testo((c or {}).get("scuola"))
    argomento = _testo(g.get("argomento"), 200).replace("\n", " ")
    punti = _intero(g.get("punti_totali"), 10, 100)
    uso = str(g.get("uso_file") or "").strip().lower()
    return {
        "materia": _da_elenco(g.get("materia"), MATERIE, escludi=("Altra materia",)),
        "scuola": scuola,
        "classe": classe,
        "argomento": argomento,
        "indicazioni": _testo(g.get("indicazioni"), 900),
        "num_esercizi": _intero(g.get("num_esercizi"), 3, 11),
        "eccellenza": _bool(g.get("eccellenza")),
        "punteggi": _bool(g.get("punteggi")),
        "punti_totali": (punti // 5 * 5 if punti and punti >= 10 else None),
        "uso_file": uso if uso in ("spunto", "rifai") else None,
    }


def pulisci_operazioni(lista, ctx: dict) -> tuple:
    """Le operazioni controllate: (valide, scartate). Gli indici arrivano da 1 (come li legge il docente) e diventano da 0.
    Si scarta ciò che punta a un esercizio inesistente, una riscrittura senza istruzione, punti impossibili; non si elimina mai l'ultimo esercizio rimasto."""
    v = ctx.get("verifica") or {}
    n = len(v.get("esercizi") or [])
    tot = int(v.get("punti_totali") or 100)
    valide, scartate, tolti = [], [], set()
    for o in (lista if isinstance(lista, list) else [])[:MAX_OPERAZIONI * 2]:
        if not isinstance(o, dict):
            continue
        tipo = str(o.get("tipo") or "").strip().lower()
        if tipo not in OPERAZIONI:
            continue
        op = {"tipo": tipo, "indice": None, "istruzione": _testo(o.get("istruzione"), 500), "punti": None, "numero": None,
              "classe": _testo(o.get("classe"), 24), "data": _testo(o.get("data"), 20)}
        if OPERAZIONI[tipo][0]:
            i = _intero(o.get("indice"), 0, 99)
            if not i or i > n:
                scartate.append(o)
                continue
            op["indice"] = i - 1
        if tipo == "riscrivi" and not op["istruzione"]:
            scartate.append(o)
            continue
        if tipo == "porta_a":
            op["numero"] = _intero(o.get("numero") or o.get("indice"), 2, 15)
            if not op["numero"] or op["numero"] <= n:           # la verifica ha già quel numero (o più): non c'è niente da aggiungere
                scartate.append({**o, "tipo": "porta_a"})
                continue
        if tipo == "punti":
            op["punti"] = _intero(o.get("punti"), 0, 1000)
            if not op["punti"] or op["punti"] >= tot:
                scartate.append(o)
                continue
        if tipo == "elimina":
            if op["indice"] in tolti or len(tolti) + 1 >= n:
                scartate.append(o)
                continue
            tolti.add(op["indice"])
        if tipo == "intestazione" and not (op["classe"] or op["data"]):
            scartate.append(o)
            continue
        valide.append(op)
    return valide[:MAX_OPERAZIONI], scartate


def descrivi_operazione(op: dict) -> str:
    """Una frase breve per la scheda di attesa e per la conferma («Riscrivo l'esercizio 3»)."""
    n = (op.get("indice") or 0) + 1
    return {"riscrivi": f"Riscrivo l'esercizio {n}", "piu_facile": f"Rendo più facile l'esercizio {n}", "piu_difficile": f"Rendo più difficile l'esercizio {n}",
            "numeri": f"Cambio i numeri dell'esercizio {n}", "sostituisci": f"Sostituisco l'esercizio {n} con uno nuovo", "aggiungi": "Aggiungo un esercizio",
            "porta_a": f"Porto la verifica a {op.get('numero')} esercizi", "elimina": f"Tolgo l'esercizio {n}",
            "punti": f"Metto {op.get('punti')} punti all'esercizio {n}", "intestazione": "Aggiorno classe e data",
            "annulla": "Torno alla versione precedente", "ripristina": "Ripristino la modifica"}.get(op.get("tipo"), "Applico la modifica")


def stima_secondi(ops: list, n_attuale: int = 0) -> int:
    """Stima (non misurata) dell'attesa: le chiamate all'AI per riscrivere partono in parallelo (circa 10 s), gli esercizi da aggiungere uno dopo l'altro
    (circa 8 s ciascuno, perché ognuno deve essere diverso dai precedenti), il PDF si rifà una volta sola (circa 6 s)."""
    agg = sum(1 for o in ops if o.get("tipo") == "aggiungi") + sum(max(0, (o.get("numero") or 0) - n_attuale) for o in ops if o.get("tipo") == "porta_a")
    par = sum(1 for o in ops if OPERAZIONI.get(o.get("tipo"), (0, 0))[1] and o.get("tipo") not in ("aggiungi", "porta_a"))
    return (10 + (4 if par > 1 else 0) if par else 0) + 8 * agg + 6


def normalizza(grezzo, ctx: dict, stage: str, domande_fatte: int, testo_utente: str = "") -> dict:
    """La risposta dell'AI controllata: azione ammessa, parametri validi, nessuna domanda oltre il limite.
    Chiavi: azione, messaggio, domanda, opzioni, crea, versioni, per_chi, modifica, assunzioni."""
    g = grezzo if isinstance(grezzo, dict) else {}
    ammesse = azioni_per(stage)
    azione = str(g.get("azione") or "").strip().lower()
    if azione not in ammesse:
        azione = "crea" if stage != "final" else "modifica"
    d = {
        "azione": azione,
        "messaggio": _testo(g.get("messaggio"), 300),
        "domanda": _testo(g.get("domanda"), 300),
        "opzioni": [o for o in (_testo(x, 60) for x in (g.get("opzioni") if isinstance(g.get("opzioni"), list) else [])) if o][:4],
        "crea": pulisci_crea(g.get("crea"), ctx.get("classi") or []),
        "versioni": pulisci_versioni(g.get("versioni")),
        "per_chi": _testo(g.get("per_chi"), 120),
        "modifica": _testo(g.get("modifica"), 700),
        "operazioni": [],
        "assunzioni": [a for a in (_testo(x, 200) for x in (g.get("assunzioni") if isinstance(g.get("assunzioni"), list) else [])) if a][:3],
    }
    # Una domanda senza testo, o oltre il limite, non ha senso: si decide con ciò che c'è
    if azione == "domanda" and (not d["domanda"] or domande_fatte >= AGENTE_MAX_DOMANDE):
        azione = d["azione"] = ("crea" if (stage != "final" and (d["crea"]["argomento"] or ctx.get("allegato"))) else
                                "modifica" if stage == "final" else "aiuto")
        if azione == "aiuto" and not d["messaggio"]:
            d["messaggio"] = "Non ho capito bene: dimmi di che argomento è la verifica e, se vuoi, per quale classe."
    if azione == "crea" and not d["crea"]["argomento"] and not ctx.get("allegato") and not ctx.get("bozza"):
        # niente da creare: si chiede l'argomento (se si può ancora) oppure si spiega
        if domande_fatte < AGENTE_MAX_DOMANDE:
            d.update(azione="domanda", domanda=d["domanda"] or "Di che argomento deve essere la verifica?", opzioni=[])
        else:
            d.update(azione="aiuto", messaggio="Dimmi di che argomento è la verifica, anche in poche parole.")
    if azione == "operazioni":
        ops, scartate = pulisci_operazioni(g.get("operazioni"), ctx)
        d["operazioni"] = ops
        if not ops:
            titoli = (ctx.get("verifica") or {}).get("esercizi") or []
            if any(o.get("tipo") == "porta_a" for o in scartate):
                d.update(azione="aiuto", messaggio=f"La verifica ha già {len(titoli)} esercizi. Per averne meno dimmi quali togliere; per averne di più, un numero più alto.")
            elif scartate and titoli and domande_fatte < AGENTE_MAX_DOMANDE:
                d.update(azione="domanda", domanda="A quale esercizio ti riferisci?",
                         opzioni=[f"Esercizio {i + 1}" for i in range(min(4, len(titoli)))])
            else:
                d.update(azione="modifica", modifica=_testo(testo_utente, 700))
    if azione == "modifica" and not d["modifica"]:
        d["modifica"] = _testo(testo_utente, 700)
    if azione == "versioni" and not d["versioni"]:
        d.update(azione="aiuto", messaggio=d["messaggio"] or "Quale documento vuoi creare? Per esempio Fila B, soluzioni, versione BES/DSA o di recupero.")
    return d


def unisci_bozza(dec: dict, bozza: dict | None) -> dict:
    """Se il docente corregge una bozza («meglio 6 esercizi»), ciò che la nuova risposta lascia vuoto resta com'era nella bozza:
    il modello può dimenticare un campo, il docente non deve doverlo ridire. Le versioni non si uniscono (toglierle è una scelta)."""
    if not bozza or dec.get("azione") != "crea":
        return dec
    for k, v in (bozza.get("crea") or {}).items():
        if dec["crea"].get(k) in (None, "") and v not in (None, ""):
            dec["crea"][k] = v
    return dec


def ripiego(testo: str, stage: str, ctx: dict) -> dict:
    """Se l'AI non risponde: nella home si crea con il testo così com'è (come faceva il modulo), nella pagina finale lo si prende come modifica."""
    base = normalizza({}, ctx, stage, AGENTE_MAX_DOMANDE, testo)
    t = _testo(testo, 900)
    if stage == "final":
        base.update(azione="modifica", modifica=t, messaggio="")
    else:
        riga, _, resto = t.partition("\n")
        base.update(azione="crea", messaggio="Ho usato la tua richiesta così com'è.")
        base["crea"] = {**base["crea"], "argomento": _testo(riga, 200), "indicazioni": _testo(resto, 900)}
    base["ripiego"] = True
    return base


def _estrai_json(testo: str):
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", (testo or "").strip())
    try:
        return json.loads(t)
    except ValueError:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except ValueError:
            return None


def interpreta(modello, chat: list, ctx: dict, stage: str, domande_fatte: int = 0) -> dict:
    """Capisce l'ultimo messaggio del docente. `modello` è un ModelloAI (già adatto al compito «agente»). Non solleva mai."""
    ultimo = next((m.get("testo") for m in reversed(chat) if m.get("ruolo") == "utente"), "") or ""
    try:
        prompt = prompt_agente(conversazione_testo(chat, stage), contesto_testo(ctx), _azioni_testo(stage),
                               max(0, AGENTE_MAX_DOMANDE - domande_fatte))
        risposta = modello.generate_content([prompt], generation_config={"json": True, "temperature": 0.2})
        grezzo = _estrai_json(risposta.text)
        if not isinstance(grezzo, dict):
            raise ValueError("risposta non valida")
        return unisci_bozza(normalizza(grezzo, ctx, stage, domande_fatte, ultimo), ctx.get("bozza"))
    except Exception as e:
        logger.warning("agente: %s", e)
        return ripiego(ultimo, stage, ctx)


# ── Scorciatoie: richieste così semplici che non serve l'AI (nessuna attesa, nessun costo) ──
_RE_VERSIONI = [(re.compile(r"\bfila\s+([b-e])\b"), None), (re.compile(r"\bsoluzion[ei]\b"), "S"),
                (re.compile(r"\b(?:bes|dsa)(?:\s*/\s*(?:bes|dsa))?\b"), "R"), (re.compile(r"\brecupero\b"), "REC"),
                (re.compile(r"\bscheda(?:\s+di\s+allenamento)?\b"), "SC"), (re.compile(r"\bgriglia(?:\s+di\s+valutazione)?\b"), "G"),
                (re.compile(r"\bword\b"), "W"), (re.compile(r"\balta\s+leggibilit[àa]\b|\bleggibil\w*\b"), "L")]
_PAROLE_VUOTE = {"fammi", "fai", "crea", "creami", "prepara", "preparami", "genera", "la", "le", "il", "con", "e", "anche", "ed", "per", "favore", "grazie", "una", "un",
                 "versione", "di", "del", "dei", "delle", "pdf", "in", "aggiungi", "metti", "voglio", "vorrei", "mi", "serve", "servono", "poi", "pure", "ora", "adesso"}
_ES = r"(?:l['’]\s*)?(?:esercizio|es\.?)\s*(\d{1,2})"
_RE_OPS = [
    (re.compile(r"^(?:togli|elimina|rimuovi|cancella)\s+" + _ES + r"$"), lambda m: [{"tipo": "elimina", "indice": m.group(1)}]),
    (re.compile(r"^(?:rendi|rendimi|fai|metti)?\s*(?:più|piu)\s+(facile|difficile)\s+" + _ES + r"$"),
     lambda m: [{"tipo": "piu_" + m.group(1), "indice": m.group(2)}]),
    (re.compile(r"^(?:rendi|rendimi|fai)\s+" + _ES + r"\s+(?:più|piu)\s+(facile|difficile)$"),
     lambda m: [{"tipo": "piu_" + m.group(2), "indice": m.group(1)}]),
    (re.compile(r"^(?:cambia|rifai)\s+i\s+numeri\s+(?:dell['’]|del(?:l['’])?\s*|nell['’])\s*(?:esercizio|es\.?)\s*(\d{1,2})$"),
     lambda m: [{"tipo": "numeri", "indice": m.group(1)}]),
    (re.compile(r"^(?:annulla|torna indietro|annulla (?:l['’]ultima )?modifica)$"), lambda m: [{"tipo": "annulla"}]),
    (re.compile(r"^(?:ripristina|ripristina (?:l['’]ultima )?modifica)$"), lambda m: [{"tipo": "ripristina"}]),
]


def scorciatoia(testo: str, stage: str, ctx: dict) -> dict | None:
    """Per le richieste brevissime e inequivocabili della pagina finale («fila B e soluzioni», «togli l'esercizio 4», «annulla») restituisce
    la decisione senza chiamare l'AI. Se c'è il minimo dubbio restituisce None e decide l'AI."""
    if stage != "final" or not (ctx.get("verifica")):
        return None
    t = re.sub(r"\s+", " ", (testo or "").lower()).strip(" .!?")
    if not t or len(t) > 80:
        return None
    for rx, fn in _RE_OPS:
        m = rx.match(t)
        if m:
            d = normalizza({"azione": "operazioni", "operazioni": fn(m)}, ctx, stage, AGENTE_MAX_DOMANDE, testo)
            if d["azione"] == "operazioni":
                d["scorciatoia"] = True
                return d
            return None
    resto, trovate = t, []
    for rx, chiave in _RE_VERSIONI:
        for m in rx.finditer(resto):
            trovate.append(chiave or m.group(1).upper())
        resto = rx.sub(" ", resto)
    if trovate and all(w in _PAROLE_VUOTE for w in re.findall(r"[a-zàèéìòù']+", resto)):
        d = normalizza({"azione": "versioni", "versioni": trovate}, ctx, stage, AGENTE_MAX_DOMANDE, testo)
        d["scorciatoia"] = True
        return d if d["azione"] == "versioni" else None
    return None


def suggerimenti(ctx: dict, massimo: int = 4) -> list:
    """Scorciatoie da proporre sotto la casella della pagina finale: [(etichetta, testo)]. Il testo passa da `scorciatoia` (istantaneo)."""
    v = ctx.get("verifica") or {}
    pronte, bloccate = set(v.get("pronte") or []), set(ctx.get("bloccate") or [])
    out = []
    for chiave, etichetta, testo in (("B", "Fila B", "fila B"), ("S", "Soluzioni", "soluzioni"), ("R", "Versione BES/DSA", "bes dsa")):
        if chiave not in pronte and chiave not in bloccate:
            out.append((etichetta, testo))
    titoli = v.get("esercizi") or []
    ultimo = next((i + 1 for i in range(len(titoli) - 1, -1, -1) if "eccellenza" not in titoli[i].lower()), None)
    if ultimo and len(titoli) >= 3:
        out.append((f"Più facile il {ultimo}", f"più facile l'esercizio {ultimo}"))
    return out[:massimo]


# ── Dal parametro al modulo ───────────────────────────────────────────────────
def riepilogo(par: dict, default_eccellenza: bool = True) -> list:
    """Le «pillole» del riepilogo mostrato al docente: [(etichetta, valore)] solo per ciò che è stato deciso."""
    out = []
    if par.get("materia"):
        out.append(("Materia", par["materia"]))
    if par.get("scuola"):
        out.append(("Scuola", par["scuola"]))
    if par.get("classe"):
        out.append(("Classe", par["classe"]))
    if par.get("num_esercizi"):
        n = par["num_esercizi"]
        out.append(("Esercizi", str(n)))
    if par.get("eccellenza") is True:
        out.append(("Eccellenza", "con esercizio finale"))
    elif par.get("eccellenza") is False:
        out.append(("Eccellenza", "senza"))
    if par.get("punteggi") is False:
        out.append(("Punteggi", "senza tabella"))
    elif par.get("punti_totali"):
        out.append(("Punteggio", f"{par['punti_totali']} pt"))
    if par.get("uso_file"):
        out.append(("Allegato", "esercizi nuovi dagli appunti" if par["uso_file"] == "spunto" else "rifatta con dati nuovi"))
    return out


def totale_predefinito(par: dict) -> int:
    """Quanti esercizi avrà la verifica se il docente non ha detto un numero: quelli della durata standard più, salvo rifiuto, quello per l'eccellenza."""
    return DURATE[DURATA_DEFAULT]["num_esercizi"] + (0 if par.get("eccellenza") is False else 1)


def seleziona_esercizi(totale: int | None, eccellenza: bool) -> int | None:
    """Il modulo chiede quanti esercizi SENZA quello per l'eccellenza (che si aggiunge): da un totale desiderato ricava il valore del menu (3-10)."""
    if not totale:
        return None
    return max(3, min(10, totale - 1 if eccellenza else totale))


def testo_richiesta(par: dict) -> str:
    """Il riquadro «Di cosa parla la verifica?»: argomento nella prima riga, indicazioni nelle righe successive."""
    return "\n".join(x for x in (par.get("argomento"), par.get("indicazioni")) if x)
