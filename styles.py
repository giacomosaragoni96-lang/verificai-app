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
    _SB_ACCENT = T.get("sidebar_accent", "#79C0FF")
    _SB_BG_CSS = T.get("sidebar_bg", "linear-gradient(180deg, #111110 0%, #0e0e0d 100%)")
    _SB_BORDER = T.get("sidebar_border", "#21262D")
    _SB_MUTED  = T.get("muted", "#6E7681")
    _SB_TEXT   = T.get("text", "#E6EDF3")
    _SB_INPUT_BG   = T.get("sidebar_input_bg", "#0D1117")
    _SB_INPUT_TEXT = T.get("sidebar_input_text", "#E6EDF3")

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

  /* Breathing room: il main container non cola sui bordi */
  .main .block-container {{
    padding-top: 1.8rem !important;
    padding-bottom: 3rem !important;
    max-width: 1100px !important;
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

  /* 0. Sovrascrive le CSS vars di Streamlit che causano il nero */
  .stApp {{
    --background-color: {T['bg']} !important;
    --secondary-background-color: {T['bg2']} !important;
    --text-color: {T['text']} !important;
  }}

  /* 1. Contenitore details */
  html body .stApp details[data-testid="stExpander"],
  html .stApp details[data-testid="stExpander"],
  .stApp details[data-testid="stExpander"] {{
    color-scheme: {_color_scheme} !important;
    --background-color: {_surf_raised} !important;
    background: {_surf_raised} !important;
    background-color: {_surf_raised} !important;
    border: 2px solid {T['border2']} !important;
    border-radius: 14px !important;
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

  /* 5. Summary APERTO — gradient teal */
  html body .stApp details[data-testid="stExpander"][open] > summary,
  html body .stApp details[data-testid="stExpander"][open] summary[role="button"],
  .stApp details[data-testid="stExpander"][open] > summary {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent2']} 100%) !important;
    background-color: {T['accent']} !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-radius: 12px 12px 0 0 !important;
    border-bottom: none !important;
    color-scheme: {_color_scheme} !important;
  }}
  html body .stApp details[data-testid="stExpander"][open] > summary > *,
  html body .stApp details[data-testid="stExpander"][open] summary[role="button"] > *,
  .stApp details[data-testid="stExpander"][open] > summary div,
  .stApp details[data-testid="stExpander"][open] > summary p,
  .stApp details[data-testid="stExpander"][open] > summary span {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    background: transparent !important;
    background-color: transparent !important;
  }}
  html body .stApp details[data-testid="stExpander"][open] > summary svg,
  html body .stApp details[data-testid="stExpander"][open] > summary svg * {{
    fill: #ffffff !important;
    stroke: #ffffff !important;
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
    padding: 4rem 2rem 4rem !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     DASHBOARD LAYOUT — spaziature e contenitori (Minimal SaaS)
     ════════════════════════════════════════════════════════════════════════ */
  .dashboard-section {{
    margin-bottom: 2rem;
  }}
  .dashboard-card {{
    background: {T['card']};
    border: 1px solid {T['border2']};
    border-radius: {_radius_lg};
    box-shadow: {_shadow_sm};
    padding: 1.6rem 1.8rem;
    transition: box-shadow {_transition};
  }}
  .dashboard-card:hover {{
    box-shadow: {_shadow_md};
  }}
  .divider-minimal {{
    height: 1px;
    background: {T['border']};
    margin: 1.5rem 0;
    border-radius: 1px;
    border: none;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     ALERTS / TOAST — success, error, warning (feedback visivo)
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stAlert"] {{
    border-radius: {_radius_md} !important;
    border: 1px solid {T['border']} !important;
    box-shadow: {T.get('shadow', '0 1px 3px rgba(0,0,0,.08)')} !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 1rem 1.25rem !important;
    transition: box-shadow .2s ease, transform .15s ease !important;
  }}
  [data-testid="stAlert"]:has([data-baseweb="notification"][kind="positive"]) {{
    border-left: 4px solid {T['success']} !important;
    background: {T.get('accent_light', _surf_raised)} !important;
  }}
  [data-testid="stAlert"]:has([data-baseweb="notification"][kind="negative"]) {{
    border-left: 4px solid {T['error']} !important;
    background: {_surf_raised} !important;
  }}
  [data-testid="stAlert"]:has([data-baseweb="notification"][kind="warning"]) {{
    border-left: 4px solid {T['warn']} !important;
    background: {_surf_raised} !important;
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
    color: {_SB_INPUT_TEXT} !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 10px !important;
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    transition: border-color .2s ease, background .2s ease !important;
  }}
  [data-testid="stSidebar"] .stButton button:hover {{
    border-color: {_SB_ACCENT} !important;
    color: {_SB_INPUT_TEXT} !important;
    background: {_SB_BORDER} !important;
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
    z-index: 999 !important;
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
    font-size: 0.9rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: {_SB_ACCENT} !important;
    margin: 1.1rem 0 0.45rem 0 !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     HERO / HEADER — legacy (non più usati direttamente)
     ════════════════════════════════════════════════════════════════════════ */
  .hero-wrap {{ display: none; }}
  .sidebar-hint-inline {{ display: none; }}
  .page-header-unified {{ display: none; }}

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
    margin: 0 0 1rem 0;
    padding: .35rem 0 .9rem 0;
    border-bottom: 1px solid {_SB_BORDER};
    display: block;
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
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    padding: 14px 16px !important;
    box-shadow: {_shadow_xs} !important;
    transition: border-color {_transition}, box-shadow {_transition} !important;
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
  /* Dropdown popup — dark mode coerente con tema Notte */
  [data-baseweb="popover"],
  [data-baseweb="popover"] > div,
  [data-baseweb="popover"] > div > div {{
    background: {T['card']} !important;
    background-color: {T['card']} !important;
    color-scheme: {_color_scheme} !important;
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
    color: {T['text2']} !important;
    font-size: 0.89rem !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
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
    font-size: 1.02rem !important;
    min-height: 50px !important;
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

  div.stButton > button[kind="secondary"],
  div.stButton > button:not([kind="primary"]) {{
    background: {_surf_raised} !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: {_radius_md} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    min-height: 48px !important;
    box-shadow: {_shadow_xs} !important;
    transition: background {_transition}, border-color {_transition}, box-shadow {_transition}, transform {_transition} !important;
  }}
  div.stButton > button[kind="secondary"]:hover,
  div.stButton > button:not([kind="primary"]):hover {{
    background: {T['hover']} !important;
    border-color: {_acc} !important;
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
    padding: 2rem 1rem 1.5rem;
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
    font-size: clamp(2.6rem, 5.5vw, 3.8rem);
    font-weight: 900;
    line-height: 1.12;
    letter-spacing: -0.04em;
    color: {T['text']};
    margin: 0 0 1.3rem 0;
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
    font-size: 1.25rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.7;
    text-align: center;
    max-width: 560px;
    margin: 0 auto 0;
  }}

  /* Classi legacy mantenute per compatibilità */
  .landing-logo-wrap {{ display:none; }}
  .tally-hero {{ text-align:center; padding:2rem 1rem 1.4rem; max-width:700px; margin:0 auto; }}
  .tally-eyebrow {{ display:none; }}
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

  /* CTA button wrapper */
  .tally-cta-wrap {{
    margin: 2rem auto .5rem;
    max-width: 480px;
  }}
  .tally-cta-wrap button[kind="primary"],
  .tally-cta-wrap button[data-testid="baseButton-primary"] {{
    font-size: 1.2rem !important;
    font-weight: 800 !important;
    padding: 1rem 2.2rem !important;
    height: auto !important;
    min-height: 62px !important;
    border-radius: 16px !important;
    letter-spacing: -.01em !important;
    box-shadow: 0 6px 28px {_acc}44 !important;
    transition: transform .15s ease, box-shadow .15s ease !important;
  }}
  .tally-cta-wrap button[kind="primary"]:hover,
  .tally-cta-wrap button[data-testid="baseButton-primary"]:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 36px {_acc}55 !important;
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
    color: {T['text2']};
    white-space: nowrap;
    padding: .35rem .9rem;
    border-radius: 20px;
    border: 1px solid {T['border2']};
    background: {T['card']};
    border-bottom: 2px solid {_acc_med};
    transition: border-color .15s, color .15s;
  }}
  .tally-feat-pill:hover {{
    color: {T['text']};
    border-color: {_acc};
    border-bottom-color: {_acc};
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
    border-radius: 14px;
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
  .side-box-badge-violet {{
    background: #D9770618;
    color: #D97706;
    border: 1px solid #D9770633;
  }}



  /* Facsimile shortcut — visivamente distaccato dal form principale */
  .side-box-facsimile {{
    background: linear-gradient(135deg, #D977060E, {T['card']});
    border: 1.5px solid #D9770644 !important;
    border-left: 3px solid #F59E0B !important;
    box-shadow: 0 2px 12px #D9770614;
  }}
  .side-box-facsimile .side-box-title {{
    color: #D97706;
  }}
  .facsimile-shortcut-btn button {{
    background: transparent !important;
    color: #F59E0B !important;
    -webkit-text-fill-color: #F59E0B !important;
    border: 2px solid #F59E0B !important;
    font-weight: 700 !important; font-size: 0.91rem !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 10px #D9770622 !important;
    transition: background .18s, color .18s !important;
  }}
  .facsimile-shortcut-btn button:hover {{
    background: #F59E0B !important;
    background-color: #F59E0B !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    box-shadow: 0 4px 20px #D9770655 !important;
  }}

  /* ═══ Facsimile Detection Banner — inline sotto argomento/upload ═══ */
  .facsimile-detection-banner {{
    display: flex;
    align-items: flex-start;
    gap: .85rem;
    background: linear-gradient(135deg, #D977060D, {T['card']});
    border: 1.5px solid #F59E0B55;
    border-left: 3px solid #F59E0B;
    border-radius: 14px;
    padding: .85rem 1.1rem;
    margin: .8rem 0 .4rem;
    box-shadow: 0 2px 12px #D9770618;
  }}
  .facsimile-detection-icon {{
    font-size: 1.5rem;
    flex-shrink: 0;
    padding-top: 1px;
  }}
  .facsimile-detection-body {{
    flex: 1;
    min-width: 0;
  }}
  .facsimile-detection-title {{
    font-size: .93rem;
    font-weight: 800;
    color: #B45309;
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .2rem;
    line-height: 1.35;
  }}
  .facsimile-detection-sub {{
    font-size: .82rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.4;
  }}

  /* ═══ Facsimile Inline Button (CTA sotto detection banner) ═══ */
  .facsimile-inline-btn {{
    margin-bottom: .9rem;
  }}
  .facsimile-inline-btn button {{
    background: transparent !important;
    color: #D97706 !important;
    -webkit-text-fill-color: #D97706 !important;
    border: 2px solid #F59E0B !important;
    font-weight: 800 !important;
    font-size: 1rem !important;
    border-radius: 12px !important;
    min-height: 50px !important;
    box-shadow: 0 2px 14px #D9770628 !important;
    transition: background .18s, color .18s, box-shadow .18s !important;
    letter-spacing: -.01em !important;
  }}
  .facsimile-inline-btn button:hover {{
    background: linear-gradient(90deg, #F59E0B, #D97706) !important;
    background-color: #F59E0B !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    box-shadow: 0 4px 22px #D9770650 !important;
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
    padding: .45rem .75rem;
    margin: .3rem 0 .4rem;
    font-size: 0.94rem;
    color: {T.get('hint_text', '#92400E')};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}

  /* ── Percorso Card ── */
  .mcard {{
    background: {T['card']};
    border: 1px solid {T['border2']};
    border-radius: {_radius_lg};
    padding: 1.4rem 1.3rem 1.2rem;
    position: relative;
    box-shadow: {_shadow_sm};
    transition: border-color {_transition}, box-shadow {_transition}, transform {_transition};
    min-height: 220px;
    display: flex;
    flex-direction: column;
    gap: .45rem;
  }}
  .mcard:hover {{
    transform: translateY(-3px);
    border-color: {_acc_med};
    box-shadow: {_shadow_soft};
  }}
  .mcard-badge {{
    position: absolute; top: -10px; right: 14px;
    font-size: 0.9rem; font-weight: 800;
    letter-spacing: .06em; text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
    color: #fff;
  }}
  .mcard-icon {{
    font-size: 1.6rem;
    margin-bottom: .2rem;
  }}
  .mcard-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 900;
    letter-spacing: -0.01em;
  }}
  .mcard-desc {{
    font-size: 0.89rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
    flex: 1;
  }}
  .mcard-hint {{
    font-size: 0.92rem;
    color: {T['muted']};
    font-style: italic;
    line-height: 1.4;
    margin-top: .3rem;
  }}
  .mcard-chips {{
    display: flex; flex-wrap: wrap; gap: 6px;
    margin-top: .5rem;
  }}
  .mcard-chip {{
    font-size: 0.9rem;
    font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    background: {_surf_overlay};
    border: 1px solid {T['border']};
    border-radius: 20px;
    padding: 3px 10px;
    color: {T['text2']};
    white-space: nowrap;
  }}

  /* ── Facsimile Card — Viola/Accento speciale ── */
  .fac-card {{
    background: linear-gradient(135deg, #7C3AED14, {T['card']});
    border: 2px solid #7C3AED44;
    border-radius: 18px;
    padding: 1.1rem 1.4rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: border-color .2s ease, box-shadow .2s ease;
  }}
  .fac-card:hover {{
    border-color: #7C3AED88;
    box-shadow: 0 4px 24px #7C3AED22;
  }}
  .fac-badge {{
    font-size: 0.9rem; font-weight: 800;
    letter-spacing: .08em; text-transform: uppercase;
    color: #A78BFA;
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
    font-size: 0.95rem;
    font-weight: 700;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 4px;
    letter-spacing: .01em;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     ONBOARDING HINT BANNER (Percorso B top)
     ════════════════════════════════════════════════════════════════════════ */
  .onboarding-hint-banner {{
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    background: linear-gradient(135deg, {_acc_soft}, {T['card']});
    border: 1.5px solid {_acc_ring};
    border-radius: 16px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 1.4rem;
  }}
  .onboarding-hint-icon {{
    font-size: 1.6rem;
    flex-shrink: 0;
    padding-top: 2px;
  }}
  .onboarding-hint-body {{
    flex: 1;
  }}
  .onboarding-hint-title {{
    font-size: 1.05rem;
    font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .3rem;
    line-height: 1.3;
  }}
  .onboarding-hint-desc {{
    font-size: 0.99rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
  }}
  .onboarding-hint-tags {{
    display: flex; flex-wrap: wrap; gap: 6px; margin-top: .5rem;
  }}
  .onboarding-hint-tag {{
    font-size: 0.95rem; font-weight: 600;
    background: {T['card']};
    border: 1px solid {T['border']};
    border-radius: 20px;
    padding: 4px 12px;
    color: {T['text2']};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     CTA GENERA — High Impact Button Wrap
     ════════════════════════════════════════════════════════════════════════ */
  .cta-genera-wrap button {{
    min-height: 60px !important;
    font-size: 1.15rem !important;
    font-weight: 900 !important;
    letter-spacing: -.01em !important;
    border-radius: 14px !important;
  }}
  /* CTA hint — testo sottile, non sembra un pulsante */
  .cta-hint-prominent {{
    display: none; /* deprecato — sostituito da cta-hint-text */
  }}
  .cta-hint-prominent-icon {{
    font-size: 1rem; flex-shrink: 0;
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
     SIDE PANEL — Right column
     ════════════════════════════════════════════════════════════════════════ */
  .side-panel-card {{
    background: {_surf_raised};
    border: 1.5px solid {T['border']};
    border-radius: 14px;
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

  .file-uploader-compact {{
    margin-bottom: .5rem;
  }}
  .file-uploader-compact [data-testid="stFileUploader"] {{
    border-radius: 12px !important;
  }}

  /* Colonna sinistra dedicata upload — label e area compatti */
  .upload-column-label {{
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 0.35rem;
  }}
  .file-uploader-narrow [data-testid="stFileUploader"] {{
    min-height: 86px !important;
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

  /* Riga form+upload: colonne allineate in alto, la destra non allunga la pagina */
  [data-testid="stHorizontalBlock"]:has(.upload-column-label) {{
    align-items: flex-start !important;
  }}

  /* Colonna upload (destra): sidebar fissa, altezza limitata, scroll interno */
  [data-testid="stColumn"]:has(.upload-column-label) {{
    background-color: {T['card']} !important;
    background: {T['card']} !important;
    border: 1px solid {T['border2']} !important;
    border-left: 3px solid {_acc} !important;
    border-radius: {_radius_lg} !important;
    padding: 0.75rem 0.85rem !important;
    min-width: 200px !important;
    max-width: 280px !important;
    height: 65vh !important;
    max-height: 65vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain !important;
    align-self: flex-start !important;
    box-shadow: {_shadow_sm} !important;
  }}
  [data-testid="stColumn"]:has(.upload-column-label) > div {{
    max-height: 100% !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
  }}

  /* Fallback: colonna con file uploader (se .upload-column-label non matcha) */
  [data-testid="stColumn"]:has(> div > [data-testid="stFileUploader"]),
  [data-testid="stColumn"]:has(> div > div > [data-testid="stFileUploader"]) {{
    background-color: {T['card']} !important;
    background: {T['card']} !important;
    border: 1px solid {T['border2']} !important;
    border-left: 3px solid {_acc} !important;
    border-radius: {_radius_lg} !important;
    padding: 0.75rem 0.85rem !important;
    min-width: 200px !important;
    max-width: 280px !important;
    height: 65vh !important;
    max-height: 65vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    align-self: flex-start !important;
    box-shadow: {_shadow_sm} !important;
  }}

  [data-testid="stColumn"]:has([data-testid="stFileUploader"]) .side-box-title,
  [data-testid="stColumn"]:has([data-testid="stFileUploader"]) .side-box-dot {{
    color: {T['text']} !important;
  }}
  [data-testid="stColumn"]:has([data-testid="stFileUploader"]) .side-box-desc {{
    color: {T['text2']} !important;
  }}
  [data-testid="stColumn"]:has([data-testid="stFileUploader"]) .side-box {{
    background: {T['card']} !important;
    border-color: {T['border2']} !important;
  }}
  [data-testid="stColumn"]:has([data-testid="stFileUploader"]) .side-box-facsimile {{
    background: {T['card']} !important;
    border-color: {_acc}44 !important;
    border-left-color: {T['warn']} !important;
  }}
  [data-testid="stColumn"]:has([data-testid="stFileUploader"]) .side-box-badge-violet {{
    background: {T['warn']}22 !important;
    color: {T['warn']} !important;
    border-color: {T['warn']}44 !important;
  }}
  [data-testid="stColumn"]:has([data-testid="stFileUploader"]) .side-box-facsimile .side-box-title {{
    color: {T['warn']} !important;
  }}
  [data-testid="stColumn"]:has([data-testid="stFileUploader"]) .side-box-facsimile .side-box-desc {{
    color: {T['text2']} !important;
  }}
  [data-testid="stColumn"]:has([data-testid="stFileUploader"])
  button:not([kind="primary"]) {{
    background: {T['card']} !important;
    border-color: {T['border2']} !important;
    color: {T['text']} !important;
  }}
  
  /* ═══ Facsimile Shortcut — stile distinto (gestito via .side-box-facsimile) ═══ */
  .facsimile-shortcut {{ display: none; }}
  .facsimile-shortcut-badge {{ display: none; }}
  .facsimile-shortcut-question {{ display: none; }}
  .facsimile-shortcut-desc {{ display: none; }}

  /* ════════════════════════════════════════════════════════════════════════
     FILE POOL — Sezione e card (contenitore unico per file caricati)
     ════════════════════════════════════════════════════════════════════════ */
  /* Sezione e card compatte (dentro colonna a scroll) */
  .file-pool-section {{
    background: transparent;
    border: none;
    padding: 0.5rem 0 0;
    margin-top: 0.6rem;
    margin-bottom: 0;
  }}
  .file-pool-section-title {{
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin: 0 0 0.4rem 0;
  }}
  .file-pool-card {{
    background: {T['bg2']};
    border: 1px solid {T['border2']};
    border-radius: {_radius_sm};
    padding: 0.6rem 0.7rem;
    margin-bottom: 0.5rem;
    box-shadow: {_shadow_xs};
    transition: border-color {_transition}, box-shadow {_transition};
  }}
  .file-pool-card:hover {{
    border-color: {_acc_med};
    box-shadow: {_shadow_sm};
  }}
  .file-pool-card:last-of-type {{
    margin-bottom: 0;
  }}
  .file-pool-card .file-ai-summary {{
    margin: 0.25rem 0 0.15rem;
    padding: 0.25rem 0.4rem;
    font-size: 0.8rem;
  }}
  .file-pool-card .file-item-b-mode-label {{
    margin: 0.1rem 0 0.05rem;
    font-size: 0.8rem;
  }}
  .file-pool-card .file-item-b-delete {{
    margin-top: 0.15rem;
  }}
  .file-pool-card .file-item-b-delete button {{
    min-height: 26px !important;
    font-size: 0.82rem !important;
  }}
  .file-pool-card .facsimile-detection-banner {{
    margin: 0.4rem 0 0.25rem;
    padding: 0.5rem 0.65rem;
  }}
  .file-pool-card .facsimile-detection-title {{
    font-size: 0.85rem !important;
  }}
  .file-pool-card .facsimile-detection-sub {{
    font-size: 0.75rem !important;
  }}
  .file-pool-card .facsimile-inline-btn button {{
    min-height: 42px !important;
    font-size: 0.9rem !important;
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
  .file-pool-card .file-item-b-name {{
    font-size: 0.82rem;
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
    background: #3B82F618; color: #3B82F6;
    border: 1px solid #3B82F633;
  }}
  .file-item-b-badge-appunti {{
    background: #10B98118; color: #10B981;
    border: 1px solid #10B98133;
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
    color: #EF4444 !important;
    border-color: #EF4444 !important;
    background: #EF444408 !important;
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

  .ocr-skeleton-wrap {{
    background: {_surf_raised};
    border: 1.5px solid {T['border']};
    border-radius: 16px;
    padding: 1.1rem 1.2rem;
    margin: .6rem 0;
    overflow: hidden;
  }}
  .ocr-skeleton-header {{
    display: flex; align-items: center; gap: .75rem;
    margin-bottom: .8rem;
  }}
  .ocr-skeleton-icon {{
    font-size: 1.4rem;
    animation: pulse-dot 1.2s ease-in-out infinite;
  }}
  .ocr-skeleton-title {{
    font-size: 0.95rem; font-weight: 800;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
  }}
  .ocr-skeleton-sub {{
    font-size: 0.92rem; color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-top: 1px;
  }}
  .ocr-skeleton-doc {{
    background: {T['bg']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: .9rem 1rem;
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
    height: 10px;
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
    color: #A78BFA;
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
    border: 2px dashed #7C3AED44;
    border-radius: 18px;
    padding: 1.3rem 1.2rem;
    margin-bottom: .5rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RECALIBRA PUNTEGGI
     ════════════════════════════════════════════════════════════════════════ */
  .recalibra-sum-ok {{
    font-size: 0.88rem; font-weight: 600;
    color: {T['success']}; font-family: 'DM Sans', sans-serif;
    background: {T['success']}14;
    border: 1px solid {T['success']}33;
    border-radius: 8px; padding: .4rem .7rem;
    margin-top: .3rem;
  }}
  .recalibra-sum-err {{
    font-size: 0.88rem; font-weight: 600;
    color: {T['warn']}; font-family: 'DM Sans', sans-serif;
    background: {T['warn']}14;
    border: 1px solid {T['warn']}33;
    border-radius: 8px; padding: .4rem .7rem;
    margin-top: .3rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RUBRICA (Valutazione MIM)
     ════════════════════════════════════════════════════════════════════════ */
  .rubrica-wrap {{
    background: {_surf_overlay};
    border: 1.5px solid {T['border']};
    border-radius: 14px;
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
    border-radius: 14px !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.99rem !important;
    font-weight: 700 !important;
    padding: .75rem 1.1rem !important;
    text-align: left !important;
    box-shadow: 0 2px 8px rgba(10,143,114,.08) !important;
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
    border-radius: 14px 14px 0 0 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.99rem !important;
    font-weight: 700 !important;
    padding: .75rem 1.1rem !important;
    text-align: left !important;
    box-shadow: 0 2px 12px rgba(10,143,114,.25) !important;
  }}
  .pers-toggle-open button:hover {{
    background: linear-gradient(135deg, {T['accent2']} 0%, {T['accent']} 100%) !important;
  }}
  /* Pannello corpo — connesso al pulsante aperto */
  .pers-body {{
    background: {T['card']} !important;
    border: 2px solid {T['accent']} !important;
    border-top: none !important;
    border-radius: 0 0 14px 14px !important;
    padding: 1.1rem 1.2rem 1.3rem !important;
    margin-bottom: .5rem !important;
    box-shadow: 0 4px 16px rgba(10,143,114,.10) !important;
  }}

  /* st.container(border=True) che segue il toggle aperto.
     Streamlit usa data-testid="stVerticalBlockBorderWrapper" per container(border=True).
     Override del bordo grigio con il teal accent, collegato visivamente all'header. */
  [data-testid="stVerticalBlockBorderWrapper"] {{
    border: 2px solid {T['border2']} !important;
    border-radius: 14px !important;
  }}
  /* Dentro pers-toggle-wrap aperto: collegato all'header senza angoli in alto */
  .pers-toggle-open ~ [data-testid="stVerticalBlockBorderWrapper"],
  .pers-toggle-open + [data-testid="stVerticalBlockBorderWrapper"],
  .pers-toggle-open ~ div > [data-testid="stVerticalBlockBorderWrapper"]:first-child {{
    border: 2px solid {T['accent']} !important;
    border-top: none !important;
    border-radius: 0 0 14px 14px !important;
    background: {T['card']} !important;
    margin-top: -2px !important;
    box-shadow: 0 4px 16px rgba(10,143,114,.10) !important;
  }}
  .personalizza-wrap details[data-testid="stExpander"] {{
    --background-color: {_surf_raised};
    background: {_surf_raised} !important;
    border: 2px solid {T['border2']} !important;
    border-radius: 14px !important;
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
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent2']} 100%) !important;
    background-color: {T['accent']} !important;
    border-radius: 12px 12px 0 0 !important;
    border-bottom: none !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    color-scheme: {_color_scheme} !important;
  }}
  .stApp .personalizza-wrap details[data-testid="stExpander"][open] > summary *,
  .personalizza-wrap details[data-testid="stExpander"][open] > summary * {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    background-color: transparent !important;
  }}
  .personalizza-wrap details[data-testid="stExpander"][open] > summary svg,
  .personalizza-wrap details[data-testid="stExpander"][open] > summary svg * {{
    fill: #ffffff !important;
    stroke: #ffffff !important;
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
  [data-testid="stFileUploaderDropzone"],
  section[data-testid="stFileUploaderDropzone"] {{
    background: {T['bg2']} !important;
    border: 2px dashed {T['border2']} !important;
    border-radius: 12px !important;
    color-scheme: {_color_scheme} !important;
    padding: .8rem !important;
  }}
  [data-testid="stFileUploaderDropzone"]:hover,
  section[data-testid="stFileUploaderDropzone"]:hover {{
    border-color: {_acc} !important;
    background: {T['card']} !important;
  }}
  [data-testid="stFileDropzoneInstructions"],
  [data-testid="stFileDropzoneInstructions"] *,
  [data-testid="stFileDropzoneInstructions"] span,
  [data-testid="stFileDropzoneInstructions"] p,
  [data-testid="stFileDropzoneInstructions"] div {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  [data-testid="stFileDropzoneInstructions"] small,
  [data-testid="stFileDropzoneInstructions"] span + span {{
    color: {T['text2']} !important;
    -webkit-text-fill-color: {T['text2']} !important;
    font-size: 0.88rem !important;
  }}
  [data-testid="stFileUploaderDropzone"] span,
  [data-testid="stFileUploaderDropzone"] p,
  [data-testid="stFileUploaderDropzone"] div:not(button) {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
  }}
  [data-testid="stFileUploaderDropzone"] button,
  section[data-testid="stFileUploaderDropzone"] button {{
    background: transparent !important;
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.89rem !important;
    font-family: 'DM Sans', sans-serif !important;
    cursor: pointer !important;
    padding: .35rem 1rem !important;
  }}
  [data-testid="stFileUploaderDropzone"] button:hover,
  section[data-testid="stFileUploaderDropzone"] button:hover {{
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    border-color: {T['accent']} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     TOAST — Streamlit override
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stToast"] {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 14px !important;
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
    color: {T['text2']} !important;
    -webkit-text-fill-color: {T['text2']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 8px !important;
    font-size: 0.89rem !important;
    font-weight: 600 !important;
    min-height: 34px !important;
    padding: 0 .9rem !important;
    box-shadow: none !important;
    transform: none !important;
    transition: color .12s ease, border-color .12s ease, background .12s ease !important;
    width: auto !important;
    letter-spacing: -.01em;
  }}
  .btn-back-discrete > div.stButton > button:hover,
  .btn-back-discrete .stButton > button:hover {{
    color: {T['text']} !important;
    -webkit-text-fill-color: {T['text']} !important;
    border-color: {T['accent']} !important;
    background: {T['hover']} !important;
    background-color: {T['hover']} !important;
    transform: none !important;
    box-shadow: none !important;
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
  [data-testid="stDownloadButton"] > button {{
    background: {_surf_raised} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    transition: border-color .15s ease, background .15s ease !important;
  }}
  [data-testid="stDownloadButton"] > button:hover {{
    border-color: {_acc} !important;
    background: {T['hover']} !important;
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
    min-height: 120px;
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
    line-height: 1.5;
    flex: 1;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     DOWNLOAD CTA — pulsante oro in STAGE_FINAL
     ════════════════════════════════════════════════════════════════════════ */
  .dl-cta-wrap {{
    margin-bottom: 1rem;
  }}
  .dl-cta-wrap button {{
    background: linear-gradient(135deg, #D97706 0%, #F59E0B 100%) !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    font-size: 1.08rem !important;
    font-weight: 900 !important;
    letter-spacing: .04em !important;
    min-height: 62px !important;
    box-shadow: 0 4px 24px #D9770650, 0 1px 4px #D9770630 !important;
    transition: all .18s ease !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  .dl-cta-wrap button:hover {{
    background: linear-gradient(135deg, #B45309 0%, #D97706 100%) !important;
    box-shadow: 0 6px 32px #D9770670 !important;
    transform: translateY(-2px) !important;
  }}
  .dl-cta-wrap button:active {{
    transform: translateY(0) !important;
    box-shadow: 0 2px 10px #D9770640 !important;
  }}

  /* CTA variante (per colleghi) */
  .shared-cta-card {{
    background: linear-gradient(135deg, {_acc}12, {_acc}06);
    border: 2px solid {_acc}35;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin: .7rem 0;
    text-align: center;
  }}
  .shared-cta-icon {{
    font-size: 1.8rem;
    margin-bottom: .3rem;
  }}
  .shared-cta-title {{
    font-size: .95rem;
    font-weight: 800;
    color: {_acc};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .3rem;
  }}
  .shared-cta-desc {{
    font-size: 0.96rem;
    color: {T['text2']};
    line-height: 1.5;
  }}

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
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 10px;
    border: 1px solid #30363D;
    background: transparent;
    color: #6E7681;
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
    border: 1px dashed #3D444D !important;
    padding: 2px 6px !important;
    font-size: 0.92rem !important;
    min-height: auto !important;
    opacity: .5;
    transition: all .15s;
  }}
  .elimina-btn button:hover {{
    opacity: 1;
    border-color: #EF4444 !important;
    color: #EF4444 !important;
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
    .variant-card {{ min-height: auto; }}
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
    border-radius: 14px;
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
  .shared-cta-card {{
    background: linear-gradient(135deg, #D97706 0%, #B45309 100%);
    border-radius: 14px;
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
    font-weight: 900;
    color: #fff;
    margin-bottom: .3rem;
  }}
  .shared-cta-desc {{
    font-size: 0.88rem;
    color: #ffffffcc;
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
    border-left-color: {T["accent"]};
    background: {T.get("hover", T["bg2"])};
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
    color: {T["text"]};
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-date {{
    font-size: 0.9rem;
    color: {T["muted"]};
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-arg {{
    font-size: 0.94rem;
    color: {T["text2"]};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 3px;
    line-height: 1.3;
  }}
  .storico-card-meta {{
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.9rem;
    color: {T["muted"]};
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-scu {{
    background: {T["bg2"]};
    padding: 1px 6px;
    border-radius: 4px;
    border: 1px solid {T["border"]};
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
  .landing-feat-card {{
    background: {T['card']};
    border: 1px solid {T['border2']};
    border-radius: {_radius_lg};
    padding: 1.4rem 1.3rem;
    text-align: left;
    box-shadow: {_shadow_sm};
    transition: border-color {_transition}, box-shadow {_transition}, transform {_transition};
    height: 100%;
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
    border: 1.5px solid ''' + T['border2'] + ''' !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.06) !important;
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
    background-color: #16a34a12 !important;
    border-color: #16a34a44 !important;
  }}
  .stApp [data-testid="stWarning"] {{
    background-color: #d9770612 !important;
    border-color: #d9770644 !important;
  }}
  .stApp [data-testid="stError"] {{
    background-color: #dc262612 !important;
    border-color: #dc262644 !important;
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
