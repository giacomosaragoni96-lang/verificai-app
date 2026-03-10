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
    #  OCEANO — Ocean Blue Theme (calm, professional, trustworthy)
    #  ═══════════════════════════════════════════════════════════════════════
    "oceano": {
        # Superfici — blu oceanico profondo
        "bg":         "#F0F9FF",
        "bg2":        "#E0F2FE",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — blu scuro per contrasto
        "text":       "#0C4A6E",
        "text2":      "#075985",
        "muted":      "#64748B",

        # Bordi — blu azzurro
        "border":     "#BAE6FD",
        "border2":    "#7DD3FC",

        # Accent — blu oceanico
        "accent":       "#0EA5E9",
        "accent2":      "#0284C7",
        "accent_light": "#F0F9FF",

        # Interazione
        "hover":      "#F0F9FF",

        # Semantici — calibrati per ocean theme
        "success":    "#059669",
        "warn":       "#EA580C",
        "error":      "#DC2626",

        # Ombre — blu morbide
        "shadow":     "0 1px 2px rgba(12, 74, 110, .04)",
        "shadow_md":  "0 4px 20px rgba(12, 74, 110, .08), 0 1px 3px rgba(12, 74, 110, .04)",
        "shadow_soft": "0 12px 40px rgba(12, 74, 110, .06), 0 2px 8px rgba(12, 74, 110, .03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — blu scuro oceanico
        "sidebar_bg":      "linear-gradient(180deg, #0C4A6E 0%, #075985 100%)",
        "sidebar_border":  "#0EA5E9",
        "sidebar_accent":  "#38BDF8",
        "sidebar_input_bg":  "#0E7490",
        "sidebar_input_text": "#F0F9FF",

        # Hint boxes
        "hint_bg":      "#F0F9FF",
        "hint_border":  "#BAE6FD",
        "hint_text":    "#0284C7",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  FORESTA — Forest Green Theme (nature, growth, harmony)
    #  ═══════════════════════════════════════════════════════════════════════
    "foresta": {
        # Superfici — verde foresta chiaro
        "bg":         "#F0FDF4",
        "bg2":        "#DCFCE7",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — verde scuro foresta
        "text":       "#14532D",
        "text2":      "#166534",
        "muted":      "#64748B",

        # Bordi — verde salvia
        "border":     "#BBF7D0",
        "border2":    "#86EFAC",

        # Accent — verde foresta
        "accent":       "#16A34A",
        "accent2":      "#15803D",
        "accent_light": "#F0FDF4",

        # Interazione
        "hover":      "#F0FDF4",

        # Semantici — calibrati per forest theme
        "success":    "#059669",
        "warn":       "#EA580C",
        "error":      "#DC2626",

        # Ombre — verdi morbide
        "shadow":     "0 1px 2px rgba(20, 83, 45, .04)",
        "shadow_md":  "0 4px 20px rgba(20, 83, 45, .08), 0 1px 3px rgba(20, 83, 45, .04)",
        "shadow_soft": "0 12px 40px rgba(20, 83, 45, .06), 0 2px 8px rgba(20, 83, 45, .03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — verde scuro foresta
        "sidebar_bg":      "linear-gradient(180deg, #14532D 0%, #166534 100%)",
        "sidebar_border":  "#16A34A",
        "sidebar_accent":  "#22C55E",
        "sidebar_input_bg":  "#15803D",
        "sidebar_input_text": "#F0FDF4",

        # Hint boxes
        "hint_bg":      "#F0FDF4",
        "hint_border":  "#BBF7D0",
        "hint_text":    "#15803D",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  TRAMONTO — Sunset Orange Theme (warm, energetic, creative)
    #  ═══════════════════════════════════════════════════════════════════════
    "tramonto": {
        # Superfici — arancione tramonto chiaro
        "bg":         "#FFF7ED",
        "bg2":        "#FED7AA",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — arancione scuro
        "text":       "#7C2D12",
        "text2":      "#9A3412",
        "muted":      "#64748B",

        # Bordi — arancione pesca
        "border":     "#FED7AA",
        "border2":    "#FDBA74",

        # Accent — arancione tramonto
        "accent":       "#EA580C",
        "accent2":      "#C2410C",
        "accent_light": "#FFF7ED",

        # Interazione
        "hover":      "#FFF7ED",

        # Semantici — calibrati per sunset theme
        "success":    "#059669",
        "warn":       "#D97706",
        "error":      "#DC2626",

        # Ombre — arancioni morbide
        "shadow":     "0 1px 2px rgba(124, 45, 18, .04)",
        "shadow_md":  "0 4px 20px rgba(124, 45, 18, .08), 0 1px 3px rgba(124, 45, 18, .04)",
        "shadow_soft": "0 12px 40px rgba(124, 45, 18, .06), 0 2px 8px rgba(124, 45, 18, .03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — arancione scuro tramonto
        "sidebar_bg":      "linear-gradient(180deg, #7C2D12 0%, #9A3412 100%)",
        "sidebar_border":  "#EA580C",
        "sidebar_accent":  "#FB923C",
        "sidebar_input_bg":  "#C2410C",
        "sidebar_input_text": "#FFF7ED",

        # Hint boxes
        "hint_bg":      "#FFF7ED",
        "hint_border":  "#FED7AA",
        "hint_text":    "#C2410C",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  LAVANDA — Lavender Purple Theme (calm, creative, elegant)
    #  ═══════════════════════════════════════════════════════════════════════
    "lavanda": {
        # Superfici — lavanda chiaro
        "bg":         "#FAF5FF",
        "bg2":        "#F3E8FF",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — viola scuro
        "text":       "#581C87",
        "text2":      "#6B21A8",
        "muted":      "#64748B",

        # Bordi — lavanda
        "border":     "#E9D5FF",
        "border2":    "#D8B4FE",

        # Accent — viola lavanda
        "accent":       "#9333EA",
        "accent2":      "#7C3AED",
        "accent_light": "#FAF5FF",

        # Interazione
        "hover":      "#FAF5FF",

        # Semantici — calibrati per lavender theme
        "success":    "#059669",
        "warn":       "#D97706",
        "error":      "#DC2626",

        # Ombre — viola morbide
        "shadow":     "0 1px 2px rgba(88, 28, 135, .04)",
        "shadow_md":  "0 4px 20px rgba(88, 28, 135, .08), 0 1px 3px rgba(88, 28, 135, .04)",
        "shadow_soft": "0 12px 40px rgba(88, 28, 135, .06), 0 2px 8px rgba(88, 28, 135, .03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — viola scuro lavanda
        "sidebar_bg":      "linear-gradient(180deg, #581C87 0%, #6B21A8 100%)",
        "sidebar_border":  "#9333EA",
        "sidebar_accent":  "#A855F7",
        "sidebar_input_bg":  "#7C3AED",
        "sidebar_input_text": "#FAF5FF",

        # Hint boxes
        "hint_bg":      "#FAF5FF",
        "hint_border":  "#E9D5FF",
        "hint_text":    "#7C3AED",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CIOCCOLATO — Chocolate Brown Theme (warm, professional, sophisticated)
    #  ═══════════════════════════════════════════════════════════════════════
    "cioccolato": {
        # Superfici — cioccolato chiaro
        "bg":         "#FEF3C7",
        "bg2":        "#FDE68A",
        "card":       "#FFFFFF",
        "card2":      "#F8FAFC",

        # Testo — marrone scuro
        "text":       "#78350F",
        "text2":      "#92400E",
        "muted":      "#64748B",

        # Bordi — marrone chiaro
        "border":     "#FDE68A",
        "border2":    "#FCD34D",

        # Accent — marrone cioccolato
        "accent":       "#D97706",
        "accent2":      "#B45309",
        "accent_light": "#FEF3C7",

        # Interazione
        "hover":      "#FEF3C7",

        # Semantici — calibrati per chocolate theme
        "success":    "#059669",
        "warn":       "#D97706",
        "error":      "#DC2626",

        # Ombre — marroni morbide
        "shadow":     "0 1px 2px rgba(120, 53, 15, .04)",
        "shadow_md":  "0 4px 20px rgba(120, 53, 15, .08), 0 1px 3px rgba(120, 53, 15, .04)",
        "shadow_soft": "0 12px 40px rgba(120, 53, 15, .06), 0 2px 8px rgba(120, 53, 15, .03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — marrone scuro cioccolato
        "sidebar_bg":      "linear-gradient(180deg, #78350F 0%, #92400E 100%)",
        "sidebar_border":  "#D97706",
        "sidebar_accent":  "#F59E0B",
        "sidebar_input_bg":  "#B45309",
        "sidebar_input_text": "#FEF3C7",

        # Hint boxes
        "hint_bg":      "#FEF3C7",
        "hint_border":  "#FDE68A",
        "hint_text":    "#B45309",
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
