def get_css(T: dict) -> str:
    """
    Restituisce il CSS dell'app adattato dinamicamente al tema T.
    Tutti i colori vengono estratti dal dizionario T passato come argomento.
    """
    # Sidebar: i colori vengono estratti dal tema (chiave sidebar_*).
    # Fallback ai valori dark storici per retrocompatibilità con temi senza queste chiavi.
    _SB_ACCENT = T.get("sidebar_accent", "#D97706")
    _SB_BG_CSS = T.get("sidebar_bg",     "linear-gradient(180deg, #111110 0%, #0e0e0d 100%)")
    _SB_BORDER = T.get("sidebar_border", "#252420")
    _SB_MUTED  = "#8a8880"
    _SB_TEXT   = "#e8e6e0"

    # Calcola se il tema è light (background chiaro) per aggiustare
    # alcuni colori del pulsante primary
    _is_light = _is_light_color(T["bg"])
    _btn_primary_bg = T["accent"]

    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; }}

  .stApp {{
    background-color: {T['bg']} !important;
    font-family: 'DM Sans', sans-serif;
    color: {T['text']};
    transition: background-color 0.25s ease, color 0.25s ease;
  }}

  .block-container {{
    padding: 5rem 1.5rem 4rem !important;
    max-width: 1050px !important;
    margin: 0 auto !important;
  }}

  #MainMenu, footer {{ visibility: hidden; }}
  .stDecoration {{ display: none; }}

  header[data-testid="stHeader"] {{
    background-color: {T['bg']} !important;
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
    border-color: {T['accent']} !important;
  }}
  header button:hover svg {{
    fill: {T['accent']} !important;
  }}
  .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a {{ display: none !important; }}

  /* ════ SIDEBAR — Dark Premium ════ */
  /* Palette fissa dark, indipendente dal tema pagina */
  [data-testid="stSidebar"] {{
    background: {_SB_BG_CSS} !important;
    border-right: 1px solid {_SB_BORDER} !important;
  }}
  .sidebar-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: .95rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    color: #f5f3ed !important;
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
  /* Testo globale sidebar */
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div {{
    color: {_SB_TEXT} !important;
  }}
  /* Label dei widget */
  [data-testid="stSidebar"] .stTextInput label p,
  [data-testid="stSidebar"] .stSelectbox label p,
  [data-testid="stSidebar"] .stNumberInput label p {{
    color: {_SB_MUTED} !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
  }}
  [data-testid="stSidebar"] .stCheckbox label {{
    color: {_SB_TEXT} !important;
    font-size: 0.9rem !important;
  }}
  /* Inputs */
  [data-testid="stSidebar"] .stTextInput input,
  [data-testid="stSidebar"] .stNumberInput input {{
    background: #1a1916 !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 8px !important;
    color: #f5f3ed !important;
    font-size: 0.88rem !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: #1a1916 !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
    color: #e8e6e0 !important;
    font-size: 0.88rem !important;
  }}
  [data-testid="stSidebar"] .stRadio label,
  [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  /* Pulsanti standard sidebar */
  [data-testid="stSidebar"] .stButton button {{
    background: #1c1b18 !important;
    color: #d8d6ce !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
  }}
  [data-testid="stSidebar"] .stButton button:hover {{
    background: #28261f !important;
    border-color: {_SB_ACCENT} !important;
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .section-label {{
    color: #4a4840 !important;
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
    border: 2px solid {T['accent']} !important;
    border-radius: 10px !important;
    color: {T['accent']} !important;
    width: 40px !important;
    height: 40px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 12px {T['accent']}33 !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
    padding: 0 !important;
  }}
  [data-testid="collapsedControl"] button:hover {{
    background: {T['accent']} !important;
    box-shadow: 0 4px 18px {T['accent']}55 !important;
    transform: scale(1.08) !important;
  }}
  [data-testid="collapsedControl"] button:hover svg {{
    fill: #ffffff !important;
    color: #ffffff !important;
    stroke: #ffffff !important;
  }}
  [data-testid="collapsedControl"] button svg {{
    fill: {T['accent']} !important;
    color: {T['accent']} !important;
    stroke: {T['accent']} !important;
    width: 18px !important;
    height: 18px !important;
  }}

  /* ── Sidebar section labels ── */
  [data-testid="stSidebar"] .sidebar-label,
  .sidebar-label {{
    font-size: 0.65rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: {_SB_ACCENT} !important;
    margin: 1.1rem 0 0.45rem 0 !important;
    padding-bottom: 0.3rem !important;
    border-bottom: 1px solid {_SB_BORDER} !important;
    display: flex !important;
    align-items: center !important;
    gap: 5px !important;
  }}

  /* ── Logout button ── */
  [data-testid="stSidebar"] .logout-btn-wrap div.stButton > button,
  [data-testid="stSidebar"] .logout-btn-wrap .stButton button,
  [data-testid="stSidebar"] .logout-btn-wrap button {{
    background: transparent !important;
    color: #f87171 !important;
    border: 1px solid #3d1515 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    width: 100% !important;
    min-height: unset !important;
    box-shadow: none !important;
    transition: background 0.15s ease, border-color 0.15s ease !important;
    letter-spacing: 0.02em !important;
  }}
  [data-testid="stSidebar"] .logout-btn-wrap div.stButton > button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap .stButton button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap button:hover {{
    background: #1f0a0a !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
  }}

  /* ════ TESTO GLOBALE — forza colore su tutti i widget (fix tema chiaro) ════ */
  .stApp p,
  .stApp span:not([class*="sidebar"]),
  .stApp div:not([data-testid="stSidebar"] *),
  .stMarkdown p,
  .stMarkdown span,
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] span,
  [data-testid="stText"] p,
  .stText p {{
    color: {T['text']} !important;
  }}

  /* Toggle help text / hint accanto ai toggle ✓ — fix chiave tema chiaro */
  .stCheckbox + div p,
  .stToggle + div p,
  [data-testid="stWidgetLabel"] p,
  [data-testid="stWidgetLabel"] span,
  [data-testid="InputInstructions"] {{
    color: {T['text2']} !important;
  }}

  /* Caption e testo small dei widget */
  small, .stCaption, .stCaption p,
  [data-testid="stCaptionContainer"],
  [data-testid="stCaptionContainer"] p {{
    color: {T['muted']} !important;
  }}

  /* Testo del selectbox e dei suoi option */
  .stSelectbox [data-baseweb="select"] [data-value],
  .stSelectbox [data-baseweb="select"] span,
  .stSelectbox label p {{
    color: {T['text']} !important;
  }}

  h1, h2, h3 {{
    font-family: 'DM Sans', sans-serif !important;
    color: {T['text']} !important;
    letter-spacing: -0.02em;
  }}

  /* ════ HERO ════ */
  .hero-wrap {{
    margin-bottom: 2.5rem;
    padding-bottom: 1.8rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    flex-wrap: wrap;
    gap: 0;
    position: relative;
  }}
  .hero-left {{ flex: 1; min-width: 200px; text-align: center; }}
  @keyframes iconBounce {{
    0%   {{ transform: rotate(0deg) scale(1); }}
    15%  {{ transform: rotate(-12deg) scale(1.15); }}
    30%  {{ transform: rotate(8deg) scale(1.1); }}
    45%  {{ transform: rotate(-6deg) scale(1.05); }}
    60%  {{ transform: rotate(3deg) scale(1.02); }}
    75%  {{ transform: rotate(-1deg) scale(1.01); }}
    100% {{ transform: rotate(0deg) scale(1); }}
  }}
  @keyframes badgePop {{
    0%   {{ opacity: 0; transform: translateY(6px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes subFadeIn {{
    0%   {{ opacity: 0; transform: translateY(4px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
  }}
  .hero-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 108px !important;
    font-weight: 900 !important;
    color: {T['text']};
    line-height: 1.0;
    margin: 0 0 0.15rem 0;
    letter-spacing: -0.04em;
    display: inline-flex;
    align-items: center;
    gap: 0;
    justify-content: center;
  }}
  .hero-icon {{
    display: inline-block;
    margin-right: 0.3em;
    animation: iconBounce 1.1s ease 0.2s both;
    transform-origin: center bottom;
  }}
  .hero-ai {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent2']} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: badgePop 0.6s ease 0.5s both;
  }}
  .hero-sub {{
    font-size: 1.05rem;
    color: {T['text2']};
    margin: 0 0 0.55rem 0;
    font-weight: 500;
    letter-spacing: -0.01em;
    animation: subFadeIn 0.5s ease 0.35s both;
    opacity: 0;
  }}
  .hero-beta {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {T['muted']};
    background: {T['card2']};
    border: 1px solid {T['border2']};
    border-radius: 100px;
    padding: 2px 10px;
    font-family: 'DM Sans', sans-serif;
    animation: badgePop 0.5s ease 0.75s both;
    opacity: 0;
  }}

  /* ════ SIDEBAR HINT MINIMALE (in alto a sinistra) ════ */
  .sidebar-hint-inline {{
    position: fixed;
    top: .6rem;
    left: 3.8rem;
    z-index: 900;
    font-size: .68rem;
    font-weight: 500;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    letter-spacing: .01em;
    pointer-events: none;
    white-space: nowrap;
  }}

  /* ════ INPUTS ════ */
  .stTextInput label p,
  .stSelectbox label p,
  .stNumberInput label p,
  .stTextArea label p,
  .stFileUploader label p {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: {T['text2']} !important;
    letter-spacing: 0.01em;
    text-transform: uppercase;
    margin-bottom: 4px !important;
  }}

  .stTextInput input,
  .stNumberInput input {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 14px 16px !important;
    min-height: 52px !important;
    height: 52px !important;
    box-sizing: border-box !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }}
  .stTextInput input::placeholder,
  .stNumberInput input::placeholder {{
    color: {T['muted']} !important;
    opacity: 1 !important;
  }}
  .stTextInput input:focus,
  .stNumberInput input:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 3px {T['accent_light']} !important;
    outline: none !important;
  }}
  .stTextArea textarea {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 10px 14px !important;
  }}
  .stTextArea textarea::placeholder {{
    color: {T['muted']} !important;
    opacity: 1 !important;
  }}
  .stTextArea textarea:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 3px {T['accent_light']} !important;
  }}

  .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
  }}
  .stSelectbox [data-baseweb="select"] span {{
    color: {T['text']} !important;
  }}

  .stCheckbox label {{
    color: {T['text']} !important;
    font-size: 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  .stCheckbox [data-testid="stCheckbox"] span:first-child {{
    background-color: {T['input_bg']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 5px !important;
  }}

  /* ════ BUTTONS ════ */
  div.stButton > button[kind="primary"] {{
    background: {_btn_primary_bg} !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.2s ease, filter 0.2s ease !important;
    box-shadow: 0 2px 12px {T['accent']}55 !important;
    display: block !important;
    min-height: 46px !important;
    padding: 0.6rem 1rem !important;
    font-size: 1rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
  }}
  div.stButton > button[kind="primary"]:hover {{
    transform: scale(1.05) !important;
    box-shadow: 0 10px 25px {T['accent']}55 !important;
    filter: brightness(1.1) !important;
    border: none !important;
  }}
  div.stButton > button[kind="primary"]:active {{
    transform: scale(0.98) !important;
  }}
  div.stButton > button[kind="primary"]:disabled {{
    background: #9CA3AF !important;
    box-shadow: none !important;
    transform: none !important;
    filter: none !important;
    cursor: not-allowed !important;
    opacity: 0.7 !important;
  }}

  .stDownloadButton button,
  [data-testid="stDownloadButton"] button,
  .stButton [data-testid="baseButton-secondary"],
  .stButton button[kind="secondary"],
  button[data-testid="baseButton-secondary"] {{
    background: {T['card']} !important;
    color: {T['text2']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.4rem !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
    width: 100% !important;
  }}
  .stDownloadButton button:hover,
  [data-testid="stDownloadButton"] button:hover,
  .stButton [data-testid="baseButton-secondary"]:hover,
  button[data-testid="baseButton-secondary"]:hover {{
    background: {T['hover']} !important;
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 6px 20px {T['accent']}28 !important;
  }}

  /* ════ DOWNLOAD ACCENT BUTTON (PDF primario) ════ */
  .dl-accent-btn .stDownloadButton button,
  .dl-accent-btn [data-testid="stDownloadButton"] button {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent']}cc 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    font-size: 1.1rem !important;
    font-weight: 800 !important;
    padding: 1rem 1.6rem !important;
    min-height: 56px !important;
    letter-spacing: .01em !important;
    box-shadow: 0 4px 24px {T['accent']}55 !important;
    transition: all .2s cubic-bezier(.175,.885,.32,1.275) !important;
    width: 100% !important;
  }}
  .dl-accent-btn .stDownloadButton button:hover,
  .dl-accent-btn [data-testid="stDownloadButton"] button:hover {{
    filter: brightness(1.12) !important;
    box-shadow: 0 8px 32px {T['accent']}77 !important;
    transform: translateY(-2px) scale(1.01) !important;
  }}

  /* ════ ACTION CARD ════ */
  .action-card {{
    background: {T['card']} !important;
    border: 2px solid {T['border']} !important;
    border-radius: 14px !important;
    padding: 1.2rem !important;
    margin-bottom: 1rem !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
  }}
  .action-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, {T['accent']} 0%, {T['accent']}00 100%);
    opacity: 0;
    transition: opacity 0.25s ease;
  }}
  .action-card:hover {{
    border-color: {T['accent']}88 !important;
    box-shadow: 0 8px 24px {T['accent']}15 !important;
    transform: translateY(-2px) !important;
  }}
  .action-card:hover::before {{
    opacity: 1;
  }}
  .action-card .stDownloadButton button,
  .action-card .stButton button {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent']}ee 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.5rem !important;
    box-shadow: 0 4px 14px {T['accent']}35 !important;
    transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
  }}
  .action-card .stDownloadButton button:hover,
  .action-card .stButton button:hover {{
    transform: scale(1.03) !important;
    box-shadow: 0 6px 20px {T['accent']}50 !important;
    filter: brightness(1.08) !important;
  }}
  .action-card .stDownloadButton button:active,
  .action-card .stButton button:active {{
    transform: scale(0.98) !important;
  }}
  .action-card [data-testid="stExpander"] {{
    background: transparent !important;
    border: 2px dashed {T['border2']} !important;
    border-radius: 12px !important;
    transition: all 0.2s ease !important;
  }}
  .action-card [data-testid="stExpander"]:hover {{
    border-color: {T['accent']} !important;
    background: {T['accent_light']} !important;
  }}
  .action-card [data-testid="stExpander"] summary {{
    background: transparent !important;
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 1rem 1.2rem !important;
  }}
  .action-card [data-testid="stExpander"] summary:hover {{
    color: {T['accent']} !important;
  }}
  .action-card [data-testid="stExpander"] summary svg {{
    color: {T['accent']} !important;
  }}

  .tex-btn-wrap .stDownloadButton button,
  .tex-btn-wrap [data-testid="stDownloadButton"] button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 6px !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    padding: 0.3rem 0.7rem !important;
    width: 100% !important;
    box-shadow: none !important;
    transform: none !important;
  }}
  .tex-btn-wrap .stDownloadButton button:hover,
  .tex-btn-wrap [data-testid="stDownloadButton"] button:hover {{
    color: {T['text2']} !important;
    border-color: {T['border2']} !important;
    background: {T['card2']} !important;
    box-shadow: none !important;
    transform: translateY(-1px) !important;
  }}

  /* ════ EXPANDER ════ */
  [data-testid="stExpander"] {{
    background: {T['card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 12px !important;
    margin-bottom: 0.75rem !important;
    overflow: hidden;
  }}
  [data-testid="stExpander"] summary {{
    padding: 0.85rem 1.1rem !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: {T['text']} !important;
    background: {T['card']} !important;
  }}
  [data-testid="stExpander"] summary:hover {{
    background: {T['hover']} !important;
  }}
  [data-testid="stExpander"] > div > div {{
    padding: 0.5rem 1.1rem 1rem !important;
  }}

  hr {{
    border: none;
    border-top: 1px solid {T['border']} !important;
    margin: 2rem 0 !important;
  }}

  [data-testid="stFileUploader"] section {{
    background: {T['card2']} !important;
    border: 1.5px dashed {T['border2']} !important;
    border-radius: 10px !important;
    padding: 0.75rem 1rem !important;
    min-height: unset !important;
  }}
  [data-testid="stFileUploader"] section > div {{ gap: 0.3rem !important; }}
  [data-testid="stFileUploadDropzone"] p,
  [data-testid="stFileUploadDropzone"] span,
  [data-testid="stFileUploadDropzone"] small,
  [data-testid="stFileUploader"] span,
  [data-testid="stFileUploader"] small,
  [data-testid="stFileUploader"] p {{
    color: {T['text2']} !important;
    opacity: 1 !important;
  }}
  [data-testid="stFileUploadDropzone"] button,
  [data-testid="stFileUploader"] button {{
    color: {T['accent']} !important;
    font-weight: 600 !important;
  }}
  [data-testid="stFileUploadDropzone"] svg {{
    fill: {T['muted']} !important;
    color: {T['muted']} !important;
  }}

  .chip {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: {T['accent_light']};
    color: {T['accent']};
    border: 1px solid {T['accent']};
    border-radius: 100px;
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}

  .expander-heading {{
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    color: {T['text2']} !important;
    margin: 1rem 0 0.4rem 0 !important;
    padding: 4px 10px !important;
    background: {T['card2']} !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 0 6px 6px 0 !important;
    display: block !important;
  }}

  /* ════ STEP LABELS ════ */
  .step-label {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 2.2rem 0 0.75rem 0;
    font-family: 'DM Sans', sans-serif;
  }}
  .step-num {{
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: {T['accent']};
    color: #ffffff;
    font-size: 0.68rem;
    font-weight: 900;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    letter-spacing: 0;
    box-shadow: 0 2px 8px {T['accent']}55;
  }}
  .step-title {{
    font-size: 0.82rem;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {T['text']};
  }}
  .step-line {{
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, {T['border2']} 0%, transparent 100%);
  }}

  /* ════ AI HINT — leggibile su qualsiasi tema ════ */
  .ai-hint {{
    display: flex;
    align-items: center;
    gap: 9px;
    background: {T.get('hint_bg', T['accent_light'])};
    border: 1px solid {T.get('hint_border', T['accent'] + '55')};
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 0.78rem;
    color: {T.get('hint_text', T['text2'])};
    margin: 1.8rem 0 0.6rem 0;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.4;
  }}
  .ai-hint-icon {{ font-size: 1rem; flex-shrink: 0; }}
  .ai-hint strong {{ color: {T['accent']}; font-weight: 700; }}

  .modifica-hint {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-left: 3px solid {T['accent']};
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 0.75rem;
    font-size: 0.8rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}
  .modifica-hint-icon {{ font-size: 1rem; flex-shrink: 0; margin-top: 1px; }}
  .modifica-hint strong {{ color: {T['text']}; font-weight: 700; }}

  /* ════ PERSONALIZZA EXPANDER ════ */
  .personalizza-wrap [data-testid="stExpander"] {{
    border: 1.5px solid {T['accent']}44 !important;
    border-radius: 14px !important;
    background: {T['card']} !important;
    box-shadow: 0 2px 16px {T['accent']}0f !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] summary {{
    background: {T['accent_light']} !important;
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    padding: 1rem 1.2rem !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] summary:hover {{
    background: {T['accent_light']} !important;
    filter: brightness(0.96);
  }}
  .personalizza-wrap [data-testid="stExpander"] summary svg {{
    color: {T['accent']} !important;
    fill: {T['accent']} !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] > div > div {{
    padding: 1rem 1.2rem 1.2rem !important;
  }}

  /* ════ GENERA SECTION ════ */
  .genera-section {{
    margin-top: 2.2rem;
    margin-bottom: 0.5rem;
  }}

  /* ════ ONBOARDING — messaggio statico, sottile ════ */
  .onboard-guide {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px 10px;
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: .45rem .9rem;
    margin-bottom: .9rem;
    font-family: 'DM Sans', sans-serif;
  }}
  .onboard-step {{
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: .7rem;
    color: {T['muted']};
    white-space: nowrap;
  }}
  .onboard-num {{
    font-size: .68rem;
    font-weight: 800;
    color: {T['accent']};
  }}
  .onboard-sep {{
    font-size: .62rem;
    color: {T['muted']};
    opacity: .5;
  }}

  .opt-label {{
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: {T['text2']} !important;
    margin: 0.7rem 0 0.3rem 0 !important;
    display: block !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* ════ PULSANTE SECONDARIO OUTLINE ════ */
  .btn-secondary-accent div.stButton > button,
  .btn-secondary-accent .stButton > button {{
    background: transparent !important;
    color: {T['accent']} !important;
    border: 1.5px solid {T['accent']}88 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: .88rem !important;
    padding: 0.45rem 1rem !important;
    min-height: 38px !important;
    box-shadow: none !important;
    transition: border-color .15s ease, color .15s ease !important;
  }}
  .btn-secondary-accent div.stButton > button:hover,
  .btn-secondary-accent .stButton > button:hover {{
    border-color: {T['accent']} !important;
    background: {T['accent_light']} !important;
  }}

  /* ════ STAGE 3 SECTION TITLES ════ */
  .s3-section-title {{
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: {T['muted']};
    margin: 1.1rem 0 .65rem 0;
    padding-bottom: .4rem;
    border-bottom: 1px solid {T['border']};
    display: flex;
    align-items: center;
    gap: 7px;
    font-family: 'DM Sans', sans-serif;
  }}
  .s3-section-title::before {{
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: {T['accent']};
    display: inline-block;
    flex-shrink: 0;
  }}

  .s3-card-label {{
    font-size: .65rem;
    font-weight: 700;
    letter-spacing: .09em;
    text-transform: uppercase;
    color: {T['muted']};
    margin: .8rem 0 .35rem 0;
    font-family: 'DM Sans', sans-serif;
  }}

  /* ════ HINT DOCX ════ */
  .hint-docx {{
    background: {T.get('hint_bg', T['accent_light'])} !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    margin-top: 8px !important;
    font-size: 0.8rem !important;
    color: {T.get('hint_text', T['text2'])} !important;
    line-height: 1.5 !important;
  }}
  .hint-docx strong {{
    color: {T['accent']} !important;
  }}

  /* ════ MISC ════ */
  .section-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {T['muted']};
    margin: 1.2rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid {T['border']};
  }}

  .hint {{
    font-size: 0.78rem;
    color: {T['muted']};
    margin-top: 4px;
    line-height: 1.4;
  }}

  .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {T['text']} !important;
    font-size: 0.88rem !important;
  }}
  .stSlider [data-baseweb="slider"] [role="slider"] {{
    background: {T['accent']} !important;
    border-color: {T['accent']} !important;
  }}
  .stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] {{
    color: {T['muted']} !important;
  }}

  .stToggle [data-baseweb="toggle"] {{
    background: {T['border2']} !important;
    border-radius: 100px !important;
    transition: background 0.2s ease;
  }}
  .stToggle [data-baseweb="toggle"][aria-checked="true"] {{
    background: {T['accent']} !important;
  }}
  /* Etichetta e testo toggle — visibile su tema chiaro E scuro */
  .stToggle span,
  .stToggle label,
  .stToggle p,
  .stToggle [data-testid="stWidgetLabel"] p,
  .stToggle [data-testid="stMarkdownContainer"] p {{
    color: {T['text']} !important;
    font-size: 0.88rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  /* Testo help (? tooltip) accanto a toggle e checkbox */
  [data-testid="stTooltipIcon"] {{
    opacity: 0.7;
  }}
  [data-testid="stTooltipIcon"] svg {{
    fill: {T['muted']} !important;
    color: {T['muted']} !important;
  }}
  /* Messaggio di help/hint inline accanto ai widget (testo dopo ✓) */
  .stCheckbox [data-testid="stMarkdownContainer"] p,
  .stCheckbox label p,
  .stCheckbox label span,
  [data-baseweb="checkbox"] span,
  [data-baseweb="checkbox"] p,
  [data-baseweb="checkbox"] label {{
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  /* Caption/help text sotto i widget */
  .stTextInput .stCaption, .stSelectbox .stCaption,
  [data-testid="stWidgetLabel"] small,
  [data-testid="stCaptionContainer"] p,
  .stCaption p,
  [data-testid="InputInstructions"] p {{
    color: {T['muted']} !important;
  }}

  .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {T['text']} !important;
    font-size: 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  .stRadio > div {{ gap: 6px !important; }}
  .stRadio [role="radio"] {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 50% !important;
  }}
  .stRadio [role="radio"][aria-checked="true"] {{
    border-color: {T['accent']} !important;
    background: {T['accent']} !important;
  }}

  /* ════ TOASTS / ALERTS ════ */
  .stAlert {{
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
  }}

  /* ════ FAB FEEDBACK (in alto a destra) ════ */
  .fab-link {{
    position: fixed;
    top: .55rem;
    right: 1rem;
    z-index: 9998;
    background: {T['card']};
    border: 1.5px solid {T['border2']};
    color: {T['text2']};
    text-decoration: none;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 5px 11px;
    border-radius: 100px;
    box-shadow: 0 2px 10px rgba(0,0,0,.15);
    transition: border-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
    backdrop-filter: blur(8px);
    white-space: nowrap;
    width: auto;
  }}
  .fab-link:hover {{
    border-color: {T['accent']};
    color: {T['accent']};
    box-shadow: 0 4px 14px {T['accent']}33;
  }}

  /* ════ APP FOOTER ════ */
  .app-footer {{
    text-align: center;
    font-size: 0.72rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    padding: 1.5rem 0 0.5rem 0;
    line-height: 1.6;
    border-top: 1px solid {T['border']};
    margin-top: 2rem;
  }}

  /* ════ MONTHLY BAR ════ */
  .monthly-bar {{
    background: #161513;
    border: 1px solid #252320;
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
    margin: 0.4rem 0 0 0;
  }}
  .monthly-bar-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 7px;
  }}
  .monthly-bar-label {{
    font-size: 0.7rem;
    font-weight: 600;
    color: #ffffff;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: .03em;
  }}
  .monthly-bar-count {{
    font-size: 0.72rem;
    font-weight: 800;
    color: #ffffff;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.03em;
  }}
  .monthly-bar-count.limit-reached {{ color: #ef4444; }}
  .monthly-bar-count.limit-near    {{ color: #D97706; }}
  .monthly-progress {{
    background: #252320;
    border-radius: 100px;
    height: 4px;
    overflow: hidden;
  }}
  .monthly-progress-fill {{
    height: 100%;
    border-radius: 100px;
    transition: width 0.5s ease;
  }}

  /* ════ USER PILL ════ */
  .user-pill {{
    display: flex;
    align-items: center;
    gap: 10px;
    background: #161513;
    border: 1px solid #252320;
    border-radius: 12px;
    padding: 0.6rem 0.85rem;
    margin: 0.5rem 0;
  }}
  .user-avatar {{
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #D97706, #16a34a);
    color: #ffffff;
    font-size: 0.82rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-family: 'DM Sans', sans-serif;
    box-shadow: 0 2px 8px rgba(217,119,6,.4);
  }}
  .user-info {{ flex: 1; min-width: 0; }}
  .user-email {{
    font-size: 0.76rem;
    font-weight: 600;
    color: #d8d6ce;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'DM Sans', sans-serif;
  }}
  .user-role {{
    font-size: 0.63rem;
    color: #4e4c44;
    font-family: 'DM Sans', sans-serif;
    margin-top: 2px;
    font-weight: 500;
  }}

  /* ════ SIDEBAR STORICO BUTTONS ════ */
  [data-testid="stSidebar"] .stButton > button,
  [data-testid="stSidebar"] .stButton > button[kind="secondary"],
  [data-testid="stSidebar"] button[data-testid="baseButton-secondary"],
  [data-testid="stSidebar"] .stDownloadButton button,
  [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {{
    background: #191815 !important;
    color: #c8c6bc !important;
    border: 1px solid #272522 !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transform: none !important;
    padding: 7px 12px !important;
    min-height: 34px !important;
    width: 100% !important;
    letter-spacing: .01em !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover,
  [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover,
  [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover,
  [data-testid="stSidebar"] .stDownloadButton button:hover,
  [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {{
    background: #221f18 !important;
    border-color: #D97706 !important;
    color: #f5c842 !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  /* ── Storico expanders ── */
  [data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: #161513 !important;
    border: 1px solid #222018 !important;
    border-radius: 10px !important;
    margin-bottom: 4px !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    background: #161513 !important;
    color: #b0ae9e !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 0.9rem !important;
    letter-spacing: .01em !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{
    background: #1f1d18 !important;
    color: #e8e6e0 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] > div > div {{
    background: #161513 !important;
    padding: 0.4rem 0.9rem 0.75rem !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] p,
  [data-testid="stSidebar"] [data-testid="stExpander"] span {{
    color: #b0ae9e !important;
  }}

  /* Buttons inside storico expanders */
  [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] button {{
    background: #1f1d18 !important;
    color: #a8a698 !important;
    border: 1px solid #2e2a22 !important;
    border-radius: 7px !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
    padding: 5px 10px !important;
    min-height: 30px !important;
    box-shadow: none !important;
    width: 100% !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button:hover,
  [data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button:hover {{
    background: #D97706 !important;
    border-color: #D97706 !important;
    color: #fff !important;
  }}
  /* Elimina button */
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn button {{
    background: transparent !important;
    border-color: #3d1515 !important;
    color: #f87171 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn .stButton > button:hover,
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn button:hover {{
    background: #1f0a0a !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
  }}
  /* Stella button */
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn button {{
    background: transparent !important;
    border-color: #3a3420 !important;
    color: #7a7040 !important;
    font-size: 1rem !important;
    padding: 2px 6px !important;
    width: auto !important;
    min-height: unset !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn-on .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn-on button {{
    background: #2a1e06 !important;
    border-color: #D97706 !important;
    color: #F59E0B !important;
    width: auto !important;
    min-height: unset !important;
  }}

  /* Logout final overrides (avoid conflicts) */
  [data-testid="stSidebar"] .logout-btn-wrap .stButton > button,
  [data-testid="stSidebar"] .logout-btn-wrap button {{
    background: transparent !important;
    color: #f87171 !important;
    border: 1px solid #3d1515 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    width: 100% !important;
    min-height: unset !important;
    box-shadow: none !important;
  }}
  [data-testid="stSidebar"] .logout-btn-wrap .stButton > button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap button:hover {{
    background: #1f0a0a !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
    box-shadow: none !important;
    transform: none !important;
  }}

  @keyframes tooltipSlideIn {{
    0%   {{ opacity: 0; transform: translateX(-12px); }}
    15%  {{ opacity: 1; transform: translateX(4px); }}
    25%  {{ opacity: 1; transform: translateX(0); }}
    75%  {{ opacity: 1; transform: translateX(0); }}
    90%  {{ opacity: 0; transform: translateX(-8px); }}
    100% {{ opacity: 0; transform: translateX(-8px); }}
  }}
  .sidebar-tooltip {{
    position: fixed;
    top: 0.9rem;
    left: 3.8rem;
    z-index: 9998;
    display: flex;
    align-items: center;
    gap: 7px;
    background: {T['accent']};
    color: #ffffff;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    padding: 7px 13px 7px 10px;
    border-radius: 20px;
    box-shadow: 0 4px 18px {T['accent']}55;
    pointer-events: none;
    white-space: nowrap;
    animation: tooltipSlideIn 4.5s ease forwards;
  }}
  .sidebar-tooltip::before {{
    content: '';
    position: absolute;
    left: -6px;
    top: 50%;
    transform: translateY(-50%);
    border-width: 5px 6px 5px 0;
    border-style: solid;
    border-color: transparent {T['accent']} transparent transparent;
  }}

  /* ════ OVERFLOW — impedisce scroll orizzontale su mobile/tablet ════ */
  html, body {{
    overflow-x: hidden !important;
    max-width: 100vw !important;
  }}
  .stApp {{
    overflow-x: hidden !important;
    max-width: 100vw !important;
  }}
  /* Tutti i container non escono dal viewport */
  .block-container,
  [data-testid="stAppViewContainer"],
  [data-testid="stVerticalBlock"],
  [data-testid="stHorizontalBlock"] {{
    max-width: 100% !important;
    box-sizing: border-box !important;
  }}

  /* ════ RESPONSIVE ════ */
  /* ── Mobile ≤640px ── */
  @media (max-width: 640px) {{
    .hero-title {{ font-size: 52px !important; }}
    /* Breadcrumb pill compatto su mobile */
    .breadcrumb-pill {{
      padding: .45rem .9rem !important;
      gap: 6px !important;
    }}
    .breadcrumb-pill .bc-label {{
      font-size: .72rem !important;
    }}
    .breadcrumb-pill .bc-circle {{
      width: 22px !important;
      height: 22px !important;
      font-size: .6rem !important;
    }}
    .breadcrumb-pill .bc-sep {{
      width: 16px !important;
    }}
    .block-container {{
      padding: 3.5rem 0.75rem 2.5rem !important;
      width: 100% !important;
      max-width: 100% !important;
      zoom: 1 !important;
    }}
    .stTextInput input, .stNumberInput input {{
      min-height: 48px !important;
      height: 48px !important;
      line-height: 1.4 !important;
      font-size: 0.95rem !important;
    }}
    .stTextInput > div > div {{ min-height: 48px !important; }}
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder {{ font-size: 0.95rem !important; opacity: 1 !important; }}
    .stSelectbox [data-baseweb="select"] > div:first-child {{
      padding: 10px 12px !important;
      min-height: 46px !important;
      height: auto !important;
    }}
    .stTextArea textarea {{ font-size: 0.9rem !important; }}
    .stButton button {{ min-height: 46px !important; font-size: 0.95rem !important; }}
    [data-testid="stSidebar"] .block-container {{ padding: 1rem !important; }}
    .stDownloadButton button {{ width: 100% !important; min-height: 46px !important; }}
  }}

  /* ── Tablet piccolo 641–767px ── */
  @media (min-width: 641px) and (max-width: 767px) {{
    .block-container {{
      padding: 1.5rem 1rem 2.5rem !important;
      max-width: 100% !important;
      zoom: 1 !important;
    }}
  }}

  /* ── Tablet grande 768–1024px ── */
  @media (min-width: 768px) and (max-width: 1024px) {{
    .block-container {{
      padding: 1.5rem 1.5rem 3rem !important;
      max-width: 900px !important;
      zoom: 1 !important;
    }}
  }}

  /* ════ PUNTEGGIO MODIFICA (Stage 2) ════ */
  .score-edit-wrap .stNumberInput input {{
    font-size: 0.9rem !important;
    min-height: 36px !important;
    height: 36px !important;
    padding: 6px 10px !important;
    text-align: center !important;
  }}
  .score-edit-wrap label {{ display: none !important; }}

  /* ════ PANNELLO RICALIBRA PUNTEGGI ════ */
  .recalibra-panel {{
    background: {T['card']};
    border: 2px solid {T['border2']};
    border-radius: 14px;
    padding: 1.1rem 1.2rem 1.2rem 1.2rem;
    margin: 1.2rem 0 .8rem 0;
  }}
  .recalibra-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: .78rem;
    font-weight: 800;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: {T['accent']};
    margin-bottom: .75rem;
    display: flex;
    align-items: center;
    gap: 7px;
  }}
  .recalibra-title::before {{
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {T['accent']};
    flex-shrink: 0;
    display: inline-block;
  }}
  .recalibra-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: .4rem .1rem;
    border-bottom: 1px solid {T['border']};
    font-family: 'DM Sans', sans-serif;
    font-size: .83rem;
    color: {T['text2']};
  }}
  .recalibra-row:last-of-type {{ border-bottom: none; }}
  .recalibra-sum-ok {{
    display: flex; align-items: center; gap: 8px;
    background: {T['success']}18;
    border: 1.5px solid {T['success']};
    border-radius: 10px;
    padding: .55rem 1rem;
    margin-top: .75rem;
    font-size: .82rem;
    font-weight: 700;
    color: {T['success']};
    font-family: 'DM Sans', sans-serif;
  }}
  .recalibra-sum-err {{
    display: flex; align-items: center; gap: 8px;
    background: {T['err']}12;
    border: 1.5px solid {T['err']};
    border-radius: 10px;
    padding: .55rem 1rem;
    margin-top: .75rem;
    font-size: .82rem;
    font-weight: 700;
    color: {T.get('hint_text', T['err'])};
    font-family: 'DM Sans', sans-serif;
  }}

  /* ════ PULSANTE CONFERMA ORO — full-width, colore ambra ════ */
  .btn-confirm-gold div.stButton > button,
  .btn-confirm-gold .stButton > button {{
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    font-size: 1.08rem !important;
    font-weight: 800 !important;
    min-height: 54px !important;
    padding: 0.75rem 1.5rem !important;
    box-shadow: 0 4px 20px #F59E0B55 !important;
    transition: all .2s cubic-bezier(.175,.885,.32,1.275) !important;
    letter-spacing: .01em !important;
    width: 100% !important;
  }}
  .btn-confirm-gold div.stButton > button:hover,
  .btn-confirm-gold .stButton > button:hover {{
    filter: brightness(1.08) !important;
    box-shadow: 0 8px 32px #F59E0B77 !important;
    transform: translateY(-2px) scale(1.01) !important;
  }}
  .btn-confirm-gold div.stButton > button:active,
  .btn-confirm-gold .stButton > button:active {{
    transform: scale(0.98) !important;
  }}

  /* ════ PULSANTE RICONFIGURA PICCOLO ════ */
  .btn-riconfigura-small div.stButton > button,
  .btn-riconfigura-small .stButton > button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 8px !important;
    font-size: .78rem !important;
    font-weight: 500 !important;
    min-height: 32px !important;
    padding: 0.25rem 0.75rem !important;
    box-shadow: none !important;
    width: auto !important;
    display: inline-block !important;
  }}
  .btn-riconfigura-small div.stButton > button:hover,
  .btn-riconfigura-small .stButton > button:hover {{
    color: {T['text2']} !important;
    border-color: {T['border2']} !important;
    background: {T['hover']} !important;
  }}

  /* ════ ZOOM 110% su desktop largo ≥1025px ════ */
  @media (min-width: 1025px) {{
    .block-container {{
      zoom: 1.1;
      max-width: 955px !important;
    }}
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

