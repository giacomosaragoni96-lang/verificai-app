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
    "⚡ Flash 2.5 Lite (veloce · Free)": {
        "id":    "gemini-2.5-flash-lite",
        "piano": "free",
    },
    "⚡ Flash 2.5 (bilanciato · Pro)": {
        "id":    "gemini-2.5-flash",
        "piano": "pro",
    },
    "🧠 Pro 2.5 (STEM/Gold)": {
        "id":    "gemini-2.5-pro",
        "piano": "gold",
    },
}

MODEL_FAST_ID = "gemini-2.5-flash-lite"

MATERIE_STEM = {
    "Matematica", "Fisica", "Chimica", "Informatica",
    "Scienze della Terra", "Biologia",
}

def get_model_id_per_piano(piano: str, materia: str = "") -> str:
    is_stem = materia in MATERIE_STEM
    if piano == "gold" or (piano == "admin" and is_stem):
        return MODELLI_DISPONIBILI["🧠 Pro 2.5 (STEM/Gold)"]["id"]
    if piano in ("pro", "admin"):
        return MODELLI_DISPONIBILI["⚡ Flash 2.5 (bilanciato · Pro)"]["id"]
    return MODEL_FAST_ID

# ── TEMA UI ─────────────────────────────────────────────────────────────────────
# Tema unico: Notte (Dark Midnight Blue).
# ───────────────────────────────────────────────────────────────────────────────

THEMES = {
    # ═══════════════════════════════════════════════════════════════════════
    #  NOTTE — Dark Midnight Blue  (default)
    # ═══════════════════════════════════════════════════════════════════════
    "notte": {
        # Superfici
        "bg":         "#0D1117",
        "bg2":        "#161B22",
        "card":       "#1C2128",
        "card2":      "#21262D",

        # Testo
        "text":       "#E6EDF3",
        "text2":      "#8B949E",
        "muted":      "#6E7681",

        # Bordi
        "border":     "#30363D",
        "border2":    "#3D444D",

        # Accent — Blu elettrico
        "accent":       "#58A6FF",
        "accent2":      "#79C0FF",
        "accent_light": "#0D2340",

        # Interazione
        "hover":      "#1F2937",

        # Semantici
        "success":    "#3FB950",
        "warn":       "#D29922",
        "error":      "#F85149",

        # Ombre
        "shadow":     "0 1px 3px rgba(0,0,0,.35)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.50)",
        "shadow_soft": "0 8px 32px rgba(0,0,0,.25), 0 2px 8px rgba(0,0,0,.15)",

        # Design system (Minimal SaaS)
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar
        "sidebar_bg":      "linear-gradient(180deg, #010409 0%, #0D1117 100%)",
        "sidebar_border":  "#21262D",
        "sidebar_accent":  "#79C0FF",
        "sidebar_input_bg":  "#0D1117",
        "sidebar_input_text": "#E6EDF3",

        # Hint boxes
        "hint_bg":      "#0D2340",
        "hint_border":  "#1F4070",
        "hint_text":    "#79C0FF",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CHIARO (Giorno) — Elegant light: cream, warm gray, teal accent
    #  Palette: Cream #FAF9F7, Warm Gray, Teal #0D9488, Slate sidebar
    # ═══════════════════════════════════════════════════════════════════════
    "chiaro": {
        # Superfici — cream e bianco caldo, nessun grigio freddo
        "bg":         "#F5F4F0",     # Warm cream — base elegante
        "bg2":        "#EBE9E4",     # secondo livello
        "card":       "#FFFFFF",     # card bianca pura
        "card2":      "#FAFAF9",     # overlay leggermente caldo

        # Testo — charcoal caldo, massima leggibilità
        "text":       "#1C1917",     # Warm black
        "text2":      "#44403C",     # secondario
        "muted":      "#78716C",     # stone muted

        # Bordi — sottili, caldi
        "border":     "#E7E5E4",     # stone 200
        "border2":    "#D6D3D1",     # stone 300

        # Accent — Teal elegante (non verde piatto)
        "accent":       "#0D9488",   # Teal 600
        "accent2":      "#0F766E",   # Teal 700 (hover)
        "accent_light": "#CCFBF1",   # Teal 100 — pill/hint

        # Interazione
        "hover":      "#F0FDFA",     # Teal 50

        # Semantici
        "success":    "#059669",     # Emerald 600
        "warn":       "#D97706",     # Amber 600
        "error":      "#DC2626",     # Red 600

        # Ombre — morbide, eleganti
        "shadow":     "0 1px 2px rgba(28,25,23,.06)",
        "shadow_md":  "0 4px 20px rgba(28,25,23,.08), 0 1px 3px rgba(28,25,23,.04)",
        "shadow_soft": "0 12px 40px rgba(28,25,23,.06), 0 2px 8px rgba(28,25,23,.03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — slate scuro elegante, accent teal
        "sidebar_bg":      "linear-gradient(180deg, #1E293B 0%, #0F172A 100%)",
        "sidebar_border":  "#334155",
        "sidebar_accent":  "#2DD4BF",   # Teal 400
        "sidebar_input_bg":  "#1E293B",
        "sidebar_input_text": "#E2E8F0",

        # Hint boxes
        "hint_bg":      "#CCFBF1",
        "hint_border":  "#5EEAD4",
        "hint_text":    "#0F766E",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  FORESTA — Elegant paper/sage: calm, study, nature, professional
    #  Palette: Paper #F5F7F4, Sage #E8EDE4, Forest #166534, Deep green sidebar
    # ═══════════════════════════════════════════════════════════════════════
    "foresta": {
        # Superfici — carta e sage chiarissimo, non cielo azzurro
        "bg":         "#F2F5F0",     # Paper — verde-grigio molto chiaro
        "bg2":        "#E8EDE4",     # Sage chiaro
        "card":       "#FFFFFF",     # carta bianca
        "card2":      "#F8FAF6",     # overlay con hint verde

        # Testo — inchiostro verde scuro (forest ink)
        "text":       "#1A2E1A",     # Forest black
        "text2":      "#2D4A2D",     # secondario
        "muted":      "#527352",     # muted sage

        # Bordi — sottili, verdi neutri
        "border":     "#D1DED1",     # bordo sage
        "border2":    "#B5C9B5",     # bordo più marcato

        # Accent — Forest green elegante
        "accent":       "#166534",   # Green 800 — forest
        "accent2":      "#15803D",   # Green 700 (hover)
        "accent_light": "#DCFCE7",   # Green 100 — pill/hint

        # Interazione
        "hover":      "#ECFDF5",     # Green 50

        # Semantici
        "success":    "#15803D",     # Green 700
        "warn":       "#CA8A04",     # Yellow 700
        "error":      "#B91C1C",     # Red 700

        # Ombre — morbide, naturali
        "shadow":     "0 1px 2px rgba(22,101,52,.06)",
        "shadow_md":  "0 4px 20px rgba(22,101,52,.08), 0 1px 3px rgba(22,101,52,.04)",
        "shadow_soft": "0 12px 40px rgba(22,101,52,.06), 0 2px 8px rgba(22,101,52,.03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — forest scuro, elegante
        "sidebar_bg":      "linear-gradient(180deg, #14532D 0%, #052E16 100%)",
        "sidebar_border":  "#166534",
        "sidebar_accent":  "#86EFAC",   # Green 300
        "sidebar_input_bg":  "#14532D",
        "sidebar_input_text": "#BBF7D0",

        # Hint boxes
        "hint_bg":      "#DCFCE7",
        "hint_border":  "#86EFAC",
        "hint_text":    "#166534",
    },
}

THEME_LABELS = {
    "notte":   "🌙 Notte",
    "chiaro":  "☀️ Giorno",
    "foresta": "🌿 Foresta",
}

DEFAULT_THEME = "notte"

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
        "Scuola primaria (6–11 anni): linguaggio semplice e diretto, frasi brevi, "
        "esercizi concreti e vicini alla realtà quotidiana. "
        "Niente simbolismi astratti, formule o tecnicismi. "
        "Struttura: massimo 4-5 esercizi brevi, pochi sotto-punti."
    ),
    "Scuola Secondaria I grado (Medie)": (
        "Scuola media (11–14 anni): linguaggio chiaro e accessibile, "
        "contenuti ancorati ai programmi ministeriali. "
        "Esercizi graduati: dal semplice al complesso. "
        "Niente dimostrazioni avanzate o calcoli complessi fuori programma."
    ),
    "Liceo Scientifico": (
        "Liceo scientifico (14–19 anni): rigore scientifico e matematico, "
        "uso appropriato di notazioni formali (ℝ, ∀, ∃, etc.). "
        "Può includere dimostrazioni, problemi aperti, ragionamento deduttivo. "
        "Livello: programma MIUR liceo scientifico."
    ),
    "Liceo Classico": (
        "Liceo classico (14–19 anni): rigore umanistico e linguistico, "
        "attenzione alla proprietà di linguaggio e all'argomentazione. "
        "Per materie scientifiche: livello base-intermedio. "
        "Può includere analisi testuale, traduzioni, riflessioni critiche."
    ),
    "Liceo Linguistico": (
        "Liceo linguistico (14–19 anni): focus su competenze comunicative, "
        "analisi del testo e produzione scritta. "
        "Possibile inclusione di esercizi in L2 se materia linguistica. "
        "Livello: programma MIUR liceo linguistico."
    ),
    "Liceo delle Scienze Umane": (
        "Liceo scienze umane (14–19 anni): taglio pedagogico, sociologico, psicologico. "
        "Testo riflessivo, connessioni interdisciplinari. "
        "Evita tecnicismi matematici avanzati."
    ),
    "Liceo Artistico": (
        "Liceo artistico (14–19 anni): taglio creativo-espressivo, "
        "attenzione alla dimensione estetica e progettuale. "
        "Per materie teoriche: approccio descrittivo e contestualizzante."
    ),
    "Istituto Tecnico Tecnologico/Industriale": (
        "ITI / ITIS (14–19 anni): approccio applicativo e tecnico-pratico. "
        "Problemi reali, calcoli ingegneristici di base, schemi, dimensionamenti. "
        "Linguaggio tecnico appropriato. Livello: programma MIUR ITI."
    ),
    "Istituto Tecnico Economico": (
        "ITE / ITEC (14–19 anni): approccio economico-aziendale, "
        "analisi di dati, bilanci semplificati, casi aziendali. "
        "Linguaggio economico-giuridico appropriato."
    ),
    "Istituto Tecnico Agrario/Ambientale": (
        "ITA (14–19 anni): approccio scientifico-applicativo in ambito agrario, "
        "biologico, ambientale. Terminologia tecnica di settore."
    ),
    "Istituto Professionale": (
        "Istituto professionale (14–19 anni): approccio pratico-laboratoriale, "
        "contenuti essenziali e immediatamente applicabili. "
        "Linguaggio semplice e diretto. Evita astrazioni eccessive."
    ),
}

# ── MATERIE ────────────────────────────────────────────────────────────────────
MATERIE = [
    "Matematica", "Fisica", "Chimica", "Biologia",
    "Scienze della Terra", "Informatica",
    "Italiano", "Latino", "Greco", "Storia", "Geografia",
    "Filosofia", "Inglese", "Francese", "Spagnolo", "Tedesco",
    "Arte e Immagine", "Musica", "Educazione Fisica",
    "Economia Aziendale", "Diritto", "Tecnologia",
    "Scienze Umane", "Psicologia", "Sociologia",
    "Religione", "Altra materia",
]

MATERIE_ICONS = {
    "Matematica": "📐", "Fisica": "⚛️", "Chimica": "🧪", "Biologia": "🧬",
    "Scienze della Terra": "🌍", "Informatica": "💻",
    "Italiano": "✍️", "Latino": "🏛️", "Greco": "🏺", "Storia": "📜",
    "Geografia": "🗺️", "Filosofia": "🤔", "Inglese": "🇬🇧",
    "Francese": "🇫🇷", "Spagnolo": "🇪🇸", "Tedesco": "🇩🇪",
    "Arte e Immagine": "🎨", "Musica": "🎵", "Educazione Fisica": "⚽",
    "Economia Aziendale": "📊", "Diritto": "⚖️", "Tecnologia": "🔧",
    "Scienze Umane": "🧠", "Psicologia": "💭", "Sociologia": "👥",
    "Religione": "✝️", "Altra materia": "📚",
}

NOTE_PLACEHOLDER = (
    "Es: includi una domanda sulla derivata di sen(x), "
    "aggiungi un grafico con pgfplots, "
    "inserisci almeno 2 esercizi Vero/Falso..."
)

TIPI_ESERCIZIO = [
    "Misto (consigliato)",
    "Solo Vero/Falso",
    "Solo Scelta Multipla",
    "Solo Completamento",
    "Solo Domande aperte",
    "Solo Problemi/Calcoli",
]
