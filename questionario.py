"""
questionario.py — il questionario dei tester (senza Streamlit): le domande e la pulizia delle risposte.

Anonimo: non si salva chi risponde (niente user_id, IP o altro). L'email è un campo facoltativo a parte,
per chi vuole essere avvisato delle novità. Tabella: `questionario_tester` (migrazione_questionario.sql, da eseguire a mano).
La pagina è `?pagina=questionario` (ui_questionario.py) e si apre anche senza accedere.
"""
import re

VERSIONE = 3        # 3: versione breve (15 domande, 9 obbligatorie, circa 2 minuti); 2 = la lunga (28 domande), le sue risposte restano nel database
MAX_TESTO = 1500
MAX_RIGA = 120
MAX_EURO = 10000

FUNZIONI = ["Verifica da una descrizione", "Impagina la tua verifica (da PDF o foto)", "Esercizio del tuo libro da una foto",
            "Modifica di un singolo esercizio", "Fila B", "Soluzioni", "Versione BES/DSA e alta leggibilità", "Word modificabile",
            "Logo della scuola", "Griglia di valutazione", "Scheda di allenamento", "Caricamento dei tuoi appunti"]

# Ogni sezione: (titolo, introduzione, [domande]). Tipi: scelta (una risposta), multi (più risposte), scala (da A a B),
# testo (risposta lunga), riga (risposta breve), euro (cifra in euro).
SEZIONI = [
    ("1. Com'è andata", "", [
        {"id": "tempo_da_zero", "tipo": "scelta", "testo": "Di solito quanto tempo ci metti a creare una verifica da zero?",
         "opzioni": ["Meno di 30 minuti", "30–60 minuti", "1–2 ore", "Più di 2 ore"]},
        {"id": "risparmio", "tipo": "scelta", "testo": "Con VerificAI, quanto tempo pensi di aver risparmiato?",
         "opzioni": ["Niente", "Un po'", "Circa la metà", "Più della metà"]},
        {"id": "utile", "tipo": "scala", "testo": "Ti è servito davvero?", "da": 1, "a": 5, "etichette": ("Per niente", "Moltissimo")},
        {"id": "correzioni", "tipo": "scelta", "testo": "Quanto hai dovuto correggere la verifica?", "opzioni": ["Niente", "Poco", "Molto"]},
        {"id": "useresti", "tipo": "scelta", "testo": "La useresti la prossima volta per una verifica vera?",
         "opzioni": ["Sì", "Forse", "No"]},
        {"id": "manca", "tipo": "testo", "testo": "Cosa manca o cosa cambieresti? (anche una frase sola)"},
    ]),
    ("2. Se un giorno fosse a pagamento",
     "Per ora VerificAI è gratuito: queste domande servono a capire cosa avrebbe senso, non a venderti nulla.", [
        {"id": "pagheresti", "tipo": "scelta", "testo": "Pagheresti per un servizio così?", "opzioni": ["Sì", "Forse", "No"]},
        {"id": "formula", "tipo": "multi", "testo": "Quale formula preferiresti? (puoi sceglierne più di una)",
         "opzioni": ["Un anno intero con un solo pagamento", "Pagamento per ogni singola verifica", "Pacchetto di verifiche",
                     "Abbonamento mensile", "Licenza per la scuola o il dipartimento", "Nessuna: non pagherei"]},
        {"id": "vw_conveniente", "tipo": "euro", "testo": "Pensando a un anno intero: a che prezzo lo troveresti conveniente? (€ all'anno)"},
        {"id": "vw_caro", "tipo": "euro", "testo": "A che prezzo comincerebbe a sembrarti caro? (€ all'anno)"},
        {"id": "vw_troppo_caro", "tipo": "euro", "testo": "A che prezzo lo troveresti troppo caro per comprarlo? (€ all'anno)"},
        {"id": "consiglieresti", "tipo": "scala", "testo": "Quanto è probabile che lo consiglieresti a un collega?", "da": 0, "a": 10,
         "etichette": ("Per niente probabile", "Sicuramente")},
    ]),
    ("3. Se hai ancora un minuto (facoltativo)", "", [
        {"id": "funzioni_mese", "tipo": "multi", "testo": "Quali funzioni useresti ogni mese?", "opzioni": FUNZIONI},
        {"id": "ordine", "tipo": "multi", "testo": "In che ordine di scuola insegni?",
         "opzioni": ["Scuola primaria", "Secondaria di primo grado (medie)", "Liceo", "Istituto tecnico", "Istituto professionale", "Altro"]},
        {"id": "altro", "tipo": "testo", "testo": "Altro che vuoi dirci?"},
    ]),
]

_DOMANDE = {d["id"]: d for _t, _i, ds in SEZIONI for d in ds}
_RE_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,200}\.[^@\s]{2,}$")


def pulisci_risposte(grezze: dict, email: str = ""):
    """
    (risposte, email_facoltativa) pronte da salvare: solo le domande rispondenti, testi tagliati, opzioni ammesse, cifre sensate.
    Se non c'è nessuna risposta ritorna ({}, None): niente da salvare.
    """
    out = {}
    for qid, d in _DOMANDE.items():
        v = (grezze or {}).get(qid)
        if v is None or v == "" or v == []:
            continue
        t = d["tipo"]
        if t == "scelta":
            if v in d["opzioni"]:
                out[qid] = v
        elif t == "multi":
            scelti = [x for x in (v if isinstance(v, (list, tuple)) else [v]) if x in d["opzioni"]]
            if scelti:
                out[qid] = scelti
        elif t == "scala":
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if d["da"] <= n <= d["a"]:
                out[qid] = n
        elif t == "euro":
            try:
                n = float(str(v).replace(",", "."))
            except ValueError:
                continue
            if 0 <= n <= MAX_EURO:
                out[qid] = round(n, 2)
        elif t == "riga":
            s = str(v).strip()[:MAX_RIGA]
            if s:
                out[qid] = s
        elif t == "testo":
            s = str(v).strip()[:MAX_TESTO]
            if s:
                out[qid] = s
    mail = (email or "").strip()[:254]
    return out, (mail if _RE_EMAIL.match(mail) else None)


def riga_da_inserire(risposte: dict, email: str | None) -> dict:
    return {"versione": VERSIONE, "risposte": risposte, "email_facoltativa": email}


def domanda(qid: str) -> dict:
    """La definizione di una domanda (per le due domande veloci prima del download)."""
    return _DOMANDE[qid]


def riga_rapida(risposte: dict) -> dict:
    """Le due domande veloci («quanto tempo hai risparmiato?», «ti è servito?»): stessa tabella, versione 0."""
    return {"versione": 0, "risposte": risposte, "email_facoltativa": None}


# Domande che servono per ricevere il codice (non «tutto»: quelle su di sé restano facoltative). Etichetta breve → per dire cosa manca.
OBBLIGATORIE = {
    "risparmio": "quanto tempo hai risparmiato", "utile": "ti è servito davvero", "useresti": "la useresti per una verifica vera",
    "manca": "cosa manca (scrivi almeno una frase)", "pagheresti": "se pagheresti", "vw_conveniente": "il prezzo conveniente",
    "vw_caro": "il prezzo che comincia a essere caro", "vw_troppo_caro": "il prezzo troppo caro", "consiglieresti": "se lo consiglieresti",
}
MIN_CARATTERI_MANCA = 10


def e_completo(risposte: dict):
    """(completo, [cosa manca]): tutte le domande chiave con risposta, un commento vero e prezzi coerenti (dal più basso al più alto)."""
    mancanti = [lab for qid, lab in OBBLIGATORIE.items() if qid not in risposte]
    if "manca" in risposte and len(str(risposte["manca"]).strip()) < MIN_CARATTERI_MANCA and OBBLIGATORIE["manca"] not in mancanti:
        mancanti.append(OBBLIGATORIE["manca"])
    prezzi = [risposte.get(k) for k in ("vw_conveniente", "vw_caro", "vw_troppo_caro")]
    if all(p is not None for p in prezzi) and any(a > b for a, b in zip(prezzi, prezzi[1:])):
        mancanti.append("i prezzi devono crescere: dal «conveniente» al «troppo caro»")
    return (not mancanti), mancanti
