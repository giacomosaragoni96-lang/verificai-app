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

# ── TEMI UI — 10 temi ──────────────────────────────────────────────────────────
# Ogni tema espone le stesse chiavi. La sidebar usa THEME_LABELS per il menu.
THEMES = {
    # 1. Original Dark — Midnight Blue con accenti Ambra
    "midnight_blue": {
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
        "accent_light": "#292215",
        "accent2":      "#10B981",
        "success":      "#10B981",
        "warn":         "#F59E0B",
        "err":          "#EF4444",
        "shadow":       "0 1px 3px rgba(0,0,0,.4)",
        "shadow_md":    "0 4px 20px rgba(0,0,0,.5)",
        "input_bg":     "#253047",
        "hover":        "#2D3F5C",
    },
    # 2. Pure Black — nero assoluto ad alto contrasto
    "pure_black": {
        "bg":           "#000000",
        "bg2":          "#0A0A0A",
        "card":         "#111111",
        "card2":        "#1A1A1A",
        "border":       "#222222",
        "border2":      "#2E2E2E",
        "text":         "#FFFFFF",
        "text2":        "#E0E0E0",
        "muted":        "#666666",
        "accent":       "#FF9500",
        "accent_light": "#1A1100",
        "accent2":      "#00D4AA",
        "success":      "#00D4AA",
        "warn":         "#FF9500",
        "err":          "#FF3B30",
        "shadow":       "0 1px 3px rgba(0,0,0,.6)",
        "shadow_md":    "0 4px 20px rgba(0,0,0,.7)",
        "input_bg":     "#1A1A1A",
        "hover":        "#222222",
    },
    # 3. Emerald Forest — verde notte con accenti smeraldo
    "emerald_forest": {
        "bg":           "#0A1A12",
        "bg2":          "#112218",
        "card":         "#112218",
        "card2":        "#172D20",
        "border":       "#1E3D2A",
        "border2":      "#275238",
        "text":         "#E8F5EE",
        "text2":        "#A7D4B8",
        "muted":        "#527A62",
        "accent":       "#10B981",
        "accent_light": "#0A2018",
        "accent2":      "#34D399",
        "success":      "#34D399",
        "warn":         "#F59E0B",
        "err":          "#EF4444",
        "shadow":       "0 1px 3px rgba(0,0,0,.4)",
        "shadow_md":    "0 4px 20px rgba(0,0,0,.5)",
        "input_bg":     "#172D20",
        "hover":        "#1E3D2A",
    },
    # 4. Nordic Light — light mode professionale con accenti blu
    "nordic_light": {
        "bg":           "#F0F4F8",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#E8EDF3",
        "border":       "#D1D9E3",
        "border2":      "#B8C4D0",
        "text":         "#1A2332",
        "text2":        "#3D5166",
        "muted":        "#7A8FA6",
        "accent":       "#2563EB",
        "accent_light": "#EBF2FF",
        "accent2":      "#0EA5E9",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(0,0,0,.07), 0 1px 2px rgba(0,0,0,.04)",
        "shadow_md":    "0 4px 12px rgba(0,0,0,.09)",
        "input_bg":     "#FFFFFF",
        "hover":        "#E8EDF3",
    },
    # 5. Deep Purple — sfondo melanzana con accenti lilla
    "deep_purple": {
        "bg":           "#12091E",
        "bg2":          "#1C1030",
        "card":         "#1C1030",
        "card2":        "#241640",
        "border":       "#2E1E52",
        "border2":      "#3D2868",
        "text":         "#F0EBFF",
        "text2":        "#C4B0E8",
        "muted":        "#6B5A8A",
        "accent":       "#A78BFA",
        "accent_light": "#1A0F30",
        "accent2":      "#E879F9",
        "success":      "#34D399",
        "warn":         "#F59E0B",
        "err":          "#F87171",
        "shadow":       "0 1px 3px rgba(0,0,0,.4)",
        "shadow_md":    "0 4px 20px rgba(0,0,0,.5)",
        "input_bg":     "#241640",
        "hover":        "#2E1E52",
    },
    # 6. Cyberpunk — neon verde/giallo su nero profondo
    "cyberpunk": {
        "bg":           "#050505",
        "bg2":          "#0D0D0D",
        "card":         "#111111",
        "card2":        "#181818",
        "border":       "#1C2E1C",
        "border2":      "#243824",
        "text":         "#E8FFE8",
        "text2":        "#8FBF8F",
        "muted":        "#4A7A4A",
        "accent":       "#00FF41",
        "accent_light": "#001A00",
        "accent2":      "#FFE600",
        "success":      "#00FF41",
        "warn":         "#FFE600",
        "err":          "#FF0055",
        "shadow":       "0 1px 3px rgba(0,255,65,.08)",
        "shadow_md":    "0 4px 20px rgba(0,255,65,.12)",
        "input_bg":     "#181818",
        "hover":        "#1C2E1C",
    },
    # 7. Arctic — ghiaccio e bianco polare con accenti azzurro
    "arctic": {
        "bg":           "#EAF3FB",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#DFF0FA",
        "border":       "#BFD9EE",
        "border2":      "#A0C4E2",
        "text":         "#0D2B45",
        "text2":        "#2C5F82",
        "muted":        "#6B9AB8",
        "accent":       "#0284C7",
        "accent_light": "#E0F2FE",
        "accent2":      "#06B6D4",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(0,0,0,.06)",
        "shadow_md":    "0 4px 12px rgba(2,132,199,.10)",
        "input_bg":     "#FFFFFF",
        "hover":        "#DFF0FA",
    },
    # 8. Earth Tones — terracotta e sabbia con accenti ocra
    "earth_tones": {
        "bg":           "#1A1208",
        "bg2":          "#251A0C",
        "card":         "#251A0C",
        "card2":        "#302212",
        "border":       "#40300F",
        "border2":      "#543E16",
        "text":         "#F5EDD8",
        "text2":        "#D4BB8A",
        "muted":        "#7A6340",
        "accent":       "#D97706",
        "accent_light": "#2A1C06",
        "accent2":      "#B45309",
        "success":      "#65A30D",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(0,0,0,.4)",
        "shadow_md":    "0 4px 20px rgba(0,0,0,.5)",
        "input_bg":     "#302212",
        "hover":        "#40300F",
    },
    # 9. Sunset — tramonto con accenti corallo/rosa
    "sunset": {
        "bg":           "#1A0A12",
        "bg2":          "#27111C",
        "card":         "#27111C",
        "card2":        "#341826",
        "border":       "#4A2038",
        "border2":      "#622A4C",
        "text":         "#FFE8F0",
        "text2":        "#F4A8C8",
        "muted":        "#8A4E68",
        "accent":       "#F43F5E",
        "accent_light": "#2A0A14",
        "accent2":      "#FB923C",
        "success":      "#34D399",
        "warn":         "#FB923C",
        "err":          "#F43F5E",
        "shadow":       "0 1px 3px rgba(0,0,0,.4)",
        "shadow_md":    "0 4px 20px rgba(244,63,94,.15)",
        "input_bg":     "#341826",
        "hover":        "#4A2038",
    },
    # 10. Slate — grigio ardesia professionale con accenti indaco
    "slate": {
        "bg":           "#0F1117",
        "bg2":          "#1A1E2A",
        "card":         "#1A1E2A",
        "card2":        "#222738",
        "border":       "#2E3347",
        "border2":      "#3C4258",
        "text":         "#E2E6F0",
        "text2":        "#A8B0C8",
        "muted":        "#5A6280",
        "accent":       "#6366F1",
        "accent_light": "#141530",
        "accent2":      "#818CF8",
        "success":      "#34D399",
        "warn":         "#F59E0B",
        "err":          "#F87171",
        "shadow":       "0 1px 3px rgba(0,0,0,.4)",
        "shadow_md":    "0 4px 20px rgba(0,0,0,.5)",
        "input_bg":     "#222738",
        "hover":        "#2E3347",
    },
}

# Nomi leggibili per il menu a tendina
THEME_LABELS = {
    "midnight_blue":  "🌌 Midnight Blue (Default)",
    "pure_black":     "⚫ Pure Black",
    "emerald_forest": "🌿 Emerald Forest",
    "nordic_light":   "☀️ Nordic Light",
    "deep_purple":    "🔮 Deep Purple",
    "cyberpunk":      "💚 Cyberpunk",
    "arctic":         "🧊 Arctic",
    "earth_tones":    "🌍 Earth Tones",
    "sunset":         "🌅 Sunset",
    "slate":          "🪨 Slate",
}

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
