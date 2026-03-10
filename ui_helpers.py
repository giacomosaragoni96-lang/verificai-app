# ── ui_helpers.py — VerificAI UI rendering helpers ───────────────────────────
# Funzioni di rendering UI estratte da main.py per ridurne la densità.
# Ogni funzione accetta T (tema dict) come parametro esplicito per garantire
# coerenza visiva e testabilità indipendente dal contesto globale.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import html as html_lib
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
    _col, _spacer = st.columns([1, 4])
    with _col:
        st.markdown('<div class="btn-back-discrete">', unsafe_allow_html=True)
        clicked = st.button(label, key=key, use_container_width=True, help=help)
        st.markdown('</div>', unsafe_allow_html=True)
    return clicked


# ═══════════════════════════════════════════════════════════════════════════════
#  KATEX HTML RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def _make_katex_html(title: str, body: str, T: dict, height_hint: int = 400) -> str:
    t = body

    # 0. Rimuovi commenti LaTeX (% ... fino a fine riga)
    t = re.sub(r'(?<![%])%[^\n\r]*', '', t)
    t = re.sub(
        r'\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}',
        '<div class="graph-ph">🖼 Immagine — visibile nel PDF finale</div>',
        t,
    )

    # 1. TikZ → placeholder
    t = re.sub(
        r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
        '<div class="graph-ph">📊 Grafico TikZ — visibile nel PDF finale</div>',
        t, flags=re.DOTALL,
    )
    t = re.sub(r"\\begin\{axis\}.*?\\end\{axis\}", "", t, flags=re.DOTALL)
    t = re.sub(
        r"\\begin\{pgfpicture\}.*?\\end\{pgfpicture\}",
        '<div class="graph-ph">📊 Grafico pgf — visibile nel PDF finale</div>',
        t, flags=re.DOTALL,
    )

    # 2. Display math \[...\] → $$...$$
    t = re.sub(r"\\\[(.*?)\\\]", r"$$\1$$", t, flags=re.DOTALL)
    t = re.sub(
        r"\\begin\{(align\*?|equation\*?|gather\*?|multline\*?)\}(.*?)\\end\{\1\}",
        r"$$\2$$", t, flags=re.DOTALL,
    )

    # 3. Liste
    t = re.sub(r"\\begin\{enumerate\}(\[[^\]]*\])?\s*", "<ol>", t)
    t = re.sub(r"\\end\{enumerate\}", "</ol>", t)
    t = re.sub(r"\\begin\{itemize\}\s*", "<ul>", t)
    t = re.sub(r"\\end\{itemize\}", "</ul>", t)
    t = re.sub(r"\\item\[([^\]]+)\]\s*", r'<li><span class="lbl">\1</span>&ensp;', t)
    t = re.sub(r"\\item\s*", "<li>", t)

    # 4. Formattazione testo
    t = re.sub(r"\\textbf\{([^}]*)\}", r"<strong>\1</strong>", t)
    t = re.sub(r"\\textit\{([^}]*)\}", r"<em>\1</em>", t)
    t = re.sub(r"\\emph\{([^}]*)\}", r"<em>\1</em>", t)
    t = re.sub(r"\\underline\{([^}]*)\}", r"<u>\1</u>", t)

    # 5. Spazi e riempitivi
    t = re.sub(
        r"\\underline\{\\hspace\{[^}]*\}\}",
        '<span class="blank">___________</span>',
        t,
    )
    t = re.sub(r"\\hspace\*?\{[^}]*\}", "&ensp;&ensp;", t)
    t = re.sub(r"\\vspace\*?\{[^}]*\}", "<br>", t)
    t = re.sub(r"\\\\", "<br>", t)
    t = re.sub(r"\\newline\b", "<br>", t)

    # 6. Comandi comuni
    t = re.sub(r"\\noindent\s*", "", t)
    t = re.sub(r"\\quad\b", "&emsp;", t)
    t = re.sub(r"\\qquad\b", "&emsp;&emsp;", t)
    t = re.sub(r"\\ldots\b|\\dots\b", "…", t)
    t = re.sub(r"\\newpage\b|\\clearpage\b", "<hr>", t)
    t = re.sub(r"\\medskip\b|\\bigskip\b", "<br>", t)
    t = re.sub(r"\\smallskip\b", "", t)

    # 7. Rimuovi \begin/\end non-math residui
    math_envs = r"(math|equation|align|gather|multline|pmatrix|bmatrix|vmatrix|cases)"
    t = re.sub(r"\\begin\{(?!" + math_envs + r")[^}]*\}", "", t)
    t = re.sub(r"\\end\{(?!"  + math_envs + r")[^}]*\}", "", t)

    # 8. Comandi LaTeX generici con argomento
    t = re.sub(r"\\(?:small|large|Large|huge|Huge|normalsize|centering)\b", "", t)
    t = re.sub(r"\\[a-zA-Z]+\*?\{([^}$]{0,80})\}", r"\1", t)

    # 9. Paragrafi
    t = re.sub(r"\n\n+", "</p><p>", t)
    t = t.replace("\n", " ")
    t = re.sub(r"\s{3,}", " ", t)

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
    _visual = STAGE_REVIEW if stage == STAGE_PREVIEW else stage

    _step_info = {
        STAGE_INPUT:  ("01", "Impostazioni", "⚙️"),
        STAGE_REVIEW: ("02", "Revisiona",    "✏️"),
        STAGE_FINAL:  ("03", "Scarica",      "📥"),
    }
    _num, _label, _icon = _step_info.get(_visual, ("01", "Impostazioni", "⚙️"))

    _bg      = T["card"]
    _border  = T["border"]
    _text    = T["text"]
    _accent  = T["accent"]
    _success = T["success"]
    _muted   = T["muted"]

    _steps_html = ""
    _steps = [
        ("01", "Impostazioni", STAGE_INPUT),
        ("02", "Revisiona",    STAGE_REVIEW),
        ("03", "Scarica",      STAGE_FINAL),
    ]
    _completed = {
        STAGE_INPUT:  _visual in (STAGE_REVIEW, STAGE_FINAL),
        STAGE_REVIEW: _visual == STAGE_FINAL,
        STAGE_FINAL:  False,
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
        f'Step {_num}/03'
        f'</span>'
        f'</div>'
    )

    if _STYLED_AVAILABLE:
        try:
            _styl.init()
            _styl.sticky_header(
                f"📝 VerificAI  ·  Step {_num}/03 — {_label}",
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
    Stepper centrato elegante: Impostazioni → Revisiona → Scarica.
    Pill-container con SVG checkmark, linee gradient, tipografia fine.
    """
    stage  = st.session_state.stage
    visual = STAGE_REVIEW if stage == STAGE_PREVIEW else stage

    steps = [
        (STAGE_INPUT,  "1", "Impostazioni"),
        (STAGE_REVIEW, "2", "Revisiona"),
        (STAGE_FINAL,  "3", "Scarica"),
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
            nodes_html += (
                f'<div class="sp-line" style="background:{line_bg};"></div>'
            )

    html = f"""
<style>
  .sp-track {{
    display: flex; justify-content: center;
    padding: 1rem 0 1.5rem 0;
    background: {card2};
    border-bottom: 1px solid {bdr2};
    margin-bottom: 1.5rem;
  }}
  .sp-pill {{
    display: flex; align-items: center; gap: 0;
    background: {card2};
    border-radius: 100px;
    padding: .75rem 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,.06);
  }}
  .sp-node {{
    display: flex; flex-direction: column;
    align-items: center; gap: 8px;
    position: relative; z-index: 1;
  }}
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
  }}
  .sp-line {{
    height: 2px; width: 72px;
    flex-shrink: 0; border-radius: 2px;
    margin-bottom: 30px;
    opacity: .7;
  }}
</style>
<div class="sp-track">
  <div class="sp-pill">
    {nodes_html}
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SPLIT DOWNLOAD BUTTON  (st_yled con fallback st.popover nativo)
# ═══════════════════════════════════════════════════════════════════════════════

def _split_download_button(
    label:           str,
    data:            bytes,
    file_name:       str,
    mime:            str,
    key:             str,
    extra_downloads: list | None = None,
    T:               dict | None = None,
) -> None:
    """
    Bottone download principale con dropdown opzioni secondarie.

    Layout:
    ┌──────────────────────────────────────┬────┐
    │  📄 Scarica PDF Fila A  ·  340 KB   │  ⋮ │
    └──────────────────────────────────────┴────┘
                                            ↓
                                    📝 Scarica DOCX (Word)
                                    📄 Scarica sorgente .tex

    Con st_yled: usa split_button() per il trigger.
    Senza st_yled: usa st.columns([10,1]) + st.popover("⋮") nativo.
    """
    T = T or {}
    extra_downloads = extra_downloads or []

    if _STYLED_AVAILABLE and extra_downloads:
        try:
            _action_labels = [d["label"] for d in extra_downloads]
            _styl.init()
            _clicked = _styl.split_button(
                primary_label=label,
                actions=_action_labels,
            )
            st.download_button(
                label=label,
                data=data,
                file_name=file_name,
                mime=mime,
                use_container_width=True,
                key=key + "_dl",
            )
            if _clicked and _clicked in _action_labels:
                _idx = _action_labels.index(_clicked)
                _dl  = extra_downloads[_idx]
                st.download_button(
                    label=_dl["label"],
                    data=_dl["data"],
                    file_name=_dl["file_name"],
                    mime=_dl["mime"],
                    use_container_width=True,
                    key=_dl["key"],
                )
            return
        except Exception:
            pass

    if extra_downloads:
        _c_main, _c_pop = st.columns([11, 1], gap="small")
        with _c_main:
            st.download_button(
                label=label,
                data=data,
                file_name=file_name,
                mime=mime,
                use_container_width=True,
                key=key,
            )
        with _c_pop:
            st.markdown(
                '<div class="btn-outline-accent-marker" style="display:none;height:0;line-height:0"></div>',
                unsafe_allow_html=True,
            )
            with st.popover("⋮", use_container_width=True):
                _muted = T.get("muted", "#9CA3AF")
                st.markdown(
                    f'<div style="font-size:.72rem;font-weight:700;'
                    f'color:{_muted};text-transform:uppercase;'
                    f'letter-spacing:.06em;margin-bottom:.5rem;'
                    f'font-family:DM Sans,sans-serif;">Altri formati</div>',
                    unsafe_allow_html=True,
                )
                for _dl in extra_downloads:
                    if _dl.get("data"):
                        st.download_button(
                            label=_dl["label"],
                            data=_dl["data"],
                            file_name=_dl["file_name"],
                            mime=_dl["mime"],
                            use_container_width=True,
                            key=_dl["key"],
                        )
                    else:
                        st.markdown(
                            f'<div style="font-size:.74rem;color:{_muted};'
                            f'font-family:DM Sans,sans-serif;padding:.2rem 0;">'
                            f'{_dl["label"]} — <em>non disponibile</em></div>',
                            unsafe_allow_html=True,
                        )
    else:
        st.download_button(
            label=label,
            data=data,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
            key=key,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  BREADCRUMB
# ═══════════════════════════════════════════════════════════════════════════════

def _render_breadcrumb(T: dict) -> None:
    stage = st.session_state.stage
    steps = [
        ("01", "Impostazioni", STAGE_INPUT),
        ("02", "Revisione",    STAGE_REVIEW),
        ("03", "Scarica",      STAGE_FINAL),
    ]
    _visual_stage = STAGE_REVIEW if stage == STAGE_PREVIEW else stage
    completed = {
        STAGE_INPUT:  _visual_stage in (STAGE_REVIEW, STAGE_FINAL),
        STAGE_REVIEW: _visual_stage == STAGE_FINAL,
        STAGE_FINAL:  False,
    }

    html = (
        '<div class="breadcrumb-wrap">'
        '<div class="breadcrumb-pill" style="display:inline-flex;align-items:center;gap:10px;'
        'padding:.7rem 1.6rem;'
        'background:' + T["card"] + ';border:1.5px solid ' + T["border"] + ';'
        'border-radius:100px;box-shadow:' + T.get("shadow_md", "0 4px 20px rgba(0,0,0,.08)") + ';">'
    )
    for i, (num, label, s) in enumerate(steps):
        is_active = s == _visual_stage
        is_done   = completed.get(s, False)
        if is_active:
            cb, cc, lc, lw = T["accent"], "#fff", T["accent"], "800"
            icon = num
        elif is_done:
            cb, cc, lc, lw = T["success"], "#fff", T["success"], "700"
            icon = "✓"
        else:
            cb, cc, lc, lw = T["border2"], T["muted"], T["muted"], "500"
            icon = num
        _op = "1" if (is_active or is_done) else ".4"
        html += (
            '<div style="display:flex;align-items:center;gap:7px;opacity:' + _op + ';">'
            '<div style="background:' + cb + ';border-radius:50%;'
            'width:28px;height:28px;display:flex;align-items:center;'
            'justify-content:center;font-size:.72rem;font-weight:800;'
            'color:' + cc + ';flex-shrink:0;box-shadow:0 2px 8px ' + cb + '44;">' + icon + '</div>'
            '<span style="font-size:.88rem;font-weight:' + lw + ';color:' + lc + ';'
            'font-family:DM Sans,sans-serif;white-space:nowrap;letter-spacing:-.01em;">' + label + '</span>'
            '</div>'
        )
        if i < len(steps) - 1:
            _sep_c = T["success"] if is_done else T["border2"]
            html += (
                '<div style="width:28px;height:1.5px;background:' + _sep_c + ';'
                'opacity:.4;flex-shrink:0;border-radius:2px;"></div>'
            )
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)
