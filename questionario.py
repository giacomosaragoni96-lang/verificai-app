"""
questionario.py — il questionario dei tester (senza Streamlit): le domande e la pulizia delle risposte.

Anonimo: non si salva chi risponde (niente user_id, IP o altro). L'email è un campo facoltativo a parte,
per chi vuole essere avvisato delle novità. Tabella: `questionario_tester` (migrazione_questionario.sql, da eseguire a mano).
La pagina è `?pagina=questionario` (ui_questionario.py) e si apre anche senza accedere.
"""
import re

VERSIONE = 1
MAX_TESTO = 1500
MAX_RIGA = 120
MAX_EURO = 10000

FUNZIONI = ["Generazione della verifica", "Modifica di un singolo esercizio", "Fila B", "Soluzioni", "Versione BES/DSA",
            "Logo della scuola", "Griglia di valutazione", "Scheda di allenamento", "Caricamento dei tuoi appunti o di una verifica"]

# Ogni sezione: (titolo, introduzione, [domande]). Tipi: scelta (una risposta), multi (più risposte), scala (da A a B),
# testo (risposta lunga), riga (risposta breve), euro (cifra in euro).
SEZIONI = [
    ("1. Chi sei (facoltativo)", "", [
        {"id": "ordine", "tipo": "multi", "testo": "In che ordine di scuola insegni?",
         "opzioni": ["Scuola primaria", "Secondaria di primo grado (medie)", "Liceo", "Istituto tecnico", "Istituto professionale", "Altro"]},
        {"id": "materie", "tipo": "riga", "testo": "Quali materie insegni?"},
        {"id": "verifiche_anno", "tipo": "scelta", "testo": "Quante verifiche scrivi in un anno?",
         "opzioni": ["0–5", "6–15", "16–30", "Più di 30"]},
    ]),
    ("2. Come fai oggi", "Prima di parlare di VerificAI, pensa a come prepari le verifiche di solito.", [
        {"id": "tempo_da_zero", "tipo": "scelta",
         "testo": "Di solito quanto tempo ci metti a creare una verifica da zero (scelta degli esercizi, impaginazione, "
                  "tabella dei punteggi, eventuali versioni)?",
         "opzioni": ["Meno di 30 minuti", "30–60 minuti", "1–2 ore", "Più di 2 ore"]},
        {"id": "parte_pesante", "tipo": "multi", "testo": "Quale parte ti pesa di più?",
         "opzioni": ["Scegliere gli esercizi", "Scriverli", "Impaginare", "Calcolare e scrivere i punteggi", "Preparare la Fila B",
                     "Preparare le soluzioni", "Adattare la verifica per BES/DSA", "Altro"]},
    ]),
    ("3. La tua esperienza con VerificAI", "", [
        {"id": "tempo_con", "tipo": "scelta", "testo": "Quanto ci hai messo a ottenere una verifica pronta da stampare?",
         "opzioni": ["Meno di 5 minuti", "5–15 minuti", "15–30 minuti", "Più di 30 minuti"]},
        {"id": "risparmio", "tipo": "scelta", "testo": "Rispetto al tuo solito, quanto tempo pensi di aver risparmiato?",
         "opzioni": ["Niente", "Un po'", "Circa la metà", "Più della metà"]},
        {"id": "utile", "tipo": "scala", "testo": "Ti è servito davvero?", "da": 1, "a": 5, "etichette": ("Per niente", "Moltissimo")},
        {"id": "useresti", "tipo": "scelta", "testo": "La useresti la prossima volta per una verifica vera?",
         "opzioni": ["Sì", "Forse", "No"]},
        {"id": "facile", "tipo": "scala", "testo": "Quanto è stato facile creare la prima verifica?", "da": 1, "a": 5,
         "etichette": ("Difficile", "Facilissimo")},
        {"id": "intuitivo", "tipo": "testo", "testo": "Cosa hai trovato più intuitivo?"},
        {"id": "confuso", "tipo": "testo", "testo": "Cosa ti ha confuso o rallentato?"},
        {"id": "pronta", "tipo": "scelta", "testo": "La verifica generata era pronta da usare?",
         "opzioni": ["Mai", "A volte", "Spesso", "Sempre"]},
        {"id": "correzioni", "tipo": "scelta", "testo": "Quanto hai dovuto correggere?", "opzioni": ["Niente", "Poco", "Molto"]},
    ]),
    ("4. Cosa manca e cosa è di troppo", "", [
        {"id": "piaciuto", "tipo": "multi", "testo": "Cosa ti è piaciuto di più?", "opzioni": FUNZIONI},
        {"id": "funzioni_mese", "tipo": "multi", "testo": "Quali funzioni useresti ogni mese?", "opzioni": FUNZIONI},
        {"id": "manca", "tipo": "testo", "testo": "Cosa manca?"},
        {"id": "troppo", "tipo": "testo", "testo": "Cosa c'è di troppo o non ti serve?"},
    ]),
    ("5. Se un giorno fosse a pagamento",
     "Per ora VerificAI è gratuito: queste domande servono a capire cosa avrebbe senso, non a venderti nulla.", [
        {"id": "pagheresti", "tipo": "scelta", "testo": "Pagheresti per un servizio così?", "opzioni": ["Sì", "Forse", "No"]},
        {"id": "perche", "tipo": "testo", "testo": "Se hai risposto «forse» o «no»: perché?"},
        {"id": "formula", "tipo": "scelta", "testo": "Quale formula preferiresti?",
         "opzioni": ["Un anno intero con un solo pagamento", "30 giorni con un solo pagamento", "Pagamento per ogni singola verifica",
                     "Pacchetto di verifiche", "Abbonamento mensile", "Licenza per la scuola o il dipartimento", "Nessuna: non pagherei"]},
        {"id": "verifiche_mese", "tipo": "scelta", "testo": "Quante verifiche al mese ti servirebbero?",
         "opzioni": ["1–2", "3–5", "6–10", "Più di 10"]},
        {"id": "vw_troppo_basso", "tipo": "euro", "testo": "Pensando a un anno intero: a che prezzo sarebbe così basso da farti dubitare della qualità? (€ all'anno)"},
        {"id": "vw_conveniente", "tipo": "euro", "testo": "A che prezzo all'anno lo troveresti conveniente? (€)"},
        {"id": "vw_caro", "tipo": "euro", "testo": "A che prezzo all'anno comincerebbe a sembrarti caro? (€)"},
        {"id": "vw_troppo_caro", "tipo": "euro", "testo": "A che prezzo all'anno lo troveresti troppo caro per comprarlo? (€)"},
        {"id": "consiglieresti", "tipo": "scala", "testo": "Quanto è probabile che lo consiglieresti a un collega?", "da": 0, "a": 10,
         "etichette": ("Per niente probabile", "Sicuramente")},
    ]),
    ("6. Ultima cosa (facoltativa)", "", [
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
