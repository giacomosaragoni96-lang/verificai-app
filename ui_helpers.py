# ── ui_helpers.py — VerificAI UI rendering helpers ───────────────────────────
# Funzioni di rendering UI estratte da main.py per ridurne la densità.
# Ogni funzione accetta T (tema dict) come parametro esplicito per garantire
# coerenza visiva e testabilità indipendente dal contesto globale.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import html as html_lib
import logging
import re

# ── Optional st_yled (sticky_header + split_button) ──────────────────────────
try:
    import st_yled as _styl
    _STYLED_AVAILABLE = True
except ImportError:
    _styl = None
    _STYLED_AVAILABLE = False

# ── Stage constants (specchio di main.py — non devono divergere) ──────────────
STAGE_INPUT   = "INPUT"
STAGE_PREVIEW = "PREVIEW"
STAGE_REVIEW  = "REVIEW"
STAGE_FINAL   = "FINAL"


# ═══════════════════════════════════════════════════════════════════════════════
#  RICHIESTA UNICA — argomento + indicazioni nello stesso riquadro
# ═══════════════════════════════════════════════════════════════════════════════

def separa_argomento_e_note(testo: str, max_argomento: int = 120) -> tuple:
    """
    Dal riquadro "Cosa vuoi nella verifica?" ricava (argomento, note).

    La prima riga è l'argomento (serve per il titolo e per il prompt); le righe
    successive sono le indicazioni (cosa includere o evitare) e vanno nelle note.
    Se la prima riga è molto lunga viene tagliata a una pausa naturale e il resto
    passa alle note. Un eventuale "Argomento:" iniziale viene tolto.
    """
    righe = [r.strip() for r in (testo or "").splitlines() if r.strip()]
    if not righe:
        return "", ""
    prima = re.sub(r"^(?:argomento|tema)\s*[:\-–]\s*", "", righe[0], flags=re.IGNORECASE)
    resto_prima = ""
    if len(prima) > max_argomento:
        taglio = max(prima.rfind(c, 0, max_argomento) for c in ".;:")
        if taglio < 15:
            taglio = prima.rfind(" ", 0, max_argomento)
        if taglio <= 0:
            taglio = max_argomento
        resto_prima = prima[taglio:].lstrip(".;:, ").strip()
        prima = prima[:taglio].rstrip(" .;:,-")
    note = "\n".join(([resto_prima] if resto_prima else []) + righe[1:])
    return prima.strip(), note


# ═══════════════════════════════════════════════════════════════════════════════
#  ERRORI — messaggi in italiano comprensibile, dettagli tecnici solo nei log
# ═══════════════════════════════════════════════════════════════════════════════

_logger = logging.getLogger("verificai.ui")


def spazio(livello: str = "md") -> None:
    """Spazio verticale preso dalla scala di config.SPAZIO_REM (xs, sm, md, lg, xl, xxl)."""
    from config import SPAZIO_REM
    rem = SPAZIO_REM.get(livello, SPAZIO_REM["md"])
    st.markdown(f"<div style='height:{rem}rem'></div>", unsafe_allow_html=True)


def messaggio(tipo: str, testo: str, icon: str | None = None) -> None:
    """Un solo modo di mostrare un messaggio fisso: tipo = errore | avviso | ok | info."""
    {"errore": st.error, "avviso": st.warning, "ok": st.success}.get(tipo, st.info)(testo, icon=icon)


def _esc(valore) -> str:
    """Escape per ogni testo (titolo, materia, scuola…) inserito in HTML con unsafe_allow_html."""
    return html_lib.escape("" if valore is None else str(valore), quote=True)


def _messaggio_errore(exc) -> str:
    """Traduce un'eccezione (o un testo di errore) in una frase per il docente."""
    t = str(exc).lower() if exc is not None else ""
    if any(k in t for k in ("429", "quota", "resource_exhausted", "resource exhausted",
                            "rate limit", "overloaded", "503", "unavailable")):
        return "L'assistente è molto richiesto in questo momento. Riprova tra un minuto."
    if any(k in t for k in ("timeout", "timed out", "deadline", "connection", "network")):
        return "La connessione è lenta o si è interrotta. Riprova."
    if any(k in t for k in ("api key", "api_key", "permission", "unauthenticated", "401", "403")):
        return "C'è un problema con il servizio. Riprova più tardi; se continua, scrivici."
    if any(k in t for k in ("latex", "pdflatex", "tikz", "compil")):
        return "Non sono riuscito a impaginare il PDF. Riprova: di solito basta un secondo tentativo."
    if any(k in t for k in ("not found", "404", "not supported", "no longer available")):
        return "Il modello scelto non è disponibile in questo momento. Riprova con un altro modello."
    if any(k in t for k in ("safety", "blocked", "finish_reason", "candidate")):
        return "L'assistente non ha prodotto una risposta valida. Riprova, magari cambiando leggermente la richiesta."
    return "Qualcosa non ha funzionato. Riprova."


def _mostra_errore(
    azione: str,
    exc=None,
    riprova_flag: str | None = None,
    riprova_key: str | None = None,
    consiglio: str | None = None,
) -> None:
    """
    Mostra un errore comprensibile e scrive i dettagli tecnici nel log.

    azione        : cosa si stava facendo, in italiano ("Non sono riuscito a creare la verifica")
    exc           : eccezione o testo grezzo (non viene mai mostrato all'utente)
    riprova_flag  : chiave di session_state che l'handler dell'azione legge per rilanciarsi;
                    se presente compare il pulsante "Riprova" (serve anche riprova_key)
    consiglio     : testo che sostituisce quello ricavato dall'eccezione
    """
    _logger.error(
        f"{azione}: {exc}",
        exc_info=exc if isinstance(exc, BaseException) else False,
    )
    st.error(f"{azione}. {consiglio or _messaggio_errore(exc)}", icon="⚠️")
    if st.session_state.get("_admin_diagnostica") and exc is not None:
        # solo per l'admin: il motivo tecnico, per capire cosa non va senza aprire i log
        st.caption(f"Dettaglio tecnico (visibile solo all'admin): {type(exc).__name__}: {str(exc)[:700]}")
    if riprova_flag and riprova_key:
        if st.button("🔁 Riprova", key=riprova_key):
            st.session_state[riprova_flag] = True
            st.rerun()


def _mostra_errore_pdf(err, dove: str = "la verifica") -> None:
    """
    Errore di compilazione PDF: una sola frase comprensibile (niente LaTeX, niente log).
    Il log completo di pdflatex va solo nel logger.
    """
    testo = str(err) if err else ""
    _logger.error(f"Compilazione PDF fallita ({dove}): {testo[:4000]}")
    if "ERRORE_TIKZ_IRRECUPERABILE" in testo:
        st.error(
            f"Un grafico di {dove} non si riesce a disegnare. "
            "Usa «Cambia esercizio» sull'esercizio con il grafico, "
            "oppure ricrea la verifica scrivendo «senza grafici» nell'argomento.",
            icon="⚠️",
        )
    elif "TikZ" in testo:
        st.error(
            "Un grafico non è venuto bene. Prova «Cambia esercizio» sull'esercizio con il grafico.",
            icon="⚠️",
        )
    else:
        st.error(
            f"Non sono riuscito a creare il PDF di {dove}. "
            "Riprova: di solito basta un secondo tentativo.",
            icon="⚠️",
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  LIMITE MENSILE — testo di rinnovo e messaggio unico
# ═══════════════════════════════════════════════════════════════════════════════

def _reset_label(giorni: int, ore: int) -> str:
    """Testo di rinnovo del contatore mensile (es. 'Si rinnova tra 18 giorni')."""
    if giorni == 0:
        return f"Si rinnova tra {ore} ore"
    if giorni == 1:
        return "Si rinnova domani"
    return f"Si rinnova tra {giorni} giorni"


def _render_limite_raggiunto(
    T: dict,
    limite: int,
    reset_str: str,
    contatto_url: str,
    text_color: str | None = None,
    pro_cb=None,
    pro_key: str = "",
) -> None:
    """Messaggio unico mostrato quando il limite mensile è esaurito (sidebar e form)."""
    # Non è un errore ma un limite normale: tono neutro (colore d'accento), non rosso
    acc = T.get("accent", "#2563EB")
    testo = text_color or T.get("text", "#1F2937")
    _mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
             "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    from datetime import datetime, timezone
    _ora = datetime.now(timezone.utc)
    _prossimo = _mesi[_ora.month % 12]
    st.markdown(
        f'<div role="status" style="background:{acc}14;border:1px solid {acc}55;border-radius:10px;'
        f'padding:.8rem .95rem;margin:.5rem 0;font-size:.88rem;color:{testo};'
        f'font-family:DM Sans,sans-serif;line-height:1.55;">'
        f'<b>Hai usato le {limite} verifiche di questo mese.</b><br/>'
        f'Tornano a disposizione il 1° {_prossimo} ({reset_str.lower()}).'
        + ("" if pro_cb else
           f'<br/><a href="{html_lib.escape(contatto_url, quote=True)}" target="_blank" rel="noopener" '
           f'style="display:inline-block;margin-top:.45rem;color:{acc};font-weight:700;">'
           f'Chiedi più verifiche →</a>')
        + '</div>',
        unsafe_allow_html=True,
    )
    if pro_cb:   # con i piani attivi: più verifiche = piano Pro
        if st.button("Passa a Pro per averne di più", key=f"limite_pro_{pro_key}", icon=":material/workspace_premium:",
                     use_container_width=True):
            pro_cb()


# ═══════════════════════════════════════════════════════════════════════════════
#  BACK BUTTON
# ═══════════════════════════════════════════════════════════════════════════════

def _render_back_button(
    label: str = "← Indietro",
    key:   str = "btn_back",
    help:  str = "Torna alla schermata precedente",
) -> bool:
    """
    Renderizza un pulsante ← Indietro piccolo, discreto e allineato a sinistra.
    Uniforme in tutta l'app. Restituisce True se cliccato.
    """
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    return st.button(label, key=key, help=help, type="tertiary")


# ═══════════════════════════════════════════════════════════════════════════════
#  KATEX HTML RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

_RE_MATEMATICA = re.compile(
    r"\$\$.*?\$\$|\$[^$]+?\$|\\\[.*?\\\]|\\\(.*?\\\)", re.DOTALL,
)


def _spec_elenco(spec: str) -> str:
    """
    Da 'a)', '(a)', 'label=\\alph*)', 'A.', 'i)', '1.' … ricava la numerazione di un enumerate
    e restituisce il tag <ol> con prefisso, tipo e suffisso (stessa etichetta del PDF).
    """
    s = (spec or "").strip()
    s = re.sub(r"^label\s*=\s*", "", s)
    s = s.replace("\\textup{", "").replace("\\textbf{", "").replace("}", "")
    m = re.search(r"\\alph\*|\\Alph\*|\\roman\*|\\Roman\*|\\arabic\*|[aAiI1]", s)
    if not m:
        return '<ol class="lt" style="--t:decimal;--p:\'\';--s:\'.\'">'
    tok = m.group(0)
    tipo = {
        "\\alph*": "lower-alpha", "a": "lower-alpha",
        "\\Alph*": "upper-alpha", "A": "upper-alpha",
        "\\roman*": "lower-roman", "i": "lower-roman",
        "\\Roman*": "upper-roman", "I": "upper-roman",
        "\\arabic*": "decimal", "1": "decimal",
    }[tok]
    pre = s[:m.start()].replace("'", "")
    suf = s[m.end():].replace("'", "")
    return f'<ol class="lt" style="--t:{tipo};--p:\'{pre}\';--s:\'{suf}\'">'


def _tabella_html(m) -> str:
    """tabular → <table> (solo il necessario per capire la struttura)."""
    corpo = re.sub(r"\\(?:hline|cline\{[^}]*\})", "", m.group(1))
    righe = [r for r in re.split(r"\\\\", corpo) if r.strip()]
    out = ["<table>"]
    for r in righe:
        celle = "".join(f"<td>{c.strip()}</td>" for c in r.split("&"))
        out.append(f"<tr>{celle}</tr>")
    out.append("</table>")
    return "".join(out)


def _latex_a_html(body: str) -> str:
    """
    LaTeX di un esercizio → HTML per l'anteprima (le formule le disegna KaTeX).
    Le zone matematiche ($…$, \\[…\\], ambienti align…) vengono messe da parte prima di
    toccare il testo e rimesse intatte alla fine: \\frac, \\sqrt, \\mathbb non vanno mai
    trattati come comandi di testo.
    """
    t = body

    # 0. Commenti LaTeX (% … fino a fine riga), ma non \%
    t = re.sub(r"(?<!\\)%[^\n\r]*", "", t)
    t = re.sub(
        r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}",
        '<div class="graph-ph">🖼 Immagine — visibile nel PDF finale</div>',
        t,
    )

    # 1. TikZ → segnaposto
    t = re.sub(
        r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
        '<div class="graph-ph">📊 Grafico — visibile nel PDF finale</div>',
        t, flags=re.DOTALL,
    )
    t = re.sub(r"\\begin\{axis\}.*?\\end\{axis\}", "", t, flags=re.DOTALL)
    t = re.sub(
        r"\\begin\{pgfpicture\}.*?\\end\{pgfpicture\}",
        '<div class="graph-ph">📊 Grafico — visibile nel PDF finale</div>',
        t, flags=re.DOTALL,
    )

    # 2. Matematica: ambienti display → $$…$$, poi tutte le zone messe da parte
    t = re.sub(
        r"\\begin\{(align\*?|equation\*?|gather\*?|multline\*?)\}(.*?)\\end\{\1\}",
        lambda m: "$$" + m.group(2) + "$$", t, flags=re.DOTALL,
    )
    zone: list = []

    def _metti_da_parte(m):
        z = m.group(0)
        if z.startswith("\\["):
            z = "$$" + z[2:-2] + "$$"
        elif z.startswith("\\("):
            z = "$" + z[2:-2] + "$"
        zone.append(z)
        return f"§§M{len(zone) - 1}§§"

    t = _RE_MATEMATICA.sub(_metti_da_parte, t)

    # 3. Liste: la numerazione segue l'etichetta scelta (a), 1., i) …) come nel PDF
    t = re.sub(r"\\begin\{enumerate\}\s*(?:\[([^\]]*)\])?\s*",
               lambda m: _spec_elenco(m.group(1)), t)
    t = re.sub(r"\\end\{enumerate\}", "</ol>", t)
    t = re.sub(r"\\begin\{itemize\}\s*(?:\[[^\]]*\])?\s*", "<ul>", t)
    t = re.sub(r"\\end\{itemize\}", "</ul>", t)
    t = re.sub(r"\\item\[([^\]]+)\]\s*", r'<li class="e"><span class="lbl">\1</span>&ensp;', t)
    t = re.sub(r"\\item\s*", "<li>", t)

    # 4. Tabelle
    t = re.sub(r"\\begin\{tabular\}(?:\{[^}]*\})?(.*?)\\end\{tabular\}", _tabella_html, t,
               flags=re.DOTALL)

    # 4b. \mbox{…} (tiene unita la riga «☐ V ☐ F»): nell'anteprima si toglie, restando il contenuto
    while True:
        _i = t.find("\\mbox{")
        if _i == -1:
            break
        _liv, _j = 0, _i + len("\\mbox")
        for _k in range(_j, len(t)):
            if t[_k] == "{":
                _liv += 1
            elif t[_k] == "}":
                _liv -= 1
                if _liv == 0:
                    t = t[:_i] + t[_j + 1:_k] + t[_k + 1:]
                    break
        else:                       # graffa non chiusa: si toglie solo il comando
            t = t[:_i] + t[_j + 1:]

    # 5. Formattazione testo
    t = re.sub(r"\\textbf\{([^}]*)\}", r"<strong>\1</strong>", t)
    t = re.sub(r"\\textit\{([^}]*)\}", r"<em>\1</em>", t)
    t = re.sub(r"\\emph\{([^}]*)\}", r"<em>\1</em>", t)
    t = re.sub(r"\\underline\{\\hspace\*?\{[^}]*\}\}", '<span class="blank">&nbsp;</span>', t)
    t = re.sub(r"\\underline\{([^}]*)\}", r"<u>\1</u>", t)

    # 6. Spazi e riempitivi
    t = re.sub(r"\\hspace\*?\{[^}]*\}", "&ensp;&ensp;", t)
    t = re.sub(r"\\vspace\*?\{[^}]*\}", "<br>", t)
    t = re.sub(r"\\\\(?:\[[^\]]*\])?", "<br>", t)
    t = re.sub(r"\\newline\b", "<br>", t)

    # 7. Comandi comuni
    t = re.sub(r"\\noindent\s*", "", t)
    t = re.sub(r"\\qquad\b", "&emsp;&emsp;", t)
    t = re.sub(r"\\quad\b", "&emsp;", t)
    t = re.sub(r"\\ldots\b|\\dots\b", "…", t)
    t = re.sub(r"\\newpage\b|\\clearpage\b", "<hr>", t)
    t = re.sub(r"\\medskip\b|\\bigskip\b", "<br>", t)
    t = re.sub(r"\\smallskip\b", "", t)
    t = re.sub(r"\\([%&#_{}])", r"\1", t)          # \% \& \# \_ \{ \} → carattere

    # 8. \begin/\end residui (fuori dalla matematica)
    t = re.sub(r"\\begin\{[^}]*\}", "", t)
    t = re.sub(r"\\end\{[^}]*\}", "", t)

    # 9. Comandi di testo generici con argomento: resta l'argomento
    t = re.sub(r"\\(?:small|large|Large|huge|Huge|normalsize|centering)\b", "", t)
    t = re.sub(r"\\[a-zA-Z]+\*?\{([^}$§]{0,80})\}", r"\1", t)

    # 10. Paragrafi
    t = re.sub(r"\n\n+", "</p><p>", t)
    t = re.sub(r"\n", "<br>", t)
    t = re.sub(r"[ \t]{3,}", " ", t)

    # 11. Rimette le formule al loro posto, intatte (il $ e il resto li gestisce KaTeX)
    t = re.sub(r"§§M(\d+)§§", lambda m: html_lib.escape(zone[int(m.group(1))], quote=False), t)
    return t


def _make_katex_html(title: str, body: str, T: dict) -> str:
    t = _latex_a_html(body)

    safe_title = html_lib.escape(title)
    bg    = T["bg2"]
    card  = T.get("card2", T["bg2"])
    fg    = T["text"]
    fg2   = T["text2"]
    acc   = T["accent"]
    bdr   = T["border"]
    muted = T["muted"]

    katex_css = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"
    katex_js  = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
    render_js = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"

    html_out = (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        "<link rel='stylesheet' href='" + katex_css + "'>"
        "<script src='" + katex_js + "'></script>"
        "<script src='" + render_js + "'></script>"
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{font-family:-apple-system,DM Sans,sans-serif;background:" + bg + ";"
        "color:" + fg + ";font-size:15px;line-height:1.75;padding:4px 0 12px 0}"
        ".t{font-size:.95rem;font-weight:800;color:" + acc + ";padding:8px 14px;"
        "background:" + card + ";border-left:3px solid " + acc + ";"
        "margin-bottom:10px;border-radius:0 6px 6px 0}"
        ".b{padding:2px 10px}"
        "ol,ul{padding-left:1.5em;margin:6px 0}"
        "li{margin:5px 0}"
        "ol.lt{list-style:none;counter-reset:c;padding-left:0}"
        "ol.lt>li{counter-increment:c;position:relative;padding-left:2em}"
        "ol.lt>li::before{content:var(--p) counter(c,var(--t)) var(--s);position:absolute;"
        "left:0;font-weight:700;color:" + acc + "}"
        "ol.lt>li.e{padding-left:0}ol.lt>li.e::before{content:none}"
        "table{border-collapse:collapse;margin:8px 0}"
        "td{border:1px solid " + bdr + ";padding:3px 10px}"
        ".lbl{font-weight:700;color:" + acc + "}"
        ".blank{display:inline-block;border-bottom:1.5px solid " + fg2 + ";"
        "min-width:110px;margin:0 3px}"
        ".graph-ph{background:" + card + ";border:1.5px dashed " + bdr + ";"
        "border-radius:8px;padding:14px;text-align:center;color:" + muted + ";"
        "font-size:.85rem;margin:10px 0}"
        "p{margin:5px 0}"
        "strong{color:" + fg + "}"
        ".katex-display{overflow-x:auto;padding:6px 0}"
        "hr{border:none;border-top:1px solid " + bdr + ";margin:10px 0}"
        "</style></head><body>"
        "<div class='t'>" + safe_title + "</div>"
        "<div class='b'><p>" + t + "</p></div>"
        "<script>"
        "window.addEventListener('load',function(){"
        "renderMathInElement(document.body,{"
        "delimiters:["
        "{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false}"
        "],"
        "throwOnError:false"
        "});"
        "});"
        "</script>"
        "</body></html>"
    )
    return html_out


# ═══════════════════════════════════════════════════════════════════════════════
#  STICKY HEADER  (st_yled con fallback CSS injection)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_sticky_header(T: dict) -> None:
    """
    Header fisso durante lo scroll — mostra logo + step corrente.

    Strategia:
    - Con st_yled installato  → usa st_yled.sticky_header()
    - Senza st_yled           → inietta un div fixed nel parent DOM via
                                window.parent.document (aggiorna senza duplicare).
    """
    stage   = st.session_state.stage
    # L'editor degli esercizi fa parte del secondo passo ("Scarica"): è opzionale.
    _visual = STAGE_FINAL if stage in (STAGE_PREVIEW, STAGE_REVIEW) else stage

    _step_info = {
        STAGE_INPUT: ("01", "Crea",    "⚙️"),
        STAGE_FINAL: ("02", "Scarica", "📥"),
    }
    _num, _label, _icon = _step_info.get(_visual, ("01", "Crea", "⚙️"))

    _bg      = T["card"]
    _border  = T["border"]
    _text    = T["text"]
    _accent  = T["accent"]
    _success = T["success"]
    _muted   = T["muted"]

    _steps_html = ""
    _steps = [
        ("01", "Crea",    STAGE_INPUT),
        ("02", "Scarica", STAGE_FINAL),
    ]
    _completed = {
        STAGE_INPUT: _visual == STAGE_FINAL,
        STAGE_FINAL: False,
    }
    for _i, (_sn, _sl, _ss) in enumerate(_steps):
        _is_active = (_ss == _visual)
        _is_done   = _completed.get(_ss, False)
        if _is_active:
            _cb, _cc, _lc, _lw = _accent, "#fff", _accent, "800"
            _si = _sn
        elif _is_done:
            _cb, _cc, _lc, _lw = _success, "#fff", _success, "700"
            _si = "✓"
        else:
            _cb, _cc, _lc, _lw = _muted + "44", _muted, _muted, "400"
            _si = _sn
        _op = "1" if (_is_active or _is_done) else ".38"
        _steps_html += (
            f'<div style="display:flex;align-items:center;gap:8px;opacity:{_op};">'
            f'<div style="background:{_cb};border-radius:50%;width:28px;height:28px;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:.75rem;font-weight:800;color:{_cc};flex-shrink:0;">{_si}</div>'
            f'<span style="font-size:.92rem;font-weight:{_lw};color:{_lc};'
            f'white-space:nowrap;">{_sl}</span>'
            f'</div>'
        )
        if _i < len(_steps) - 1:
            _sep_c = _success if _is_done else _muted + "44"
            _steps_html += (
                f'<div style="width:28px;height:1.5px;background:{_sep_c};'
                f'border-radius:2px;flex-shrink:0;"></div>'
            )

    _inner_html = (
        f'<div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">'
        f'<span style="font-size:1.15rem;font-weight:900;color:{_text};'
        f'font-family:DM Sans,sans-serif;letter-spacing:-.02em;">'
        f'📝 Verific<span style="color:{_accent};">AI</span>'
        f'</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        + _steps_html +
        f'</div>'
        f'<div style="font-size:.85rem;color:{_muted};font-family:DM Sans,sans-serif;'
        f'flex-shrink:0;display:flex;align-items:center;gap:5px;">'
        f'<span style="background:{_accent}18;color:{_accent};border:1px solid {_accent}33;'
        f'border-radius:6px;padding:3px 11px;font-weight:700;font-size:.82rem;">'
        f'Step {_num}/02'
        f'</span>'
        f'</div>'
    )

    if _STYLED_AVAILABLE:
        try:
            _styl.init()
            _styl.sticky_header(
                f"📝 VerificAI  ·  Step {_num}/02 — {_label}",
                background_color=_bg,
                border_bottom=f"1.5px solid {_border}",
            )
            return
        except Exception:
            pass

    _escaped = _inner_html.replace("`", "\\`").replace("${", "\\${")
    _shadow  = T.get("shadow_md", "0 4px 16px rgba(0,0,0,.20)")
    components.html(f"""
<script>
(function() {{
  var doc = window.parent.document;
  var ID  = '_vai_sticky_hdr';

  var old = doc.getElementById(ID);
  if (old) old.remove();

  var hdr = doc.createElement('div');
  hdr.id  = ID;
  hdr.style.cssText = [
    'position:fixed',
    'top:0',
    'left:0',
    'right:0',
    'z-index:999',
    'background:{_bg}f2',
    'backdrop-filter:blur(14px)',
    '-webkit-backdrop-filter:blur(14px)',
    'border-bottom:1.5px solid {_border}',
    'padding:.75rem 1.8rem .75rem 3.6rem',
    'display:flex',
    'align-items:center',
    'justify-content:space-between',
    'gap:1rem',
    'font-family:DM Sans,sans-serif',
    'box-shadow:{_shadow}',
    'box-sizing:border-box',
    'pointer-events:none',
  ].join(';');

  var inner = doc.createElement('div');
  inner.style.cssText = 'pointer-events:auto;display:flex;align-items:center;justify-content:space-between;gap:1rem;width:100%;';
  inner.innerHTML = `{_escaped}`;
  hdr.appendChild(inner);

  doc.body.insertBefore(hdr, doc.body.firstChild);

  var main = doc.querySelector('.main .block-container');
  if (main) {{
    var cur = parseInt(window.parent.getComputedStyle(main).paddingTop) || 0;
    if (cur < 80) main.style.paddingTop = '78px';
  }}
}})();
</script>
""", height=0)


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP PROGRESS BAR — inline, centrato, visibile su tutte le pagine non-landing
# ═══════════════════════════════════════════════════════════════════════════════

def _render_step_progress(T: dict) -> None:
    """
    Stepper centrato elegante: Crea → Scarica (l'editor è parte del secondo passo).
    Pill-container con SVG checkmark, linee gradient, tipografia fine.
    """
    stage  = st.session_state.stage
    visual = STAGE_FINAL if stage in (STAGE_PREVIEW, STAGE_REVIEW) else stage

    steps = [
        (STAGE_INPUT, "1", "Crea"),
        (STAGE_FINAL, "2", "Scarica"),
    ]
    order = {s: i for i, (s, _, _) in enumerate(steps)}
    cur   = order.get(visual, 0)

    acc   = T["accent"]
    ok    = T["success"]
    muted = T["muted"]
    txt   = T["text"]
    card2 = T.get("card2", T["bg2"])
    bdr2  = T["border2"]

    _chk = (
        '<svg width="14" height="11" viewBox="0 0 11 9" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M1 4.5L4 7.5L10 1" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )

    nodes_html = ""
    for i, (s, num, label) in enumerate(steps):
        is_active = (s == visual)
        is_done   = order.get(s, 0) < cur

        if is_active:
            dot_bg      = acc
            dot_color   = "#fff"
            dot_border  = f"2px solid {acc}"
            dot_shadow  = f"0 0 0 3px {acc}30, 0 2px 10px {acc}40"
            dot_content = f'<span style="font-size:.9rem;font-weight:800;font-family:DM Sans,sans-serif;">{num}</span>'
            lbl_color   = txt
            lbl_weight  = "700"
        elif is_done:
            dot_bg      = ok
            dot_color   = "#fff"
            dot_border  = f"2px solid {ok}"
            dot_shadow  = f"0 0 0 4px {ok}25"
            dot_content = _chk
            lbl_color   = ok
            lbl_weight  = "600"
        else:
            dot_bg      = card2
            dot_color   = muted
            dot_border  = f"1.5px solid {bdr2}"
            dot_shadow  = "none"
            dot_content = f'<span style="font-size:.9rem;font-weight:600;font-family:DM Sans,sans-serif;opacity:.6;">{num}</span>'
            lbl_color   = muted
            lbl_weight  = "500"

        nodes_html += (
            f'<div class="sp-node">'
            f'  <div class="sp-dot" style="background:{dot_bg};color:{dot_color};'
            f'border:{dot_border};box-shadow:{dot_shadow};">{dot_content}</div>'
            f'  <div class="sp-lbl" style="color:{lbl_color};font-weight:{lbl_weight};">{label}</div>'
            f'</div>'
        )

        if i < len(steps) - 1:
            is_filled = cur > i
            line_bg   = f"linear-gradient(90deg, {ok}, {acc})" if is_filled else bdr2
            line_op   = "1" if is_filled else "0.4"
            nodes_html += (
                f'<div class="sp-line" style="background:{line_bg};opacity:{line_op};"></div>'
            )

    html = f"""
<style>
  .sp-track {{
    display: flex; justify-content: center;
    padding: 1rem 0 1.5rem 0;
    background: transparent;
    border-bottom: none;
    margin-bottom: 1.5rem;
    width: 100%;
    align-items: center;
    position: relative;
    left: 50%;
    transform: translateX(-50%);
  }}
  .sp-pill {{
    display: flex; align-items: center; gap: 0;
    background: transparent;
    border-radius: 0px;
    padding: .75rem 1.5rem;
    box-shadow: none;
    width: 100%;
    max-width: 320px;
    margin: 0 auto;
    justify-content: center;
  }}
  .sp-node {{
    display: flex; flex-direction: column;
    align-items: center; gap: 8px;
    position: relative; z-index: 1;
    margin: 0 10px;
    flex: 1;
  }}
  .sp-node:first-child {{ margin-left: 0; }}
  .sp-node:last-child {{ margin-right: 0; }}
  .sp-dot {{
    width: 40px; height: 40px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    transition: box-shadow .3s ease, background .3s ease;
  }}
  .sp-lbl {{
    font-size: .82rem; font-family: 'DM Sans', sans-serif;
    white-space: nowrap; letter-spacing: .02em;
    transition: color .25s;
    text-align: center;
  }}
  .sp-line {{
    height: 1px; width: 60px;
    flex-shrink: 0; border-radius: 1px;
    margin-bottom: 30px;
    background: currentColor;
    transition: opacity .3s ease;
  }}
</style>
<div class="sp-track">
  <div class="sp-pill">
    {nodes_html}
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)





def render_privacy(T: dict, contatto_url: str) -> None:
    """Pagina pubblica «Informativa sulla privacy» (si apre con ?pagina=privacy, senza accedere)."""
    from config import LEGALE as _LEG
    st.markdown(
        f'<div style="max-width:760px;margin:0 auto;font-family:DM Sans,sans-serif;'
        f'color:{T["text"]};line-height:1.6;">'
        f'<h1 style="font-size:1.9rem;font-weight:800;margin:1rem 0 .2rem;">Informativa sulla privacy</h1>'
        f'<div style="color:{T["muted"]};font-size:.9rem;margin-bottom:1.5rem;">'
        f'VerificAI · ultimo aggiornamento: 15 ottobre 2026</div></div>',
        unsafe_allow_html=True,
    )
    from config import PREZZI_VISIBILI as _MON
    # I fornitori dei pagamenti compaiono solo quando i pagamenti esistono
    _ACQUISTO = ("- **Acquisto del piano Pro:** il pagamento è gestito da Lemon Squeezy, che ti vende il piano. Noi **non vediamo né conserviamo i dati della tua carta**:\n"
                 "  riceviamo solo l'esito, il codice di licenza e la sua scadenza, che salviamo insieme al tuo account.\n") if _MON else ""
    _LEMON = "- **Lemon Squeezy:** pagamenti, imposte e fatture del piano Pro, e verifica del codice di licenza.\n" if _MON else ""
    _c1, _c2, _c3 = st.columns([1, 6, 1])
    with _c2:
        st.markdown(f"""
**Chi siamo.** VerificAI è un servizio web per docenti che genera verifiche scolastiche con l'aiuto
dell'intelligenza artificiale. Il servizio è gestito da Giacomo Saragoni. Per qualsiasi richiesta
sui tuoi dati puoi scriverci a **{_LEG['email']}**.

### Quali dati trattiamo
- **Account:** l'indirizzo email con cui ti registri. Se accedi con Google riceviamo da Google
  la tua email e il nome del profilo; non accediamo a Gmail, Drive o altri dati del tuo account Google.
- **Contenuti che crei:** materia, tipo di scuola, argomento e istruzioni che scrivi, le verifiche generate
  e il loro storico.
- **File che carichi** (appunti, verifiche, fogli di esercizi): vengono usati solo per generare la verifica richiesta.
- **Dati d'uso:** il numero di verifiche create nel mese e le preferenze che salvi (per esempio materia e scuola abituali).
{_ACQUISTO}- **Segnalazioni anonime:** se usi «Qualcosa non va in questa verifica?» salviamo quello che scrivi e, se lasci la spunta,
  il testo della verifica e i dettagli tecnici della generazione. **Non** salviamo il tuo nome, la tua email né il tuo indirizzo IP.

### Come usiamo i dati che riceviamo da Google
I dati dell'accesso con Google (email, nome e foto del profilo) li usiamo **soltanto** per creare il tuo account, farti accedere
e mostrarti il tuo nome nell'applicazione. Non li usiamo per pubblicità, non li vendiamo, non li cediamo a terzi e non li usiamo per
addestrare modelli di intelligenza artificiale; sono condivisi solo con il fornitore che gestisce l'autenticazione per nostro conto (Supabase).
L'uso e il trasferimento a qualsiasi altra app delle informazioni ricevute dalle API di Google da parte di VerificAI rispetteranno la
Google API Services User Data Policy, inclusi i requisiti di Uso limitato (*Limited Use*).

### Perché li trattiamo
Per farti accedere, generare le verifiche, mostrarti lo storico, applicare i limiti del piano e
migliorare il servizio. Non vendiamo i tuoi dati e non li usiamo per pubblicità.

### Con chi li condividiamo
Usiamo fornitori che trattano i dati per nostro conto:
- **Supabase:** autenticazione, database e salvataggio dello storico.
- **Google:** accesso con Google e Gemini, il modello di intelligenza artificiale che riceve l'argomento,
  le istruzioni e gli eventuali file per generare la verifica.
- **Streamlit Community Cloud:** hosting dell'applicazione.
{_LEMON}
### Consiglio importante
Non inserire nelle richieste o nei file dati personali degli studenti (nomi, voti, valutazioni individuali).
Per generare una verifica non servono.

### Conservazione e cancellazione
Conserviamo i dati finché il tuo account è attivo. Puoi eliminare le singole verifiche dal tuo storico
e puoi chiederci in qualsiasi momento di cancellare l'account e tutti i dati collegati.

### I tuoi diritti
Hai diritto di chiedere accesso, rettifica, cancellazione, limitazione o portabilità dei tuoi dati
e di opporti al loro trattamento. Per esercitarli scrivi a **{_LEG['email']}**.
Puoi anche rivolgerti al Garante per la protezione dei dati personali (garanteprivacy.it).
""")
