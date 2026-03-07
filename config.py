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

        # Sidebar
        "sidebar_bg":      "linear-gradient(180deg, #010409 0%, #0D1117 100%)",
        "sidebar_border":  "#21262D",
        "sidebar_accent":  "#79C0FF",

        # Hint boxes
        "hint_bg":      "#0D2340",
        "hint_border":  "#1F4070",
        "hint_text":    "#79C0FF",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CHIARO — White Smoke + Sea Green  (tema chiaro professionale)
    #  Palette: Carbon Black #1C2321, White Smoke #F3F3F3,
    #           Sea Green #058C42, Tomato Jam #C3423F, Orange #F9A620
    # ═══════════════════════════════════════════════════════════════════════
    "chiaro": {
        # Superfici — White Smoke come base, degradate verso il grigio
        "bg":         "#EAEAEA",     # White Smoke scurito leggermente (no abbagliamento)
        "bg2":        "#E0E0E0",     # secondo livello
        "card":       "#F3F3F3",     # card — White Smoke puro
        "card2":      "#FFFFFF",     # card overlay — bianco per contrasto

        # Testo — Carbon Black come base
        "text":       "#1C2321",     # Carbon Black — massimo contrasto
        "text2":      "#3D5048",     # Carbon Black schiarito — secondario
        "muted":      "#6B8078",     # muted verdino su fondo chiaro

        # Bordi
        "border":     "#C4CECA",     # bordo grigio-verde leggero
        "border2":    "#A8B8B2",     # bordo più marcato

        # Accent — Sea Green su sfondo chiaro: contrasto AAA
        "accent":       "#058C42",   # Sea Green
        "accent2":      "#047A3A",   # Sea Green leggermente più scuro (hover)
        "accent_light": "#D4F0E2",   # tinta chiarissima per sfondi pill

        # Interazione
        "hover":      "#D8E8E2",     # hover card — verde chiarissimo

        # Semantici
        "success":    "#058C42",     # Sea Green
        "warn":       "#E09010",     # Orange scurito per contrasto su chiaro
        "error":      "#C3423F",     # Tomato Jam

        # Ombre — più leggere su tema chiaro
        "shadow":     "0 1px 3px rgba(28,35,33,.12)",
        "shadow_md":  "0 4px 20px rgba(28,35,33,.18)",

        # Sidebar — Carbon Black leggero per contrasto con area principale
        "sidebar_bg":      "linear-gradient(180deg, #2A3533 0%, #1C2321 100%)",
        "sidebar_border":  "#3A4E47",
        "sidebar_accent":  "#07C45A",

        # Hint boxes
        "hint_bg":      "#D4F0E2",
        "hint_border":  "#7DD4A8",
        "hint_text":    "#036830",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  FORESTA — Azure Cielo + Verde Salvia  (tema chiaro freddo)
    #  Palette:  Cielo Azzurro  #B8D8E8  (sfondo principale)
    #            Carta          #EAF4F8  (card, superfici chiare)
    #            Blu Acciaio    #3A7CA5  (accent primario)
    #            Verde Salvia   #4A8C6A  (accent secondario / success)
    #            Inchiostro     #1A3040  (testo principale)
    # ═══════════════════════════════════════════════════════════════════════
    "foresta": {
        # Superfici — azzurro medio-chiaro come base (non troppo pallido)
        "bg":         "#B8D8E8",     # Cielo Azzurro — sfondo principale
        "bg2":        "#AACEDD",     # leggermente più saturo per profondità
        "card":       "#EAF4F8",     # carta quasi-bianca con tono freddo
        "card2":      "#D6EAEF",     # card secondaria, tono intermedio

        # Testo — inchiostro scuro per contrasto elevato su azzurro
        "text":       "#1A3040",     # Inchiostro Notte — leggibilità massima
        "text2":      "#2E5268",     # blu-grigio medio
        "muted":      "#5A7F96",     # muted freddo

        # Bordi
        "border":     "#8CBDD0",     # bordo azzurro medio
        "border2":    "#6A9FB8",     # bordo più marcato

        # Accent — Blu Acciaio come primario, Verde Salvia come secondario
        "accent":       "#3A7CA5",   # Blu Acciaio — buon contrasto su azzurro chiaro
        "accent2":      "#2E6A90",   # Blu Acciaio scurito (hover)
        "accent_light": "#C8E4EF",   # tinta chiarissima per sfondi pill

        # Interazione
        "hover":      "#C4DDE8",     # hover card — azzurro leggermente più scuro

        # Semantici
        "success":    "#4A8C6A",     # Verde Salvia
        "warn":       "#C07820",     # ambra scurito (contrasto su azzurro)
        "error":      "#B03A3A",     # rosso mattone (leggibile su azzurro)

        # Ombre
        "shadow":     "0 1px 4px rgba(26,48,64,.14)",
        "shadow_md":  "0 4px 20px rgba(26,48,64,.20)",

        # Sidebar — blu acciaio scuro, contrasto con area principale azzurra
        "sidebar_bg":      "linear-gradient(180deg, #1A3040 0%, #22485E 100%)",
        "sidebar_border":  "#2E5268",
        "sidebar_accent":  "#7DCAE0",

        # Hint boxes
        "hint_bg":      "#C8E4EF",
        "hint_border":  "#7BB8CE",
        "hint_text":    "#1E5470",
    },
}

THEME_LABELS = {
    "notte":   "🌙 Notte",
    "chiaro":  "☀️ Chiaro",
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
