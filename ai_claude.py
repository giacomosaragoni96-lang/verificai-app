# ── ai_claude.py ───────────────────────────────────────────────────────────────
# Adattatore Claude (Anthropic) con la stessa forma di ai_client.ModelloAI:
# .per(compito), .generate_content(contenuto, generation_config, stream) → risposta con .text.
# Serve al piano Free (Claude Haiku al posto di Flash-Lite, scelta dopo il confronto del 2 novembre 2026).
# Registra token e costi nello stesso registro di ai_client (riepilogo_uso). Nessun import di streamlit.
#
# Divisione dei compiti (come config.scegli_modello_per_compito, con Haiku al posto di Flash-Lite):
#   compiti leggeri e del piano (titolo, piano, corpo, controlli, varianti, modifiche…) → Haiku
#   config.COMPITI_CLAUDE_FORTE (oggi solo l'autoverifica dei calcoli)                  → Sonnet
#   compiti «flash» con immagini o file (foto, agente, correzione dei compiti…)         → restano Gemini Flash

import base64
import logging
import threading
import time

import config

logger = logging.getLogger("verificai.ai")

_client = None
_lock = threading.Lock()


def disponibile() -> bool:
    """True se c'è la chiave e il pacchetto: altrimenti il piano Free resta su Gemini Flash-Lite."""
    return config.free_usa_claude()


def _get_client():
    global _client
    with _lock:
        if _client is None:
            import anthropic
            _client = anthropic.Anthropic(max_retries=2, timeout=240.0)     # la chiave è in ANTHROPIC_API_KEY
        return _client


class _Risposta:
    """Risposta con .text (mai None) e .uso (token consumati)."""

    def __init__(self, testo: str, uso: dict):
        self.text = testo or ""
        self.uso = uso


class _Pezzo:
    def __init__(self, testo: str):
        self.text = testo or ""


def _livello(ragionamento) -> str:
    """Tetto di ragionamento dell'app (0, None, numero, «alto») → spento | basso | medio."""
    if ragionamento == 0:
        return "spento"
    if ragionamento == "alto" or (isinstance(ragionamento, int) and ragionamento > 1024):
        return "medio"
    return "basso"


def _blocchi(contenuto) -> list:
    """Stringa o lista di stringhe/{"mime_type","data"} → blocchi di contenuto per Claude."""
    if isinstance(contenuto, str):
        return [{"type": "text", "text": contenuto}]
    blocchi = []
    for x in contenuto:
        if isinstance(x, dict) and "data" in x:
            mime = x.get("mime_type", "image/png")
            dati = base64.standard_b64encode(x["data"]).decode("ascii")
            tipo = "document" if mime == "application/pdf" else "image"
            blocchi.append({"type": tipo, "source": {"type": "base64", "media_type": mime, "data": dati}})
        else:
            blocchi.append({"type": "text", "text": str(x)})
    return blocchi


class ModelloClaude:
    """Un modello Claude con il suo livello di ragionamento. Usare .per(compito) per cambiarlo."""

    def __init__(self, model_id: str | None = None, compito: str | None = None, ragionamento=None):
        self.model_id = model_id or config.MODEL_CLAUDE_FAST_ID
        self.compito = compito
        self.ragionamento = ragionamento

    def per(self, compito: str):
        """Stesso piano, ma modello e ragionamento adatti al compito (vedi config.COMPITI_AI)."""
        tipo, rag = config.COMPITI_AI.get(compito, ("piano", None))
        if tipo == "flash" and compito not in config.COMPITI_CLAUDE_FORTE:
            import ai_client                                    # foto, agente, correzione…: Gemini Flash come per tutti i piani
            mid, rag_g = config.scegli_modello_per_compito(compito, config.MODEL_FAST_ID)
            return ai_client.ModelloAI(mid, compito, rag_g)
        mid = config.MODEL_CLAUDE_STRONG_ID if tipo == "flash" else config.MODEL_CLAUDE_FAST_ID
        return ModelloClaude(mid, compito, rag)

    def _parametri(self, contenuto, generation_config) -> dict:
        kw = {"model": self.model_id, "max_tokens": 32000, "messages": [{"role": "user", "content": _blocchi(contenuto)}]}
        if isinstance(generation_config, dict) and generation_config.get("json"):
            kw["system"] = "Rispondi esclusivamente con un oggetto JSON valido, senza testo attorno e senza backtick."
        livello = _livello(self.ragionamento)
        if livello == "spento":
            # Haiku accetta «disabled»; Sonnet no (400): lì si usa «between_tools», che non ragiona prima di rispondere
            kw["thinking"] = {"type": "disabled"} if self.model_id == config.MODEL_CLAUDE_FAST_ID else {"type": "between_tools"}
        else:
            kw["thinking"] = {"type": "adaptive"}
            kw["output_config"] = {"effort": "low" if livello == "basso" else "medium"}
        return kw

    def _registra(self, messaggio, t0: float) -> dict:
        import ai_client
        u = messaggio.usage
        uso = {"input": int(getattr(u, "input_tokens", 0) or 0), "output": int(getattr(u, "output_tokens", 0) or 0), "pensiero": 0}
        ai_client._registra(self.model_id, self.compito, uso, time.time() - t0)
        if getattr(messaggio, "stop_reason", None) == "refusal":
            logger.warning("Claude ha rifiutato la richiesta (%s)", self.compito)
        return uso

    def generate_content(self, contenuto, generation_config=None, stream: bool = False):
        kw = self._parametri(contenuto, generation_config)
        t0 = time.time()
        if stream:
            return self._flusso(kw, t0)
        with _get_client().messages.stream(**kw) as s:       # anche senza flusso visibile: richieste lunghe → timeout evitati
            msg = s.get_final_message()
        uso = self._registra(msg, t0)
        return _Risposta("".join(b.text for b in msg.content if b.type == "text"), uso)

    def _flusso(self, kw: dict, t0: float):
        with _get_client().messages.stream(**kw) as s:
            for testo in s.text_stream:
                yield _Pezzo(testo)
            msg = s.get_final_message()
        self._registra(msg, t0)


def errore_definitivo(exc: Exception) -> bool:
    """True se riprovare è inutile: chiave non valida, richiesta errata, permessi, crediti finiti."""
    try:
        import anthropic
    except Exception:
        return False
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError,
                        anthropic.BadRequestError, anthropic.NotFoundError)):
        return True
    return False
