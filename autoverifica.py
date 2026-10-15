"""
autoverifica.py — controllo e correzione degli esercizi delle materie scientifiche (senza Streamlit).

Dopo la generazione, un secondo passaggio con un modello più accurato RISOLVE ogni esercizio e segnala gli errori certi
(problema senza soluzione, scelta multipla senza risposta corretta, grafico incoerente…). Gli esercizi segnalati vengono
riscritti uno per uno, controllati di nuovo, e quelli che restano dubbi finiscono in un avviso per il docente.

Non solleva mai eccezioni: in caso di guasto si tiene il testo originale e si registra l'errore nel resoconto.
"""
import json
import logging
import re

from config import MATERIE_STEM
from latex_utils import conta_punti_latex
from prompts import prompt_autoverifica, prompt_correggi_esercizio

logger = logging.getLogger(__name__)

MAX_CORREZIONI = 3          # esercizi riscritti al massimo per verifica (oltre: solo avviso)
_RE_SPLIT = re.compile(r"(?=\\subsection\*\{)")


def e_materia_scientifica(materia: str) -> bool:
    return (materia or "") in MATERIE_STEM


def _blocchi(corpo: str):
    """(testa, [blocchi]) dove ogni blocco inizia con \\subsection*{ ; l'\\end{document} resta in coda all'ultimo."""
    parti = _RE_SPLIT.split(corpo)
    if len(parti) <= 1:
        return corpo, []
    return parti[0], parti[1:]


def _senza_fine(blocco: str) -> str:
    return re.sub(r"\s*\\end\{document\}\s*$", "", blocco)


def _json(testo: str):
    """Estrae l'oggetto JSON dalla risposta (anche se circondato da ```json … ```)."""
    t = (testo or "").strip()
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except ValueError:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                return None
    return None


def _modello(model):
    per = getattr(model, "per", None)
    return per("autoverifica") if per else model


def _genera(model, prompt: str, json_out: bool = False, temperatura: float = 0.2) -> str:
    cfg = {"temperature": temperatura}
    if json_out:
        cfg["json"] = True
    try:
        return model.generate_content(prompt, generation_config=cfg).text or ""
    except TypeError:                       # modelli senza generation_config
        return model.generate_content(prompt).text or ""


def _verifica(model, materia: str, scuola: str, esercizi: list) -> list:
    """Problemi trovati: [{"num", "problema", "suggerimento"}]. Lista vuota = tutto a posto."""
    risposta = _json(_genera(model, prompt_autoverifica(materia, scuola, esercizi), json_out=True))
    if not isinstance(risposta, dict):
        raise ValueError("risposta dell'autoverifica non leggibile")
    problemi = []
    for e in risposta.get("esercizi") or []:
        if isinstance(e, dict) and e.get("ok") is False:
            try:
                num = int(e.get("num"))
            except (TypeError, ValueError):
                continue
            problemi.append({"num": num, "problema": str(e.get("problema") or "errore non specificato")[:300],
                             "suggerimento": str(e.get("suggerimento") or "")[:300]})
    return problemi


def _verifica_con_ripetizione(model, materia: str, scuola: str, esercizi: list) -> list:
    """Come _verifica, ma se la chiamata cade (guasto momentaneo, per esempio «Bad file descriptor») ci riprova una volta."""
    try:
        return _verifica(model, materia, scuola, esercizi)
    except Exception:
        logger.warning("Autoverifica: primo tentativo non riuscito, riprovo", exc_info=True)
        return _verifica(model, materia, scuola, esercizi)


def _riscrivi(model, materia, argomento, blocco, problema, mostra_punteggi):
    """Nuovo blocco corretto, oppure None se non è valido (titolo mancante, punteggi diversi)."""
    originale = _senza_fine(blocco)
    for tentativo in (0, 1):
        testo = _genera(model, prompt_correggi_esercizio(materia, argomento, originale, problema["problema"],
                                                         problema["suggerimento"], mostra_punteggi), temperatura=0.4)
        testo = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", testo.strip())
        if not testo.startswith("\\subsection*{") or len(_RE_SPLIT.split(testo)) != 2:
            continue
        if mostra_punteggi and conta_punti_latex(testo) != conta_punti_latex(originale):
            continue                        # i punteggi devono restare identici: si riprova una volta
        return _senza_fine(testo)
    return None


def autoverifica_corpo(model, materia: str, scuola: str, argomento: str, corpo: str,
                       mostra_punteggi: bool = True, on_progress=None):
    """
    Controlla e corregge il corpo della verifica. Ritorna (corpo, resoconto):
      resoconto = {"eseguita": bool, "controllati": n, "corretti": [num…], "irrisolti": [{num, problema}…], "errore": str|None}
    """
    resoconto = {"eseguita": False, "controllati": 0, "corretti": [], "irrisolti": [], "errore": None}
    try:
        if not e_materia_scientifica(materia):
            return corpo, resoconto
        testa, blocchi = _blocchi(corpo)
        if not blocchi:
            return corpo, resoconto
        mod = _modello(model)
        esercizi = [(i + 1, _senza_fine(b)) for i, b in enumerate(blocchi)]
        resoconto["controllati"] = len(esercizi)
        problemi = _verifica_con_ripetizione(mod, materia, scuola, esercizi)
        resoconto["eseguita"] = True
        resoconto["segnalati"] = [{"num": p["num"], "problema": p["problema"], "suggerimento": p["suggerimento"]}
                                  for p in problemi]          # per capire a posteriori perché è stato riscritto un esercizio
        if not problemi:
            return corpo, resoconto

        if on_progress:
            on_progress(f"🧮  Correggo {min(len(problemi), MAX_CORREZIONI)} esercizio/i con dati incoerenti…")
        nuovi = list(blocchi)
        corretti, da_ricontrollare = [], []
        for p in [x for x in problemi if 1 <= x["num"] <= len(blocchi)][:MAX_CORREZIONI]:
            nuovo = _riscrivi(mod, materia, argomento, blocchi[p["num"] - 1], p, mostra_punteggi)
            if nuovo:
                ha_fine = "\\end{document}" in blocchi[p["num"] - 1]
                nuovi[p["num"] - 1] = nuovo.rstrip() + ("\n\\end{document}\n" if ha_fine else "\n\n")
                corretti.append(p["num"])
                da_ricontrollare.append(p["num"])
            else:
                resoconto["irrisolti"].append({"num": p["num"], "problema": p["problema"]})
        # i problemi oltre il tetto di correzioni restano solo segnalati
        gia = set(corretti) | {x["num"] for x in resoconto["irrisolti"]}
        for p in problemi:
            if p["num"] not in gia and 1 <= p["num"] <= len(blocchi):
                resoconto["irrisolti"].append({"num": p["num"], "problema": p["problema"]})

        # secondo controllo, solo sugli esercizi riscritti
        if da_ricontrollare:
            ancora = _verifica(mod, materia, scuola, [(n, _senza_fine(nuovi[n - 1])) for n in da_ricontrollare])
            for p in ancora:
                if p["num"] in da_ricontrollare:
                    resoconto["irrisolti"].append({"num": p["num"], "problema": p["problema"]})
                    corretti.remove(p["num"])
        resoconto["corretti"] = sorted(corretti)
        return testa + "".join(nuovi), resoconto
    except Exception as e:
        logger.warning("Autoverifica non riuscita (tengo il testo originale): %s", e, exc_info=True)
        resoconto["errore"] = str(e)[:200]
        return corpo, resoconto
