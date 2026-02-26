# ── config.py ──────────────────────────────────────────────────────────────────
# Tutte le costanti dell'app. Nessuna logica, nessun import di streamlit.
# Importa con: from config import *
# oppure selettivamente: from config import MATERIE, THEMES, ...
# ───────────────────────────────────────────────────────────────────────────────

# ── APP ────────────────────────────────────────────────────────────────────────
APP_NAME          = "VerificAI"
APP_ICON          = "📝"
APP_TAGLINE       = "Crea verifiche su misura in pochi secondi"
SHARE_URL         = "https://verificai.streamlit.app"
FEEDBACK_FORM_URL = "https://forms.gle/KNu8v8iDVUiGkQUL8"

# ── LIMITI E RUOLI ─────────────────────────────────────────────────────────────
LIMITE_MENSILE = 5          # verifiche gratuite al mese per utente free
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
THEMES = {
    "light": {
        "bg":           "#F7F7F5",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#F0EFEB",
        "border":       "#E5E4DF",
        "border2":      "#D1D0CA",
        "text":         "#1A1915",
        "text2":        "#4A4840",
        "muted":        "#8C8A82",
        "accent":       "#D97706",
        "accent_light": "#FEF3C7",
        "accent2":      "#059669",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.05)",
        "shadow_md":    "0 4px 12px rgba(0,0,0,.08)",
        "input_bg":     "#FFFFFF",
        "hover":        "#F0EFEB",
    },
    "dark": {
        "bg":           "#0F0F0E",
        "bg2":          "#1A1916",
        "card":         "#1A1916",
        "card2":        "#232320",
        "border":       "#2E2D28",
        "border2":      "#3D3C36",
        "text":         "#F5F4EF",
        "text2":        "#C8C6BC",
        "muted":        "#6B6960",
        "accent":       "#F59E0B",
        "accent_light": "#292215",
        "accent2":      "#10B981",
        "success":      "#10B981",
        "warn":         "#F59E0B",
        "err":          "#EF4444",
        "shadow":       "0 1px 3px rgba(0,0,0,.3)",
        "shadow_md":    "0 4px 16px rgba(0,0,0,.4)",
        "input_bg":     "#232320",
        "hover":        "#232320",
    },
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
