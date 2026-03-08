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
    #  GRAFITE — Carbon Blue  (Vercel/Linear-inspired · precise · modern SaaS)
    #  Near-black bg con micro cast blu · electric blue accent · cool white
    # ═══════════════════════════════════════════════════════════════════════
    "grafite": {
        # Superfici — near-black con sottile cast blue-gray
        "bg":         "#0C0D10",
        "bg2":        "#131518",
        "card":       "#1A1D22",
        "card2":      "#21252C",

        # Testo — cool white con gerarchia precisa
        "text":       "#F0F2F5",
        "text2":      "#8B93A0",
        "muted":      "#545E6B",

        # Bordi — minimal, barely-there
        "border":     "#252B33",
        "border2":    "#323A44",

        # Accent — Electric Blue (fiducia, azione, sistema)
        "accent":       "#3B82F6",
        "accent2":      "#60A5FA",
        "accent_light": "#0D1F3C",

        # Interazione
        "hover":      "#181D24",

        # Semantici — calibrati per massima leggibilità su dark
        "success":    "#34D399",
        "warn":       "#FBBF24",
        "error":      "#F87171",

        # Ombre — profonde, cinema dark
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(12,13,16,.70), 0 2px 8px rgba(0,0,0,.30)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — deep carbon, accent blue freddo
        "sidebar_bg":       "linear-gradient(180deg, #070809 0%, #0C0D10 100%)",
        "sidebar_border":   "#252B33",
        "sidebar_accent":   "#60A5FA",
        "sidebar_input_bg":  "#131518",
        "sidebar_input_text": "#F0F2F5",

        # Hint boxes
        "hint_bg":      "#0D1F3C",
        "hint_border":  "#1D3A6A",
        "hint_text":    "#60A5FA",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  INCHIOSTRO — Warm Editorial Dark  (espresso bg · amber gold · cream text)
    #  Ispirazione: pubblicazione di lusso, notebook analogico, Bear dark
    # ═══════════════════════════════════════════════════════════════════════
    "inchiostro": {
        # Superfici — espresso caldo, profondità senza freddo
        "bg":         "#0D0B07",
        "bg2":        "#151209",
        "card":       "#1E1913",
        "card2":      "#27211A",

        # Testo — crema calda, gerarchia editoriale
        "text":       "#F5EFE4",
        "text2":      "#AA9880",
        "muted":      "#6B5B48",

        # Bordi — warm, organici
        "border":     "#2E2418",
        "border2":    "#3F3226",

        # Accent — Amber Gold (calore, autorevolezza, azione)
        "accent":       "#E8971E",
        "accent2":      "#F5B84A",
        "accent_light": "#2C1C00",

        # Interazione
        "hover":      "#1A1510",

        # Semantici — warm-calibrated
        "success":    "#4ADE80",
        "warn":       "#FB923C",
        "error":      "#F87171",

        # Ombre — calde, profonde
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(13,11,7,.75), 0 2px 8px rgba(0,0,0,.30)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — quasi nero caldo, accento oro
        "sidebar_bg":       "linear-gradient(180deg, #070503 0%, #0D0B07 100%)",
        "sidebar_border":   "#2E2418",
        "sidebar_accent":   "#F5B84A",
        "sidebar_input_bg":  "#151209",
        "sidebar_input_text": "#F5EFE4",

        # Hint boxes — ambra scura
        "hint_bg":      "#2C1C00",
        "hint_border":  "#6A4500",
        "hint_text":    "#F5B84A",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CARTA — Ultra-clean Paper White  (Linear light · Stripe · GitHub light)
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
        "hover":      "#F0F4FF",

        # Semantici — vividi per leggibilità su bianco
        "success":    "#059669",
        "warn":       "#D97706",
        "error":      "#DC2626",

        # Ombre — ultra-soft, quasi impercettibili
        "shadow":     "0 1px 2px rgba(15,17,23,.06)",
        "shadow_md":  "0 4px 20px rgba(15,17,23,.08), 0 1px 3px rgba(15,17,23,.04)",
        "shadow_soft": "0 12px 40px rgba(15,17,23,.06), 0 2px 8px rgba(15,17,23,.03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — slate scuro, accent blue coerente
        "sidebar_bg":       "linear-gradient(180deg, #0F172A 0%, #1E293B 100%)",
        "sidebar_border":   "#334155",
        "sidebar_accent":   "#60A5FA",
        "sidebar_input_bg":  "#0F172A",
        "sidebar_input_text": "#E2E8F0",

        # Hint boxes — blue very light
        "hint_bg":      "#EFF6FF",
        "hint_border":  "#BFDBFE",
        "hint_text":    "#1D4ED8",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  AVORIO — Warm Ivory Editorial  (Notion · Readwise · Bear light)
    #  Ivory bg caldo · violet accent ricco · charcoal caldo
    # ═══════════════════════════════════════════════════════════════════════
    "avorio": {
        # Superfici — avorio caldo, texture carta di qualità
        "bg":         "#F8F5F0",
        "bg2":        "#EEE9E2",
        "card":       "#FFFFFF",
        "card2":      "#FAF8F5",

        # Testo — charcoal caldo, mai neutro-freddo
        "text":       "#1A1612",
        "text2":      "#4A4038",
        "muted":      "#7A6E64",

        # Bordi — warm, organici
        "border":     "#E0DAD2",
        "border2":    "#D0C8BE",

        # Accent — Violet vivido (creatività, premium, editoriale)
        "accent":       "#7C3AED",
        "accent2":      "#6D28D9",
        "accent_light": "#F5F3FF",

        # Interazione
        "hover":      "#F3F0FF",

        # Semantici — warm-calibrated per sfondo avorio
        "success":    "#059669",
        "warn":       "#D97706",
        "error":      "#DC2626",

        # Ombre — calde, eleganti
        "shadow":     "0 1px 2px rgba(26,22,18,.07)",
        "shadow_md":  "0 4px 20px rgba(26,22,18,.09), 0 1px 3px rgba(26,22,18,.05)",
        "shadow_soft": "0 12px 40px rgba(26,22,18,.07), 0 2px 8px rgba(26,22,18,.04)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — slate plum scuro, accent violet
        "sidebar_bg":       "linear-gradient(180deg, #1E1B2E 0%, #2D2540 100%)",
        "sidebar_border":   "#3D3560",
        "sidebar_accent":   "#A78BFA",
        "sidebar_input_bg":  "#1E1B2E",
        "sidebar_input_text": "#EDE9FE",

        # Hint boxes — lavender leggero
        "hint_bg":      "#F5F3FF",
        "hint_border":  "#DDD6FE",
        "hint_text":    "#6D28D9",
    },
}

THEME_LABELS = {
    "notte":      "🌙 Notte",
    "chiaro":     "☀️ Giorno",
    "grafite":    "◼ Grafite",
    "inchiostro": "🟤 Inchiostro",
    "carta":      "📄 Carta",
    "avorio":     "🟡 Avorio",
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
