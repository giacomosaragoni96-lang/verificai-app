def get_css(T: dict) -> str:
    """
    Restituisce il CSS dell'app adattato dinamicamente al tema T.
    Tutti i colori vengono estratti dal dizionario T passato come argomento.

    DESIGN SYSTEM v2 — Principi:
    • Gerarchia visiva con accenti di colore mirati (no "tutto bianco" / "tutto nero")
    • Font grandi e leggibili per docenti non tecnici
    • Effetti di caricamento professionali
    • Linguaggio non tecnico (hint, label)
    """
    _SB_ACCENT = T.get("sidebar_accent", "#3B82F6")  # Blu più vivido
    _SB_BG_CSS = T.get("sidebar_bg", "linear-gradient(180deg, #1E293B 0%, #0F172A 100%)")  # Grigio scuro più contrasto
    _SB_BORDER = T.get("sidebar_border", "#475569")  # Grigio medio per bordi più visibili
    _SB_INPUT_BG   = T.get("sidebar_input_bg", "#334155")  # Input più scuri per contrasto
    _SB_INPUT_TEXT = T.get("sidebar_input_text", "#F8FAFC")  # Bianco quasi puro
    # La sidebar ha sempre sfondo scuro → i colori testo DEVONO essere chiari
    # indipendentemente dal tema principale (chiaro/scuro).
    _SB_TEXT   = _SB_INPUT_TEXT
    _SB_MUTED  = "#CBD5E1"   # Grigio chiaro per label (più visibile)

    _is_light = _is_light_color(T["bg"])

    # ── Design System — Accent tokens ─────────────────────────────────────────
    _acc  = T["accent"]
    _acc2 = T.get("accent2", _acc)
    _acc_soft = _acc + "14"     # hover/fill molto leggero
    _acc_med  = _acc + "30"     # border, separatori
    _acc_ring = _acc + "40"     # focus ring
    _acc_glow = _acc + "22"     # ombra glow sui bottoni primari

    # ── Surface elevation tokens ───────────────────────────────────────────────
    _surf_raised  = T.get("card", T["bg2"])
    _surf_overlay = T.get("card2", T["bg2"])

    # ── Design system — radius scale ───────────────────────────────────────────
    _radius_sm = T.get("radius_sm", "8px")
    _radius_md = T.get("radius_md", "12px")
    _radius_lg = T.get("radius_lg", "16px")

    # ── Shadow scale (morbida, elegante su temi chiari e scuri) ───────────────
    _shadow_xs   = T.get("shadow", "0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04)")
    _shadow_sm   = "0 2px 8px rgba(0,0,0,.07), 0 1px 3px rgba(0,0,0,.04)"
    _shadow_md   = T.get("shadow_md", "0 4px 16px rgba(0,0,0,.08), 0 2px 6px rgba(0,0,0,.04)")
    _shadow_soft = T.get("shadow_soft", "0 8px 32px rgba(0,0,0,.08), 0 2px 8px rgba(0,0,0,.04)")
    _shadow_lg   = "0 16px 48px rgba(0,0,0,.10), 0 4px 16px rgba(0,0,0,.06)"

    # ── Primary button text color ─────────────────────────────────────────────
    # Su temi chiari l'accent è spesso scuro (teal, forest green) → testo bianco.
    # Se l'accent è chiaro (es. light yellow) usare testo scuro.
    _btn_text = "#ffffff" if not _is_light_color(_acc) else T["text"]

    # ── Placeholder e color-scheme ─────────────────────────────────────────────
    _placeholder_color = T.get("muted", "#6E7681")
    _color_scheme = "light" if _is_light else "dark"

    # ── Expander header APERTO — adattivo chiaro/scuro ─────────────────────────
    # Su temi scuri: gradiente accent scuro + testo bianco (come prima)
    # Su temi chiari: sfondo accent_light (tinta chiarissima) + testo accent scuro
    _acc_light_tint = T.get("accent_light", "#E0F2FE")
    if _is_light:
        # Sfondo SOLIDO (nessuna trasparenza) per evitare bleeding del dark bg di Streamlit
        _exp_open_bg    = _acc_light_tint
        _exp_open_text  = _acc
        _exp_open_border = f"1px solid {_acc}44"
    else:
        _exp_open_bg    = f"linear-gradient(135deg, {_acc}dd 0%, {_acc} 60%, {T.get('accent2', _acc)}cc 100%)"
        _exp_open_text  = "#ffffff"
        _exp_open_border = "none"

    # ── Transition standard ────────────────────────────────────────────────────
    _transition = "0.2s cubic-bezier(.4,0,.2,1)"

    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; }}

  /* ════════════════════════════════════════════════════════════════════════
     SIDEBAR — z-index superiore allo sticky header (che ora è 999)
     Il toggle sidebar deve sempre essere cliccabile
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stSidebar"],
  [data-testid="stSidebar"] *,
  [data-testid="stSidebar"] > div,
  [data-testid="stSidebar"] > div > div,
  [data-testid="stSidebar"] .element-container,
  [data-testid="stSidebar"] .stVerticalBlock,
  [data-testid="stSidebar"] .stVerticalBlock > div,
  [data-testid="stSidebar"] .stVerticalBlock > div > div,
  [data-testid="stSidebar"] div,
  [data-testid="stSidebar"] section,
  [data-testid="stSidebar"] article {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
  }},
  section[data-testid="stSidebar"] {{
    z-index: 1100 !important;
  }}
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="stSidebarCollapseButton"],
  button[aria-label="Open sidebar"],
  button[aria-label="Collapse sidebar"],
  [class*="collapsedControl"] {{
    z-index: 1200 !important;
    position: relative !important;
  }}

  /* ── Global typography ── */
  .stApp p,
  .stApp li,
  .stApp label,
  .stApp [data-testid="stMarkdownContainer"] p,
  .stApp [data-testid="stMarkdownContainer"] li {{
    font-size: 1rem !important;
    line-height: 1.65 !important;
    font-family: 'DM Sans', sans-serif !important;
    color: {T['text']} !important;
  }}

  .stApp {{
    background-color: {T['bg']} !important;
    font-family: 'DM Sans', sans-serif;
    font-size: 16px;
    color: {T['text']};
    transition: background-color {_transition}, color {_transition};
  }}

  /* Breathing room: pagina larga e centrata */
  .main .block-container {{
    padding-top: 1.6rem !important;
    padding-bottom: 3rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1440px !important;
    margin: 0 auto !important;
  }}

  /* ── Streamlit CSS custom properties override (previene dark bleed) ── */
  .stApp,
  .stApp * {{
    --background-color: {T['bg']} !important;
    --secondary-background-color: {T['bg2']} !important;
    --text-color: {T['text']} !important;
  }}

  /* ── Typographic hierarchy — heading scale elegante ── */
  .stApp h1, .stMarkdown h1 {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: clamp(1.75rem, 3vw, 2.25rem) !important;
    font-weight: 900 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.15 !important;
    color: {T['text']} !important;
    margin-bottom: .5rem !important;
  }}
  .stApp h2, .stMarkdown h2 {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: clamp(1.35rem, 2.5vw, 1.7rem) !important;
    font-weight: 800 !important;
    letter-spacing: -0.025em !important;
    line-height: 1.2 !important;
    color: {T['text']} !important;
    margin-bottom: .4rem !important;
  }}
  .stApp h3, .stMarkdown h3 {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em !important;
    color: {T['text']} !important;
    margin-bottom: .3rem !important;
  }}
  .stApp h4, .stMarkdown h4 {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    color: {T['text2']} !important;
    text-transform: uppercase !important;
    letter-spacing: .06em !important;
  }}

  /* ══════════════════════════════════════════════════════════════════════════
     EXPANDER — Override completo dark-bleed. Strategia:
     1. CSS vars su :root (Streamlit le legge da qui)
     2. Prefisso html body .stApp per specificità massima
     3. Ogni proprietà con !important doppio livello
     ══════════════════════════════════════════════════════════════════════════ */

  /* 1. Contenitore details */
  html body .stApp details[data-testid="stExpander"],
  html .stApp details[data-testid="stExpander"],
  .stApp details[data-testid="stExpander"] {{
    color-scheme: {_color_scheme} !important;
    --background-color: {_surf_raised} !important;
    background: {_surf_raised} !important;
    background-color: {_surf_raised} !important;
    border: 2px solid {T['border2']} !important;
    border-radius: {_radius_lg} !important;
    overflow: hidden !important;
    margin-bottom: .5rem !important;
  }}

  /* 2. Summary CHIUSO */
  html body .stApp details[data-testid="stExpander"] > summary,
  html body .stApp details[data-testid="stExpander"] summary[role="button"],
  .stApp details[data-testid="stExpander"] > summary {{
    color-scheme: {_color_scheme} !important;
    background: {_surf_raised} !important;
    background-color: {_surf_raised} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.97rem !important;
    font-weight: 700 !important;
    padding: .85rem 1.1rem !important;
    border-radius: 12px !important;
  }}
  html body .stApp details[data-testid="stExpander"] > summary > *,
  html body .stApp details[data-testid="stExpander"] summary[role="button"] > *,
  .stApp details[data-testid="stExpander"] > summary div,
  .stApp details[data-testid="stExpander"] > summary p,
  .stApp details[data-testid="stExpander"] > summary span {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    background: transparent !important;
    background-color: transparent !important;
  }}

  /* 3. Freccia SVG chiuso */
  html body .stApp details[data-testid="stExpander"]:not([open]) > summary svg,
  html body .stApp details[data-testid="stExpander"]:not([open]) > summary svg * {{
    fill: {T['text2']} !important;
    stroke: {T['text2']} !important;
  }}

  /* 4. Summary hover chiuso */
  html body .stApp details[data-testid="stExpander"]:not([open]) > summary:hover,
  .stApp details[data-testid="stExpander"]:not([open]) > summary:hover {{
    background: {T['hover']} !important;
    background-color: {T['hover']} !important;
    color: {_acc} !important;
    -webkit-text-fill-color: {_acc} !important;
  }}

  /* 5. Summary APERTO — adattivo chiaro/scuro
     Copre entrambe le strutture DOM Streamlit:
     A) details[data-testid="stExpander"][open] (Streamlit ≤ 1.32)
     B) div[data-testid="stExpander"] > details[open] (Streamlit ≥ 1.33+) */
  html body .stApp details[data-testid="stExpander"][open] > summary,
  html body .stApp details[data-testid="stExpander"][open] summary[role="button"],
  .stApp details[data-testid="stExpander"][open] > summary,
  html body .stApp [data-testid="stExpander"] details[open] > summary,
  html body .stApp [data-testid="stExpander"] details[open] summary[role="button"],
  .stApp [data-testid="stExpander"] details[open] > summary {{
    background: {_exp_open_bg} !important;
    background-color: {_exp_open_bg} !important;
    color: {_exp_open_text} !important;
    -webkit-text-fill-color: {_exp_open_text} !important;
    border-radius: 12px 12px 0 0 !important;
    border-bottom: {_exp_open_border} !important;
    color-scheme: {_color_scheme} !important;
  }}
  html body .stApp details[data-testid="stExpander"][open] > summary *,
  .stApp details[data-testid="stExpander"][open] > summary *,
  html body .stApp [data-testid="stExpander"] details[open] > summary *,
  .stApp [data-testid="stExpander"] details[open] > summary * {{
    color: {_exp_open_text} !important;
    -webkit-text-fill-color: {_exp_open_text} !important;
    background: transparent !important;
    background-color: transparent !important;
  }}
  html body .stApp details[data-testid="stExpander"][open] > summary svg *,
  html body .stApp [data-testid="stExpander"] details[open] > summary svg * {{
    fill: {_exp_open_text} !important;
    stroke: {_exp_open_text} !important;
    background: transparent !important;
  }}

  /* 6. CONTENT AREA — la causa principale del nero */
  html body .stApp details[data-testid="stExpander"] > div,
  html body .stApp details[data-testid="stExpander"] > div[data-testid="stExpanderDetails"],
  html body .stApp details[data-testid="stExpander"] > section,
  .stApp details[data-testid="stExpander"] > div {{
    color-scheme: {_color_scheme} !important;
    --background-color: {_surf_raised} !important;
    background: {_surf_raised} !important;
    background-color: {_surf_raised} !important;
    padding: 1.1rem 1.2rem 1.3rem !important;
    border-radius: 0 0 12px 12px !important;
  }}

  /* 7. Tutto il testo dentro content area */
  html body .stApp details[data-testid="stExpander"] > div p,
  html body .stApp details[data-testid="stExpander"] > div label,
  html body .stApp details[data-testid="stExpander"] > div span:not(.site-header-ai),
  html body .stApp details[data-testid="stExpander"] > div small,
  html body .stApp details[data-testid="stExpander"] > div div[class*="label"] {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
  }}
  /* color-scheme su tutti i child */
  html body .stApp details[data-testid="stExpander"] > div * {{
    color-scheme: {_color_scheme} !important;
  }}

  .block-container {{
    max-width: 1440px !important;
  }}


  /* ════════════════════════════════════════════════════════════════════════
     ALERTS / TOAST — success, error, warning (feedback visivo)
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stAlert"] {{
    border-radius: {_radius_md} !important;
    border: 1px solid {T['border']} !important;
    box-shadow: {T.get('shadow', '0 1px 3px rgba(0,0,0,.08)')} !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: .9rem 1.1rem .9rem 1.4rem !important;
    transition: box-shadow .2s ease, transform .15s ease !important;
  }}
  [data-testid="stAlert"]:has([data-baseweb="notification"][kind="positive"]) {{
    border-left: 5px solid {T['success']} !important;
    background: {T['success']}12 !important;
  }}
  [data-testid="stAlert"]:has([data-baseweb="notification"][kind="negative"]) {{
    border-left: 5px solid {T['error']} !important;
    background: {T['error']}10 !important;
  }}
  [data-testid="stAlert"]:has([data-baseweb="notification"][kind="warning"]) {{
    border-left: 5px solid {T['warn']} !important;
    background: {T['warn']}10 !important;
  }}
  [data-testid="stAlert"] [data-baseweb="notification"] {{
    background: transparent !important;
    border: none !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     SPINNER — caricamento (micro-interazione, colore tema)
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stSpinner"] {{
    color: {_acc} !important;
  }}
  [data-testid="stSpinner"] > div {{
    border-color: {_acc}33 !important;
    border-top-color: {_acc} !important;
    animation-duration: 0.9s !important;
  }}
  [data-testid="stSpinner"] + div {{
    color: {T['text2']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
  }}

  #MainMenu, footer {{ visibility: hidden; }}
  .stDecoration {{ display: none; }}

  header[data-testid="stHeader"] {{
    background-color: {T['bg']}ee !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid {T['border']} !important;
  }}

  header button svg {{
    fill: {T['text']} !important;
    color: {T['text']} !important;
    stroke: {T['text']} !important;
  }}
  header button {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 8px !important;
    color: {T['text']} !important;
  }}
  header button:hover {{
    background: {T['hover']} !important;
    border-color: {_acc} !important;
  }}
  header button:hover svg {{
    fill: {_acc} !important;
  }}
  .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a {{ display: none !important; }}

  /* ════════════════════════════════════════════════════════════════════════
     SIDEBAR — Elegant, theme-aware (dark panel per tutti i temi)
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stSidebar"] {{
    background: {_SB_BG_CSS} !important;
    border-right: 1px solid {_SB_BORDER} !important;
    box-shadow: 4px 0 32px rgba(0,0,0,.14) !important;
  }}
  .sidebar-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: .95rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    color: {_SB_TEXT} !important;
    margin: 0 0 1.2rem 0;
    padding: .6rem 0 .8rem 0;
    border-bottom: 1px solid {_SB_BORDER};
    display: flex;
    align-items: center;
    gap: 7px;
  }}
  [data-testid="stSidebar"] .block-container {{
    padding: 1.4rem 1.1rem !important;
    max-width: 100% !important;
  }}
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stTextInput label p,
  [data-testid="stSidebar"] .stSelectbox label p,
  [data-testid="stSidebar"] .stNumberInput label p {{
    color: {_SB_MUTED} !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
  }}
  [data-testid="stSidebar"] .stCheckbox label {{
    color: {_SB_TEXT} !important;
    font-size: 0.9rem !important;
  }}
  [data-testid="stSidebar"] .stTextInput input,
  [data-testid="stSidebar"] .stNumberInput input {{
    background: {_SB_INPUT_BG} !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 10px !important;
    color: {_SB_INPUT_TEXT} !important;
    font-size: 0.9rem !important;
    padding: 10px 12px !important;
    transition: border-color {_transition}, box-shadow {_transition} !important;
  }}
  [data-testid="stSidebar"] .stTextInput input:focus,
  [data-testid="stSidebar"] .stNumberInput input:focus {{
    border-color: {_SB_ACCENT} !important;
    box-shadow: 0 0 0 3px {_SB_ACCENT}30 !important;
    outline: none !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: {_SB_INPUT_BG} !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 10px !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
    color: {_SB_INPUT_TEXT} !important;
    font-size: 0.88rem !important;
  }}
  [data-testid="stSidebar"] .stRadio label,
  [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stButton button {{
    background: {_SB_INPUT_BG} !important;
    background-color: {_SB_INPUT_BG} !important;
    color: {_SB_INPUT_TEXT} !important;
    -webkit-text-fill-color: {_SB_INPUT_TEXT} !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    min-height: 34px !important;
    padding: .3rem .6rem !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    transition: border-color .2s ease, background .2s ease !important;
  }}
  [data-testid="stSidebar"] .stButton button:hover {{
    border-color: {_SB_ACCENT} !important;
    color: {_SB_INPUT_TEXT} !important;
    -webkit-text-fill-color: {_SB_INPUT_TEXT} !important;
    background: {_SB_BORDER} !important;
    background-color: {_SB_BORDER} !important;
  }}
  [data-testid="stSidebar"] .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .section-label {{
    color: {_SB_MUTED} !important;
    border-bottom-color: {_SB_BORDER} !important;
  }}

  /* Sidebar toggle button */
  [data-testid="collapsedControl"] {{
    top: 0.75rem !important;
    left: 0.75rem !important;
  }}
  [data-testid="collapsedControl"] button {{
    background: {T['card']} !important;
    border: 2px solid {_acc} !important;
    border-radius: 10px !important;
    color: {_acc} !important;
    width: 40px !important;
    height: 40px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 12px {_acc_med} !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
    padding: 0 !important;
  }}
  [data-testid="collapsedControl"] button:hover {{
    background: {_acc} !important;
    box-shadow: 0 4px 18px {_acc_ring} !important;
    transform: scale(1.08) !important;
  }}
  [data-testid="collapsedControl"] button:hover svg {{
    fill: #ffffff !important;
    color: #ffffff !important;
    stroke: #ffffff !important;
  }}
  [data-testid="collapsedControl"] button svg {{
    fill: {_acc} !important;
    color: {_acc} !important;
    stroke: {_acc} !important;
    width: 18px !important;
    height: 18px !important;
  }}

  [data-testid="stSidebar"] .sidebar-label,
  .sidebar-label {{
    font-size: 0.67rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    color: {_SB_ACCENT} !important;
    margin: 1.2rem 0 0.4rem 0 !important;
    font-family: 'DM Sans', sans-serif !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
  }}
  [data-testid="stSidebar"] .sidebar-label::before,
  .sidebar-label::before {{
    content: '' !important;
    display: inline-block !important;
    width: 3px !important;
    height: 10px !important;
    background: {_SB_ACCENT} !important;
    border-radius: 2px !important;
    flex-shrink: 0 !important;
  }}

  /* ── Sidebar: sezione divider sottile ── */
  .sb-divider {{
    display: none !important;
    height: 0 !important;
    background: transparent !important;
    border: none !important;
    margin: 0 !important;
    opacity: 0 !important;
  }}

  /* ── Sidebar: monthly usage bar ── */
  .monthly-bar {{
    background: transparent !important;
    border: none !important;
    border-radius: 10px;
    padding: .6rem .75rem;
    margin-top: .35rem;
  }}
  .monthly-bar-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: .4rem;
  }}
  .monthly-bar-label {{
    font-size: .78rem;
    color: {_SB_TEXT};
    font-family: 'DM Sans', sans-serif;
  }}
  .monthly-bar-count {{
    font-size: .8rem;
    font-weight: 700;
    color: {_SB_TEXT};
    font-family: 'DM Sans', sans-serif;
  }}
  .monthly-progress {{
    height: 4px;
    background: transparent !important;
    border: none !important;
    border-radius: 10px;
    overflow: hidden;
  }}
  .monthly-progress-fill {{
    height: 100%;
    border-radius: 10px;
    transition: width .6s ease;
  }}
  .limit-reached {{ color: {T['error']} !important; }}
  .limit-near    {{ color: {T['warn']}  !important; }}

  /* Mobile progress container - completely transparent */
  .mobile-progress-container {{
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 0 !important;
  }}

  /* ── Sidebar: Pro CTA card con gradient border ── */
  .sb-pro-card {{
    background: linear-gradient(135deg, {_SB_INPUT_BG}ee, {_SB_INPUT_BG}cc) padding-box,
                linear-gradient(135deg, {_SB_ACCENT}99, {_acc2}55) border-box;
    border: 1.5px solid transparent;
    border-radius: 12px;
    padding: .8rem 1rem;
    margin: .6rem 0 .4rem 0;
    box-shadow: 0 2px 8px rgba(0,0,0,.1);
  }}
  .sb-pro-card-header {{
    font-size: .76rem;
    font-weight: 800;
    color: {_SB_ACCENT};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 6px;
    letter-spacing: .02em;
  }}
  .sb-pro-card-body {{
    font-size: .72rem;
    color: {_SB_TEXT};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
    margin-bottom: .4rem;
    font-weight: 500;
  }}
  .sb-pro-card-footer {{
    font-size: .65rem;
    color: {_SB_MUTED};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.4;
    opacity: .9;
  }}

  /* ── Sidebar: user pill ── */
  .user-pill {{
    display: flex;
    align-items: center;
    gap: .7rem;
    padding: .8rem .3rem .5rem .3rem;
    border-top: 1px solid {_SB_BORDER}44;
    margin-top: 1.2rem;
    background: {_SB_INPUT_BG}22;
    border-radius: 8px;
  }}
  .user-avatar {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, {_SB_ACCENT}, {_acc2});
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: .9rem;
    font-weight: 800;
    color: {_SB_INPUT_BG};
    flex-shrink: 0;
    font-family: 'DM Sans', sans-serif;
    box-shadow: 0 2px 6px rgba(0,0,0,.2);
  }}
  .user-info {{
    overflow: hidden;
    min-width: 0;
  }}
  .user-email {{
    font-size: .76rem;
    color: {_SB_TEXT};
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .user-role {{
    font-size: .67rem;
    color: {_SB_MUTED};
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
  }}

  /* ── Sidebar: logout button ── */
  .logout-btn-wrap .stButton > button {{
    background: {_SB_INPUT_BG}33 !important;
    background-color: {_SB_INPUT_BG}33 !important;
    border: 1px solid {_SB_BORDER}66 !important;
    color: {_SB_MUTED} !important;
    -webkit-text-fill-color: {_SB_MUTED} !important;
    font-size: .82rem !important;
    font-weight: 600 !important;
    min-height: 36px !important;
    width: 100% !important;
    margin-top: .6rem !important;
    border-radius: 8px !important;
    transition: all .2s ease !important;
  }}
  .logout-btn-wrap .stButton > button:hover {{
    border-color: {T.get('error','#DC2626')}88 !important;
    color: {T.get('error','#DC2626')} !important;
    -webkit-text-fill-color: {T.get('error','#DC2626')} !important;
    background: {T.get('error','#DC2626')}15 !important;
    background-color: {T.get('error','#DC2626')}15 !important;
    transform: translateY(-1px);
  }}

  /* ── Sidebar: logo sub-title ── */
  .sidebar-logo-sub {{
    font-size: .63rem;
    color: {_SB_MUTED};
    font-weight: 500;
    letter-spacing: .03em;
    margin-top: 1px;
    font-family: 'DM Sans', sans-serif;
  }}


  /* ════════════════════════════════════════════════════════════════════════
     SITE HEADER — header globale, identico su OGNI pagina, sempre centrato
     ════════════════════════════════════════════════════════════════════════ */
  .site-header {{
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2.8rem 1rem 1.8rem;
    margin-bottom: 1rem;
  }}
  .site-header-logo {{
    display: inline-flex;
    align-items: center;
    gap: 14px;
    text-decoration: none !important;
  }}
  .site-header-icon {{
    font-size: 3.8rem;
    line-height: 1;
    filter: drop-shadow(0 3px 14px {_acc}55);
  }}
  .site-header-name {{
    font-family: 'DM Sans', sans-serif;
    font-size: clamp(3.4rem, 7vw, 5rem);
    font-weight: 900;
    letter-spacing: -0.05em;
    color: {T['text']};
    line-height: 1;
  }}
  .site-header-ai {{
    background: linear-gradient(135deg, {_acc}, {T.get('accent2', _acc)});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .site-header-beta {{
    font-size: 0.88rem;
    font-weight: 800;
    letter-spacing: .1em;
    text-transform: uppercase;
    background: {_acc_soft};
    color: {_acc};
    border: 1px solid {_acc_med};
    border-radius: 20px;
    padding: 4px 10px;
    align-self: flex-start;
    margin-top: 8px;
    font-family: 'DM Sans', sans-serif;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     SIDEBAR LOGO — branding compatto, colore da tema (sidebar_accent)
     ════════════════════════════════════════════════════════════════════════ */
  .sidebar-logo {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.08rem !important;
    font-weight: 900 !important;
    letter-spacing: -0.02em;
    color: {_SB_TEXT} !important;
    margin: 0 0 .6rem 0;
    padding: .35rem 0 .5rem 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}


  /* ════════════════════════════════════════════════════════════════════════
     GLOBAL — Form Inputs
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stTextInput"] input,
  [data-testid="stTextArea"] textarea {{
    background: {_surf_overlay} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: {_radius_md} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    caret-color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    padding: 14px 16px !important;
    box-shadow: {_shadow_xs} !important;
    transition: border-color {_transition}, box-shadow {_transition} !important;
    color-scheme: {_color_scheme} !important;
  }}
  [data-testid="stTextInput"] input:focus,
  [data-testid="stTextArea"] textarea:focus {{
    border-color: {_acc} !important;
    box-shadow: 0 0 0 3px {_acc_ring}, {_shadow_xs} !important;
    outline: none !important;
  }}
  /* Placeholder — vendor prefixes per browser coverage + alto contrasto */
  [data-testid="stTextInput"] input::placeholder,
  [data-testid="stTextArea"] textarea::placeholder {{
    color: {_placeholder_color} !important;
    opacity: 1 !important;
  }}
  [data-testid="stTextInput"] input::-webkit-input-placeholder,
  [data-testid="stTextArea"] textarea::-webkit-input-placeholder {{
    color: {_placeholder_color} !important;
    opacity: 1 !important;
  }}
  [data-testid="stTextInput"] input::-moz-placeholder,
  [data-testid="stTextArea"] textarea::-moz-placeholder {{
    color: {_placeholder_color} !important;
    opacity: 1 !important;
  }}
  [data-testid="stTextInput"] input:-ms-input-placeholder,
  [data-testid="stTextArea"] textarea:-ms-input-placeholder {{
    color: {_placeholder_color} !important;
    opacity: 1 !important;
  }}

  /* ── Selectbox — trigger control (closed state) ───────────────── */
  [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child {{
    background: {_surf_raised} !important;
    background-color: {_surf_raised} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: {_radius_md} !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.06) !important;
    color-scheme: {_color_scheme} !important;
  }}
  [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:focus-within,
  [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:hover,
  [data-testid="stSelectbox"] [data-baseweb="select"][aria-expanded="true"] > div:first-child {{
    border-color: {_acc} !important;
    box-shadow: 0 0 0 3px {_acc_soft} !important;
    background: {_surf_raised} !important;
    background-color: {_surf_raised} !important;
  }}
  /* Selected value text and all spans/divs inside the trigger */
  [data-testid="stSelectbox"] [data-baseweb="select"] span,
  [data-testid="stSelectbox"] [data-baseweb="select"] div[class],
  [data-testid="stSelectbox"] [data-baseweb="select"] [aria-selected],
  [data-testid="stSelectbox"] [data-baseweb="select"] [data-value],
  [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child * {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    font-size: 1.02rem !important;
    font-family: 'DM Sans', sans-serif !important;
    color-scheme: {_color_scheme} !important;
  }}
  /* SVG arrow inside trigger */
  [data-testid="stSelectbox"] [data-baseweb="select"] svg,
  [data-testid="stSelectbox"] [data-baseweb="select"] svg * {{
    fill: {T['text2']} !important;
    stroke: {T['text2']} !important;
  }}

  /* ── Dropdown popup menu (portal, fuori dal DOM normale) ────────── */
  [data-baseweb="popover"],
  [data-baseweb="popover"] > div,
  [data-baseweb="popover"] > div > div {{
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    color-scheme: {_color_scheme} !important;
  }}
  /* Search input nella barra in cima al dropdown — spesso lasciata nera */
  [data-baseweb="popover"] [data-baseweb="input"],
  [data-baseweb="popover"] [data-baseweb="input"] > div,
  [data-baseweb="popover"] [data-baseweb="base-input"],
  [data-baseweb="popover"] input,
  [data-baseweb="popover"] [data-baseweb="block"] {{
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    caret-color: {T['text']} !important;
    color-scheme: {_color_scheme} !important;
    border-color: {T['border2']} !important;
  }}
  [data-baseweb="popover"] [data-baseweb="menu"],
  [data-baseweb="popover"] ul {{
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,.13) !important;
    padding: 4px !important;
    color-scheme: {_color_scheme} !important;
  }}
  [data-baseweb="popover"] [role="option"],
  [data-baseweb="popover"] li {{
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.97rem !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    color-scheme: {_color_scheme} !important;
  }}
  [data-baseweb="popover"] [role="option"]:hover,
  [data-baseweb="popover"] [aria-selected="true"],
  [data-baseweb="popover"] [data-highlighted="true"] {{
    background: {_acc_soft} !important;
    background-color: {_acc_soft} !important;
    color: {_acc} !important;
    -webkit-text-fill-color: {_acc} !important;
  }}
  /* Forza colore su tutti i testi figli del popover */
  [data-baseweb="popover"] span,
  [data-baseweb="popover"] p,
  [data-baseweb="popover"] div,
  [data-baseweb="popover"] * {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    color-scheme: {_color_scheme} !important;
  }}
  /* Eccezione: elemento selezionato e hover mantengono il colore accent */
  [data-baseweb="popover"] [aria-selected="true"] *,
  [data-baseweb="popover"] [data-highlighted="true"] * {{
    color: {_acc} !important;
    -webkit-text-fill-color: {_acc} !important;
  }}

  .stCheckbox label span[data-baseweb="checkbox"] {{
    border-color: {T['border2']} !important;
  }}

  /* Number Input — global, previene sfondo dark di Streamlit */
  :not([data-testid="stSidebar"])
    [data-testid="stNumberInput"] input {{
    background: {_surf_raised} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.99rem !important;
  }}
  :not([data-testid="stSidebar"])
    [data-testid="stNumberInput"] button {{
    background: {_surf_raised} !important;
    border-color: {T['border']} !important;
    color: {T['text']} !important;
  }}

  /* Labels */
  [data-testid="stTextInput"] label p,
  [data-testid="stTextArea"] label p,
  [data-testid="stSelectbox"] label p {{
    color: {T['text']} !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    font-family: 'DM Sans', sans-serif !important;
    letter-spacing: .015em !important;
    opacity: .82 !important;
  }}

  /* Toggle + Checkbox label — forza colore tema */
  [data-testid="stCheckbox"] label,
  [data-testid="stToggle"] label,
  [data-testid="stCheckbox"] label p,
  [data-testid="stToggle"] label p,
  .stCheckbox label span:last-child,
  .stToggle label span:last-child {{
    color: {T['text']} !important;
    font-size: 1.02rem !important;
    font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     BUTTONS — Primary & Secondary
     Altezze unificate a 48px per evitare disallineamento in righe miste
     ════════════════════════════════════════════════════════════════════════ */
  div.stButton > button[kind="primary"],
  div.stButton > button[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, {_acc} 0%, {_acc2} 100%) !important;
    color: {_btn_text} !important;
    -webkit-text-fill-color: {_btn_text} !important;
    border: none !important;
    border-radius: {_radius_md} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.97rem !important;
    min-height: 48px !important;
    padding: .6rem 1.4rem !important;
    letter-spacing: -.01em !important;
    box-shadow: 0 4px 20px {_acc_glow}, 0 1px 4px {_acc_med} !important;
    transition: filter {_transition}, box-shadow {_transition}, transform {_transition} !important;
  }}
  div.stButton > button[kind="primary"]:hover,
  div.stButton > button[data-testid="stBaseButton-primary"]:hover {{
    filter: brightness(1.06) !important;
    box-shadow: 0 8px 28px {_acc_ring}, 0 2px 6px {_acc_med} !important;
    transform: translateY(-2px) !important;
  }}
  div.stButton > button[kind="primary"]:active,
  div.stButton > button[data-testid="stBaseButton-primary"]:active {{
    transform: translateY(0) scale(.98) !important;
    box-shadow: 0 2px 10px {_acc_med} !important;
    filter: brightness(.97) !important;
  }}
  div.stButton > button[kind="primary"]:disabled {{
    opacity: .45 !important;
    box-shadow: none !important;
    filter: grayscale(.3) !important;
    transform: none !important;
  }}

  /* ── SECONDARY BUTTONS: specificità massima per battere emotion CSS ────── */
  html body .stApp [data-testid="stBaseButton-secondary"],
  html body .stApp div.stButton > button[kind="secondary"],
  html body .stApp div.stButton > button:not([kind="primary"]),
  html body .stApp [data-testid="stButton"] > button:not([data-testid*="primary"]),
  div.stButton > button[kind="secondary"],
  div.stButton > button:not([kind="primary"]) {{
    background: {_surf_raised} !important;
    background-color: {_surf_raised} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: {_radius_md} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    min-height: 44px !important;
    padding: .6rem 1.2rem !important;
    box-shadow: {_shadow_xs} !important;
    transition: background {_transition}, border-color {_transition}, box-shadow {_transition}, transform {_transition} !important;
  }}
  html body .stApp [data-testid="stBaseButton-secondary"]:hover,
  html body .stApp div.stButton > button[kind="secondary"]:hover,
  html body .stApp div.stButton > button:not([kind="primary"]):hover,
  html body .stApp [data-testid="stButton"] > button:not([data-testid*="primary"]):hover,
  div.stButton > button[kind="secondary"]:hover,
  div.stButton > button:not([kind="primary"]):hover {{
    background: {T['hover']} !important;
    border-color: {_acc} !important;
    color: {_acc} !important;
    -webkit-text-fill-color: {_acc} !important;
    box-shadow: 0 4px 16px {_acc_soft}, {_shadow_xs} !important;
    transform: translateY(-1px) !important;
  }}
  div.stButton > button[kind="secondary"]:active,
  div.stButton > button:not([kind="primary"]):active {{
    transform: scale(0.98) !important;
    box-shadow: none !important;
  }}
  div.stButton > button:focus-visible {{
    outline: 2px solid {_acc} !important;
    outline-offset: 3px !important;
    box-shadow: 0 0 0 4px {_acc_ring} !important;
  }}

  /* ── SIDEBAR buttons: override definitivo con specificità massima ──────
     Deve stare DOPO le regole generali. Specificità (0,3,2) batte (0,2,2).
     Corregge la regressione "sidebar buttons diventati bianchi".          */
  html body .stApp [data-testid="stSidebar"] div.stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]),
  html body .stApp [data-testid="stSidebar"] .stButton button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]),
  html body .stApp [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
  html body .stApp [data-testid="stSidebar"] [data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {{
    background: {_SB_INPUT_BG} !important;
    background-color: {_SB_INPUT_BG} !important;
    color: {_SB_INPUT_TEXT} !important;
    -webkit-text-fill-color: {_SB_INPUT_TEXT} !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    min-height: 34px !important;
    padding: .3rem .6rem !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    box-shadow: none !important;
  }}
  html body .stApp [data-testid="stSidebar"] div.stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]):hover,
  html body .stApp [data-testid="stSidebar"] .stButton button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]):hover,
  html body .stApp [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
    background: {_SB_BORDER} !important;
    background-color: {_SB_BORDER} !important;
    border-color: {_SB_ACCENT} !important;
    color: {_SB_INPUT_TEXT} !important;
    -webkit-text-fill-color: {_SB_INPUT_TEXT} !important;
    transform: none !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     DOWNLOAD BUTTONS — teal-accented, visivamente distinti dai bottoni azione
     ════════════════════════════════════════════════════════════════════════ */
  /* ── DOWNLOAD BUTTONS: specificità massima per testo verde chiaro ────── */
  html body .stApp div.stDownloadButton > button,
  div.stDownloadButton > button {{
    background: {T.get('card2', _surf_overlay)} !important;
    background-color: {T.get('card2', _surf_overlay)} !important;
    color: {T['success']} !important;
    -webkit-text-fill-color: {T['success']} !important;
    border: 1.5px solid {T['success']}55 !important;
    border-radius: {_radius_md} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    min-height: 44px !important;
    padding: .55rem 1.2rem !important;
    box-shadow: none !important;
    transition: background {_transition}, border-color {_transition}, box-shadow {_transition}, transform {_transition} !important;
  }}
  html body .stApp div.stDownloadButton > button:hover,
  div.stDownloadButton > button:hover {{
    background: {T['success']}14 !important;
    background-color: {T['success']}14 !important;
    border-color: {T['success']}99 !important;
    color: {T['success']} !important;
    -webkit-text-fill-color: {T['success']} !important;
    box-shadow: 0 3px 12px {T['success']}22 !important;
    transform: translateY(-1px) !important;
  }}
  div.stDownloadButton > button:active {{
    transform: scale(.98) !important;
    box-shadow: none !important;
  }}
  div.stDownloadButton > button svg {{
    fill: {T['success']} !important;
    stroke: {T['success']} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     OUTLINE-ACCENT BUTTON — coppia coerente "Genera variante" / "Cambia esercizio"
     Applicato tramite marker div .btn-outline-accent-marker prima del button.
     Entrambi i bottoni nella coppia usano questo stile uniforme.
     ════════════════════════════════════════════════════════════════════════ */
  /* Approccio: marker hidden div → sibling button */
  .btn-outline-accent-marker + div button,
  .element-container:has(.btn-outline-accent-marker) + .element-container button,
  [data-testid="stVerticalBlock"] > div:has(.btn-outline-accent-marker) + div button {{
    background: transparent !important;
    background-color: transparent !important;
    color: {_acc} !important;
    -webkit-text-fill-color: {_acc} !important;
    border: 1.5px solid {_acc} !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    min-height: 48px !important;
    box-shadow: none !important;
    transition: background .15s ease, box-shadow .15s ease !important;
  }}
  .btn-outline-accent-marker + div button:hover,
  .element-container:has(.btn-outline-accent-marker) + .element-container button:hover,
  [data-testid="stVerticalBlock"] > div:has(.btn-outline-accent-marker) + div button:hover {{
    background: {_acc_soft} !important;
    background-color: {_acc_soft} !important;
    box-shadow: 0 2px 12px {_acc_soft} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     PROGRESS BAR (Breadcrumb)
     ════════════════════════════════════════════════════════════════════════ */
  .breadcrumb-wrap {{
    display: flex; justify-content: center; margin-bottom: 1.6rem;
  }}
  .breadcrumb-pill {{
    display: inline-flex; align-items: center; gap: 12px;
    padding: .65rem 1.8rem;
    background: {T['card']};
    border: 1px solid {T['border2']};
    border-radius: 100px;
    box-shadow: {_shadow_md};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     HOME LANDING
     ════════════════════════════════════════════════════════════════════════ */
  .home-landing-wrap {{
    text-align: center;
    margin-bottom: 2rem;
    padding: 1.2rem 0 .5rem;
  }}
  .home-landing-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.6rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    color: {T['text']};
    margin-bottom: .5rem;
  }}
  .home-landing-desc {{
    font-size: 0.99rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    max-width: 520px;
    margin: 0 auto;
    line-height: 1.55;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     LANDING HERO — Logo MOLTO GRANDE + headline centrati
     ════════════════════════════════════════════════════════════════════════ */

  /* Landing hero — logo rimosso (ora nel site-header globale) */
  .landing-hero-unified {{
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 1.5rem 1rem 1rem;
    max-width: 860px;
    margin: 0 auto;
  }}
  .landing-logo-row,
  .landing-logo-icon-xl,
  .landing-logo-name-xl,
  .landing-logo-ai-xl,
  .landing-logo-beta-xl {{
    display: none;
  }}

  /* Headline grande */
  .landing-headline-xl {{
    font-family: 'DM Sans', sans-serif;
    font-size: clamp(2.4rem, 5.5vw, 3.6rem);
    font-weight: 900;
    line-height: 0.85 !important;
    letter-spacing: -0.03em;
    color: {T['text']};
    margin: 0 0 0.3rem 0;
    padding: 0;
    text-align: center;
  }}
  .landing-headline-accent-xl {{
    background: linear-gradient(135deg, {_acc}, {T.get('accent2', _acc)}cc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}

  /* Sottotitolo — centrato, leggibile */
  .landing-sub-xl {{
    font-size: 1.15rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    line-height: 1.5;
    text-align: center;
    max-width: 520px;
    margin: 0.2rem auto 1.5rem;
  }}

  /* Classi legacy mantenute per compatibilità */
  .landing-logo-wrap {{ display:none; }}
  .tally-headline {{
    font-family:'DM Sans',sans-serif; font-size:clamp(2.2rem,5vw,3.2rem);
    font-weight:900; line-height:1.1; letter-spacing:-0.04em;
    color:{T['text']}; margin:0 0 1.1rem 0; padding:0;
  }}
  .tally-headline-accent {{
    background:linear-gradient(135deg,{_acc},{T.get('accent2',_acc)}cc);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  }}
  .tally-sub {{
    font-size:1rem; color:{T['text2']}; font-family:'DM Sans',sans-serif;
    line-height:1.6; margin:0 auto; max-width:480px; text-align:center;
  }}


  /* ════════════════════════════════════════════════════════════════════════
     LANDING PAGE — Kicker + sezione preview gallery
     ════════════════════════════════════════════════════════════════════════ */
  .landing-kicker {{
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: {_acc};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .8rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .landing-kicker::before {{
    content: '';
    display: inline-block;
    width: 18px;
    height: 2px;
    background: {_acc};
    border-radius: 2px;
    flex-shrink: 0;
  }}
  .landing-section-kicker {{
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: {_acc};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .5rem;
  }}
  .landing-section-title {{
    font-size: clamp(1.4rem, 3vw, 1.8rem);
    font-weight: 900;
    letter-spacing: -0.03em;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .4rem;
    line-height: 1.15;
  }}
  .landing-section-sub {{
    font-size: 1rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.6;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     ST.STATUS WIDGET — Override per coerenza visiva con il tema
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stStatus"] {{
    background: {_surf_raised} !important;
    border: 1px solid {T['border2']} !important;
    border-radius: {_radius_md} !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  [data-testid="stStatus"] summary,
  [data-testid="stStatus"] > summary {{
    background: {_surf_raised} !important;
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.97rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  [data-testid="stStatus"][data-state="running"] summary {{
    color: {_acc} !important;
  }}
  [data-testid="stStatus"][data-state="complete"] summary {{
    color: {T['success']} !important;
  }}
  [data-testid="stStatus"][data-state="error"] summary {{
    color: {T['error']} !important;
  }}

  /* Feature strip — singole pill con underline */
  .tally-features {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 10px 8px;
    margin: 1.8rem auto 0;
    max-width: 720px;
    padding-bottom: .8rem;
  }}
  .tally-feat-pill {{
    font-size: .95rem;
    font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    color: #0369a1;
    white-space: nowrap;
    padding: 8px 16px;
    border-radius: 20px;
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    transition: all .15s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .tally-feat-pill:hover {{
    background: #e0f2fe;
    border-color: #7dd3fc;
    transform: translateY(-1px);
  }}
  .pill-emoji {{
    font-size: 1.28em;
    vertical-align: -0.06em;
    display: inline-block;
    margin-right: .1em;
  }}
  /* Legacy classes kept for compatibility */
  .tally-feat {{
    font-size: 0.89rem; font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    color: {T['text2']}; white-space: nowrap;
  }}
  .tally-feat-sep {{ display: none; }}

  /* Social proof (compatibilità) */
  .tally-proof {{ display: none; }}
  .tally-proof-dot {{ display: none; }}

  /* ════════════════════════════════════════════════════════════════════════
     SIDE-BOX — Colonna destra form (sostituisce facsimile-shortcut + side-panel-card)
     ════════════════════════════════════════════════════════════════════════ */
  .side-box {{
    background: {T['card']};
    border: 1px solid {T['border2']};
    border-radius: {_radius_lg};
    padding: 1.1rem 1.2rem 1rem;
    margin-bottom: .65rem;
    box-shadow: {_shadow_sm};
    transition: box-shadow {_transition}, border-color {_transition};
  }}
  .side-box:hover {{
    box-shadow: {_shadow_md};
    border-color: {T['border']};
  }}
  .side-box-header {{
    margin-bottom: .45rem;
  }}
  .side-box-badge {{
    font-size: 0.9rem;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
    border-radius: 20px;
    padding: 3px 9px;
    display: inline-block;
  }}
  .side-box-title {{
    font-size: 0.95rem;
    font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .35rem;
  }}
  .side-box-title-flex {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .side-box-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {_acc};
    box-shadow: 0 0 6px {_acc_med};
    flex-shrink: 0;
  }}
  .side-box-desc {{
    font-size: 0.88rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
  }}
    
  /* ── File AI summary (cosa ha capito l'AI) ── */
  .file-ai-summary {{
    display: flex;
    align-items: flex-start;
    gap: 6px;
    background: {_acc_soft};
    border: 1px solid {_acc_med};
    border-radius: 8px;
    padding: .4rem .7rem;
    margin: .35rem 0 .45rem;
    font-size: 0.94rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.45;
  }}
  .file-ai-summary-icon {{
    flex-shrink: 0;
    font-size: 0.89rem;
    margin-top: .05rem;
  }}
  .file-ai-summary-text {{
    flex: 1;
  }}

  /* ── Hint "esercizio da inserire" ── */
  .file-includi-hint {{
    background: {T.get('hint_bg', '#FEF3C7')};
    border: 1px solid {T.get('hint_border', '#FDE68A')};
    border-radius: 8px;
    padding: .45rem .8rem;
    margin: .3rem 0 .4rem;
    font-size: 0.87rem;
    color: {T.get('hint_text', '#92400E')};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}
  .file-fonte-hint {{
    background: {_acc_soft};
    border: 1px solid {_acc_med};
    border-radius: 8px;
    padding: .45rem .8rem;
    margin: .3rem 0 .4rem;
    font-size: 0.87rem;
    color: {_acc};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}


  /* ── Facsimile Card — Viola/Accento speciale ── */
  .fac-card {{
    background: linear-gradient(135deg, {_acc}14, {T['card']});
    border: 2px solid {_acc}44;
    border-radius: {_radius_lg};
    padding: 1.1rem 1.4rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: border-color .2s ease, box-shadow .2s ease;
  }}
  .fac-card:hover {{
    border-color: {_acc}88;
    box-shadow: 0 4px 24px {_acc}22;
  }}
  .fac-badge {{
    font-size: 0.9rem; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase;
    color: {_acc};
    margin-bottom: .15rem;
  }}
  .fac-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 900;
    color: {T['text']};
    margin-bottom: .15rem;
  }}
  .fac-desc {{
    font-size: 0.89rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}

  /* viola button override */
  .mbtn-viola button {{
    background: linear-gradient(135deg,#7C3AED,#6D28D9) !important;
    color: #fff !important; border: none !important;
    border-radius: 12px !important; font-weight: 700 !important;
    font-size: 0.99rem !important;
    box-shadow: 0 4px 20px #7C3AED44 !important;
  }}
  .mbtn-viola button:hover {{
    background: linear-gradient(135deg,#A78BFA,#7C3AED) !important;
    box-shadow: 0 6px 28px #7C3AED66 !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FORM SECTION HEADERS — Percorso B
     ════════════════════════════════════════════════════════════════════════ */
  .form-section-header {{
    display: flex; align-items: center; gap: 10px;
    margin: 1.4rem 0 .8rem;
  }}
  .form-section-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {_acc};
    flex-shrink: 0;
    box-shadow: 0 0 0 3px {_acc_soft};
  }}
  .form-section-title {{
    font-size: .82rem;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: {T.get('muted', T['text2'])};
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap;
  }}
  .form-section-line {{
    flex: 1; height: 1px;
    background: linear-gradient(90deg, {T['border2']}, transparent);
  }}

  .opt-label {{
    font-size: 0.84rem;
    font-weight: 700;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 5px;
    letter-spacing: .04em;
    text-transform: uppercase;
    opacity: .78;
  }}


  /* ════════════════════════════════════════════════════════════════════════
     CONTEXT SYNC BADGE — badge autofill da file caricato
     ════════════════════════════════════════════════════════════════════════ */
  .context-sync-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: {T['success']}14;
    border: 1px solid {T['success']}44;
    border-radius: 20px;
    padding: .3rem .85rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: {T['success']};
    font-family: 'DM Sans', sans-serif;
    margin: .35rem 0 .5rem;
    line-height: 1.4;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     BTN WRAPPERS — varianti dimensionali e stilistiche per bottoni speciali
     ════════════════════════════════════════════════════════════════════════ */

  /* Oro: bottone conferma finale in STAGE_REVIEW */
  .btn-confirm-gold button {{
    background: linear-gradient(135deg, #D97706, #F59E0B) !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    border: none !important;
    border-radius: {_radius_lg} !important;
    font-weight: 800 !important;
    font-size: 1.05rem !important;
    min-height: 56px !important;
    letter-spacing: -.01em !important;
    box-shadow: 0 4px 22px #D9770640, 0 1px 4px #D9770625 !important;
    transition: filter .2s ease, box-shadow .2s ease, transform .15s ease !important;
  }}
  .btn-confirm-gold button:hover {{
    filter: brightness(1.07) !important;
    box-shadow: 0 8px 28px #D9770655 !important;
    transform: translateY(-2px) !important;
  }}
  .btn-confirm-gold button:active {{
    transform: scale(.98) !important;
    box-shadow: none !important;
  }}

  /* Piccolo + discreto: "← Riconfigura" sotto il form review */
  .btn-riconfigura-small button {{
    background: transparent !important;
    color: {T['muted']} !important;
    -webkit-text-fill-color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    min-height: 32px !important;
    padding: .2rem .9rem !important;
    box-shadow: none !important;
    border-radius: 8px !important;
    letter-spacing: 0 !important;
    opacity: .7 !important;
    transition: opacity .15s ease, border-color .15s ease !important;
  }}
  .btn-riconfigura-small button:hover {{
    opacity: 1 !important;
    border-color: {T['border2']} !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  /* Back discreto: usato in ui_helpers._render_back_button */
  .btn-back-discrete button {{
    background: transparent !important;
    color: {T['muted']} !important;
    -webkit-text-fill-color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    min-height: 34px !important;
    padding: .25rem .9rem !important;
    box-shadow: none !important;
    border-radius: 8px !important;
    opacity: .75 !important;
    transition: opacity .15s ease, border-color .15s ease, color .15s ease !important;
  }}
  .btn-back-discrete button:hover {{
    opacity: 1 !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border-color: {T['border2']} !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     CTA GENERA — High Impact Button Wrap - GREEN/GOLD EDITION
     ════════════════════════════════════════════════════════════════════════ */
  .cta-genera-wrap button {{
    min-height: 72px !important;
    font-size: 1.3rem !important;
    font-weight: 900 !important;
    border-radius: {_radius_lg} !important;
    background: linear-gradient(135deg, #10b981, #f59e0b) !important;
    border: 2px solid #10b981 !important;
    box-shadow: 0 8px 25px -5px rgba(16, 185, 129, 0.4) !important;
    transition: all .3s ease !important;
    text-transform: none !important;
    letter-spacing: .02em !important;
  }}
  .cta-genera-wrap button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 35px -5px rgba(16, 185, 129, 0.5) !important;
    background: linear-gradient(135deg, #059669, #d97706) !important;
  }}
  .cta-genera-wrap button:active {{
    transform: translateY(0) !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     SECONDARY BUTTONS — Orange Edition (no border)
     ════════════════════════════════════════════════════════════════════════ */
  button[data-testid="baseButton-secondary"],
  button[data-testid="baseButton-primary"],
  .element-container button,
  div[data-testid="stVerticalBlock"] button {{
    background: linear-gradient(135deg, #EA580C, #FB923C) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    min-height: 48px !important;
    transition: all 0.3s ease !important;
  }}
  
  button[data-testid="baseButton-secondary"]:hover,
  button[data-testid="baseButton-primary"]:hover,
  .element-container button:hover,
  div[data-testid="stVerticalBlock"] button:hover {{
    background: linear-gradient(135deg, #C2410C, #FCD34D) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px -2px rgba(234, 88, 12, 0.3) !important;
  }}

  /* Forza testo bianco su tutti i pulsanti */
  button[data-testid="baseButton-secondary"] *,
  button[data-testid="baseButton-primary"] *,
  .element-container button *,
  div[data-testid="stVerticalBlock"] button * {{
    color: white !important;
    -webkit-text-fill-color: white !important;
  }}

  /* Nuovo: hint testuale leggero sopra il pulsante Genera */
  .cta-hint-text {{
    text-align: center;
    font-size: 0.96rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .45rem;
    font-style: italic;
    opacity: .9;
    letter-spacing: .01em;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     BACK BUTTON micro — piccolo, muted, in fondo
     ════════════════════════════════════════════════════════════════════════ */
  /* Stile per il pulsante "← Indietro" in fondo al form (colonne plain) */
  [data-testid="stHorizontalBlock"] .stButton button[data-testid*="btn_back"],
  .stButton > button[data-testid*="btn_back"] {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    min-height: 30px !important;
    padding: 0 .7rem !important;
    box-shadow: none !important;
    border-radius: 8px !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     PAGE NAV BUTTONS — Precedente / Successiva (anteprima multi-pagina)
     ════════════════════════════════════════════════════════════════════════ */
  .page-nav-btn-wrap + div button,
  .element-container:has(.page-nav-btn-wrap) + .element-container button {{
    background: {T['card']} !important;
    color: {T['text2']} !important;
    -webkit-text-fill-color: {T['text2']} !important;
    border: 1px solid {T['border']} !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    min-height: 34px !important;
    padding: .2rem .8rem !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    opacity: .8 !important;
    letter-spacing: 0 !important;
  }}
  .page-nav-btn-wrap + div button:hover,
  .element-container:has(.page-nav-btn-wrap) + .element-container button:hover {{
    opacity: 1 !important;
    border-color: {_acc} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    transform: none !important;
    box-shadow: none !important;
  }}
  .page-nav-btn-wrap + div button:disabled,
  .element-container:has(.page-nav-btn-wrap) + .element-container button:disabled {{
    opacity: .25 !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     SIDE PANEL — Right column
     ════════════════════════════════════════════════════════════════════════ */
  .side-panel-card {{
    background: {_surf_raised};
    border: 1.5px solid {T['border']};
    border-radius: {_radius_lg};
    padding: .85rem 1rem .6rem;
    margin-bottom: .3rem;
  }}
  .side-panel-card-title {{
    font-size: 0.89rem; font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    display: flex; align-items: center; gap: 8px;
  }}
  .side-panel-card-title-dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {_acc};
    box-shadow: 0 0 6px {_acc_med};
  }}

  .upload-hint-compact {{
    font-size: 0.88rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
    padding: .4rem 0 .6rem;
  }}

  /* File uploader compact wrap — usato nell'expander inline */
  .file-uploader-compact {{
    margin-bottom: .5rem;
  }}
  .file-uploader-compact [data-testid="stFileUploader"] {{
    border-radius: 12px !important;
  }}
  .file-uploader-narrow [data-testid="stFileUploader"] {{
    min-height: 76px !important;
  }}
  .argomento-label-inline {{
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 0.35rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RIGHT COLUMN — colonna upload/materiale
     Strategia: target direttamente la colonna che CONTIENE il file uploader,
     non il blocco padre. Evita di stylare altri :last-child su altri blocchi.
     ════════════════════════════════════════════════════════════════════════ */

  /* Div placeholder: collassato, invisibile, zero impatto */
  .right-col-container {{
    display: none !important;
  }}


  /* ════════════════════════════════════════════════════════════════════════
     FILE POOL — Card compatta per ogni documento caricato (in expander inline)
     ════════════════════════════════════════════════════════════════════════ */

  .file-pool-card {{
    background: {T['bg2']};
    border: 1px solid {T['border2']};
    border-radius: {_radius_sm};
    padding: 0.55rem 0.7rem 0.45rem;
    margin-bottom: 0.5rem;
    transition: border-color {_transition}, box-shadow {_transition};
  }}
  .file-pool-card:hover {{
    border-color: {_acc_med};
    box-shadow: 0 2px 10px {_acc}18;
  }}

  /* ── Header row: icon + name + meta ────────────────────────────────── */
  .fpc-header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.4rem;
    margin-bottom: 0.3rem;
  }}
  .fpc-name {{
    font-size: 0.8rem;
    font-weight: 700;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
  }}
  .fpc-meta {{
    font-size: 0.68rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .fpc-meta strong {{ color: {T['text2']}; }}

  /* ── Mode radio — pill toggle ───────────────────────────────────────── */
  .file-pool-card [data-testid="stRadio"] {{
    margin: 0.3rem 0 0.1rem !important;
  }}
  .file-pool-card [data-testid="stRadio"] > div {{
    gap: 0.35rem !important;
    flex-wrap: nowrap !important;
  }}
  .file-pool-card [data-testid="stRadio"] label {{
    font-size: 0.75rem !important;
    padding: 2px 9px !important;
    border-radius: 20px !important;
    border: 1px solid {T['border2']} !important;
    background: transparent !important;
    color: {T['text2']} !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    white-space: nowrap !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  .file-pool-card [data-testid="stRadio"] label:has(input:checked) {{
    background: {_acc_soft} !important;
    border-color: {_acc} !important;
    color: {_acc} !important;
    font-weight: 700 !important;
  }}
  .file-pool-card [data-testid="stRadio"] input[type="radio"] {{
    display: none !important;
  }}

  /* ── Delete row — tiny right-aligned button ──────────────────────────── */
  .fpc-delete-row {{
    display: flex;
    justify-content: flex-end;
    margin-top: 0.25rem;
  }}
  .fpc-delete-row button {{
    min-height: 22px !important;
    height: 22px !important;
    padding: 0 8px !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    color: {T['muted']} !important;
    background: transparent !important;
    border: 1px solid {T['border2']} !important;
    border-radius: 20px !important;
    line-height: 1 !important;
    transition: color 0.15s, border-color 0.15s !important;
    box-shadow: none !important;
  }}
  .fpc-delete-row button:hover {{
    color: {T['error']} !important;
    border-color: {T['error']}40 !important;
    background: {T['error']}08 !important;
  }}

  /* ── Tag pills ──────────────────────────────────────────────────────── */
  .doc-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem;
    margin-bottom: 0.2rem;
  }}
  .doc-tag {{
    display: inline-flex;
    align-items: center;
    gap: 0.1rem;
    font-size: 0.65rem;
    font-weight: 600;
    padding: 1px 5px;
    border-radius: 4px;
    white-space: nowrap;
    font-family: 'DM Sans', sans-serif;
  }}
  .doc-tag-tipo    {{ background:{_acc_soft}; color:{_acc};    border:1px solid {_acc_ring}; }}
  .doc-tag-content {{ background:{T['border2']}44; color:{T['text2']}; border:1px solid {T['border2']}; }}
  .doc-tag-formula {{ background:{_acc}12; color:{_acc}; border:1px solid {_acc}28; }}
  .doc-tag-grafico {{ background:{T['warn']}12; color:{T['warn']}; border:1px solid {T['warn']}28; }}

  /* ── Empty state ────────────────────────────────────────────────────── */
  .doc-pool-empty {{
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 1.6rem 1.2rem 1.4rem;
    text-align: center;
    gap: 0.4rem;
  }}
  .doc-pool-empty-icon {{
    width: 36px; height: 36px;
    opacity: 0.3;
    margin-bottom: .2rem;
  }}
  .doc-pool-empty-title {{
    font-size: 0.8rem;
    font-weight: 700;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
  }}
  .doc-pool-empty-sub {{
    font-size: 0.7rem;
    color: {T['muted']};
    line-height: 1.5;
    max-width: 200px;
    font-family: 'DM Sans', sans-serif;
  }}

  /* Confirm pulisci */
  .confirm-pulisci-box {{
    background: {T['error']}15;
    border: 1px solid {T['error']}30;
    border-radius: {_radius_sm};
    padding: 0.55rem 0.65rem;
    margin: 0.4rem 0 0.2rem;
    font-size: 0.8rem;
    color: {T['text']};
  }}
  .confirm-pulisci-box strong {{
    color: {T['error']};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FILE ITEMS — Compact list (Percorso B, dentro file-pool-card)
     ════════════════════════════════════════════════════════════════════════ */
  .file-item-b {{
    background: {_surf_overlay};
    border: 1.5px solid {T['border']};
    border-radius: 12px;
    padding: .55rem .8rem;
    margin-bottom: .3rem;
    transition: border-color .15s ease;
  }}
  .file-pool-card .file-item-b {{
    padding: 0.35rem 0.5rem;
    margin-bottom: 0.2rem;
    border-radius: {_radius_sm};
  }}
  /* header diretto nella card (senza wrapper .file-item-b) */
  .file-pool-card .file-item-b-header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.4rem;
    margin-bottom: 0.1rem;
  }}
  .file-pool-card .file-item-b-name {{
    font-size: 0.84rem;
    font-weight: 700;
    color: {T['text']};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
    min-width: 0;
  }}
  .file-pool-card .file-item-b-badge {{
    font-size: 0.75rem;
    padding: 1px 5px;
  }}
  .file-item-b:hover {{
    border-color: {_acc_ring};
  }}
  .file-item-b-header {{
    display: flex; align-items: center; gap: .4rem;
    flex-wrap: nowrap;
  }}
  .file-item-b-icon {{ font-size: 0.97rem; flex-shrink: 0; }}
  .file-item-b-name {{
    font-size: 0.88rem; font-weight: 700;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1; min-width: 0;
  }}
  .file-item-b-badge {{
    font-size: 0.9rem; font-weight: 700;
    padding: 2px 7px; border-radius: 5px;
    white-space: nowrap; flex-shrink: 0;
  }}
  .file-item-b-badge-verifica {{
    background: {_acc_soft}; color: {_acc};
    border: 1px solid {_acc_med};
  }}
  .file-item-b-badge-appunti {{
    background: {T['success']}18; color: {T['success']};
    border: 1px solid {T['success']}33;
  }}
  .file-item-b-badge-altro {{
    background: {T['border2']}44; color: {T['text2']};
    border: 1px solid {T['border2']};
  }}
  .file-item-b-mode-label {{
    font-size: 0.9rem; font-weight: 600;
    color: {T['muted']}; font-family: 'DM Sans', sans-serif;
    margin: .2rem 0 .15rem;
  }}
  .file-item-b-delete {{
    margin-top: .25rem;
  }}
  .file-item-b-delete button {{
    min-height: 28px !important;
    font-size: 0.9rem !important;
    color: {T['muted']} !important;
    background: transparent !important;
    border: 1px dashed {T['border']} !important;
    border-radius: 6px !important;
    opacity: .7;
    transition: opacity .15s, color .15s, border-color .15s !important;
  }}
  .file-item-b-delete button:hover {{
    opacity: 1;
    color: {T['error']} !important;
    border-color: {T['error']} !important;
    background: {T['error']}08 !important;
  }}

  /* ═══ Context sync badge ═══ */
  .context-sync-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 0.92rem; font-weight: 600;
    color: {T['success']}; font-family: 'DM Sans', sans-serif;
    background: {T['success']}14;
    border: 1px solid {T['success']}33;
    border-radius: 8px; padding: 4px 10px;
    margin-bottom: .4rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     OCR SKELETON LOADING — Premium Effect
     ════════════════════════════════════════════════════════════════════════ */
  @keyframes shimmer {{
    0% {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
  }}
  @keyframes scanLine {{
    0% {{ top: 0; opacity: 1; }}
    80% {{ top: 92%; opacity: .7; }}
    100% {{ top: 92%; opacity: 0; }}
  }}
  @keyframes pulse-dot {{
    0%, 100% {{ opacity: .4; }}
    50% {{ opacity: 1; }}
  }}

  /* ── Analysis skeleton card ── */
  .ocr-skeleton-wrap {{
    background: {T['card']};
    border: 1px solid {T['border2']};
    border-radius: 16px;
    padding: 1.1rem 1.2rem;
    margin: .6rem 0;
    overflow: hidden;
    box-shadow: {_shadow_sm};
  }}
  .ocr-skeleton-header {{
    display: flex; align-items: center; gap: .75rem;
    margin-bottom: .7rem;
  }}
  .ocr-skeleton-icon {{
    font-size: 1.4rem;
    animation: pulse-dot 1.2s ease-in-out infinite;
  }}
  .ocr-skeleton-title {{
    font-size: .95rem; font-weight: 800;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
  }}
  .ocr-skeleton-sub {{
    font-size: .82rem; color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-top: 2px;
  }}

  /* ── 3-step progress row inside skeleton ── */
  .ocr-skeleton-steps {{
    display: flex; gap: 6px; margin-bottom: .75rem;
  }}
  .ocr-skeleton-step {{
    flex: 1;
    font-size: .75rem; font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    color: {T['muted']};
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-radius: 8px;
    padding: .3rem .5rem;
    text-align: center;
    opacity: .55;
    transition: opacity .3s ease, background .3s ease;
  }}
  .ocr-skeleton-step.ocr-step-active {{
    color: {_acc};
    background: {_acc_soft};
    border-color: {_acc_med};
    opacity: 1;
    animation: pulse-dot 1.4s ease-in-out infinite;
  }}

  .ocr-skeleton-doc {{
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: .8rem 1rem;
    position: relative;
    overflow: hidden;
  }}
  .ocr-skeleton-scan {{
    position: absolute; top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, {_acc}, transparent);
    animation: scanLine 2s ease-in-out infinite;
  }}
  .ocr-skeleton-line {{
    height: 9px;
    border-radius: 6px;
    margin-bottom: 8px;
    background: linear-gradient(90deg,
      {T['border']} 25%, {T['border2']} 50%, {T['border']} 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
  }}


  /* ════════════════════════════════════════════════════════════════════════
     OCR HINT BANNER
     ════════════════════════════════════════════════════════════════════════ */
  .ocr-hint-banner {{
    display: flex; align-items: flex-start; gap: .9rem;
    background: linear-gradient(135deg, {T.get('hint_bg', _surf_raised)}, {T['card']});
    border: 1.5px solid {T.get('hint_border', T['border'])};
    border-radius: 16px;
    padding: .9rem 1.1rem;
    margin-bottom: .8rem;
  }}
  .ocr-hint-icon {{ font-size: 1.3rem; flex-shrink: 0; }}
  .ocr-hint-body {{ flex: 1; }}
  .ocr-hint-title {{
    font-size: 0.95rem; font-weight: 800;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
    margin-bottom: .2rem;
  }}
  .ocr-hint-desc {{
    font-size: 0.88rem; color: {T['text2']};
    font-family: 'DM Sans', sans-serif; line-height: 1.5;
  }}
  .ocr-hint-tags {{
    display: flex; flex-wrap: wrap; gap: 5px; margin-top: .45rem;
  }}
  .ocr-hint-tag {{
    font-size: 0.9rem; font-weight: 600;
    background: {T['card']}; border: 1px solid {T['border']};
    border-radius: 20px; padding: 3px 9px;
    color: {T['text2']};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FACSIMILE PAGE
     ════════════════════════════════════════════════════════════════════════ */
  .facsimile-page-wrap {{
    text-align: center;
    padding: .6rem 0 1rem;
    margin-bottom: .6rem;
  }}
  .facsimile-page-icon {{
    font-size: 2rem;
    display: block;
    margin-bottom: .3rem;
  }}
  .facsimile-page-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.4rem; font-weight: 900;
    color: {T['text']};
    letter-spacing: -.02em;
    margin-bottom: .3rem;
  }}
  .facsimile-page-desc {{
    font-size: 0.95rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    max-width: 480px;
    margin: 0 auto;
    line-height: 1.55;
  }}
  .facsimile-page-uploader {{
    background: {_surf_raised};
    border: 2px dashed {_acc}44;
    border-radius: {_radius_lg};
    padding: 1.3rem 1.2rem;
    margin-bottom: .5rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RECALIBRA PUNTEGGI
     ════════════════════════════════════════════════════════════════════════ */
  /* ── Ricalibra Punteggi — redesign ─────────────────────────────────── */
  .rc-header-desc {{
    font-size: .8rem; color: {T['text2']};
    font-family: 'DM Sans', sans-serif; line-height: 1.5;
    margin-bottom: .9rem; padding-bottom: .65rem;
    border-bottom: 1px solid {T['border']};
  }}

  /* Exercise header row */
  .rc-ex-header {{
    display: flex; align-items: center; gap: .5rem;
    margin: .75rem 0 .4rem;
  }}
  .rc-ex-num {{
    font-size: .72rem; font-weight: 800;
    letter-spacing: .06em; text-transform: uppercase;
    color: {_acc}; font-family: 'DM Sans', sans-serif;
    background: {_acc_soft}; border: 1px solid {_acc_med};
    border-radius: 6px; padding: 2px 8px;
    flex-shrink: 0;
  }}
  .rc-ex-title {{
    font-size: .85rem; font-weight: 700;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}

  /* Item grid — 2 per row */
  .rc-items-wrap {{ margin-bottom: .3rem; }}
  .rc-item-chip {{
    display: flex; align-items: center; gap: .35rem;
    padding: .22rem 0 .1rem;
  }}
  .rc-item-badge {{
    font-size: .68rem; font-weight: 800;
    color: {T['text2']}; font-family: 'DM Sans', sans-serif;
    background: {T['border2']}66;
    border-radius: 4px; padding: 1px 6px;
    flex-shrink: 0; min-width: 20px; text-align: center;
  }}
  .rc-item-text-sm {{
    font-size: .73rem; color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1;
  }}
  /* legacy compat */
  .rc-item-text {{
    font-size: .8rem; color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1;
  }}

  /* Compact selectbox for recalibra */
  .rc-sel-wrap {{ margin-bottom: .55rem; }}
  .rc-sel-wrap [data-testid="stSelectbox"] {{ margin: 0 !important; }}
  .rc-sel-wrap [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child {{
    min-height: 30px !important;
    height: 30px !important;
    padding: 0 .5rem !important;
    font-size: .88rem !important;
    font-weight: 700 !important;
    background: {T['card2']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 6px !important;
  }}
  .rc-sel-wrap [data-testid="stSelectbox"] [data-baseweb="select"] svg {{
    width: 14px !important; height: 14px !important;
  }}

  /* Subtotal per exercise */
  .rc-ex-subtotal {{
    font-size: .75rem; font-weight: 600;
    color: {T['muted']}; font-family: 'DM Sans', sans-serif;
    text-align: right; padding: .3rem 0 .1rem;
  }}
  .rc-ex-subtotal strong {{ color: {T['text2']}; }}

  /* Grand total rows */
  .recalibra-sum-ok {{
    font-size: .88rem; font-weight: 700;
    color: {T['success']}; font-family: 'DM Sans', sans-serif;
    background: {T['success']}14;
    border: 1px solid {T['success']}33;
    border-radius: {_radius_sm}; padding: .45rem .8rem;
  }}
  .recalibra-sum-err {{
    font-size: .88rem; font-weight: 600;
    color: {T['warn']}; font-family: 'DM Sans', sans-serif;
    background: {T['warn']}14;
    border: 1px solid {T['warn']}33;
    border-radius: {_radius_sm}; padding: .45rem .8rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RUBRICA (Valutazione MIM)
     ════════════════════════════════════════════════════════════════════════ */
  .rubrica-wrap {{
    background: {_surf_overlay};
    border: 1.5px solid {T['border']};
    border-radius: {_radius_lg};
    padding: .8rem 1rem;
    margin-bottom: .6rem;
  }}
  .rubrica-header {{
    display: flex; align-items: center; gap: .5rem;
    margin-bottom: .5rem;
  }}
  .rubrica-title {{
    font-size: 0.95rem; font-weight: 800;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
  }}
  .rubrica-badge {{
    font-size: 0.9rem; font-weight: 700;
    background: {_acc_soft}; color: {_acc};
    border: 1px solid {_acc_ring};
    border-radius: 20px; padding: 2px 8px;
    margin-left: auto;
  }}
  .rubrica-content {{
    font-size: 0.97rem; color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.6;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FAB — Floating feedback button
     ════════════════════════════════════════════════════════════════════════ */
  .fab-link {{
    position: fixed; bottom: 1.2rem; right: 1.2rem;
    z-index: 998;
    background: {T['card']};
    color: {T['text2']} !important;
    font-size: 0.92rem; font-weight: 700;
    font-family: 'DM Sans', sans-serif;
    padding: .45rem .85rem;
    border-radius: 100px;
    border: 1.5px solid {T['border']};
    box-shadow: {T.get('shadow_md', '0 4px 20px rgba(0,0,0,.08)')};
    text-decoration: none !important;
    transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
  }}
  .fab-link:hover {{
    border-color: {_acc};
    color: {_acc} !important;
    box-shadow: 0 4px 24px {_acc_soft};
    transform: translateY(-2px);
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FOOTER
     ════════════════════════════════════════════════════════════════════════ */
  .app-footer {{
    text-align: center;
    font-size: 0.92rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    padding: 1.5rem 0 .5rem;
    line-height: 1.6;
    margin-top: 1rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     PERSONALIZZA WRAPPER — contenitore con alta specificità per l'expander
     ════════════════════════════════════════════════════════════════════════ */
  .personalizza-wrap {{
    margin: .8rem 0;
  }}

  /* ── Toggle Personalizzazione Avanzata ─────────────────────────────────── */
  .pers-toggle-wrap {{
    margin: .5rem 0 0;
  }}
  /* Stato CHIUSO — bianco con bordo teal */
  .pers-toggle-closed button {{
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    border: 2px solid {T['border2']} !important;
    border-radius: {_radius_lg} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.99rem !important;
    font-weight: 700 !important;
    padding: .75rem 1.1rem !important;
    text-align: left !important;
    box-shadow: 0 2px 8px {_acc}14 !important;
    transition: background .2s, border-color .2s !important;
  }}
  .pers-toggle-closed button:hover {{
    border-color: {T['accent']} !important;
    background: {T['hover']} !important;
    background-color: {T['hover']} !important;
    color: {T['accent']} !important;
    -webkit-text-fill-color: {T['accent']} !important;
  }}
  /* Stato APERTO — gradiente teal, testo bianco, angoli in basso quadrati */
  .pers-toggle-open button {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent2']} 100%) !important;
    background-color: {T['accent']} !important;
    border: 2px solid {T['accent']} !important;
    border-bottom: 2px solid {T['accent2']} !important;
    border-radius: {_radius_lg} {_radius_lg} 0 0 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.99rem !important;
    font-weight: 700 !important;
    padding: .75rem 1.1rem !important;
    text-align: left !important;
    box-shadow: 0 2px 12px {_acc}40 !important;
  }}
  .pers-toggle-open button:hover {{
    background: linear-gradient(135deg, {T['accent2']} 0%, {T['accent']} 100%) !important;
  }}
  /* Pannello corpo — connesso al pulsante aperto */
  .pers-body {{
    background: {T['card']} !important;
    border: 2px solid {T['accent']} !important;
    border-top: none !important;
    border-radius: 0 0 {_radius_lg} {_radius_lg} !important;
    padding: 1.1rem 1.2rem 1.3rem !important;
    margin-bottom: .5rem !important;
    box-shadow: 0 4px 16px {_acc}1A !important;
  }}

  /* st.container(border=True) che segue il toggle aperto.
     Streamlit usa data-testid="stVerticalBlockBorderWrapper" per container(border=True).
     Override del bordo grigio con il teal accent, collegato visivamente all'header. */
  [data-testid="stVerticalBlockBorderWrapper"] {{
    border: 2px solid {T['border2']} !important;
    border-radius: {_radius_lg} !important;
  }}
  /* Dentro pers-toggle-wrap aperto: collegato all'header senza angoli in alto */
  .pers-toggle-open ~ [data-testid="stVerticalBlockBorderWrapper"],
  .pers-toggle-open + [data-testid="stVerticalBlockBorderWrapper"],
  .pers-toggle-open ~ div > [data-testid="stVerticalBlockBorderWrapper"]:first-child {{
    border: 2px solid {T['accent']} !important;
    border-top: none !important;
    border-radius: 0 0 {_radius_lg} {_radius_lg} !important;
    background: {T['card']} !important;
    margin-top: -2px !important;
    box-shadow: 0 4px 16px {_acc}1A !important;
  }}
  .personalizza-wrap details[data-testid="stExpander"] {{
    --background-color: {_surf_raised};
    background: {_surf_raised} !important;
    border: 2px solid {T['border2']} !important;
    border-radius: {_radius_lg} !important;
    overflow: hidden !important;
    box-shadow: 0 2px 12px rgba(0,0,0,.04) !important;
  }}
  .personalizza-wrap details[data-testid="stExpander"] > summary,
  .personalizza-wrap details[data-testid="stExpander"] summary[role="button"] {{
    background-color: {_surf_raised} !important;
    background: {_surf_raised} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.97rem !important;
    font-weight: 700 !important;
    padding: .85rem 1.1rem !important;
    border-radius: 12px !important;
  }}
  .stApp .personalizza-wrap details[data-testid="stExpander"][open] > summary,
  .personalizza-wrap details[data-testid="stExpander"][open] > summary {{
    background: {_exp_open_bg} !important;
    background-color: {_exp_open_bg} !important;
    border-radius: 12px 12px 0 0 !important;
    border-bottom: {_exp_open_border} !important;
    color: {_exp_open_text} !important;
    -webkit-text-fill-color: {_exp_open_text} !important;
    color-scheme: {_color_scheme} !important;
  }}
  .stApp .personalizza-wrap details[data-testid="stExpander"][open] > summary *,
  .personalizza-wrap details[data-testid="stExpander"][open] > summary * {{
    color: {_exp_open_text} !important;
    -webkit-text-fill-color: {_exp_open_text} !important;
    background-color: transparent !important;
  }}
  .personalizza-wrap details[data-testid="stExpander"][open] > summary svg,
  .personalizza-wrap details[data-testid="stExpander"][open] > summary svg * {{
    fill: {_exp_open_text} !important;
    stroke: {_exp_open_text} !important;
  }}
  .personalizza-wrap details[data-testid="stExpander"] > summary:hover {{
    background-color: {T['hover']} !important;
    color: {_acc} !important;
    -webkit-text-fill-color: {_acc} !important;
  }}
  .personalizza-wrap details[data-testid="stExpander"] > div {{
    background: {_surf_raised} !important;
    padding: 1.1rem 1.2rem 1.3rem !important;
    border-radius: 0 0 12px 12px !important;
  }}
  .personalizza-wrap details[data-testid="stExpander"] p,
  .personalizza-wrap details[data-testid="stExpander"] label,
  .personalizza-wrap details[data-testid="stExpander"] span:not(.site-header-ai) {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     EXPANDER — widget dentro il contenuto (input, select, button, toggle)
     ════════════════════════════════════════════════════════════════════════ */

  /* Selectbox dentro expander */
  .stApp details[data-testid="stExpander"] [data-baseweb="select"] > div:first-child {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 10px !important;
  }}
  .stApp details[data-testid="stExpander"] [data-baseweb="select"] span,
  .stApp details[data-testid="stExpander"] [data-baseweb="select"] [data-value],
  .stApp details[data-testid="stExpander"] [data-baseweb="select"] div[class] {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    background: transparent !important;
  }}
  /* NumberInput dentro expander */
  .stApp details[data-testid="stExpander"] [data-testid="stNumberInput"] input {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border-radius: 10px !important;
  }}
  .stApp details[data-testid="stExpander"] [data-testid="stNumberInput"] button,
  .stApp details[data-testid="stExpander"] [data-testid="stNumberInput"] button * {{
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    border-color: {T['border']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
  }}
  /* TextArea/Input dentro expander */
  .stApp details[data-testid="stExpander"] input,
  .stApp details[data-testid="stExpander"] textarea {{
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    border: 1.5px solid {T['border']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border-radius: 10px !important;
  }}
  /* Toggle/Checkbox dentro expander */
  .stApp details[data-testid="stExpander"] [data-testid="stCheckbox"] label,
  .stApp details[data-testid="stExpander"] [data-testid="stToggle"] label {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
  }}
  /* Pulsanti secondari dentro expander (es. Applica Modifica, Applica Punteggi) */
  .stApp details[data-testid="stExpander"] .stButton > button {{
    color-scheme: {_color_scheme} !important;
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 10px !important;
  }}
  .stApp details[data-testid="stExpander"] .stButton > button:hover {{
    background: {T['hover']} !important;
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
    -webkit-text-fill-color: {T['accent']} !important;
  }}
  /* Pulsante primary dentro expander */
  .stApp details[data-testid="stExpander"] .stButton > button[kind="primary"],
  .stApp details[data-testid="stExpander"] .stButton > button[data-testid="baseButton-primary"] {{
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-color: transparent !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FILE UPLOADER — Streamlit override (usa token tema: chiaro su foresta/chiaro)
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stFileUploader"] {{
    background: transparent !important;
    border-radius: 12px !important;
    padding: 0 !important;
  }}
  /* Hide the default cloud-upload SVG icon from Streamlit */
  [data-testid="stFileUploaderDropzone"] svg {{
    display: none !important;
  }}
  [data-testid="stFileUploaderDropzone"],
  section[data-testid="stFileUploaderDropzone"] {{
    background: {T['bg2']} !important;
    border: 1.5px dashed {T['border2']} !important;
    border-radius: 12px !important;
    color-scheme: {_color_scheme} !important;
    padding: .65rem 1rem !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: .75rem !important;
    transition: border-color .15s, background .15s !important;
  }}
  [data-testid="stFileUploaderDropzone"]:hover,
  section[data-testid="stFileUploaderDropzone"]:hover {{
    border-color: {_acc} !important;
    background: {_acc}0A !important;
  }}
  /* Instructions block: shrink and tidy */
  [data-testid="stFileDropzoneInstructions"] {{
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 1px !important;
  }}
  [data-testid="stFileDropzoneInstructions"] *,
  [data-testid="stFileDropzoneInstructions"] span,
  [data-testid="stFileDropzoneInstructions"] p,
  [data-testid="stFileDropzoneInstructions"] div {{
    color: {T['text2']} !important;
    -webkit-text-fill-color: {T['text2']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.8rem !important;
    line-height: 1.3 !important;
    margin: 0 !important;
  }}
  [data-testid="stFileDropzoneInstructions"] small,
  [data-testid="stFileDropzoneInstructions"] span + span,
  [data-testid="stFileDropzoneInstructions"] p + p {{
    color: {T['muted']} !important;
    -webkit-text-fill-color: {T['muted']} !important;
    font-size: 0.7rem !important;
  }}
  [data-testid="stFileUploaderDropzone"] span,
  [data-testid="stFileUploaderDropzone"] p,
  [data-testid="stFileUploaderDropzone"] div:not(button):not([data-testid]) {{
    color: {T['text2']} !important;
    -webkit-text-fill-color: {T['text2']} !important;
  }}
  /* "Browse files" button — accent filled */
  [data-testid="stFileUploaderDropzone"] button,
  section[data-testid="stFileUploaderDropzone"] button {{
    background: {_acc} !important;
    color: #0D1117 !important;
    -webkit-text-fill-color: #0D1117 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
    font-size: 0.78rem !important;
    font-family: 'DM Sans', sans-serif !important;
    cursor: pointer !important;
    padding: .4rem .85rem !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
    transition: filter .12s !important;
  }}
  [data-testid="stFileUploaderDropzone"] button:hover,
  section[data-testid="stFileUploaderDropzone"] button:hover {{
    filter: brightness(1.12) !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     TOAST — Streamlit override
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stToast"] {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: {_radius_lg} !important;
    box-shadow: 0 8px 32px rgba(0,0,0,.15) !important;
  }}
  [data-testid="stToast"] [data-testid="stMarkdownContainer"] {{
    color: {T['text']} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     BACK BUTTON — Discrete, piccolo, allineato a sinistra (uniforme in tutta l'app)
     ════════════════════════════════════════════════════════════════════════ */
  .btn-back-discrete > div.stButton > button,
  .btn-back-discrete .stButton > button {{
    background: transparent !important;
    background-color: transparent !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border: 1px solid {T['border']} !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 6px 12px !important;
    min-height: 32px !important;
    border-radius: 6px !important;
    width: auto !important;
    letter-spacing: -.01em;
  }}
  .btn-back-discrete > div.stButton > button:hover,
  .btn-back-discrete .stButton > button:hover {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border-color: {T['accent']} !important;
    background: {T['hover']} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     UNDO BUTTON — "↩️ Annulla modifica"
     Usa CSS :has() perché st.markdown è un sibling (non parent) del button.
     Seleziona l'element-container che segue quello con il marker .btn-undo-wrap.
     ════════════════════════════════════════════════════════════════════════ */
  .element-container:has(.btn-undo-wrap) + .element-container button,
  div:has(> .btn-undo-wrap) + div button,
  div:has(.btn-undo-wrap) + div .stButton > button {{
    background: transparent !important;
    background-color: transparent !important;
    color: {T['accent']} !important;
    -webkit-text-fill-color: {T['accent']} !important;
    border: 1.5px solid {T['accent']} !important;
    border-radius: 10px !important;
    font-size: 0.89rem !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    box-shadow: none !important;
    color-scheme: {_color_scheme} !important;
  }}
  .element-container:has(.btn-undo-wrap) + .element-container button:hover,
  div:has(.btn-undo-wrap) + div .stButton > button:hover {{
    background: {T['accent_light']} !important;
    background-color: {T['accent_light']} !important;
    color: {T['accent2']} !important;
    -webkit-text-fill-color: {T['accent2']} !important;
    border-color: {T['accent2']} !important;
    box-shadow: 0 2px 10px {T['accent']}22 !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     NAV SECONDARY BUTTON — "← Torna alla revisione"
     Stesso approccio :has() con marker .btn-nav-secondary-wrap
     ════════════════════════════════════════════════════════════════════════ */
  .element-container:has(.btn-nav-secondary-wrap) + .element-container button,
  div:has(> .btn-nav-secondary-wrap) + div button,
  div:has(.btn-nav-secondary-wrap) + div .stButton > button {{
    background: transparent !important;
    background-color: transparent !important;
    color: {T['text2']} !important;
    -webkit-text-fill-color: {T['text2']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 10px !important;
    font-size: 0.91rem !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    box-shadow: none !important;
    color-scheme: {_color_scheme} !important;
  }}
  .element-container:has(.btn-nav-secondary-wrap) + .element-container button:hover,
  div:has(.btn-nav-secondary-wrap) + div .stButton > button:hover {{
    background: {T['hover']} !important;
    background-color: {T['hover']} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border-color: {T['accent']} !important;
    box-shadow: 0 2px 8px {T['accent']}18 !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     TEMPLATE GALLERY (optional)
     ════════════════════════════════════════════════════════════════════════ */
  .tmpl-gallery-wrap {{
    display: flex; flex-wrap: wrap; gap: 8px;
    margin: .5rem 0;
  }}
  .tmpl-card {{
    background: {_surf_overlay};
    border: 1.5px solid {T['border']};
    border-radius: 10px;
    padding: .5rem .7rem;
    cursor: pointer;
    transition: border-color .15s, box-shadow .15s;
    flex: 0 1 calc(50% - 4px);
    min-width: 130px;
  }}
  .tmpl-card:hover {{
    border-color: {_acc_ring};
    box-shadow: 0 2px 12px {_acc_soft};
  }}
  .tmpl-card-sel {{
    border-color: {_acc} !important;
    background: {_acc_soft} !important;
  }}
  .tmpl-card-title {{
    font-size: 0.96rem; font-weight: 700;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
    margin-bottom: 2px;
  }}
  .tmpl-card-desc {{
    font-size: 0.88rem;
    color: {T['muted']}; font-family: 'DM Sans', sans-serif;
    line-height: 1.4;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     DOWNLOAD BUTTONS
     ════════════════════════════════════════════════════════════════════════ */
  @keyframes dl-glow {{
    0%, 100% {{ box-shadow: 0 0 0 0 {_acc}44, 0 4px 20px {_acc}30 !important; }}
    50%       {{ box-shadow: 0 0 0 6px {_acc}00, 0 4px 28px {_acc}55 !important; }}
  }}
  [data-testid="stDownloadButton"] > button {{
    background: linear-gradient(135deg, {_acc} 0%, {_acc}cc 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #0D1117 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 800 !important;
    font-size: 1.08rem !important;
    letter-spacing: .02em !important;
    min-height: 62px !important;
    padding: .9rem 1.8rem !important;
    animation: dl-glow 2.4s ease-in-out infinite !important;
    transition: filter .15s ease, transform .12s ease !important;
  }}
  [data-testid="stDownloadButton"] > button:hover {{
    filter: brightness(1.12) !important;
    transform: translateY(-2px) !important;
    animation: none !important;
    box-shadow: 0 6px 28px {_acc}55 !important;
  }}
  [data-testid="stDownloadButton"] > button:active {{
    transform: translateY(0) !important;
    filter: brightness(.96) !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     GENERATING PROGRESS — Animated bar
     ════════════════════════════════════════════════════════════════════════ */
  @keyframes progress-pulse {{
    0%, 100% {{ opacity: .7; }}
    50% {{ opacity: 1; }}
  }}
  .gen-progress-wrap {{
    margin: .6rem 0 1rem;
  }}
  .gen-progress-label {{
    font-size: 0.89rem; font-weight: 600;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 6px;
    animation: progress-pulse 1.5s ease-in-out infinite;
  }}
  .gen-progress-bar {{
    background: {T['border']};
    border-radius: 100px;
    height: 8px;
    overflow: hidden;
  }}
  .gen-progress-fill {{
    background: linear-gradient(90deg, {_acc}, {_acc}cc);
    height: 100%;
    border-radius: 100px;
    transition: width .4s ease;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FEATURE #3 — Quick Regen: classi legacy mantenute per compatibilità
     (il blocco principale è definito in fondo, sezione IDEA #3)
     ════════════════════════════════════════════════════════════════════════ */

  /* ════════════════════════════════════════════════════════════════════════
     VARIANT CARDS — Download page (Fila B, BES/DSA, Soluzioni)
     ════════════════════════════════════════════════════════════════════════ */
  .variant-section-label {{
    font-size: 0.9rem;
    font-weight: 800;
    color: {T['muted']};
    letter-spacing: .1em;
    font-family: 'DM Sans', sans-serif;
    text-transform: uppercase;
    margin-bottom: .55rem;
  }}
  /* ── Variant cards row: stretch columns to equal height ────────────── */
  [data-testid="stHorizontalBlock"]:has(.variant-card) {{
    align-items: stretch !important;
  }}
  [data-testid="stHorizontalBlock"]:has(.variant-card) > [data-testid="stColumn"] {{
    display: flex !important;
    flex-direction: column !important;
  }}
  [data-testid="stHorizontalBlock"]:has(.variant-card) > [data-testid="stColumn"] > [data-testid="stVerticalBlock"],
  [data-testid="stHorizontalBlock"]:has(.variant-card) > [data-testid="stColumn"] > div {{
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
  }}
  [data-testid="stHorizontalBlock"]:has(.variant-card) .stMarkdown,
  [data-testid="stHorizontalBlock"]:has(.variant-card) .stMarkdown > div {{
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100% !important;
  }}

  .variant-card {{
    background: {T['card']};
    border: 1px solid {T['border']};
    border-radius: {_radius_lg};
    padding: 1.1rem 1rem 1rem;
    margin-bottom: .35rem;
    display: flex;
    flex-direction: column;
    gap: .5rem;
    flex: 1;
    height: 180px;  /* Altezza fissa invece di min-height */
    position: relative;
    overflow: hidden;
    transition: border-color .2s ease, box-shadow .2s ease, transform .15s ease;
    box-sizing: border-box;
  }}
  .variant-card:hover {{
    transform: translateY(-2px);
  }}
  .variant-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
  }}
  .variant-card:hover {{
    box-shadow: {T.get('shadow_md', '0 4px 20px rgba(0,0,0,.1)')};
  }}
  /* Blue (Fila B) */
  .variant-card-blue::before {{ background: linear-gradient(90deg, {_acc}, {T.get('accent2', _acc)}); }}
  .variant-card-blue:hover {{ border-color: {_acc}66; }}
  /* Violet (BES/DSA) */
  .variant-card-violet::before {{ background: linear-gradient(90deg, #7C3AED, #A78BFA); }}
  .variant-card-violet:hover {{ border-color: #7C3AED66; }}
  /* Green (Soluzioni) */
  .variant-card-green::before {{ background: linear-gradient(90deg, #059669, #34D399); }}
  .variant-card-green:hover {{ border-color: #05966966; }}
  /* Orange (Griglia di Valutazione) */
  .variant-card-orange::before {{ background: linear-gradient(90deg, #D97706, #F59E0B); }}
  .variant-card-orange:hover {{ border-color: #D9770666; }}
  /* Teal (Formato Word / DOCX) */
  .variant-card-teal::before {{ background: linear-gradient(90deg, #0891B2, #22D3EE); }}
  .variant-card-teal:hover {{ border-color: #0891B266; }}

  /* Icon + Title inline row */
  .variant-card-header {{
    display: flex;
    align-items: center;
    gap: .5rem;
    margin-bottom: .1rem;
  }}
  .variant-card-icon {{
    font-size: 1.4rem;
    line-height: 1;
    flex-shrink: 0;
  }}
  .variant-card-title {{
    font-size: 1.05rem;
    font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.2;
  }}
  .variant-card-desc {{
    font-size: 0.94rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.45;
    flex-grow: 1;  /* Fa occupare lo spazio rimanente */
    display: flex;
    flex-direction: column;
    justify-content: flex-start;  /* Allinea il testo in alto */
    overflow: hidden;  /* Nasconde il testo che trabocca */
    text-overflow: ellipsis;  /* Aggiunge "..." se il testo è troppo lungo */
    display: -webkit-box;
    -webkit-line-clamp: 3;  /* Limita a 3 linee */
    -webkit-box-orient: vertical;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     DOWNLOAD CTA — pulsante ROSSO VIBRANTE v2.0 - UPDATED 2025-03-10
     ════════════════════════════════════════════════════════════════════════ */
  @keyframes dl-shimmer {{
    0%   {{ background-position: 200% center; }}
    100% {{ background-position: -200% center; }}
  }}
  @keyframes dl-pulse-red {{
    0%, 100% {{ 
      box-shadow: 
        0 10px 40px rgba(220,38,38,0.4), 
        0 4px 16px rgba(220,38,38,0.3),
        inset 0 2px 0 rgba(255,255,255,0.3);
    }}
    50% {{ 
      box-shadow: 
        0 14px 48px rgba(220,38,38,0.6), 
        0 6px 20px rgba(220,38,38,0.4),
        inset 0 2px 0 rgba(255,255,255,0.4);
    }}
  }}
  .dl-cta-wrap {{
    margin-bottom: 1.5rem;
    position: relative;
    z-index: 10;
  }}
  /* specificità MASSIMA (0,0,3,3) — batte TUTTI gli altri stili di download */
  .dl-cta-wrap div.stDownloadButton > button,
  .dl-cta-wrap [data-testid="stDownloadButton"] > button,
  div[data-testid="stDownloadButton"] > button,
  button[k*="dl_pdf"] {{
    background: linear-gradient(
      135deg,
      #DC2626 0%,      /* Rosso vivo */
      #EF4444 20%,     /* Rosso brillante */
      #F87171 40%,     /* Rosso chiaro */
      #EF4444 60%,     /* Rosso brillante */
      #DC2626 80%,     /* Rosso vivo */
      #991B1B 100%     /* Rosso scuro */
    ) !important;
    background-size: 300% auto !important;
    background-position: 0% 50% !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border: 3px solid rgba(255,255,255,0.3) !important;
    border-radius: 18px !important;
    font-size: 1.3rem !important;
    font-weight: 900 !important;
    letter-spacing: .07em !important;
    min-height: 84px !important;
    padding: 1.3rem 2.2rem !important;
    box-shadow: 
      0 10px 40px rgba(220,38,38,0.4), 
      0 4px 16px rgba(220,38,38,0.3),
      inset 0 2px 0 rgba(255,255,255,0.3),
      0 0 0 1px rgba(255,255,255,0.1) !important;
    animation: 
      dl-shimmer 3s linear infinite,
      dl-pulse-red 2s ease-in-out infinite !important;
    transition: all .3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    font-family: 'DM Sans', sans-serif !important;
    text-transform: uppercase !important;
    position: relative;
    overflow: hidden;
    text-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
  }}
  .dl-cta-wrap div.stDownloadButton > button::before,
  .dl-cta-wrap [data-testid="stDownloadButton"] > button::before {{
    content: '';
    position: absolute;
    top: 0; left: -100%; width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    transition: left 0.6s ease;
  }}
  .dl-cta-wrap div.stDownloadButton > button:hover::before,
  .dl-cta-wrap [data-testid="stDownloadButton"] > button:hover::before {{
    left: 100%;
  }}
  .dl-cta-wrap div.stDownloadButton > button:hover,
  .dl-cta-wrap [data-testid="stDownloadButton"] > button:hover,
  div[data-testid="stDownloadButton"] > button:hover,
  button[k*="dl_pdf"]:hover {{
    filter: brightness(1.2) saturate(1.3) !important;
    box-shadow: 
      0 16px 56px rgba(220,38,38,0.6), 
      0 8px 24px rgba(220,38,38,0.4),
      inset 0 2px 0 rgba(255,255,255,0.4),
      0 0 0 2px rgba(255,255,255,0.2) !important;
    transform: translateY(-4px) scale(1.02) !important;
    animation: none !important;
    background-size: 200% auto !important;
    background-position: 50% 0% !important;
    border-color: rgba(255,255,255,0.4) !important;
  }}
  .dl-cta-wrap div.stDownloadButton > button:active,
  .dl-cta-wrap [data-testid="stDownloadButton"] > button:active,
  div[data-testid="stDownloadButton"] > button:active,
  button[k*="dl_pdf"]:active {{
    transform: translateY(-2px) scale(.98) !important;
    filter: brightness(0.95) saturate(1.1) !important;
    animation: none !important;
    box-shadow: 
      0 8px 32px rgba(220,38,38,0.7), 
      0 4px 16px rgba(220,38,38,0.5),
      inset 0 1px 0 rgba(255,255,255,0.3) !important;
  }}

  /* CTA variante (per colleghi) — definita una sola volta più in basso */

  /* ════════════════════════════════════════════════════════════════════════
     STORICO — Sidebar migliorato
     (chip filtro, stella, pulsante elimina; card definita più sotto)
     ════════════════════════════════════════════════════════════════════════ */

  /* Filtro materia chips (sidebar) */
  .storico-filter {{
    display: flex;
    align-items: center;
    gap: .3rem;
    margin-bottom: .5rem;
    flex-wrap: wrap;
  }}
  .storico-filter-chip {{
    font-size: 0.9rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    border: 1px solid {T['border']};
    background: transparent;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-filter-chip-active {{
    background: {_acc}20;
    border-color: {_acc};
    color: {_acc};
  }}
  /* Stella e delete in storico */
  .stella-btn, .stella-btn-on {{
    margin: 0;
  }}
  .stella-btn button, .stella-btn-on button {{
    background: transparent !important;
    border: none !important;
    padding: 2px 4px !important;
    font-size: 0.89rem !important;
    min-height: auto !important;
    line-height: 1 !important;
  }}
  .stella-btn-on button {{
    color: {_acc} !important;
  }}
  .elimina-btn button {{
    background: transparent !important;
    border: 1px dashed {T['border2']} !important;
    padding: 2px 6px !important;
    font-size: 0.92rem !important;
    min-height: auto !important;
    opacity: .5;
    transition: all .15s;
  }}
  .elimina-btn button:hover {{
    opacity: 1;
    border-color: {T['error']} !important;
    color: {T['error']} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RESPONSIVE
     ════════════════════════════════════════════════════════════════════════ */
  @media (max-width: 767px) {{
    .onboarding-hint-banner {{
      flex-direction: column;
      gap: .6rem;
    }}
    .facsimile-shortcut {{ display: none; }}
    .hero-title {{ font-size: 1.3rem; }}
    .home-landing-title {{ font-size: 1.3rem; }}
    .mcard {{ min-height: auto; }}
    .page-header-name {{
      font-size: 1.6rem;
    }}
    .page-header-icon {{ font-size: 1.6rem; }}
    .tally-features {{ gap: 5px 4px; }}
    .tally-feat-pill {{ font-size: 0.94rem; }}
    .variant-card {{ height: 180px !important; }}
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     IDEA #3 — QUICK REGEN (variante rapida) — action section header
     Il div è solo un'etichetta sopra i due pulsanti, senza dashed box
     che creerebbe un contenitore visivamente orfano.
     ═══════════════════════════════════════════════════════════════════════ */

  .quick-regen-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: .4rem .2rem .3rem;
    margin-bottom: .35rem;
  }}
  .quick-regen-label {{
    font-size: 0.96rem;
    font-family: 'DM Sans', sans-serif;
    color: {T["text2"]};
    line-height: 1.4;
    font-weight: 600;
  }}
  .quick-regen-label strong {{
    color: {T["text"]};
    font-weight: 800;
  }}
  .quick-regen-hint {{
    display: inline;
    font-size: 0.96rem;
    color: {T["text2"]};
    font-weight: 400;
  }}
  .quick-regen-sep {{
    display: inline-block;
    margin: 0 .3rem;
    color: {T["muted"]};
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     IDEA #5 — SHARE WITH DEPARTMENT
     ═══════════════════════════════════════════════════════════════════════ */

  .share-dept-card {{
    background: linear-gradient(135deg, {T.get("card2", T["card"])} 0%, {T["card"]} 100%);
    border: 1px solid {T["border"]};
    border-radius: {_radius_lg};
    padding: 1rem 1.2rem;
    margin-bottom: .6rem;
  }}
  .share-dept-header {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }}
  .share-dept-icon {{
    font-size: 1.5rem;
    flex-shrink: 0;
    margin-top: 2px;
  }}
  .share-dept-title-wrap {{
    flex: 1;
  }}
  .share-dept-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 0.99rem;
    font-weight: 800;
    color: {T["text"]};
    margin-bottom: 4px;
  }}
  .share-dept-subtitle {{
    font-size: 0.96rem;
    color: {T["text2"]};
    line-height: 1.45;
  }}

  .share-link-box {{
    background: {T.get("card2", T["card"])};
    border: 2px solid {T["success"]}44;
    border-radius: 10px;
    padding: .7rem .9rem;
    margin-bottom: .5rem;
  }}
  .share-link-status {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
    font-weight: 700;
    color: {T["success"]};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 6px;
  }}
  .share-link-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: {T["success"]};
    animation: pulse-dot 2s ease-in-out infinite;
  }}
  .share-link-url {{
    font-size: 0.92rem;
    color: {T["muted"]};
    font-family: 'DM Sans', monospace;
    word-break: break-all;
    padding: .3rem .5rem;
    background: {T["bg"]};
    border-radius: 6px;
    border: 1px solid {T["border"]};
  }}

  /* ── Shared view (link aperto da collega) ──────────────────────── */
  .shared-view-banner {{
    background: linear-gradient(135deg, {T.get("card2", T["card"])} 0%, {T["card"]} 100%);
    border: 2px solid {T["accent"]}55;
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
  }}
  .shared-view-header {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: .7rem;
  }}
  .shared-view-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 900;
    color: {T["accent"]};
  }}
  .shared-view-meta {{
    font-size: 0.88rem;
    color: {T["text2"]};
    margin-top: 2px;
  }}
  .shared-view-badges {{
    display: flex;
    gap: .4rem;
    flex-wrap: wrap;
  }}
  .shared-view-badge {{
    background: {T.get("card2", T["card"])};
    border: 1px solid {T["border"]};
    border-radius: 8px;
    padding: .2rem .6rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: {T["text2"]};
    font-family: 'DM Sans', sans-serif;
  }}
  /* CTA variante (per colleghi) */
  .shared-cta-card {{
    background: linear-gradient(135deg, {T['warn']}22 0%, {T['warn']}0e 100%);
    border: 2px solid {T['warn']}40;
    border-radius: {_radius_lg};
    padding: 1.1rem 1.3rem;
    margin-bottom: .7rem;
    text-align: center;
  }}
  .shared-cta-icon {{
    font-size: 1.8rem;
    margin-bottom: .3rem;
  }}
  .shared-cta-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    font-weight: 800;
    color: {T['warn']};
    margin-bottom: .3rem;
  }}
  .shared-cta-desc {{
    font-size: 0.88rem;
    color: {T['text2']};
    line-height: 1.45;
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     STORICO — Card redesign
     ═══════════════════════════════════════════════════════════════════════ */

  .storico-card {{
    margin-top: .5rem;
    padding: .55rem .65rem .45rem;
    border-radius: 8px;
    border-left: 3px solid transparent;
    background: transparent;
    transition: border-left-color {_transition}, background {_transition};
  }}
  .storico-card:hover {{
    border-left-color: {_SB_ACCENT};
    background: {_SB_BORDER}33;
  }}
  .storico-card-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2px;
  }}
  .storico-card-mat {{
    font-size: 0.88rem;
    font-weight: 700;
    color: {_SB_TEXT};
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-date {{
    font-size: 0.9rem;
    color: {_SB_MUTED};
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-arg {{
    font-size: 0.94rem;
    color: {_SB_TEXT}CC;
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 3px;
    line-height: 1.3;
  }}
  .storico-card-meta {{
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.9rem;
    color: {_SB_MUTED};
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-scu {{
    background: {_SB_INPUT_BG};
    padding: 1px 6px;
    border-radius: 4px;
    border: 1px solid {_SB_BORDER};
  }}
  .storico-card-nes {{
    opacity: .8;
  }}
  .storico-card-badges {{
    display: flex;
    gap: 3px;
    margin-top: 4px;
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     LANDING FEATURE CARDS — fallback per st_yled.badge_card_one
     ═══════════════════════════════════════════════════════════════════════ */
  .landing-fe.variant-card {{
    background: {T['card']};
    border: 1px solid {T['border']};
    border-radius: {_radius_lg};
    padding: 1.2rem 1rem;
    position: relative;
    cursor: pointer;
    min-height: 160px;  /* Altezza minima fissa per tutte le cards */
    height: 100%;  /* Assicura che tutte le cards siano della stessa altezza */
    display: flex;
    flex-direction: column;
    transition: border-color .2s ease, box-shadow .2s ease, transform .15s ease;
    box-sizing: border-box;
  }}
  .landing-feat-card:hover {{
    border-color: {_acc};
    box-shadow: {_shadow_md};
    transform: translateY(-4px);
  }}
  .landing-feat-badge {{
    display: inline-block;
    font-size: 0.9rem;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
    background: {_acc_soft};
    color: {_acc};
    border: 1px solid {_acc_med};
    border-radius: 20px;
    padding: 3px 10px;
    margin-bottom: .65rem;
    font-family: 'DM Sans', sans-serif;
  }}
  .landing-feat-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.02rem;
    font-weight: 800;
    color: {T['text']};
    margin-bottom: .4rem;
    line-height: 1.25;
  }}
  .landing-feat-desc {{
    font-size: 0.93rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     LANDING — Section headers & kicker labels
     ════════════════════════════════════════════════════════════════════════ */
  .landing-kicker {{
    display: inline-block;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: {_acc};
    font-family: 'DM Sans', sans-serif;
    background: {_acc_soft};
    border: 1px solid {_acc_med};
    border-radius: 20px;
    padding: .22rem .75rem;
    margin-bottom: 1.1rem;
  }}
  .landing-section-kicker {{
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: {_acc};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .45rem;
  }}
  .landing-section-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.65rem;
    font-weight: 900;
    color: {T['text']};
    letter-spacing: -.025em;
    line-height: 1.2;
    margin-bottom: .5rem;
  }}
  .landing-section-sub {{
    font-size: .95rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.6;
    max-width: 460px;
    margin: 0 auto;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     PREVIEW GALLERY — "Cosa aspettarsi"
     ════════════════════════════════════════════════════════════════════════ */
  .preview-gallery-section {{
    position: relative;
    margin: 0 -1rem;
  }}
  .preview-gallery {{
    display: flex;
    gap: 1rem;
    overflow-x: auto;
    padding: .6rem 1.5rem 1.1rem;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    scrollbar-color: {_acc_med} transparent;
  }}
  .preview-gallery::-webkit-scrollbar {{ height: 4px; }}
  .preview-gallery::-webkit-scrollbar-thumb {{ background: {_acc_med}; border-radius: 2px; }}
  .preview-gallery::-webkit-scrollbar-track {{ background: transparent; }}
  .preview-gallery-fade {{
    position: absolute;
    right: 0; top: 0; bottom: 1.1rem;
    width: 64px;
    background: linear-gradient(to right, transparent, {T['bg']});
    pointer-events: none;
  }}
  .preview-gallery-hint {{
    text-align: center;
    font-size: .72rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    padding: 0 0 .6rem;
    letter-spacing: .05em;
  }}
  .preview-doc {{
    flex: 0 0 194px;
    background: #f5f6f8;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,.24), 0 1px 4px rgba(0,0,0,.08);
    scroll-snap-align: start;
    transition: transform .22s ease, box-shadow .22s ease;
  }}
  .preview-doc:hover {{
    transform: translateY(-6px) scale(1.015);
    box-shadow: 0 14px 40px rgba(0,0,0,.32), 0 2px 6px rgba(0,0,0,.1);
  }}
  .preview-doc-header {{
    padding: .62rem .78rem .52rem;
    color: #fff;
  }}
  .preview-doc-subject {{
    font-size: .78rem;
    font-weight: 800;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: .01em;
    margin-bottom: .1rem;
  }}
  .preview-doc-class {{
    font-size: .61rem;
    font-weight: 500;
    opacity: .88;
    font-family: 'DM Sans', sans-serif;
  }}
  .preview-doc-body {{
    padding: .62rem .7rem .68rem;
    background: #f5f6f8;
  }}
  .preview-doc-title {{
    font-size: .66rem;
    font-weight: 800;
    color: #1c1c2e;
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .26rem;
    line-height: 1.3;
  }}
  .preview-doc-meta {{
    font-size: .52rem;
    color: #888;
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .52rem;
    padding-bottom: .36rem;
    border-bottom: 1px solid #ddd;
  }}
  .preview-doc-ex {{ margin-bottom: .4rem; }}
  .preview-doc-ex-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: .16rem;
  }}
  .preview-doc-ex-label {{
    font-size: .59rem;
    font-weight: 800;
    color: #1c1c2e;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: .01em;
  }}
  .preview-doc-ex-pts {{
    font-size: .51rem;
    font-weight: 700;
    color: #fff;
    border-radius: 8px;
    padding: 1px 5px;
    font-family: 'DM Sans', sans-serif;
  }}
  .preview-doc-ex-text {{
    font-size: .56rem;
    color: #555;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.42;
    margin-bottom: .2rem;
  }}
  .preview-doc-inline {{
    font-size: .56rem;
    color: #333;
    font-family: 'DM Sans', sans-serif;
    margin: .18rem 0 .26rem;
    padding-left: .35rem;
    line-height: 1.5;
  }}
  .preview-doc-lines {{ display: flex; flex-direction: column; gap: 3px; }}
  .preview-doc-line {{ height: 1.5px; background: #d2d2d2; border-radius: 1px; width: 100%; }}
  .preview-doc-line.short {{ width: 56%; }}
  .preview-doc-footer {{
    margin-top: .42rem;
    padding-top: .32rem;
    border-top: 1px solid #e0e0e0;
    font-size: .51rem;
    color: #aaa;
    font-family: 'DM Sans', sans-serif;
    text-align: right;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     LIGHT THEME OVERRIDES — applicate solo su temi chiari (Giorno, Foresta)
     Forza ogni widget Streamlit a usare la palette del tema in modo coerente.
     ════════════════════════════════════════════════════════════════════════ */

  {'''
  /* ── Reset background globale ── */
  .stApp,
  .main,
  section.main,
  [data-testid="stAppViewContainer"] {{
    background-color: ''' + T['bg'] + ''' !important;
  }}

  /* ── Streamlit header e toolbar ── */
  header[data-testid="stHeader"] {{
    background: ''' + T['bg'] + ''' !important;
    border-bottom: 1px solid ''' + T['border2'] + ''' !important;
  }}

  /* ── Form widgets: input, textarea, number ── */
  .stApp [data-testid="stTextInput"] input,
  .stApp [data-testid="stTextArea"] textarea,
  .stApp [data-testid="stNumberInput"] input,
  .stApp [data-testid="stDateInput"] input {{
    background-color: ''' + T['card'] + ''' !important;
    background: ''' + T['card'] + ''' !important;
    color: ''' + T['text'] + ''' !important;
    -webkit-text-fill-color: ''' + T['text'] + ''' !important;
    caret-color: ''' + T['text'] + ''' !important;
    border: 1.5px solid ''' + T['border2'] + ''' !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.06) !important;
    color-scheme: light !important;
  }}
  /* ── Popover/dropdown search header su tema chiaro ── */
  [data-baseweb="popover"] [data-baseweb="input"],
  [data-baseweb="popover"] [data-baseweb="input"] > div,
  [data-baseweb="popover"] [data-baseweb="base-input"],
  [data-baseweb="popover"] input,
  [data-baseweb="popover"] [data-baseweb="block"] {{
    background: ''' + T['card'] + ''' !important;
    background-color: ''' + T['card'] + ''' !important;
    color: ''' + T['text'] + ''' !important;
    -webkit-text-fill-color: ''' + T['text'] + ''' !important;
    caret-color: ''' + T['text'] + ''' !important;
    color-scheme: light !important;
  }}
  .stApp [data-testid="stTextInput"] input:focus,
  .stApp [data-testid="stTextArea"] textarea:focus,
  .stApp [data-testid="stNumberInput"] input:focus {{
    border-color: ''' + T['accent'] + ''' !important;
    box-shadow: 0 0 0 3px ''' + T['accent'] + '''22 !important;
  }}

  /* ── Selectbox & MultiSelect ── */
  .stApp [data-testid="stSelectbox"] > div > div,
  .stApp [data-testid="stMultiSelect"] > div > div,
  .stApp .stSelectbox [data-baseweb="select"] > div,
  .stApp .stTextArea [data-baseweb="textarea"],
  .stApp .stTextInput [data-baseweb="input"] {{
    background-color: ''' + T['card'] + ''' !important;
    background: ''' + T['card'] + ''' !important;
    border-color: ''' + T['border2'] + ''' !important;
    border-radius: 12px !important;
  }}
  .stApp [data-testid="stSelectbox"] span,
  .stApp [data-testid="stSelectbox"] div[class] {{
    color: ''' + T['text'] + ''' !important;
    -webkit-text-fill-color: ''' + T['text'] + ''' !important;
  }}
  .stApp [data-testid="stSelectbox"] svg,
  .stApp [data-testid="stMultiSelect"] svg {{
    fill: ''' + T['text2'] + ''' !important;
    stroke: ''' + T['text2'] + ''' !important;
  }}

  /* ── Labels e testi widget ── */
  .stApp [data-testid="stWidgetLabel"] label,
  .stApp [data-testid="stWidgetLabel"] p,
  .stApp label, .stApp p {{
    color: ''' + T['text'] + ''' !important;
    -webkit-text-fill-color: ''' + T['text'] + ''' !important;
  }}
  .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
    color: ''' + T['text'] + ''' !important;
  }}

  /* ── Markdown container ── */
  .stApp [data-testid="stMarkdownContainer"] p,
  .stApp [data-testid="stMarkdownContainer"] span,
  .stApp [data-testid="stMarkdownContainer"] li {{
    color: ''' + T['text'] + ''' !important;
  }}

  /* ── Metric ── */
  .stApp [data-testid="stMetricValue"],
  .stApp [data-testid="stMetricLabel"],
  .stApp [data-testid="stMetricDelta"] {{
    color: ''' + T['text'] + ''' !important;
  }}

  /* ── Alert boxes ── */
  .stApp [data-testid="stInfo"] {{
    background-color: ''' + T['accent'] + '''12 !important;
    border-color: ''' + T['accent'] + '''44 !important;
    color: ''' + T['text'] + ''' !important;
  }}
  .stApp [data-testid="stSuccess"] {{
    background-color: ''' + T['success'] + '''12 !important;
    border-color: ''' + T['success'] + '''44 !important;
    color: ''' + T['text'] + ''' !important;
  }}
  .stApp [data-testid="stWarning"] {{
    background-color: ''' + T['warn'] + '''12 !important;
    border-color: ''' + T['warn'] + '''44 !important;
    color: ''' + T['text'] + ''' !important;
  }}
  .stApp [data-testid="stError"] {{
    background-color: ''' + T['error'] + '''12 !important;
    border-color: ''' + T['error'] + '''44 !important;
    color: ''' + T['text'] + ''' !important;
  }}

  /* ── Number input step buttons ── */
  .stApp [data-testid="stNumberInput"] button {{
    background: ''' + T['card'] + ''' !important;
    border-color: ''' + T['border2'] + ''' !important;
    color: ''' + T['text'] + ''' !important;
  }}

  /* ── Slider ── */
  .stApp [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
    background: ''' + T['accent'] + ''' !important;
    border-color: ''' + T['accent'] + ''' !important;
  }}

  /* ── Checkbox & Toggle ── */
  .stApp .stCheckbox label, .stApp .stToggle label {{
    color: ''' + T['text'] + ''' !important;
  }}

  /* ── File uploader ── */
  .stApp [data-testid="stFileUploader"] {{
    background: ''' + T['card'] + ''' !important;
    border-color: ''' + T['border2'] + ''' !important;
  }}
  .stApp [data-testid="stFileUploader"] label,
  .stApp [data-testid="stFileUploader"] p,
  .stApp [data-testid="stFileUploader"] span,
  .stApp [data-testid="stFileUploader"] small {{
    color: ''' + T['text2'] + ''' !important;
  }}

  /* ── Expander (body content) on light ── */
  .stApp details[data-testid="stExpander"] > div {{
    background: ''' + T['card'] + ''' !important;
  }}

  /* ── Toast ── */
  .stApp [data-testid="stToast"] {{
    background: ''' + T['card'] + ''' !important;
    color: ''' + T['text'] + ''' !important;
    border-color: ''' + T['border2'] + ''' !important;
    box-shadow: 0 8px 32px rgba(0,0,0,.10) !important;
  }}

  /* ── Spinner ── */
  .stApp [data-testid="stSpinner"] {{
    color: ''' + T['accent'] + ''' !important;
  }}

  /* ── Dataframe / Table ── */
  .stApp [data-testid="stDataFrame"] {{
    background: ''' + T['card'] + ''' !important;
    border-color: ''' + T['border2'] + ''' !important;
  }}
  ''' if _is_light else '/* Dark mode: no additional overrides needed */'}


  /* ════════════════════════════════════════════════════════════════════════
     RESPONSIVE — Mobile & Tablet
     Breakpoint 768px: tablet/phone; 480px: phone piccoli.
     Nessuna modifica a layout desktop (> 768px).
     ════════════════════════════════════════════════════════════════════════ */

  @media (max-width: 768px) {{

    /* ── Container: padding laterale ridotto ─────────────────────────── */
    .main .block-container,
    .block-container {{
      padding-left: 0.65rem !important;
      padding-right: 0.65rem !important;
      padding-top: 0.8rem !important;
      padding-bottom: 2rem !important;
      max-width: 100% !important;
    }}

    /* ── Streamlit columns: stack verticale ──────────────────────────── */
    [data-testid="stHorizontalBlock"] {{
      flex-direction: column !important;
      gap: 0.6rem !important;
    }}
    [data-testid="stColumn"] {{
      width: 100% !important;
      flex: none !important;
      min-width: unset !important;
      max-width: 100% !important;
    }}


    /* ── Step progress: più compatto su tablet ──────────────────────── */
    .sp-pill {{ padding: .5rem 1.2rem; }}
    .sp-dot  {{ width: 34px; height: 34px; }}
    .sp-lbl  {{ font-size: .75rem; }}
    .sp-line {{ width: 48px; }}

    /* ── Landing: headline ridotta ───────────────────────────────────── */
    .landing-headline-xl {{
      font-size: clamp(1.7rem, 7vw, 2.4rem) !important;
      letter-spacing: -0.025em !important;
    }}
    .landing-sub-xl {{ font-size: 0.95rem !important; }}

    /* ── Feature pills: leggermente più piccole ──────────────────────── */
    .tally-feat-pill {{ font-size: .88rem; padding: .3rem .75rem; }}

    /* ── Form section headers: meno spazio ───────────────────────────── */
    .form-section-header {{ margin-top: 0.5rem !important; }}

    /* ── File pool card: padding compatto ────────────────────────────── */
    .file-pool-card {{ padding: 0.5rem 0.65rem 0.4rem; }}

    /* ── Genera bozza CTA: altezza ridotta ───────────────────────────── */
    .cta-genera-wrap button {{ min-height: 52px !important; font-size: 1rem !important; }}

    /* ── Pulsante conferma PDF ───────────────────────────────────────── */
    .btn-confirm-gold button,
    [data-testid="stButton"]:has(.btn-confirm-gold) button {{
      min-height: 58px !important;
    }}

    /* ── Download CTA button ─────────────────────────────────────────── */
    .dl-cta-wrap div.stDownloadButton > button,
    .dl-cta-wrap [data-testid="stDownloadButton"] > button {{
      min-height: 60px !important;
      font-size: 1.02rem !important;
      padding-left: 1rem !important;
      padding-right: 1rem !important;
    }}

    /* ── Storico sidebar card ────────────────────────────────────────── */
    .storico-card {{ padding: 0.55rem 0.7rem; }}

    /* ── Radio buttons: a capo se serve ──────────────────────────────── */
    .file-pool-card [data-testid="stRadio"] > div {{
      flex-wrap: wrap !important;
      gap: 0.3rem !important;
    }}

    /* ── Select: no troncamento ──────────────────────────────────────── */
    [data-testid="stSelectbox"] > div > div {{ min-width: 0 !important; }}

    /* ── Site header (logo landing) ──────────────────────────────────── */
    .site-header {{ padding: 0.6rem 0.8rem; }}
    .site-header-name {{ font-size: 1.1rem !important; }}

    /* ── Context sync badge ──────────────────────────────────────────── */
    .context-sync-badge {{ font-size: 0.72rem; padding: 0.3rem 0.55rem; }}

    /* ── Number input group (Ricalibra punteggi) ─────────────────────── */
    [data-testid="stNumberInput"] input {{ font-size: 0.9rem !important; }}

    /* ── Expander label ──────────────────────────────────────────────── */
    details[data-testid="stExpander"] summary span {{
      font-size: 0.9rem !important;
    }}

    /* ── KaTeX iframe: altezza massima ───────────────────────────────── */
    [data-testid="stIFrame"] {{ max-height: 420px !important; }}

    /* ── Anteprima PDF (colonna destra review): adatta ───────────────── */
    [data-testid="stImage"] img {{ border-radius: 8px; }}

    /* ── variant-card: altezza auto su mobile ────────────────────────── */
    .variant-card {{ min-height: 100px !important; height: auto !important; }}

    /* ── Rubrica button full width ───────────────────────────────────── */
    .btn-outline-accent-marker ~ div button {{ width: 100% !important; }}
  }}

  @media (max-width: 480px) {{

    /* ── Padding ultra-compatto ──────────────────────────────────────── */
    .main .block-container,
    .block-container {{
      padding-left: 0.4rem !important;
      padding-right: 0.4rem !important;
    }}

    /* ── Landing headline ancora più piccola ─────────────────────────── */
    .landing-headline-xl {{
      font-size: clamp(1.5rem, 8.5vw, 2rem) !important;
    }}
    .landing-sub-xl {{ font-size: 0.88rem !important; line-height: 1.55 !important; }}
    .tally-feat-pill {{ font-size: .8rem; padding: .25rem .6rem; }}

    /* ── Step progress: compatto su mobile ──────────────────────────── */
    .sp-pill {{ padding: .4rem .9rem; }}
    .sp-dot  {{ width: 30px; height: 30px; }}
    .sp-lbl  {{ font-size: .65rem; letter-spacing: 0; }}
    .sp-line {{ width: 28px; }}

    /* ── Heading scale ridotta ───────────────────────────────────────── */
    .stApp h1, .stMarkdown h1 {{
      font-size: 1.55rem !important;
    }}
    .stApp h2, .stMarkdown h2 {{
      font-size: 1.2rem !important;
    }}

    /* ── Global font size base ───────────────────────────────────────── */
    .stApp {{
      font-size: 15px !important;
    }}
    .stApp p, .stApp li, .stApp label,
    .stApp [data-testid="stMarkdownContainer"] p {{
      font-size: 0.94rem !important;
    }}

    /* ── Bottoni primari: altezza gestibile ──────────────────────────── */
    .cta-genera-wrap button {{ min-height: 46px !important; }}
    .dl-cta-wrap button      {{ min-height: 52px !important; font-size: 0.95rem !important; }}
  }}

  /* ════════════════════════════════════════════════════════════════════════
     INFO CARD — componente generico riutilizzabile
     ════════════════════════════════════════════════════════════════════════ */
  .info-card {{
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: {_radius_lg};
    padding: 1.1rem 1.3rem;
    margin: .7rem 0;
    box-shadow: {_shadow_xs};
    transition: box-shadow {_transition}, border-color {_transition};
  }}
  .info-card:hover {{
    box-shadow: {_shadow_sm};
    border-color: {_acc_med};
  }}
  .info-card-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: .8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: {T['muted']};
    margin-bottom: .45rem;
  }}
  .info-card-body {{
    font-family: 'DM Sans', sans-serif;
    font-size: .95rem;
    color: {T['text']};
    line-height: 1.55;
  }}
  .info-card-accent {{
    border-left: 3px solid {_acc};
    padding-left: 1rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     SKELETON LOADING — placeholder animato per contenuti in caricamento
     ════════════════════════════════════════════════════════════════════════ */
  @keyframes skeleton-shimmer {{
    0%   {{ background-position: -400px 0; }}
    100% {{ background-position: 400px 0; }}
  }}
  .skeleton {{
    border-radius: {_radius_sm};
    background: linear-gradient(
      90deg,
      {T['border']} 25%,
      {T['border2']} 50%,
      {T['border']} 75%
    );
    background-size: 800px 100%;
    animation: skeleton-shimmer 1.4s ease-in-out infinite;
  }}
  .skeleton-text  {{ height: 14px; margin: 6px 0; width: 80%; }}
  .skeleton-title {{ height: 22px; margin: 8px 0; width: 55%; }}
  .skeleton-block {{ height: 80px; margin: 8px 0; width: 100%; }}

  /* ════════════════════════════════════════════════════════════════════════
     FOCUS RING — accessibilità WCAG AA
     ════════════════════════════════════════════════════════════════════════ */
  :focus-visible {{
    outline: 2.5px solid {_acc} !important;
    outline-offset: 2px !important;
    border-radius: {_radius_sm} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     STATUS BADGES — pill colorata per stati contestuali
     ════════════════════════════════════════════════════════════════════════ */
  .badge {{
    display: inline-flex; align-items: center; gap: 5px;
    padding: .25rem .7rem;
    border-radius: 100px;
    font-size: .78rem;
    font-weight: 700;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: .01em;
    white-space: nowrap;
  }}
  .badge-success {{
    background: {T['success']}1a;
    color: {T['success']};
    border: 1px solid {T['success']}33;
  }}
  .badge-warn {{
    background: {T['warn']}1a;
    color: {T['warn']};
    border: 1px solid {T['warn']}33;
  }}
  .badge-error {{
    background: {T['error']}1a;
    color: {T['error']};
    border: 1px solid {T['error']}33;
  }}
  .badge-accent {{
    background: {_acc_soft};
    color: {_acc};
    border: 1px solid {_acc_med};
  }}
  .badge-muted {{
    background: {T['border']};
    color: {T['muted']};
    border: 1px solid {T['border2']};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     DIVIDER — separatore semantico leggero
     ════════════════════════════════════════════════════════════════════════ */
  .section-divider {{
    height: 1px;
    background: linear-gradient(90deg, transparent, {T['border2']}, transparent);
    margin: 1.5rem 0;
    border: none;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     APP FOOTER — migliorato con separatore e layout bilanciato
     ════════════════════════════════════════════════════════════════════════ */
  .app-footer {{
    text-align: center;
    font-size: 0.82rem !important;
    color: {T['muted']} !important;
    font-family: 'DM Sans', sans-serif;
    padding: 1.6rem .5rem 1rem;
    margin-top: 2.5rem;
    border-top: 1px solid {T['border']};
    line-height: 1.6;
    opacity: .75;
    transition: opacity .2s;
  }}
  .app-footer:hover {{ opacity: 1; }}
  .app-footer a {{
    color: {_acc} !important;
    text-decoration: none;
  }}
  .app-footer a:hover {{ text-decoration: underline; }}

  /* ════════════════════════════════════════════════════════════════════════
     EMPTY STATE — messaggio "nessun risultato"
     ════════════════════════════════════════════════════════════════════════ */
  .empty-state {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
    text-align: center;
    gap: .7rem;
  }}
  .empty-state-icon {{
    font-size: 2.5rem;
    opacity: .45;
  }}
  .empty-state-title {{
    font-size: 1rem;
    font-weight: 700;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
  }}
  .empty-state-desc {{
    font-size: .875rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    max-width: 340px;
    line-height: 1.5;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     STEP TRANSITION ANIMATION — per cambio di stage fluido
     ════════════════════════════════════════════════════════════════════════ */
  @keyframes stage-fade-in {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .stage-enter {{
    animation: stage-fade-in .22s ease-out both;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     MOBILE touch targets — ≥ 44px per WCAG
     ════════════════════════════════════════════════════════════════════════ */
  @media (max-width: 768px) {{
    .stButton > button,
    [data-testid="stButton"] > button {{
      min-height: 44px !important;
    }}
    [data-testid="stSelectbox"] > div {{
      min-height: 44px !important;
    }}
  }}

/* ── ULTRA AGGRESSIVE FINAL OVERRIDE ───────────────────────────────────────
     Ultima risorsa: forza TUTTI i bottoni secondari ad avere testo leggibile.
     Questa regola è alla fine del CSS per massima priorità.                      */
  button[data-testid="stBaseButton-secondary"],
  button[kind="secondary"],
  div.stButton > button:not([kind="primary"]):not([data-testid*="primary"]),
  [data-testid="stButton"] > button:not([data-testid*="primary"]) {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    background-color: {T.get("card", T["bg2"])} !important;
    background: {T.get("card", T["bg2"])} !important;
  }}
  /* Download buttons */
  div.stDownloadButton > button {{
    color: {T.get("success", "#059669")} !important;
    -webkit-text-fill-color: {T.get("success", "#059669")} !important;
  }}
  /* Sidebar buttons - always dark */
  [data-testid="stSidebar"] button:not([kind="primary"]):not([data-testid*="primary"]) {{
    background: {_SB_INPUT_BG} !important;
    background-color: {_SB_INPUT_BG} !important;
    color: {_SB_INPUT_TEXT} !important;
    -webkit-text-fill-color: {_SB_INPUT_TEXT} !important;
    border: 1px solid {_SB_BORDER} !important;
  }}

  /* ── PREVIEW CARDS ───────────────────────────────────────────────────────────── */
  .preview-card {{
    cursor: pointer !important;
    overflow: hidden !important;
  }}
  .preview-card:hover {{
    transform: translateY(-6px) !important;
    box-shadow: 0 8px 24px {_acc_soft} !important;
    border-color: {_acc} !important;
  }}
  .preview-card img {{
    transition: transform 0.3s ease !important;
  }}
  .preview-card:hover img {{
    transform: scale(1.05) !important;
  }}

</style>
"""


def _is_light_color(hex_color: str) -> bool:
    """Restituisce True se il colore è chiaro (luminosità > 0.5)."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5
    except Exception:
        return False
