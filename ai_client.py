# ── ai_client.py ───────────────────────────────────────────────────────────────
# Adattatore sottile su google-genai (l'SDK google-generativeai è dismesso).
# Mantiene la forma d'uso di prima: modello.generate_content(...) → risposta.text,
# e in più: scelta del modello e del ragionamento per compito, registro dei token
# e dei costi stimati, riconoscimento degli errori non recuperabili.
# Nessun import di streamlit: resta testabile in isolamento.

import logging
import os
import threading
import time
from collections import deque

from google import genai
from google.genai import errors, types

from config import PREZZI_USD_PER_MILIONE, scegli_modello_per_compito

logger = logging.getLogger("verificai.ai")

_client = None
_lock = threading.Lock()
_registro = deque(maxlen=1000)      # ultime chiamate (in memoria, si azzera al riavvio)


# ── CLIENT ────────────────────────────────────────────────────────────────────

def configura(api_key: str | None = None):
    """Crea il client condiviso. Va chiamato una volta all'avvio."""
    global _client
    chiave = api_key or os.getenv("GOOGLE_API_KEY")
    _client = genai.Client(
        api_key=chiave,
        http_options=types.HttpOptions(timeout=240_000),   # ms: evita attese infinite
    )
    return _client


def _get_client():
    return _client or configura()


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
    p_in, p_out = PREZZI_USD_PER_MILIONE.get(model_id, (0.0, 0.0))
    return (uso["input"] * p_in + (uso["output"] + uso["pensiero"]) * p_out) / 1_000_000


def _registra(model_id: str, compito: str | None, uso: dict, secondi: float):
    voce = {
        "t": time.time(), "modello": model_id, "compito": compito or "-",
        "secondi": round(secondi, 1), "costo_usd": _costo_usd(model_id, uso), **uso,
    }
    with _lock:
        _registro.append(voce)
    logger.info(
        "AI uso | %s | %s | in=%d out=%d pensiero=%d | ~$%.4f | %.1fs",
        model_id, voce["compito"], uso["input"], uso["output"], uso["pensiero"],
        voce["costo_usd"], secondi,
    )


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

    def _config(self, generation_config):
        kw = {}
        temp = _temperatura(generation_config)
        if temp is not None:
            kw["temperature"] = temp
        rag = self.ragionamento
        if rag is not None:
            if "pro" in self.model_id:
                rag = max(int(rag), 128)      # Pro non può spegnere il ragionamento
            kw["thinking_config"] = types.ThinkingConfig(thinking_budget=int(rag))
        return types.GenerateContentConfig(**kw) if kw else None

    def generate_content(self, contenuto, generation_config=None, stream: bool = False):
        cfg = self._config(generation_config)
        cont = _contenuto(contenuto)
        t0 = time.time()
        if stream:
            return self._stream(cont, cfg, t0)
        risposta = _get_client().models.generate_content(model=self.model_id, contents=cont, config=cfg)
        uso = _uso_da_meta(getattr(risposta, "usage_metadata", None))
        _registra(self.model_id, self.compito, uso, time.time() - t0)
        return RispostaAI(risposta, uso)

    def _stream(self, cont, cfg, t0):
        ultimo_meta = None
        for pezzo in _get_client().models.generate_content_stream(
            model=self.model_id, contents=cont, config=cfg
        ):
            meta = getattr(pezzo, "usage_metadata", None)
            if meta is not None:
                ultimo_meta = meta
            try:
                testo = pezzo.text
            except Exception:
                testo = ""
            yield _Pezzo(testo)
        _registra(self.model_id, self.compito, _uso_da_meta(ultimo_meta), time.time() - t0)


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
