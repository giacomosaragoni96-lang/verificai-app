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
# Chiavi obbligatorie per ogni tema:
#   bg, bg2, card, card2, border, border2
#   text, text2, muted
#   accent, accent_light, accent2
#   success, warn, err
#   shadow, shadow_md, input_bg, hover
#   hint_bg, hint_text, hint_border
#   sidebar_bg      → gradient CSS del pannello sidebar
#   sidebar_border  → bordo destro sidebar
#   sidebar_accent  → accent per label/hover sidebar
# ───────────────────────────────────────────────────────────────────────────────

THEMES = {

    # ══════════════════════════════════════════════════════════════════════════
    # ── TEMI CHIARI  (11: 1 storico + 10 nuovi)
    # ══════════════════════════════════════════════════════════════════════════

    # 1. ARCTIC BLUE — predefinito storico
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
        "sidebar_bg":     "linear-gradient(180deg, #0D2235 0%, #091A28 100%)",
        "sidebar_border": "#1A3A52",
        "sidebar_accent": "#D97706",
    },

    # 2. IVORY SCHOLAR — carta da biblioteca, accent verde smeraldo
    "ivory_scholar": {
        "bg":           "#F9F6EF",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#F4F0E6",
        "border":       "#E2D9C8",
        "border2":      "#C8BA9A",
        "text":         "#2A1F0E",
        "text2":        "#4A3B26",
        "muted":        "#7A6B52",
        "accent":       "#1B6B4A",
        "accent_light": "#D8F0E6",
        "accent2":      "#2E9E6F",
        "success":      "#1B6B4A",
        "warn":         "#A0530A",
        "err":          "#B91C1C",
        "shadow":       "0 1px 3px rgba(42,31,14,.08)",
        "shadow_md":    "0 4px 14px rgba(27,107,74,.12)",
        "input_bg":     "#F5F1E8",
        "hover":        "#E8F5EE",
        "hint_bg":      "#D8F0E6",
        "hint_text":    "#0F4A30",
        "hint_border":  "#2E9E6F",
        "sidebar_bg":     "linear-gradient(180deg, #0F2018 0%, #0A180F 100%)",
        "sidebar_border": "#1B3D28",
        "sidebar_accent": "#2E9E6F",
    },

    # 3. ROSE CHALK — bianco gessoso con accent rosa antico
    "rose_chalk": {
        "bg":           "#FDF6F6",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FEF0F0",
        "border":       "#F5D5D5",
        "border2":      "#E8AAAA",
        "text":         "#3A1515",
        "text2":        "#6B2E2E",
        "muted":        "#A06060",
        "accent":       "#C0392B",
        "accent_light": "#FDECEA",
        "accent2":      "#E74C3C",
        "success":      "#1A7A4A",
        "warn":         "#C47A00",
        "err":          "#C0392B",
        "shadow":       "0 1px 3px rgba(192,57,43,.08)",
        "shadow_md":    "0 4px 14px rgba(192,57,43,.12)",
        "input_bg":     "#FEF8F8",
        "hover":        "#FDECEA",
        "hint_bg":      "#FDECEA",
        "hint_text":    "#7B1010",
        "hint_border":  "#E8AAAA",
        "sidebar_bg":     "linear-gradient(180deg, #1A0808 0%, #130606 100%)",
        "sidebar_border": "#3A1515",
        "sidebar_accent": "#E74C3C",
    },

    # 4. OCEAN MIST — nebbia marina, accent teal vibrante
    "ocean_mist": {
        "bg":           "#EEF6F8",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#E8F4F7",
        "border":       "#B8DCE5",
        "border2":      "#7EC8D8",
        "text":         "#0D2E36",
        "text2":        "#1D5464",
        "muted":        "#4A8A98",
        "accent":       "#0891B2",
        "accent_light": "#CFFAFE",
        "accent2":      "#06B6D4",
        "success":      "#0D7A50",
        "warn":         "#B45309",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(8,145,178,.08)",
        "shadow_md":    "0 4px 14px rgba(8,145,178,.14)",
        "input_bg":     "#F0F9FB",
        "hover":        "#CFFAFE",
        "hint_bg":      "#CFFAFE",
        "hint_text":    "#0C4A58",
        "hint_border":  "#7EC8D8",
        "sidebar_bg":     "linear-gradient(180deg, #071820 0%, #051218 100%)",
        "sidebar_border": "#0D2E36",
        "sidebar_accent": "#06B6D4",
    },

    # 5. LAVENDER DESK — postazione studio lilla, accent viola profondo
    "lavender_desk": {
        "bg":           "#F3F0FB",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#EDE8FA",
        "border":       "#D4C8F5",
        "border2":      "#B09EE8",
        "text":         "#1E1040",
        "text2":        "#3D2A7A",
        "muted":        "#7060AA",
        "accent":       "#6D28D9",
        "accent_light": "#EDE9FE",
        "accent2":      "#8B5CF6",
        "success":      "#059669",
        "warn":         "#B45309",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(109,40,217,.08)",
        "shadow_md":    "0 4px 14px rgba(109,40,217,.14)",
        "input_bg":     "#F7F4FE",
        "hover":        "#EDE9FE",
        "hint_bg":      "#EDE9FE",
        "hint_text":    "#3B0764",
        "hint_border":  "#B09EE8",
        "sidebar_bg":     "linear-gradient(180deg, #0E0820 0%, #0A0618 100%)",
        "sidebar_border": "#1E1040",
        "sidebar_accent": "#8B5CF6",
    },

    # 6. MINT FRESH — menta ghiacciata su bianco, accent verde brillante
    "mint_fresh": {
        "bg":           "#F0FDF8",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#E6FAF4",
        "border":       "#BBEDD8",
        "border2":      "#6EE7B7",
        "text":         "#022C22",
        "text2":        "#064E3B",
        "muted":        "#34926A",
        "accent":       "#059669",
        "accent_light": "#D1FAE5",
        "accent2":      "#10B981",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(5,150,105,.08)",
        "shadow_md":    "0 4px 14px rgba(5,150,105,.14)",
        "input_bg":     "#F0FDF8",
        "hover":        "#D1FAE5",
        "hint_bg":      "#D1FAE5",
        "hint_text":    "#014737",
        "hint_border":  "#6EE7B7",
        "sidebar_bg":     "linear-gradient(180deg, #011A12 0%, #010E0A 100%)",
        "sidebar_border": "#022C22",
        "sidebar_accent": "#10B981",
    },

    # 7. GOLDEN HOUR — tramonto ambrato, accent arancio caldo
    "golden_hour": {
        "bg":           "#FFFBF0",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FFF4D6",
        "border":       "#F5DFA0",
        "border2":      "#F0C040",
        "text":         "#2A1800",
        "text2":        "#5A3A00",
        "muted":        "#9A6A20",
        "accent":       "#D97706",
        "accent_light": "#FEF3C7",
        "accent2":      "#F59E0B",
        "success":      "#15803D",
        "warn":         "#92400E",
        "err":          "#B91C1C",
        "shadow":       "0 1px 3px rgba(217,119,6,.10)",
        "shadow_md":    "0 4px 14px rgba(217,119,6,.18)",
        "input_bg":     "#FFFCF0",
        "hover":        "#FEF3C7",
        "hint_bg":      "#FEF3C7",
        "hint_text":    "#451A00",
        "hint_border":  "#F0C040",
        "sidebar_bg":     "linear-gradient(180deg, #1A0E00 0%, #120A00 100%)",
        "sidebar_border": "#3A2200",
        "sidebar_accent": "#F59E0B",
    },

    # 8. PAPER WHITE — minimalismo assoluto, accent blu inchiostro
    "paper_white": {
        "bg":           "#FAFAFA",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#F5F5F5",
        "border":       "#E8E8E8",
        "border2":      "#D0D0D0",
        "text":         "#111111",
        "text2":        "#333333",
        "muted":        "#888888",
        "accent":       "#1A56DB",
        "accent_light": "#EBF2FF",
        "accent2":      "#2563EB",
        "success":      "#0A6640",
        "warn":         "#9A3A00",
        "err":          "#B91C1C",
        "shadow":       "0 1px 2px rgba(0,0,0,.06)",
        "shadow_md":    "0 4px 12px rgba(26,86,219,.10)",
        "input_bg":     "#FFFFFF",
        "hover":        "#EBF2FF",
        "hint_bg":      "#EBF2FF",
        "hint_text":    "#1A3A8A",
        "hint_border":  "#93C5FD",
        "sidebar_bg":     "linear-gradient(180deg, #0A0A0A 0%, #050505 100%)",
        "sidebar_border": "#1A1A1A",
        "sidebar_accent": "#2563EB",
    },

    # 9. TERRACOTTA STUDIO — cotto toscano e lino, accent arancio bruciato
    "terracotta_studio": {
        "bg":           "#FAF2EC",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#F5E8DE",
        "border":       "#E8C9B0",
        "border2":      "#D4956A",
        "text":         "#2C1008",
        "text2":        "#5A2E14",
        "muted":        "#9A6040",
        "accent":       "#C05A20",
        "accent_light": "#FDEEE4",
        "accent2":      "#E07040",
        "success":      "#2D6A4F",
        "warn":         "#92400E",
        "err":          "#B91C1C",
        "shadow":       "0 1px 3px rgba(192,90,32,.09)",
        "shadow_md":    "0 4px 14px rgba(192,90,32,.14)",
        "input_bg":     "#FDF6F0",
        "hover":        "#FDEEE4",
        "hint_bg":      "#FDEEE4",
        "hint_text":    "#6B1E04",
        "hint_border":  "#D4956A",
        "sidebar_bg":     "linear-gradient(180deg, #180A04 0%, #110602 100%)",
        "sidebar_border": "#3A1A08",
        "sidebar_accent": "#E07040",
    },

    # 10. NORDIC PINE — legno chiaro e azzurro fiordo, accent acciaio
    "nordic_pine": {
        "bg":           "#F2F6F8",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#E8F0F4",
        "border":       "#C4D8E2",
        "border2":      "#8DBCCF",
        "text":         "#0E2030",
        "text2":        "#1E4060",
        "muted":        "#4A6E84",
        "accent":       "#2D7D9A",
        "accent_light": "#D8EEF5",
        "accent2":      "#3A9EC0",
        "success":      "#2D6A4F",
        "warn":         "#B45309",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(45,125,154,.08)",
        "shadow_md":    "0 4px 14px rgba(45,125,154,.14)",
        "input_bg":     "#EEF5F8",
        "hover":        "#D8EEF5",
        "hint_bg":      "#D8EEF5",
        "hint_text":    "#0E3048",
        "hint_border":  "#8DBCCF",
        "sidebar_bg":     "linear-gradient(180deg, #071520 0%, #040E16 100%)",
        "sidebar_border": "#0E2030",
        "sidebar_accent": "#3A9EC0",
    },

    # 11. CHERRY BLOSSOM — petali di ciliegio, accent carminio
    "cherry_blossom": {
        "bg":           "#FDF2F6",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FAE8F0",
        "border":       "#F0C4D8",
        "border2":      "#E090B4",
        "text":         "#2A0A1A",
        "text2":        "#5A1E3A",
        "muted":        "#9A5070",
        "accent":       "#B5295A",
        "accent_light": "#FCE4EE",
        "accent2":      "#D94479",
        "success":      "#1A7A4A",
        "warn":         "#A0530A",
        "err":          "#B91C1C",
        "shadow":       "0 1px 3px rgba(181,41,90,.08)",
        "shadow_md":    "0 4px 14px rgba(181,41,90,.13)",
        "input_bg":     "#FEF5F8",
        "hover":        "#FCE4EE",
        "hint_bg":      "#FCE4EE",
        "hint_text":    "#6B0A2A",
        "hint_border":  "#E090B4",
        "sidebar_bg":     "linear-gradient(180deg, #180510 0%, #10030A 100%)",
        "sidebar_border": "#3A1028",
        "sidebar_accent": "#D94479",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ── TEMA SCURO UFFICIALE
    # ══════════════════════════════════════════════════════════════════════════

    # 12. SLATE CARBON — grigio carbone iOS-style, accent blu elettrico
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
        "sidebar_bg":     "linear-gradient(180deg, #101010 0%, #0A0A0A 100%)",
        "sidebar_border": "#2C2C2E",
        "sidebar_accent": "#0A84FF",
    },
}

# ── Etichette leggibili per il menu a tendina ──────────────────────────────────
THEME_LABELS = {
    # Chiari
    "chiaro":             "☀️  Arctic Blue",
    "ivory_scholar":      "📜  Ivory Scholar",
    "rose_chalk":         "🌹  Rose Chalk",
    "ocean_mist":         "🌊  Ocean Mist",
    "lavender_desk":      "💜  Lavender Desk",
    "mint_fresh":         "🌿  Mint Fresh",
    "golden_hour":        "🌅  Golden Hour",
    "paper_white":        "📄  Paper White",
    "terracotta_studio":  "🏺  Terracotta Studio",
    "nordic_pine":        "🌲  Nordic Pine",
    "cherry_blossom":     "🌸  Cherry Blossom",
    # Scuro
    "slate_carbon":       "🩶  Slate Carbon",
}

# Tema predefinito all'avvio
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
