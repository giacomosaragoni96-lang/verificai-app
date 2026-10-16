"""
profilo.py — preferenze fisse del docente e sue classi (senza Streamlit).

Il profilo sta nella tabella `docente_preferenze` (riga con materia «__profilo__», campo jsonb): nessuna migrazione.
Contenuto: `note_fisse` (istruzioni che valgono per ogni verifica: «numeri interi, niente dimostrazioni…») e `classi`
([{nome, scuola, note}]). Per ogni verifica si possono scegliere una classe, che precompila la scuola e aggiunge le sue note.

REGOLA ASSOLUTA: le note scritte dal docente QUELLA volta vincono sempre sulle preferenze fisse. Le fisse si accodano in coda alle sue
note, con la dicitura che valgono solo se non contraddicono quanto scritto sopra.
"""
import re

CHIAVE = "__profilo__"
MAX_NOTE = 600
MAX_CLASSI = 30
_RE_NOME = re.compile(r"\s+")


def vuoto() -> dict:
    return {"note_fisse": "", "classi": []}


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
        classi.append({"nome": n, "scuola": str(c.get("scuola") or "")[:80], "note": str(c.get("note") or "").strip()[:MAX_NOTE]})
        if len(classi) >= MAX_CLASSI:
            break
    return {"note_fisse": str(g.get("note_fisse") or "").strip()[:MAX_NOTE], "classi": classi}


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
