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
# Tema default: Carta (light) + opzione Notte (dark)
# ───────────────────────────────────────────────────────────────────────────────

THEMES = {
    # ═══════════════════════════════════════════════════════════════════════
    #  CARTA — Ultra-clean Paper White  (Linear light · Stripe · GitHub light) - DEFAULT
    #  Massima leggibilità · blue accent autorevole · tipografia precisa
    # ═══════════════════════════════════════════════════════════════════════
    "carta": {
        # Superfici — bianco-carta con micro-warmth, non freddo
        "bg":         "#FAFAFA",
        "bg2":        "#F2F3F5",
        "card":       "#FFFFFF",
        "card2":      "#F8F9FA",

        # Testo — near-black quasi neutro, massimo contrasto
        "text":       "#0F1117",
        "text2":      "#4A5166",
        "muted":      "#7A8299",

        # Bordi — minimal, ultra-sottili
        "border":     "#E2E5EB",
        "border2":    "#CDD1D9",

        # Accent — Blue autorevole (sistema, fiducia, azione)
        "accent":       "#2563EB",
        "accent2":      "#1D4ED8",
        "accent_light": "#EFF6FF",

        # Interazione
        "hover":      "#F8FAFC",

        # Semantici — calibrati per light theme
        "success":    "#059669",
        "warn":       "#D97706",
        "error":      "#DC2626",

        # Ombre — ultra-morbide, professionali
        "shadow":     "0 1px 2px rgba(15,17,23,.04)",
        "shadow_md":  "0 4px 20px rgba(15,17,23,.08), 0 1px 3px rgba(15,17,23,.04)",
        "shadow_soft": "0 12px 40px rgba(15,17,23,.06), 0 2px 8px rgba(15,17,23,.03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — grigio scuro professionale
        "sidebar_bg":      "linear-gradient(180deg, #1E293B 0%, #0F172A 100%)",
        "sidebar_border":  "#475569",
        "sidebar_accent":  "#3B82F6",
        "sidebar_input_bg":  "#334155",
        "sidebar_input_text": "#F8FAFC",

        # Hint boxes
        "hint_bg":      "#EFF6FF",
        "hint_border":  "#BFDBFE",
        "hint_text":    "#1D4ED8",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  NOTTE — Dark Midnight Blue  (opzione dark)
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
    #  OCEANO — Ocean Blue Theme (clean, minimal)
    #  ═══════════════════════════════════════════════════════════════════════
    "oceano": {
        # Superfici — bianco con accenti blu
        "bg":         "#FFFFFF",
        "bg2":        "#F8FAFC",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — blu scuro
        "text":       "#1E40AF",
        "text2":      "#3B82F6",
        "muted":      "#6B7280",

        # Bordi — blu molto leggero
        "border":     "#EFF6FF",
        "border2":    "#DBEAFE",

        # Accent — blu oceanico
        "accent":       "#3B82F6",
        "accent2":      "#2563EB",
        "accent_light": "#EFF6FF",

        # Interazione
        "hover":      "#F8FAFC",

        # Semantici
        "success":    "#059669",
        "warn":       "#F59E0B",
        "error":      "#EF4444",

        # Ombre — minimal
        "shadow":     "0 1px 3px rgba(0, 0, 0, .1)",
        "shadow_md":  "0 4px 6px rgba(0, 0, 0, .1)",
        "shadow_soft": "0 10px 15px rgba(0, 0, 0, .05)",

        # Design system
        "radius_sm":  "6px",
        "radius_md":  "8px",
        "radius_lg":  "12px",

        # Sidebar — blu scuro minimal
        "sidebar_bg":      "linear-gradient(180deg, #1E293B 0%, #334155 100%)",
        "sidebar_border":  "#475569",
        "sidebar_accent":  "#818CF8",
        "sidebar_input_bg":  "#1E293B",
        "sidebar_input_text": "#F8FAFC",

        # Hint boxes
        "hint_bg":      "#EFF6FF",
        "hint_border":  "#3B82F6",
        "hint_text":    "#1E40AF",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  FORESTA — Forest Green Theme (natural, clean)
    #  ═══════════════════════════════════════════════════════════════════════
    "foresta": {
        # Superfici — bianco con accenti verdi
        "bg":         "#FFFFFF",
        "bg2":        "#F8FAFC",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — verde scuro
        "text":       "#14532D",
        "text2":      "#16A34A",
        "muted":      "#6B7280",

        # Bordi — verde molto leggero
        "border":     "#F0FDF4",
        "border2":    "#DCFCE7",

        # Accent — verde foresta
        "accent":       "#16A34A",
        "accent2":      "#15803D",
        "accent_light": "#F0FDF4",

        # Interazione
        "hover":      "#F8FAFC",

        # Semantici
        "success":    "#059669",
        "warn":       "#F59E0B",
        "error":      "#EF4444",

        # Ombre — minimal
        "shadow":     "0 1px 3px rgba(0, 0, 0, .1)",
        "shadow_md":  "0 4px 6px rgba(0, 0, 0, .1)",
        "shadow_soft": "0 10px 15px rgba(0, 0, 0, .05)",

        # Design system
        "radius_sm":  "6px",
        "radius_md":  "8px",
        "radius_lg":  "12px",

        # Sidebar — verde scuro minimal
        "sidebar_bg":      "linear-gradient(180deg, #14532D 0%, #166534 100%)",
        "sidebar_border":  "#16A34A",
        "sidebar_accent":  "#22C55E",
        "sidebar_input_bg":  "#14532D",
        "sidebar_input_text": "#F0FDF4",

        # Hint boxes
        "hint_bg":      "#F0FDF4",
        "hint_border":  "#16A34A",
        "hint_text":    "#14532D",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  TRAMONTO — Sunset Orange Theme (warm, simple)
    #  ═══════════════════════════════════════════════════════════════════════
    "tramonto": {
        # Superfici — bianco con accenti arancioni
        "bg":         "#FFFFFF",
        "bg2":        "#F8FAFC",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — arancione scuro
        "text":       "#9A3412",
        "text2":      "#EA580C",
        "muted":      "#6B7280",

        # Bordi — arancione molto leggero
        "border":     "#FFF7ED",
        "border2":    "#FED7AA",

        # Accent — arancione tramonto
        "accent":       "#EA580C",
        "accent2":      "#C2410C",
        "accent_light": "#FFF7ED",

        # Interazione
        "hover":      "#F8FAFC",

        # Semantici
        "success":    "#059669",
        "warn":       "#F59E0B",
        "error":      "#EF4444",

        # Ombre — minimal
        "shadow":     "0 1px 3px rgba(0, 0, 0, .1)",
        "shadow_md":  "0 4px 6px rgba(0, 0, 0, .1)",
        "shadow_soft": "0 10px 15px rgba(0, 0, 0, .05)",

        # Design system
        "radius_sm":  "6px",
        "radius_md":  "8px",
        "radius_lg":  "12px",

        # Sidebar — arancione scuro minimal
        "sidebar_bg":      "linear-gradient(180deg, #9A3412 0%, #EA580C 100%)",
        "sidebar_border":  "#EA580C",
        "sidebar_accent":  "#FB923C",
        "sidebar_input_bg":  "#9A3412",
        "sidebar_input_text": "#FFF7ED",

        # Hint boxes
        "hint_bg":      "#FFF7ED",
        "hint_border":  "#EA580C",
        "hint_text":    "#9A3412",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  LAVANDA — Lavender Purple Theme (elegant, minimal)
    #  ═══════════════════════════════════════════════════════════════════════
    "lavanda": {
        # Superfici — bianco con accenti viola
        "bg":         "#FFFFFF",
        "bg2":        "#F8FAFC",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — viola scuro
        "text":       "#6B21A8",
        "text2":      "#9333EA",
        "muted":      "#6B7280",

        # Bordi — viola molto leggero
        "border":     "#FAF5FF",
        "border2":    "#F3E8FF",

        # Accent — viola lavanda
        "accent":       "#9333EA",
        "accent2":      "#7C3AED",
        "accent_light": "#FAF5FF",

        # Interazione
        "hover":      "#F8FAFC",

        # Semantici
        "success":    "#059669",
        "warn":       "#F59E0B",
        "error":      "#EF4444",

        # Ombre — minimal
        "shadow":     "0 1px 3px rgba(0, 0, 0, .1)",
        "shadow_md":  "0 4px 6px rgba(0, 0, 0, .1)",
        "shadow_soft": "0 10px 15px rgba(0, 0, 0, .05)",

        # Design system
        "radius_sm":  "6px",
        "radius_md":  "8px",
        "radius_lg":  "12px",

        # Sidebar — viola scuro minimal
        "sidebar_bg":      "linear-gradient(180deg, #6B21A8 0%, #9333EA 100%)",
        "sidebar_border":  "#9333EA",
        "sidebar_accent":  "#A855F7",
        "sidebar_input_bg":  "#6B21A8",
        "sidebar_input_text": "#FAF5FF",

        # Hint boxes
        "hint_bg":      "#FAF5FF",
        "hint_border":  "#9333EA",
        "hint_text":    "#6B21A8",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CIOCCOLATO — Chocolate Brown Theme (warm, professional)
    #  ═══════════════════════════════════════════════════════════════════════
    "cioccolato": {
        # Superfici — bianco con accenti marroni
        "bg":         "#FFFFFF",
        "bg2":        "#F8FAFC",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — marrone scuro
        "text":       "#92400E",
        "text2":      "#D97706",
        "muted":      "#6B7280",

        # Bordi — marrone molto leggero
        "border":     "#FEF3C7",
        "border2":    "#FDE68A",

        # Accent — marrone cioccolato
        "accent":       "#D97706",
        "accent2":      "#B45309",
        "accent_light": "#FEF3C7",

        # Interazione
        "hover":      "#F8FAFC",

        # Semantici
        "success":    "#059669",
        "warn":       "#F59E0B",
        "error":      "#EF4444",

        # Ombre — minimal
        "shadow":     "0 1px 3px rgba(0, 0, 0, .1)",
        "shadow_md":  "0 4px 6px rgba(0, 0, 0, .1)",
        "shadow_soft": "0 10px 15px rgba(0, 0, 0, .05)",

        # Design system
        "radius_sm":  "6px",
        "radius_md":  "8px",
        "radius_lg":  "12px",

        # Sidebar — marrone scuro minimal
        "sidebar_bg":      "linear-gradient(180deg, #92400E 0%, #D97706 100%)",
        "sidebar_border":  "#D97706",
        "sidebar_accent":  "#F59E0B",
        "sidebar_input_bg":  "#92400E",
        "sidebar_input_text": "#FEF3C7",

        # Hint boxes
        "hint_bg":      "#FEF3C7",
        "hint_border":  "#D97706",
        "hint_text":    "#92400E",
    },
}

THEME_LABELS = {
    "carta": "📄 Carta",
    "notte": "🌙 Notte",
    "oceano": "🌊 Oceano",
    "foresta": "🌲 Foresta",
    "tramonto": "🌅 Tramonto",
    "lavanda": "💜 Lavanda",
    "cioccolato": "🍫 Cioccolato",
}

DEFAULT_THEME = "carta"

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
