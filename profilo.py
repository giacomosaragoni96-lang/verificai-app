"""
profilo.py — preferenze fisse del docente e sue classi (senza Streamlit).

Il profilo sta nella tabella `docente_preferenze` (riga con materia «__profilo__», campo jsonb): nessuna migrazione.
Contenuto: `note_fisse` (istruzioni che valgono per ogni verifica: «numeri interi, niente dimostrazioni…») e `classi`
([{nome, scuola, note}]). Per ogni verifica si possono scegliere una classe, che precompila la scuola e aggiunge le sue note.

REGOLA ASSOLUTA: le note scritte dal docente QUELLA volta vincono sempre sulle preferenze fisse. Le fisse si accodano in coda alle sue
note, con la dicitura che valgono solo se non contraddicono quanto scritto sopra.
"""
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone

CHIAVE = "__profilo__"
MAX_NOTE = 600
MAX_CLASSI = 30
_RE_NOME = re.compile(r"\s+")


# Colori delle classi, nell'ordine dei pallini della pagina profilo; gli ultimi quattro erano scelte di prima (restano validi per le classi già salvate)
COLORI = ["#2563EB", "#7C3AED", "#DC2626", "#EA580C", "#CA8A04", "#16A34A", "#1E293B", "#92400E", "#DB2777", "#0D9488", "#0891B2", "#475569"]

# Preferenze pronte da accendere: id → (etichetta, frase che si aggiunge alle istruzioni)
PILLOLE = {
    "interi": ("Numeri interi", "Usa numeri interi o frazioni semplici, risultati puliti."),
    "no_dim": ("Niente dimostrazioni", "Evita le dimostrazioni e richieste come «dimostra che»."),
    "eccellenza": ("Esercizio per l'eccellenza", "Chiudi con un esercizio per l'eccellenza, facoltativo e più difficile."),
    "linguaggio": ("Linguaggio semplice", "Consegne brevi e con linguaggio semplice."),
    "poche_formule": ("Poche formule", "Privilegia richieste a parole e brevi: poche formule lunghe."),
    "realta": ("Un problema di vita reale", "Includi almeno un problema legato a una situazione di vita quotidiana."),
    "grafico": ("Un grafico da leggere", "Includi un esercizio con un grafico da leggere e interpretare."),
}


def vuoto() -> dict:
    return {"note_fisse": "", "pillole": [], "stile": "", "classi": []}


def pulisci_nome(nome: str) -> str:
    return _RE_NOME.sub(" ", str(nome or "")).strip()[:24]


def pulisci(grezzo) -> dict:
    """Il profilo in forma sicura: testi tagliati, classi uniche e con nome."""
    g = grezzo if isinstance(grezzo, dict) else {}
    classi, visti = [], set()
    for c in (g.get("classi") if isinstance(g.get("classi"), list) else []):
        if not isinstance(c, dict):
            continue
        n = pulisci_nome(c.get("nome"))
        if not n or n.lower() in visti:
            continue
        visti.add(n.lower())
        col = str(c.get("colore") or "")
        classi.append({"nome": n, "scuola": str(c.get("scuola") or "")[:80], "note": str(c.get("note") or "").strip()[:MAX_NOTE],
                       "colore": col if col in COLORI else COLORI[len(classi) % len(COLORI)]})
        if len(classi) >= MAX_CLASSI:
            break
    pill = [x for x in (g.get("pillole") if isinstance(g.get("pillole"), list) else []) if x in PILLOLE]
    return {"note_fisse": str(g.get("note_fisse") or "").strip()[:MAX_NOTE], "pillole": pill, "stile": str(g.get("stile") or "")[:20], "classi": classi}


def classe(profilo: dict, nome: str | None):
    for c in (profilo or {}).get("classi", []):
        if nome and c["nome"].lower() == nome.lower():
            return c
    return None


def nomi_classi(profilo: dict, dallo_storico: list | None = None) -> list:
    """Le classi del profilo più quelle già usate nelle verifiche salvate (senza doppioni, nell'ordine in cui compaiono)."""
    out, visti = [], set()
    for n in [c["nome"] for c in (profilo or {}).get("classi", [])] + [pulisci_nome(x) for x in (dallo_storico or [])]:
        if n and n.lower() not in visti:
            visti.add(n.lower())
            out.append(n)
    return out


def note_per_generazione(profilo: dict, nome_classe: str | None, note_docente: str) -> str:
    """Le note da dare alla generazione: quelle del docente (che vincono) seguite dalle preferenze fisse e dalle note della classe."""
    fisse = []
    p = profilo or {}
    for _id in p.get("pillole") or []:
        if _id in PILLOLE:
            fisse.append(PILLOLE[_id][1])
    if (p.get("note_fisse") or "").strip():
        fisse.append(p["note_fisse"].strip())
    c = classe(p, nome_classe)
    if c and (c.get("note") or "").strip():
        fisse.append(f"Per la classe {c['nome']}: {c['note'].strip()}")
    base = (note_docente or "").strip()
    if not fisse:
        return base
    blocco = ("PREFERENZE ABITUALI DEL DOCENTE (valgono solo se NON contraddicono le istruzioni scritte sopra o la descrizione della verifica; "
              "in caso di conflitto vince ciò che ha scritto per questa verifica):\n" + "\n".join("- " + f for f in fisse))
    return (base + "\n\n" + blocco).strip() if base else blocco


def frasi_preferenze(profilo: dict, nome_classe: str | None = None) -> list:
    """Le istruzioni fisse che l'AI riceverà (pillole, note e note della classe), una per voce: per mostrarle al docente."""
    p = profilo or {}
    out = [PILLOLE[i][1] for i in (p.get("pillole") or []) if i in PILLOLE]
    if (p.get("note_fisse") or "").strip():
        out.append(p["note_fisse"].strip())
    c = classe(p, nome_classe)
    if c and (c.get("note") or "").strip():
        out.append(f"Per la classe {c['nome']}: {c['note'].strip()}")
    return out


def _giorno(ts) -> date | None:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
    except Exception:
        return None


def statistiche(verifiche: list, oggi: date | None = None) -> dict:
    """Numeri per la pagina profilo da un elenco di verifiche: totali, per materia e per classe, ultime, calendario delle ultime 53 settimane."""
    oggi = oggi or datetime.now(timezone.utc).date()
    per_giorno, per_materia, per_classe = Counter(), Counter(), {}
    for v in verifiche:
        g = _giorno(v.get("created_at"))
        if g:
            per_giorno[g] += 1
        per_materia[v.get("materia") or "Altra"] += 1
        c = (v.get("classe") or "").strip()
        if c:
            d = per_classe.setdefault(c.lower(), {"nome": c, "n": 0, "ultima": None, "ultima_titolo": ""})
            d["n"] += 1
            if g and (d["ultima"] is None or g >= d["ultima"]):
                d["ultima"], d["ultima_titolo"] = g, v.get("argomento") or ""
    # calendario: 53 colonne (settimane) da lunedì, ultima colonna = settimana corrente
    inizio = oggi - timedelta(days=oggi.weekday()) - timedelta(weeks=52)
    giorni = []
    for i in range(53 * 7):
        d = inizio + timedelta(days=i)
        giorni.append({"data": d, "n": per_giorno.get(d, 0) if d <= oggi else None})
    primo = min(per_giorno) if per_giorno else None
    return {"totale": len(verifiche), "materie": per_materia.most_common(), "classi": per_classe, "calendario": giorni,
            "giorni_attivi": len(per_giorno), "dal": primo, "ultime": sorted(verifiche, key=lambda v: v.get("created_at") or "", reverse=True)[:5]}


def scala_colore(n, massimo: int) -> int:
    """Livello 0-4 di una cella del calendario (None = giorno futuro)."""
    if n is None:
        return -1
    if n <= 0:
        return 0
    return min(4, 1 + int(3 * (n - 1) / max(1, massimo - 1))) if massimo > 1 else 2
