# ── config.py ──────────────────────────────────────────────────────────────────
# Tutte le costanti dell'app. Nessuna logica, nessun import di streamlit.
# ───────────────────────────────────────────────────────────────────────────────

# ── APP ────────────────────────────────────────────────────────────────────────
APP_NAME          = "VerificAI"
APP_ICON          = "📝"
APP_TAGLINE       = "Crea verifiche su misura in pochi secondi"
SHARE_URL         = "https://verificai.streamlit.app"
FEEDBACK_FORM_URL = "https://forms.gle/KNu8v8iDVUiGkQUL8"

# ── LIMITI E RUOLI ─────────────────────────────────────────────────────────────
LIMITE_MENSILE = 5
ADMIN_EMAILS   = {"giacomosaragoni96@gmail.com"}

# ── MODELLI AI ─────────────────────────────────────────────────────────────────
MODELLI_DISPONIBILI = {
    "⚡ Flash 2.5 Lite (velocissimo)": {
        "id":  "gemini-2.5-flash-lite",
        "pro": False,
    },
    "⚡ Flash 2.5 (bilanciato)": {
        "id":  "gemini-2.5-flash",
        "pro": True,
    },
    "🧠 Pro 2.5 (massima qualità)": {
        "id":  "gemini-2.5-pro",
        "pro": True,
    },
}

# ── TEMI UI ────────────────────────────────────────────────────────────────────
# Ogni tema espone le stesse chiavi per garantire compatibilità con styles.py.
# Chiavi obbligatorie:
#   bg, bg2, card, card2, border, border2, text, text2, muted,
#   accent, accent_light, accent2, success, warn, err,
#   shadow, shadow_md, input_bg, hover,
#   hint_bg, hint_text, hint_border
#   sidebar_bg      → sfondo sidebar (linear-gradient CSS)
#   sidebar_border  → bordo destro sidebar
#   sidebar_accent  → colore accent sidebar (label, hover btn, ecc.)
# ───────────────────────────────────────────────────────────────────────────────

THEMES = {

    # ══════════════════════════════════════════════════════════════════
    # TEMI CHIARI  (5 originali + 1 esistente)
    # ══════════════════════════════════════════════════════════════════

    # 1. ARCTIC BLUE — predefinito storico (chiaro)
    "chiaro": {
        "bg":           "#EAF3FB",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FFF8E7",
        "border":       "#BFD9EE",
        "border2":      "#E8C87A",
        "text":         "#0D2B45",
        "text2":        "#2C5F82",
        "muted":        "#4A7A9B",
        "accent":       "#D97706",
        "accent_light": "#FEF3C7",
        "accent2":      "#F59E0B",
        "success":      "#059669",
        "warn":         "#B45309",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.05)",
        "shadow_md":    "0 4px 12px rgba(217,119,6,.15)",
        "input_bg":     "#F4F9FD",
        "hover":        "#FEF3C7",
        "hint_bg":      "#FEF3C7",
        "hint_text":    "#78350F",
        "hint_border":  "#F59E0B",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #111110 0%, #0e0e0d 100%)",
        "sidebar_border": "#252420",
        "sidebar_accent": "#D97706",
    },

    # 2. MINIMAL GRAY (chiaro)
    "minimal_gray": {
        "bg":           "#F5F5F5",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FAFAFA",
        "border":       "#E0E0E0",
        "border2":      "#BDBDBD",
        "text":         "#1A1A1A",
        "text2":        "#424242",
        "muted":        "#757575",
        "accent":       "#424242",
        "accent_light": "#F5F5F5",
        "accent2":      "#616161",
        "success":      "#2E7D32",
        "warn":         "#E65100",
        "err":          "#C62828",
        "shadow":       "0 1px 3px rgba(0,0,0,.10)",
        "shadow_md":    "0 4px 12px rgba(0,0,0,.12)",
        "input_bg":     "#FAFAFA",
        "hover":        "#EEEEEE",
        "hint_bg":      "#EEEEEE",
        "hint_text":    "#1A1A1A",
        "hint_border":  "#BDBDBD",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #1C1C1C 0%, #141414 100%)",
        "sidebar_border": "#2A2A2A",
        "sidebar_accent": "#9E9E9E",
    },

    # 3. SOFT BLUE (chiaro)
    "soft_blue": {
        "bg":           "#EFF6FF",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#EFF6FF",
        "border":       "#BFDBFE",
        "border2":      "#93C5FD",
        "text":         "#1E3A5F",
        "text2":        "#2D5B8E",
        "muted":        "#5B8DB8",
        "accent":       "#2563EB",
        "accent_light": "#DBEAFE",
        "accent2":      "#3B82F6",
        "success":      "#16A34A",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(37,99,235,.10)",
        "shadow_md":    "0 4px 14px rgba(37,99,235,.18)",
        "input_bg":     "#F0F7FF",
        "hover":        "#DBEAFE",
        "hint_bg":      "#DBEAFE",
        "hint_text":    "#1E3A5F",
        "hint_border":  "#93C5FD",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #0F172A 0%, #0C1422 100%)",
        "sidebar_border": "#1E3A5F",
        "sidebar_accent": "#3B82F6",
    },

    # 4. SAGE GARDEN (chiaro, verde salvia)
    "sage_garden": {
        "bg":           "#F0F4F0",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#F7FAF7",
        "border":       "#C8D8C8",
        "border2":      "#A8C4A8",
        "text":         "#1C2E1C",
        "text2":        "#2D4A2D",
        "muted":        "#5C7A5C",
        "accent":       "#2D6A2D",
        "accent_light": "#E6F2E6",
        "accent2":      "#3D8B3D",
        "success":      "#1A7A3A",
        "warn":         "#C47A00",
        "err":          "#C0392B",
        "shadow":       "0 1px 3px rgba(45,106,45,.10)",
        "shadow_md":    "0 4px 14px rgba(45,106,45,.15)",
        "input_bg":     "#F3F8F3",
        "hover":        "#DFF0DF",
        "hint_bg":      "#E6F2E6",
        "hint_text":    "#1C2E1C",
        "hint_border":  "#A8C4A8",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #0E1A0E 0%, #0B150B 100%)",
        "sidebar_border": "#1C2E1C",
        "sidebar_accent": "#3D8B3D",
    },

    # 5. SANDY EARTH (chiaro, toni caldi terracotta)
    "sandy_earth": {
        "bg":           "#FAF5EF",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FDF8F2",
        "border":       "#E8D5BC",
        "border2":      "#D4B896",
        "text":         "#3D2009",
        "text2":        "#6B3A18",
        "muted":        "#9C6640",
        "accent":       "#B45309",
        "accent_light": "#FEF3C7",
        "accent2":      "#D97706",
        "success":      "#15803D",
        "warn":         "#92400E",
        "err":          "#B91C1C",
        "shadow":       "0 1px 3px rgba(180,83,9,.10)",
        "shadow_md":    "0 4px 14px rgba(180,83,9,.15)",
        "input_bg":     "#FDF6EE",
        "hover":        "#FDE8C8",
        "hint_bg":      "#FEF3C7",
        "hint_text":    "#3D2009",
        "hint_border":  "#D4B896",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #1A0D05 0%, #140A03 100%)",
        "sidebar_border": "#2E1A0A",
        "sidebar_accent": "#D97706",
    },

    # 6. HIGH CONTRAST WHITE (chiaro, massima accessibilità WCAG AA)
    "high_contrast": {
        "bg":           "#FFFFFF",
        "bg2":          "#F2F2F2",
        "card":         "#FFFFFF",
        "card2":        "#F8F8F8",
        "border":       "#767676",
        "border2":      "#505050",
        "text":         "#000000",
        "text2":        "#1A1A1A",
        "muted":        "#444444",
        "accent":       "#0000CC",
        "accent_light": "#E8E8FF",
        "accent2":      "#0000AA",
        "success":      "#006600",
        "warn":         "#804000",
        "err":          "#CC0000",
        "shadow":       "0 1px 3px rgba(0,0,0,.20)",
        "shadow_md":    "0 4px 14px rgba(0,0,0,.25)",
        "input_bg":     "#F8F8F8",
        "hover":        "#E8E8FF",
        "hint_bg":      "#E8E8FF",
        "hint_text":    "#000080",
        "hint_border":  "#0000CC",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #000000 0%, #111111 100%)",
        "sidebar_border": "#444444",
        "sidebar_accent": "#FFFFFF",
    },

    # ══════════════════════════════════════════════════════════════════
    # TEMI SCURI  (5 nuovi + 1 esistente)
    # ══════════════════════════════════════════════════════════════════

    # 7. MIDNIGHT BLUE — esistente (scuro)
    "scuro": {
        "bg":           "#0F172A",
        "bg2":          "#1E293B",
        "card":         "#1E293B",
        "card2":        "#253047",
        "border":       "#2D3F5C",
        "border2":      "#3B4F6E",
        "text":         "#F1F5F9",
        "text2":        "#CBD5E1",
        "muted":        "#64748B",
        "accent":       "#F59E0B",
        "accent_light": "#29220F",
        "accent2":      "#10B981",
        "success":      "#10B981",
        "warn":         "#F59E0B",
        "err":          "#EF4444",
        "shadow":       "0 1px 3px rgba(0,0,0,.4)",
        "shadow_md":    "0 4px 20px rgba(0,0,0,.5)",
        "input_bg":     "#253047",
        "hover":        "#2D3F5C",
        "hint_bg":      "#29220F",
        "hint_text":    "#FDE68A",
        "hint_border":  "#78450A",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #111110 0%, #0e0e0d 100%)",
        "sidebar_border": "#252420",
        "sidebar_accent": "#F59E0B",
    },

    # 8. DEEP MIDNIGHT (scuro, blu petrolio profondo)
    "deep_midnight": {
        "bg":           "#050D1A",
        "bg2":          "#0A1628",
        "card":         "#0D1C32",
        "card2":        "#112240",
        "border":       "#1A2F4A",
        "border2":      "#223C5E",
        "text":         "#CCD6F6",
        "text2":        "#8892B0",
        "muted":        "#4A5568",
        "accent":       "#64FFDA",
        "accent_light": "#0A2A24",
        "accent2":      "#57CBFF",
        "success":      "#64FFDA",
        "warn":         "#FFCB6B",
        "err":          "#FF5370",
        "shadow":       "0 2px 8px rgba(0,0,0,.6)",
        "shadow_md":    "0 6px 24px rgba(0,0,0,.7)",
        "input_bg":     "#112240",
        "hover":        "#1A2F4A",
        "hint_bg":      "#0A2A24",
        "hint_text":    "#64FFDA",
        "hint_border":  "#0D4037",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #020810 0%, #040C1A 100%)",
        "sidebar_border": "#0E1F36",
        "sidebar_accent": "#64FFDA",
    },

    # 9. SLATE CARBON (scuro, grigio carbone professionale)
    "slate_carbon": {
        "bg":           "#1C1C1E",
        "bg2":          "#2C2C2E",
        "card":         "#2C2C2E",
        "card2":        "#3A3A3C",
        "border":       "#3A3A3C",
        "border2":      "#4A4A4C",
        "text":         "#F2F2F7",
        "text2":        "#EBEBF5",
        "muted":        "#8E8E93",
        "accent":       "#0A84FF",
        "accent_light": "#001A33",
        "accent2":      "#30D158",
        "success":      "#30D158",
        "warn":         "#FF9F0A",
        "err":          "#FF453A",
        "shadow":       "0 2px 6px rgba(0,0,0,.5)",
        "shadow_md":    "0 6px 20px rgba(0,0,0,.6)",
        "input_bg":     "#3A3A3C",
        "hover":        "#48484A",
        "hint_bg":      "#001A33",
        "hint_text":    "#0A84FF",
        "hint_border":  "#003366",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #101010 0%, #0A0A0A 100%)",
        "sidebar_border": "#2C2C2E",
        "sidebar_accent": "#0A84FF",
    },

    # 10. FOREST DARK (scuro, verde foresta profondo)
    "forest_dark": {
        "bg":           "#0D1F0D",
        "bg2":          "#142614",
        "card":         "#182E18",
        "card2":        "#1E3A1E",
        "border":       "#264726",
        "border2":      "#2E5C2E",
        "text":         "#D4EDDA",
        "text2":        "#A9D6B5",
        "muted":        "#5A8A65",
        "accent":       "#52D68A",
        "accent_light": "#0A2A14",
        "accent2":      "#A3E635",
        "success":      "#52D68A",
        "warn":         "#FBBF24",
        "err":          "#F87171",
        "shadow":       "0 2px 8px rgba(0,0,0,.5)",
        "shadow_md":    "0 6px 22px rgba(0,0,0,.65)",
        "input_bg":     "#1A301A",
        "hover":        "#254025",
        "hint_bg":      "#0A2A14",
        "hint_text":    "#52D68A",
        "hint_border":  "#1A5C2A",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #060F06 0%, #040B04 100%)",
        "sidebar_border": "#142614",
        "sidebar_accent": "#52D68A",
    },

    # 11. DRACULA / PURPLE (scuro, viola ispirato a Dracula theme)
    "dracula": {
        "bg":           "#1E1A2E",
        "bg2":          "#282A36",
        "card":         "#282A36",
        "card2":        "#323443",
        "border":       "#44475A",
        "border2":      "#6272A4",
        "text":         "#F8F8F2",
        "text2":        "#CFCFE8",
        "muted":        "#6272A4",
        "accent":       "#BD93F9",
        "accent_light": "#261A3E",
        "accent2":      "#FF79C6",
        "success":      "#50FA7B",
        "warn":         "#FFB86C",
        "err":          "#FF5555",
        "shadow":       "0 2px 8px rgba(0,0,0,.5)",
        "shadow_md":    "0 6px 22px rgba(0,0,0,.65)",
        "input_bg":     "#323443",
        "hover":        "#44475A",
        "hint_bg":      "#261A3E",
        "hint_text":    "#BD93F9",
        "hint_border":  "#6272A4",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #120F1E 0%, #0E0B18 100%)",
        "sidebar_border": "#282A36",
        "sidebar_accent": "#BD93F9",
    },

    # 12. AMOLED BLACK (scuro, massimo risparmio batteria OLED)
    "amoled": {
        "bg":           "#000000",
        "bg2":          "#0A0A0A",
        "card":         "#111111",
        "card2":        "#181818",
        "border":       "#222222",
        "border2":      "#333333",
        "text":         "#FFFFFF",
        "text2":        "#E0E0E0",
        "muted":        "#666666",
        "accent":       "#00E5FF",
        "accent_light": "#001820",
        "accent2":      "#00BFA5",
        "success":      "#00E676",
        "warn":         "#FFD600",
        "err":          "#FF1744",
        "shadow":       "0 2px 6px rgba(0,0,0,.9)",
        "shadow_md":    "0 6px 24px rgba(0,0,0,.95)",
        "input_bg":     "#181818",
        "hover":        "#222222",
        "hint_bg":      "#001820",
        "hint_text":    "#00E5FF",
        "hint_border":  "#005566",
        # Sidebar
        "sidebar_bg":     "linear-gradient(180deg, #000000 0%, #050505 100%)",
        "sidebar_border": "#1A1A1A",
        "sidebar_accent": "#00E5FF",
    },
}

# Nomi leggibili per il menu a tendina ─────────────────────────────────────────
# Formato: "emoji Etichetta" — emoji aiuta a distinguere visivamente
THEME_LABELS = {
    # Chiari
    "chiaro":       "☀️  Arctic Blue",
    "minimal_gray": "🪨  Minimal Gray",
    "soft_blue":    "🫐  Soft Blue",
    "sage_garden":  "🌿  Sage Garden",
    "sandy_earth":  "🏜️  Sandy Earth",
    "high_contrast":"⬛  High Contrast",
    # Scuri
    "scuro":        "🌙  Midnight Blue",
    "deep_midnight":"🌊  Deep Midnight",
    "slate_carbon": "🩶  Slate Carbon",
    "forest_dark":  "🌲  Forest Dark",
    "dracula":      "🧛  Dracula Purple",
    "amoled":       "⚫  Amoled Black",
}

# Tema predefinito all'avvio ───────────────────────────────────────────────────
DEFAULT_THEME = "chiaro"

# ── SCUOLE E CALIBRAZIONE ──────────────────────────────────────────────────────
SCUOLE = [
    "Generico",
    "Scuola Primaria (Elementari)",
    "Scuola Secondaria I grado (Medie)",
    "Liceo Scientifico",
    "Liceo Classico",
    "Liceo Linguistico",
    "Liceo delle Scienze Umane",
    "Liceo Artistico",
    "Istituto Tecnico Tecnologico/Industriale",
    "Istituto Tecnico Economico",
    "Istituto Tecnico Agrario/Ambientale",
    "Istituto Professionale",
]

CALIBRAZIONE_SCUOLA = {
    "Generico": (
        "Livello NON specificato: adatta autonomamente difficoltà, registro linguistico e complessità, "
        "se non specificato consulta indicazioni nazionali e cerca di capire l'argomento indicato quando "
        "viene trattato nella scuola italiana per capire il contesto. "
        "in base all'argomento e alle istruzioni del docente. "
        "Se l'argomento suggerisce un livello (es. 'derivate' → superiori, 'addizioni' → primaria), "
        "calibra di conseguenza. "
        "Usa un linguaggio chiaro, diretto e professionale. Nessun vincolo di scuola."
    ),
    "Scuola Primaria (Elementari)": (
        "Target: 6-11 anni. Linguaggio ludico-concreto. "
        "Contesto: vita quotidiana familiare, gioco, spesa. "
        "Usa frasi brevi e numeri entro il 1000. Evita simboli astratti, preferisci il testo narrativo."
    ),
    "Scuola Secondaria I grado (Medie)": (
        "Target: 11-14 anni. Linguaggio in transizione verso il tecnico. "
        "Contesto: scuola, sport, socialità, prime esplorazioni scientifiche. "
        "Difficoltà bilanciata: calcolo procedurale e primi problemi logici con frazioni e variabili."
    ),
    "Liceo Scientifico": (
        "Target: 14-19 anni. Linguaggio rigoroso e accademico. "
        "Contesto: ricerca scientifica, astrazione pura, modellizzazione complessa. "
        "Livello elevato: stimola il ragionamento deduttivo e la giustificazione dei passaggi."
    ),
    "Liceo Classico": (
        "Target: 14-19 anni. Linguaggio formale ma DIRETTO e CHIARO. "
        "Contesto: storia, letteratura, filosofia, lingue classiche. "
        "IMPORTANTE: registro colto ma non aulico. Frasi dirette, domande nette. "
        "La profondità sta nel contenuto, NON nel lessico. Evita perifrasi, paroloni rari e fronzoli retorici. "
        "Una domanda ben posta vale più di tre righe di introduzione filosofica."
    ),
    "Liceo Linguistico": (
        "Target: 14-19 anni. Linguaggio chiaro e internazionale. "
        "Contesto: lingue straniere, cultura, comunicazione, letteratura comparata. "
        "Stile neutro e diretto. Privilegia la chiarezza espositiva. "
        "Evita tecnicismi inutili e riferimenti troppo specialistici."
    ),
    "Liceo delle Scienze Umane": (
        "Target: 14-19 anni. Linguaggio accessibile con riferimenti alle scienze sociali. "
        "Contesto: psicologia, sociologia, pedagogia, antropologia. "
        "Stile semplice e concreto, con esempi pratici tratti dalla realtà quotidiana. "
        "Evita gergo accademico pesante."
    ),
    "Liceo Artistico": (
        "Target: 14-19 anni. Linguaggio descrittivo e visivo. "
        "Contesto: storia dell'arte, teoria, tecniche artistiche, progettazione. "
        "Stile diretto e pratico. Privilegia domande operative e descrittive. "
        "Evita astrattismi: chiedi di osservare, descrivere, confrontare opere concrete."
    ),
    "Istituto Tecnico Tecnologico/Industriale": (
        "Target: 14-19 anni. Linguaggio tecnico-professionale. "
        "Contesto: laboratorio, tecnologia, elettronica, meccanica, informatica applicata. "
        "Enfasi su applicazione pratica, dati reali, scenari lavorativi concreti. "
        "Esercizi con misure, tolleranze, schemi, calcoli ingegneristici di base."
    ),
    "Istituto Tecnico Economico": (
        "Target: 14-19 anni. Linguaggio economico-aziendale. "
        "Contesto: azienda, contabilità, economia, diritto commerciale, marketing. "
        "Privilegia casi aziendali reali, calcoli su bilanci, problemi di gestione. "
        "Stile professionale ma accessibile."
    ),
    "Istituto Tecnico Agrario/Ambientale": (
        "Target: 14-19 anni. Linguaggio tecnico-naturalistico. "
        "Contesto: agricoltura, ambiente, biologia applicata, chimica agraria, territorio. "
        "Privilegia esempi concreti legati a colture, ecosistemi, analisi del suolo, sostenibilità. "
        "Stile pratico e operativo."
    ),
    "Istituto Professionale": (
        "Target: 14-19 anni. Linguaggio pratico e operativo. "
        "Contesto: situazioni lavorative simulate, compiti di realtà, problem solving guidato. "
        "Suddividi i problemi complessi in step chiari ed espliciti. "
        "Domande brevi, dirette, con un unico obiettivo per volta."
    ),
}

# ── MATERIE ────────────────────────────────────────────────────────────────────
MATERIE = [
    "Matematica", "Fisica", "Chimica", "Biologia", "Scienze della Terra",
    "Italiano", "Storia", "Geografia", "Latino", "Greco",
    "Inglese", "Francese", "Spagnolo", "Tedesco",
    "Filosofia", "Storia dell'Arte", "Musica",
    "Informatica", "Economia", "Diritto",
    "Educazione Civica", "Scienze Motorie",
]

NOTE_PLACEHOLDER = {
    "Matematica":          "es. Includi un esercizio sul teorema di Pitagora e due problemi algebrici.",
    "Fisica":              "es. Un esercizio sulla seconda legge di Newton, uno sul moto uniformemente accelerato.",
    "Chimica":             "es. Bilanciamento di reazioni ed esercizi sulla mole.",
    "Biologia":            "es. Struttura della cellula e ciclo cellulare. Privilegia la comprensione.",
    "Scienze della Terra": "es. Tettonica a placche e ciclo delle rocce. Schema da completare.",
    "Italiano":            "es. Analisi del testo narrativo, figure retoriche. Testo di circa 15 righe.",
    "Storia":              "es. Prima Guerra Mondiale: cause, fasi, conseguenze. Includi una fonte.",
    "Geografia":           "es. Climi e biomi. Una domanda su cartina muta e una su dati demografici.",
    "Latino":              "es. Versione dal De Bello Gallico (40-50 parole). Declinazioni I e II.",
    "Greco":               "es. Versione da Lisia (30-40 parole). Presente e imperfetto attivo.",
    "Inglese":             "es. Reading comprehension (150 parole), present perfect, short writing task.",
    "Francese":            "es. Compréhension écrite, passé composé, production écrite guidée.",
    "Spagnolo":            "es. Comprensión lectora, pretérito indefinido vs imperfecto, escritura breve.",
    "Tedesco":             "es. Leseverstehen, Perfekt und Präteritum, kurze Schreibaufgabe.",
    "Filosofia":           "es. Problema mente-corpo in Cartesio vs Spinoza. Una domanda aperta e una di definizione.",
    "Storia dell'Arte":    "es. Impressionismo: tecnica e confronto Monet/Renoir. Analisi di un'opera.",
    "Musica":              "es. Sonata classica e confronto Mozart/Beethoven. Domande di teoria.",
    "Informatica":         "es. Bubble sort e selection sort. Pseudocodice e complessità computazionale.",
    "Economia":            "es. Domanda e offerta, elasticità dei prezzi. Un esercizio numerico.",
    "Diritto":             "es. Fonti del diritto e gerarchia normativa. Un caso pratico.",
    "Educazione Civica":   "es. Struttura della Costituzione italiana. Diritti e doveri dei cittadini.",
    "Scienze Motorie":     "es. Apparato muscolare e scheletrico. Norme di sicurezza in palestra.",
}

# ── TIPI ESERCIZIO ─────────────────────────────────────────────────────────────
TIPI_ESERCIZIO = ["Aperto", "Scelta multipla", "Vero/Falso", "Completamento"]
