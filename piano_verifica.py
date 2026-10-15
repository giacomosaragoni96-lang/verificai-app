"""
piano_verifica.py — il «piano» di una verifica, deciso PRIMA di scrivere gli esercizi (nessuna dipendenza da Streamlit).

Il flusso:
1. `scheletro_piano` (struttura-tipo di prompts.struttura_verifica): ruoli e punti di ogni esercizio, decisi dal codice.
2. L'AI (una chiamata breve) riempie lo scheletro: titolo, tipo e richieste (con livello 1-3 e una nota) di ogni esercizio.
3. `normalizza_piano` controlla e corregge la risposta con regole fisse (conteggi, livelli crescenti, mix di difficoltà…);
   i punti di ogni richiesta li calcola il codice dal livello, non l'AI.
4. `piano_a_testo` lo trasforma in istruzioni per la chiamata che scrive gli esercizi.
5. `applica_punti_piano` rimette nel LaTeX i punti decisi dal piano (se il numero di esercizi e di richieste coincide).

Funziona per ogni materia: i livelli sono 1 = ricordare/applicare in modo diretto, 2 = un passaggio in più o un caso particolare,
3 = più concetti insieme, una trappola, un ragionamento non standard.
"""
import json
import logging
import re

from prompts import struttura_verifica
from latex_utils import (
    _maschera_liste_annidate, _ripristina_liste_annidate, apply_item_pts_to_body, bilancia_punti, _PT_PATTERN,
)

logger = logging.getLogger(__name__)

TIPI = ("aperto", "vero_falso", "scelta_multipla", "completamento")
_CHIUSI = ("vero_falso", "scelta_multipla", "completamento")
_ETICHETTA_TIPO = {"aperto": "aperto", "vero_falso": "Vero/Falso", "scelta_multipla": "scelta multipla",
                   "completamento": "completamento"}
_NOME_LIVELLO = {1: "FACILE", 2: "MEDIO", 3: "DIFFICILE"}
# numero di richieste ammesso per ruolo: (minimo, massimo)
_LIMITI_RICHIESTE = {"A": (1, 4), "B": (1, 4), "C": (3, 8), "M": (2, 4), "G": (2, 6), "P": (2, 3), "E": (1, 2)}
# peso dei punti di una richiesta in base al livello (facile : media : difficile ≈ 1 : 1,7 : 2,7)
_PESO_LIVELLO = {1: 10, 2: 17, 3: 27}
# parole che rivelano che le note del docente dicono qualcosa sulla struttura (rete di sicurezza oltre al giudizio dell'AI)
_PAROLE_VINCOLO = ("esercizio", "esercizi", "punt", "richiest", "sottopunt", "difficil", "facil", "semplic", "vero o falso", "scelta multipla",
                   "completamento", "primo", "secondo", "terzo", "quarto", "quinto", "ultimo", "iniziare", "parti con", "finisci",
                   "numero di", "almeno", "massimo", "minimo", "soltanto", "solo ", "tutti gli", "ciascun", "ogni ")
_PAROLE_CHIUSI = ("vero o falso", "vero/falso", "scelta multipla", "completamento", "a risposta multipla", "completa")


def scheletro_piano(num_esercizi: int, punti_totali: int, primo_base: bool, eccellenza: bool, argomento: str) -> list:
    """Ruoli e punti di ogni esercizio, decisi dal codice: [{"ruolo", "descrizione", "punti"}]."""
    return struttura_verifica(num_esercizi, punti_totali or 100, primo_base, eccellenza, argomento)


def max_esercizi_chiusi(num_esercizi: int) -> int:
    return 1 if num_esercizi <= 4 else (2 if num_esercizi <= 7 else 3)


def estrai_json(testo: str):
    """Il primo oggetto JSON della risposta dell'AI (anche dentro ```json … ```); None se non c'è."""
    t = (testo or "").replace("```json", "").replace("```", "").strip()
    a, b = t.find("{"), t.rfind("}")
    if a == -1 or b <= a:
        return None
    try:
        return json.loads(t[a:b + 1])
    except (ValueError, TypeError):
        return None


def _livello(v) -> int:
    try:
        return min(3, max(1, int(round(float(v)))))
    except (ValueError, TypeError):
        s = str(v or "").lower()
        return 3 if "diffic" in s else (1 if "facil" in s else 2)


def punti_richieste(livelli: list, totale: int, tipo: str = "aperto") -> list:
    """Punti di ogni richiesta: in proporzione al livello (le chiuse tutte uguali); interi, somma = totale, minimo 1."""
    if not livelli:
        return []
    pesi = [1 if tipo in _CHIUSI else _PESO_LIVELLO[l] for l in livelli]
    return bilancia_punti(pesi, max(totale, len(livelli)))


def docente_ha_vincoli(grezzo, note_docente: str) -> bool:
    """True se le note del docente dicono qualcosa sulla struttura: allora il piano si adatta a lui e il codice non impone regole."""
    note = (note_docente or "").strip().lower()
    if not note:
        return False
    if isinstance(grezzo, dict) and grezzo.get("docente_vincola") is True:
        return True
    return any(k in note for k in _PAROLE_VINCOLO)


def normalizza_piano(grezzo, scheletro: list, note_docente: str = "") -> dict | None:
    """
    Controlla e corregge il piano scritto dall'AI. Ritorna {"esercizi": [...], "vincolo": bool} oppure None se non è utilizzabile
    (allora si genera come prima, senza piano). Ogni esercizio: ruolo, descrizione, titolo, tipo, punti, richieste
    [{"livello", "nota"}], punti_richieste.
    PRECEDENZA AL DOCENTE: se le sue note dicono qualcosa sulla struttura (vincolo=True) il codice NON riscrive livelli, tipi né numero di
    richieste (solo controlli di forma), usa i punti che il docente ha indicato, e non impone i punti per richiesta.
    """
    if not isinstance(grezzo, dict) or not isinstance(grezzo.get("esercizi"), list) or not scheletro:
        return None
    vincolo = docente_ha_vincoli(grezzo, note_docente)
    ai = [e for e in grezzo["esercizi"] if isinstance(e, dict)]
    n = len(scheletro)
    if len(ai) < n:
        logger.warning("Piano scartato: %s esercizi invece di %s", len(ai), n)
        return None
    ai = ai[:n]
    esercizi = []
    for i, (sk, e) in enumerate(zip(scheletro, ai)):
        ruolo = sk["ruolo"]
        tipo = str(e.get("tipo") or "aperto").strip().lower().replace("/", "_").replace(" ", "_")
        tipo = {"vero_o_falso": "vero_falso", "multipla": "scelta_multipla"}.get(tipo, tipo)
        if tipo not in TIPI:
            tipo = "aperto"
        grezze = e.get("richieste")
        if not isinstance(grezze, list) or not grezze:
            logger.warning("Piano scartato: l'esercizio %s non ha richieste", i + 1)
            return None
        rich = []
        for r in grezze:
            if isinstance(r, dict):
                rich.append({"livello": _livello(r.get("livello")), "nota": re.sub(r"\s+", " ", str(r.get("nota") or "")).strip()[:170]})
            else:
                rich.append({"livello": 2, "nota": re.sub(r"\s+", " ", str(r)).strip()[:170]})
        minimo, massimo = _LIMITI_RICHIESTE.get(ruolo, (1, 8))
        rich = rich[:12] if vincolo else rich[:massimo]
        esercizi.append({
            "ruolo": ruolo, "descrizione": sk["descrizione"], "punti": int(sk["punti"]),
            "titolo": re.sub(r"\s+", " ", str(e.get("titolo") or "")).strip()[:120] or f"Esercizio {i + 1}",
            "tipo": tipo, "richieste": rich, "_punti_docente": e.get("punti") if vincolo else None,
        })

    sotto = [] if vincolo else [i for i, e in enumerate(esercizi)
                                if len(e["richieste"]) < _LIMITI_RICHIESTE.get(e["ruolo"], (1, 8))[0]
                                and not (e["ruolo"] == "G" and len(e["richieste"]) == 1)]
    if vincolo:
        _punti_del_docente(esercizi)
        for e in esercizi:
            e.pop("_punti_docente", None)
            e["punti_richieste"] = []
        return {"esercizi": esercizi, "vincolo": True}

    for e in esercizi:
        e.pop("_punti_docente", None)
    # troppi esercizi chiusi: i più leggeri tornano aperti (salvo che il docente li abbia chiesti)
    if not any(k in (note_docente or "").lower() for k in _PAROLE_CHIUSI):
        chiusi = [e for e in esercizi if e["tipo"] in _CHIUSI]
        for e in sorted(chiusi, key=lambda e: e["punti"], reverse=True)[max_esercizi_chiusi(n):]:
            e["tipo"] = "aperto"

    for e in esercizi:
        _regola_livelli(e)
    _riequilibra_mix(esercizi)
    for e in esercizi:
        e["punti_richieste"] = punti_richieste([r["livello"] for r in e["richieste"]], e["punti"], e["tipo"])
    return {"esercizi": esercizi, "vincolo": False, "sotto": sotto}


def _punti_del_docente(esercizi: list) -> None:
    """Se il docente ha indicato i punti di alcuni esercizi, quelli restano; gli altri si dividono il resto come da scheletro."""
    totale = sum(e["punti"] for e in esercizi)
    fissi = {}
    for i, e in enumerate(esercizi):
        try:
            v = int(float(e.get("_punti_docente")))
        except (TypeError, ValueError):
            continue
        if v > 0:
            fissi[i] = v
    altri = [i for i in range(len(esercizi)) if i not in fissi]
    if not fissi or sum(fissi.values()) + len(altri) > totale or (not altri and sum(fissi.values()) != totale):
        if fissi and not altri and sum(fissi.values()) != totale:     # tutti indicati ma la somma non fa il totale: si riscala
            nuovi = bilancia_punti([fissi[i] for i in range(len(esercizi))], totale)
            for e, v in zip(esercizi, nuovi):
                e["punti"] = v
        return
    resto = totale - sum(fissi.values())
    nuovi = bilancia_punti([esercizi[i]["punti"] for i in altri], resto) if altri else []
    for i, v in fissi.items():
        esercizi[i]["punti"] = v
    for i, v in zip(altri, nuovi):
        esercizi[i]["punti"] = v


def _regola_livelli(e: dict) -> None:
    """Livelli coerenti col ruolo: apertura non difficile, centrale dal facile al difficile, eccellenza tutta difficile."""
    rich, ruolo = e["richieste"], e["ruolo"]
    if e["tipo"] in _CHIUSI:
        for r in rich:
            r["livello"] = min(r["livello"], 2)
    if ruolo == "E":
        for r in rich:
            r["livello"] = 3
        return
    if ruolo == "B":
        for r in rich:
            r["livello"] = 1
    elif ruolo == "A":
        for r in rich:
            r["livello"] = min(r["livello"], 2)
    rich.sort(key=lambda r: r["livello"])             # mai in discesa dentro lo stesso esercizio (ordinamento stabile)
    if ruolo == "C" and len(rich) >= 2:
        rich[0]["livello"] = 1
        rich[-1]["livello"] = 3
        if len(rich) >= 4 and rich[-2]["livello"] < 2:
            rich[-2]["livello"] = 2


def _riequilibra_mix(esercizi: list) -> None:
    """Livello di partenza ALTO: almeno circa il 25% di richieste difficili e non più del 45%; almeno il 20% facili."""
    tutte = [(e, r) for e in esercizi if e["tipo"] not in _CHIUSI for r in e["richieste"]]
    if len(tutte) < 6:
        return
    n = len(tutte)

    def conta(l):
        return sum(1 for _, r in tutte if r["livello"] == l)

    # poche difficili: l'ultima richiesta media dei problemi/analisi/medi diventa difficile
    for e in reversed(esercizi):
        if conta(3) >= round(n * 0.25):
            break
        if e["ruolo"] in ("G", "P", "M") and e["tipo"] not in _CHIUSI and e["richieste"][-1]["livello"] == 2:
            e["richieste"][-1]["livello"] = 3
    # troppe difficili: le ultime difficili dei problemi/analisi tornano medie (mai il fondo del centrale né l'eccellenza)
    for e in esercizi:
        if conta(3) <= round(n * 0.45):
            break
        if e["ruolo"] in ("G", "P", "M") and len(e["richieste"]) >= 2 and e["richieste"][-1]["livello"] == 3:
            e["richieste"][-1]["livello"] = 2
    # troppo poche facili: la prima richiesta media dell'apertura o dell'esercizio medio diventa facile
    for e in esercizi:
        if conta(1) >= round(n * 0.20):
            break
        if e["ruolo"] in ("A", "M", "G") and e["richieste"][0]["livello"] == 2:
            e["richieste"][0]["livello"] = 1


def piano_a_testo(piano: dict, mostra_punteggi: bool = True) -> str:
    """Istruzioni per la chiamata che scrive gli esercizi: il piano da seguire alla lettera."""
    righe = [
        "PIANO DETTAGLIATO DELLA VERIFICA — DA SEGUIRE ALLA LETTERA (questo piano ha la precedenza sulle indicazioni generiche di struttura):",
        "Stessi esercizi, nello stesso ordine, con lo stesso numero di richieste e lo stesso livello. Livelli: FACILE = applicazione diretta "
        "o ricordare; MEDIO = un passaggio in più o un caso particolare; DIFFICILE = più concetti insieme, una trappola o un ragionamento "
        "non standard: deve essere DAVVERO difficile (non basta un calcolo più lungo).",
    ]
    vincolo = bool(piano.get("vincolo"))
    if vincolo:
        righe.append("ATTENZIONE: il docente ha dato istruzioni precise: SE contraddicono questo piano, vincono le sue istruzioni "
                     "(il piano serve da traccia dove il docente non ha detto nulla).")
    for i, e in enumerate(piano["esercizi"], 1):
        tipo = "" if e["tipo"] == "aperto" else f" — tipo: {_ETICHETTA_TIPO[e['tipo']]} (tutte le richieste dello stesso tipo)"
        base = " — apertura di BASE voluta dal docente: resta semplice" if e["ruolo"] == "B" else ""
        righe.append(f"Esercizio {i}: «{e['titolo']}»{tipo}{base}" + (f" — totale {e['punti']} pt" if mostra_punteggi else ""))
        for k, r in enumerate(e["richieste"]):
            lettera = "abcdefghijklmnopqrstuvwxyz"[k % 26]
            pt = e["punti_richieste"][k] if (not vincolo and k < len(e.get("punti_richieste") or [])) else None
            righe.append(f"   {lettera}) {_NOME_LIVELLO[r['livello']]}"
                         + (f" — [nota per te, NON scriverla nel testo: {r['nota']}]" if r["nota"] else "")
                         + (f" — ({pt} pt)" if (mostra_punteggi and pt is not None) else ""))
    righe.append("Consegna di ogni esercizio: UNA riga, breve. Le richieste sono brevi: la difficoltà sta nei dati e nel tipo, non nella lunghezza. "
                 "Se la nota di una richiesta indica una trappola o un passaggio da fare, i dati devono richiederlo davvero.")
    return "\n".join(righe)


def _conta_sottopunti(body: str) -> int:
    """Quanti sottopunti (che portano punti) ha il corpo di un esercizio."""
    masked, _ = _maschera_liste_annidate(body)
    if re.search(r"\\item\[", masked):
        return len(re.findall(r"\\item\[[^\]]*\][^\n]*", masked))
    if re.search(r"\\item\s+", masked):
        return len(re.findall(r"\\item\s+[^\n]+", masked))
    return 1 if _PT_PATTERN.search(body) else 0


def applica_punti_piano(latex: str, piano: dict | None) -> str:
    """
    Rimette nel LaTeX i punti decisi dal piano. Serve lo stesso numero di esercizi del piano; per ogni esercizio, se i sottopunti
    sono quanti quelli del piano si usano i suoi punti, altrimenti il totale dell'esercizio si divide con una rampa crescente.
    Se i conti non tornano non cambia nulla (poi riscala_punti riporta la somma al totale).
    """
    if not piano or piano.get("vincolo"):
        return latex                    # con istruzioni del docente i punti restano quelli scritti dal modello (e poi riscalati)
    parti = re.split(r"(?=\\subsection\*\{)", latex)
    blocchi = parti[1:]
    if len(blocchi) != len(piano["esercizi"]):
        logger.info("Punti del piano non applicati: %s esercizi scritti, %s nel piano", len(blocchi), len(piano["esercizi"]))
        return latex
    out = [parti[0]]
    for blocco, e in zip(blocchi, piano["esercizi"]):
        m = re.match(r"[^\n]*\n?", blocco)
        testa, corpo = blocco[:m.end()], blocco[m.end():]
        k = _conta_sottopunti(corpo)
        if k == 0:
            out.append(blocco)
            continue
        if k == len(e["punti_richieste"]):
            nuovi = list(e["punti_richieste"])
        else:
            pesi = [1] * k if e["tipo"] in _CHIUSI else [10 + 7 * j for j in range(k)]
            nuovi = bilancia_punti(pesi, max(e["punti"], k))
        out.append(testa + apply_item_pts_to_body(corpo, nuovi))
    return "".join(out)
