# ── ai_client.py ───────────────────────────────────────────────────────────────
# Adattatore sottile su google-genai (l'SDK google-generativeai è dismesso).
# Mantiene la forma d'uso di prima: modello.generate_content(...) → risposta.text,
# e in più: scelta del modello e del ragionamento per compito, registro dei token
# e dei costi stimati, riconoscimento degli errori non recuperabili e
# sostituzione automatica dei modelli ritirati (es. 2.5 → versione più recente).
# Nessun import di streamlit: resta testabile in isolamento.

import logging
import os
import re
import threading
import time
from collections import deque

from google import genai
from google.genai import errors, types

from config import PREZZI_STIMATI_GEN3, PREZZI_USD_PER_MILIONE, scegli_modello_per_compito

logger = logging.getLogger("verificai.ai")

_client = None
_lock = threading.Lock()
_conta = 0                         # numero progressivo delle chiamate (non si azzera)
_registro = deque(maxlen=1000)      # ultime chiamate (in memoria, si azzera al riavvio)

_alias: dict = {}                   # modello richiesto → modello realmente usato (se ritirato)
_ritirati = set()                    # modelli elencati ma che rispondono 404: da non riproporre
_modelli_disponibili = None         # elenco dei modelli che la chiave può usare (cache)
_senza_ragionamento: set = set()    # modelli che rifiutano la configurazione del ragionamento


# ── CLIENT ────────────────────────────────────────────────────────────────────

def configura(api_key: str | None = None):
    """Crea il client condiviso. Va chiamato una volta all'avvio."""
    global _client, _modelli_disponibili
    chiave = api_key or os.getenv("GOOGLE_API_KEY")
    _client = genai.Client(
        api_key=chiave,
        http_options=types.HttpOptions(timeout=240_000),   # ms: evita attese infinite
    )
    _modelli_disponibili = None
    return _client


def _get_client():
    return _client or configura()


# ── MODELLI: famiglia, versione, prezzi, sostituzione dei ritirati ─────────────

def _famiglia(model_id: str):
    if "flash-lite" in model_id:
        return "lite"
    if "flash" in model_id:
        return "flash"
    if "pro" in model_id:
        return "pro"
    return None


def _generazione(model_id: str) -> float:
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", model_id)
    return float(m.group(1)) if m else 0.0


def _prezzi(model_id: str):
    esatto = PREZZI_USD_PER_MILIONE.get(model_id)
    if esatto:
        return esatto
    if _generazione(model_id) >= 3:
        return PREZZI_STIMATI_GEN3.get(_famiglia(model_id), (0.0, 0.0))
    return (0.0, 0.0)


def _effettivo(model_id: str) -> str:
    return _alias.get(model_id, model_id)


def modelli_sostituiti() -> dict:
    """Modelli richiesti dal codice e ritirati, con quello usato al loro posto."""
    return dict(_alias)


def _elenca_modelli() -> list:
    global _modelli_disponibili
    if _modelli_disponibili is None:
        nomi = []
        for m in _get_client().models.list():
            nome = (getattr(m, "name", "") or "").replace("models/", "")
            azioni = getattr(m, "supported_actions", None) or []
            if azioni and "generateContent" not in azioni:
                continue
            nomi.append(nome)
        _modelli_disponibili = nomi
    return _modelli_disponibili


_SCARTI = ("image", "tts", "audio", "live", "embedding", "robotics", "computer",
           "vision", "customtools", "learnlm", "gemma", "aqa", "research")


def _scopri_modello(richiesto: str):
    """Il modello più recente della stessa famiglia (lite/flash/pro) che la chiave può usare."""
    fam = _famiglia(richiesto)
    if not fam:
        return None
    nome_fam = "flash-lite" if fam == "lite" else fam
    candidati = []
    try:
        elenco = _elenca_modelli()
    except Exception as e:
        logger.error("Elenco modelli non disponibile: %s", e)
        return None
    for nome in elenco:
        if nome in _ritirati:
            continue
        m = re.fullmatch(r"gemini-(\d+(?:\.\d+)?)-(flash-lite|flash|pro)(-[a-z0-9\-]+)?", nome)
        if not m or m.group(2) != nome_fam:
            continue
        suffisso = m.group(3) or ""
        if any(s in suffisso for s in _SCARTI):
            continue
        stabile = not any(s in suffisso for s in ("preview", "exp", "latest"))
        candidati.append((stabile, float(m.group(1)), -len(nome), nome))
    return max(candidati)[3] if candidati else None


def _non_disponibile(exc) -> bool:
    return isinstance(exc, errors.APIError) and getattr(exc, "code", None) == 404


# ── RISPOSTE ──────────────────────────────────────────────────────────────────

class RispostaAI:
    """Risposta con .text (testo, mai None) e .uso (token consumati)."""

    def __init__(self, risposta, uso: dict):
        self._risposta = risposta
        self.uso = uso
        try:
            self.text = risposta.text or ""
        except Exception:
            self.text = ""


class _Pezzo:
    """Pezzo di una risposta in streaming."""

    def __init__(self, testo: str):
        self.text = testo or ""


def _uso_da_meta(meta) -> dict:
    def n(nome):
        return int(getattr(meta, nome, 0) or 0) if meta is not None else 0
    return {
        "input":     n("prompt_token_count"),
        "output":    n("candidates_token_count"),
        "pensiero":  n("thoughts_token_count"),
    }


def _costo_usd(model_id: str, uso: dict) -> float:
    p_in, p_out = _prezzi(model_id)
    return (uso["input"] * p_in + (uso["output"] + uso["pensiero"]) * p_out) / 1_000_000


def _registra(model_id: str, compito: str | None, uso: dict, secondi: float):
    voce = {
        "t": time.time(), "modello": model_id, "compito": compito or "-",
        "secondi": round(secondi, 1), "costo_usd": _costo_usd(model_id, uso), **uso,
    }
    global _conta
    with _lock:
        _conta += 1
        voce["n"] = _conta
        _registro.append(voce)
    logger.info(
        "AI uso | %s | %s | in=%d out=%d pensiero=%d | ~$%.4f | %.1fs",
        model_id, voce["compito"], uso["input"], uso["output"], uso["pensiero"],
        voce["costo_usd"], secondi,
    )


def azzera_uso():
    """Svuota il registro dei consumi (utile per misurare una singola prova)."""
    with _lock:
        _registro.clear()


def numero_chiamate() -> int:
    """Quante chiamate sono state registrate finora (serve a isolare quelle di una singola generazione)."""
    with _lock:
        return _conta


def chiamate_da(n: int) -> list:
    """Le chiamate registrate dopo la n-esima: compito, modello vero, token, ragionamento, costo, secondi."""
    with _lock:
        return [dict(v) for v in _registro if v.get("n", 0) > n]


def riepilogo_uso(ultime: int | None = None) -> list:
    """Totali per (compito, modello) sulle ultime N chiamate registrate (None = tutte)."""
    with _lock:
        voci = list(_registro)
    if ultime:
        voci = voci[-ultime:]
    tot = {}
    for v in voci:
        k = (v["compito"], v["modello"])
        r = tot.setdefault(k, {"compito": k[0], "modello": k[1], "chiamate": 0,
                               "input": 0, "output": 0, "pensiero": 0, "costo_usd": 0.0})
        r["chiamate"] += 1
        for campo in ("input", "output", "pensiero", "costo_usd"):
            r[campo] += v[campo]
    return sorted(tot.values(), key=lambda r: -r["costo_usd"])


# ── MODELLO ───────────────────────────────────────────────────────────────────

def _contenuto(inp):
    """Stringa o lista di stringhe/{"mime_type","data"} → contenuto per google-genai."""
    if isinstance(inp, str):
        return inp
    pezzi = []
    for x in inp:
        if isinstance(x, dict) and "data" in x:
            pezzi.append(types.Part.from_bytes(data=x["data"], mime_type=x.get("mime_type", "image/png")))
        else:
            pezzi.append(x)
    return pezzi


def _temperatura(generation_config):
    if generation_config is None:
        return None
    if isinstance(generation_config, dict):
        return generation_config.get("temperature")
    return getattr(generation_config, "temperature", None)


def _ragionamento_config(model_id: str, tetto):
    """Tetto di token di ragionamento → configurazione adatta alla serie del modello."""
    if model_id in _senza_ragionamento:
        return None
    if _generazione(model_id) >= 3:
        # Serie 3.x: si sceglie un livello, non un numero di token. Senza indicazioni il
        # modello ragiona a livello medio/alto (costoso e lento): lo teniamo basso.
        if tetto is None:
            tetto = 1024
        if "pro" in model_id:
            livello = types.ThinkingLevel.LOW if tetto < 8192 else types.ThinkingLevel.HIGH
        elif tetto <= 0:
            livello = types.ThinkingLevel.MINIMAL
        elif tetto <= 1024:
            livello = types.ThinkingLevel.LOW
        elif tetto <= 2048:
            livello = types.ThinkingLevel.MEDIUM
        else:
            livello = types.ThinkingLevel.HIGH
        return types.ThinkingConfig(thinking_level=livello)
    if tetto is None:
        return None                       # 2.5: ragionamento predefinito del modello
    if "pro" in model_id:
        tetto = max(int(tetto), 128)      # Pro 2.5 non può spegnere il ragionamento
    return types.ThinkingConfig(thinking_budget=int(tetto))


class ModelloAI:
    """Un modello Gemini con il suo tetto di ragionamento. Usare .per(compito) per cambiarlo."""

    def __init__(self, model_id: str, compito: str | None = None, ragionamento=None):
        self.model_id = model_id
        self.compito = compito
        self.ragionamento = ragionamento

    def per(self, compito: str) -> "ModelloAI":
        """Stesso piano, ma modello e ragionamento adatti al compito (vedi config.COMPITI_AI)."""
        mid, rag = scegli_modello_per_compito(compito, self.model_id)
        return ModelloAI(mid, compito, rag)

    def _config(self, generation_config, model_id: str):
        kw = {}
        temp = _temperatura(generation_config)
        if temp is not None:
            kw["temperature"] = temp
        if isinstance(generation_config, dict) and generation_config.get("json"):
            kw["response_mime_type"] = "application/json"      # risposta in JSON valido
        pensiero = _ragionamento_config(model_id, self.ragionamento)
        if pensiero is not None:
            kw["thinking_config"] = pensiero
        return types.GenerateContentConfig(**kw) if kw else None

    def _con_ripieghi(self, esegui, generation_config):
        """Esegue la chiamata; se il modello è ritirato prova il più recente della famiglia,
        se rifiuta il ragionamento riprova senza. Restituisce (risultato, modello_usato)."""
        sostituzioni = 0
        while True:
            mid = _effettivo(self.model_id)
            cfg = self._config(generation_config, mid)
            try:
                return esegui(mid, cfg), mid
            except errors.APIError as e:
                testo = str(e).lower()
                if _non_disponibile(e) and sostituzioni < 2:
                    _ritirati.add(mid)
                    nuovo = _scopri_modello(self.model_id)
                    if nuovo and nuovo != mid:
                        logger.warning("Modello %s non disponibile, uso %s", mid, nuovo)
                        _alias[self.model_id] = nuovo
                        sostituzioni += 1
                        continue
                    if nuovo is None:
                        fam = _famiglia(self.model_id) or ""
                        visibili = [n for n in (_modelli_disponibili or []) if fam and fam in n]
                        raise RuntimeError(
                            f"Il modello {mid} è ritirato e la chiave non vede un sostituto della famiglia «{fam}». "
                            f"Modelli visibili di quella famiglia: {', '.join(visibili[:8]) or 'nessuno'}. "
                            f"(Pro 3.x richiede spesso un account Google AI a pagamento.)"
                        ) from e
                if (getattr(e, "code", None) == 400 and cfg is not None
                        and getattr(cfg, "thinking_config", None) is not None
                        and ("thinking" in testo or "thought" in testo)):
                    logger.warning("Il modello %s rifiuta il ragionamento configurato: riprovo senza", mid)
                    _senza_ragionamento.add(mid)
                    continue
                raise

    def generate_content(self, contenuto, generation_config=None, stream: bool = False):
        cont = _contenuto(contenuto)
        t0 = time.time()
        if stream:
            return self._stream(cont, generation_config, t0)
        risposta, mid = self._con_ripieghi(
            lambda m, cfg: _get_client().models.generate_content(model=m, contents=cont, config=cfg),
            generation_config,
        )
        uso = _uso_da_meta(getattr(risposta, "usage_metadata", None))
        _registra(mid, self.compito, uso, time.time() - t0)
        return RispostaAI(risposta, uso)

    def _stream(self, cont, generation_config, t0):
        # Apre il flusso con i ripieghi (un errore sul modello compare alla prima lettura)
        def apri(m, cfg):
            it = iter(_get_client().models.generate_content_stream(model=m, contents=cont, config=cfg))
            return it, next(it, None)

        (it, primo), mid = self._con_ripieghi(apri, generation_config)
        ultimo_meta = None

        def pezzi():
            if primo is not None:
                yield primo
            yield from it

        for pezzo in pezzi():
            meta = getattr(pezzo, "usage_metadata", None)
            if meta is not None:
                ultimo_meta = meta
            try:
                testo = pezzo.text
            except Exception:
                testo = ""
            yield _Pezzo(testo)
        _registra(mid, self.compito, _uso_da_meta(ultimo_meta), time.time() - t0)


def crea_modello(model_id: str, compito: str | None = None) -> ModelloAI:
    """Modello «così com'è» (senza tetto di ragionamento), per es. quello del piano dell'utente."""
    if compito:
        return ModelloAI(model_id, compito, None)
    return ModelloAI(model_id)


# ── ERRORI ────────────────────────────────────────────────────────────────────

def errore_definitivo(exc: Exception) -> bool:
    """True se riprovare è inutile: chiave non valida, richiesta errata, crediti/fatturazione finiti."""
    if isinstance(exc, errors.APIError):
        codice = getattr(exc, "code", None)
        testo = str(exc).lower()
        if codice in (400, 401, 403, 404):
            return True
        if codice == 429 and any(p in testo for p in ("credit", "billing", "prepayment", "spending cap")):
            return True
    return False
