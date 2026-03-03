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
#
#  Routing intelligente per piano:
#  ┌──────────────────────────────┬────────────────────────────────────────────┐
#  │ Piano Free                   │ gemini-2.5-flash-lite                      │
#  │ Piano Pro (umanistiche/ling) │ gemini-2.5-flash                           │
#  │ Piano Gold / Pro+ STEM       │ gemini-2.5-pro                             │
#  └──────────────────────────────┴────────────────────────────────────────────┘
#
#  Usi speciali (sempre Flash Lite, nessun piano richiesto):
#    - analisi metadati upload (percorso A)
#    - feedback testuale / messaggi dialogo
#    - modifica singolo blocco esercizio
#
MODELLI_DISPONIBILI = {
    "⚡ Flash 2.5 Lite (veloce · Free)": {
        "id":    "gemini-2.5-flash-lite",
        "piano": "free",   # disponibile a tutti
    },
    "⚡ Flash 2.5 (bilanciato · Pro)": {
        "id":    "gemini-2.5-flash",
        "piano": "pro",    # richiede piano Pro
    },
    "🧠 Pro 2.5 (STEM/Gold)": {
        "id":    "gemini-2.5-pro",
        "piano": "gold",   # richiede piano Gold
    },
}

# ── ID MODELLO rapido usato per task economici (analisi upload, feedback, edit blocco)
MODEL_FAST_ID = "gemini-2.5-flash-lite"

# ── Materie STEM: usano routing Pro (Gold) se disponibile
MATERIE_STEM = {
    "Matematica", "Fisica", "Chimica", "Informatica",
    "Scienze della Terra", "Biologia",
}

# ── Routing automatico: dato piano + materia → model_id
def get_model_id_per_piano(piano: str, materia: str = "") -> str:
    """
    Restituisce il model_id corretto per piano e materia.
    piano: "free" | "pro" | "gold" | "admin"
    """
    is_stem = materia in MATERIE_STEM
    if piano == "gold" or (piano == "admin" and is_stem):
        return MODELLI_DISPONIBILI["🧠 Pro 2.5 (STEM/Gold)"]["id"]
    if piano in ("pro", "admin"):
        return MODELLI_DISPONIBILI["⚡ Flash 2.5 (bilanciato · Pro)"]["id"]
    # Free — sempre Lite
    return MODEL_FAST_ID  # Free — sempre Lite

# ── TEMI UI ────────────────────────────────────────────────────────────────────
# 4 temi: scuro (dark, default), chiaro, midnight, aurora.
# ───────────────────────────────────────────────────────────────────────────────

THEMES = {
    # ═══════════════════════════════════════════════════════════════════════
    #  CHIARO — Warm Sand & Amber Accents
    #  Sfondo caldo, non bianco puro; card con bordi morbidi;
    #  accent ambra/arancio per CTA, verde per success, viola per facsimile.
    # ═══════════════════════════════════════════════════════════════════════
    "chiaro": {
        # Superfici (3 livelli di elevazione)
        "bg":         "#F8F6F2",     # sfondo principale — warm sand, non bianco puro
        "bg2":        "#F0EDE6",     # sfondo secondario (aree interne)
        "card":       "#FFFFFF",     # card primarie — bianco vero per contrasto
        "card2":      "#F5F3EE",     # card secondarie / overlay morbido

        # Testo (3 livelli di gerarchia)
        "text":       "#1A1815",     # titoli e testo primario — quasi nero warm
        "text2":      "#5C574D",     # testo secondario / descrizioni
        "muted":      "#9B9588",     # label, hint, placeholder

        # Bordi (2 livelli)
        "border":     "#E5E0D8",     # bordo principale
        "border2":    "#D4CFC5",     # bordo accentuato (card in rilievo)

        # Accent — Amber/Arancio dorato (CTA primarie)
        "accent":       "#C96B00",   # arancio dorato — high contrast su bianco
        "accent2":      "#D97706",   # gradient endpoint
        "accent_light": "#FEF3C7",   # sfondo tinta accent (badge, hint)

        # Interazione
        "hover":      "#F0EDE6",     # hover su card

        # Semantici
        "success":    "#16A34A",     # verde — azione completata
        "warn":       "#D97706",     # arancio — attenzione
        "error":      "#DC2626",     # rosso — errore

        # Ombre
        "shadow":     "0 1px 3px rgba(0,0,0,.04)",
        "shadow_md":  "0 4px 20px rgba(0,0,0,.06)",

        # Sidebar (sempre dark)
        "sidebar_bg":      "linear-gradient(180deg, #111110 0%, #0e0e0d 100%)",
        "sidebar_border":  "#252420",
        "sidebar_accent":  "#D97706",

        # Hint boxes
        "hint_bg":      "#FEF3C7",     # giallo tenue
        "hint_border":  "#FDE68A",     # giallo bordo
        "hint_text":    "#92400E",     # testo ambra scuro
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  SCURO — Deep Charcoal & Amber Glow
    #  Sfondo carbone profondo (non nero puro); card con elevazione sottile;
    #  accent ambra/arancio luminoso per visibilità su dark; verde neon per success.
    # ═══════════════════════════════════════════════════════════════════════
    "scuro": {
        # Superfici
        "bg":         "#0E0E0D",     # carbone profondo — non nero puro
        "bg2":        "#141412",     # secondo livello
        "card":       "#1A1917",     # card primarie — elevazione 1
        "card2":      "#1F1E1B",     # card secondarie — elevazione 2

        # Testo
        "text":       "#F5F3ED",     # titoli — bianco caldo
        "text2":      "#B8B5AB",     # testo secondario
        "muted":      "#6B6860",     # label, hint, placeholder

        # Bordi
        "border":     "#2A2824",     # bordo principale
        "border2":    "#3A3730",     # bordo accentuato

        # Accent
        "accent":       "#D97706",   # ambra luminoso — pop su dark
        "accent2":      "#F59E0B",   # gradient endpoint più chiaro
        "accent_light": "#D9770618", # sfondo tinta accent (trasparente)

        # Interazione
        "hover":      "#242320",     # hover

        # Semantici
        "success":    "#22C55E",     # verde neon — visibility su dark
        "warn":       "#F59E0B",     # giallo ambra
        "error":      "#EF4444",     # rosso vivo

        # Ombre
        "shadow":     "0 1px 4px rgba(0,0,0,.25)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.35)",

        # Sidebar
        "sidebar_bg":      "linear-gradient(180deg, #111110 0%, #0e0e0d 100%)",
        "sidebar_border":  "#252420",
        "sidebar_accent":  "#D97706",

        # Hint boxes
        "hint_bg":      "#1C1A15",     # carbone caldo
        "hint_border":  "#3A3420",     # bordo ambra tenue
        "hint_text":    "#D4A554",     # testo ambra morbido
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  AURORA — Light Fresh Teal
    #  Sfondo bianco caldo con venatura acquamarina; accent teal moderno;
    #  ottimo per contesti diurni prolungati.
    # ═══════════════════════════════════════════════════════════════════════
    "aurora": {
        # Superfici
        "bg":         "#F4FAF8",     # bianco con tocco acquamarina
        "bg2":        "#E8F5F1",     # secondo livello teal pallido
        "card":       "#FFFFFF",     # card bianche pure
        "card2":      "#F0FAF7",     # card secondarie teal tenue

        # Testo
        "text":       "#0E2A22",     # verde scuro quasi-nero
        "text2":      "#2D6B58",     # verde medio per testo secondario
        "muted":      "#6BA896",     # teal muted

        # Bordi
        "border":     "#C4E0D8",     # bordo teal chiaro
        "border2":    "#A0CCB8",     # bordo accentuato

        # Accent — Teal/Acquamarina
        "accent":       "#0A8F72",   # teal verde vivace — ottima leggibilità
        "accent2":      "#12B191",   # teal più chiaro per gradienti
        "accent_light": "#D4F4ED",   # sfondo tinta accent (badge, hint)

        # Interazione
        "hover":      "#E0F5EF",     # hover teal tenue

        # Semantici
        "success":    "#059669",
        "warn":       "#D97706",
        "error":      "#DC2626",

        # Ombre
        "shadow":     "0 1px 3px rgba(10,143,114,.06)",
        "shadow_md":  "0 4px 20px rgba(10,143,114,.10)",

        # Sidebar (sempre dark)
        "sidebar_bg":      "linear-gradient(180deg, #0A2218 0%, #061410 100%)",
        "sidebar_border":  "#163D2A",
        "sidebar_accent":  "#12B191",

        # Hint boxes
        "hint_bg":      "#D4F4ED",
        "hint_border":  "#74D6BC",
        "hint_text":    "#065545",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  MIDNIGHT — Deep Navy Blue
    #  Fondo navy profondo; accent blu elettrico vivace; gerarchia elevata;
    #  ideale per sessioni serali di lunga durata.
    # ═══════════════════════════════════════════════════════════════════════
    "midnight": {
        # Superfici
        "bg":         "#0B0F1A",     # navy profondo — non nero puro
        "bg2":        "#111520",     # secondo livello
        "card":       "#161B2B",     # card primarie — blu notte
        "card2":      "#1C2235",     # card secondarie — più chiare

        # Testo
        "text":       "#E8EDF8",     # bianco-blu freddo
        "text2":      "#9AA8C8",     # testo secondario blu-grigio
        "muted":      "#546080",     # muted blu scuro

        # Bordi
        "border":     "#252D42",     # bordo principale
        "border2":    "#3A445E",     # bordo accentuato

        # Accent — Blu Elettrico
        "accent":       "#4A90E2",   # blu elettrico — alta visibilità su navy
        "accent2":      "#6AAFF5",   # blu più chiaro per gradienti
        "accent_light": "#0D2545",   # sfondo tinta accent (badge, hint)

        # Interazione
        "hover":      "#1E2638",     # hover navy

        # Semantici
        "success":    "#22C55E",     # verde neon per dark
        "warn":       "#F59E0B",     # ambra
        "error":      "#EF4444",     # rosso vivo

        # Ombre
        "shadow":     "0 1px 4px rgba(0,0,0,.40)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.55)",

        # Sidebar
        "sidebar_bg":      "linear-gradient(180deg, #060810 0%, #030508 100%)",
        "sidebar_border":  "#161B2B",
        "sidebar_accent":  "#4A90E2",

        # Hint boxes
        "hint_bg":      "#0D1F3A",
        "hint_border":  "#254880",
        "hint_text":    "#7AAEE8",
    },
}

# ── Etichette leggibili per il menu a tendina ──────────────────────────────────
THEME_LABELS = {
    "scuro":    "🌙  Scuro",
    "chiaro":   "☀️  Chiaro",
    "midnight": "🌌  Midnight",
    "aurora":   "🌿  Aurora",
}

# Tema predefinito all'avvio — SCURO
DEFAULT_THEME = "scuro"

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

# ── ICONE MATERIE (emoji per card UI) ──────────────────────────────────────────
MATERIE_ICONS = {
    "Matematica":          "📐",
    "Fisica":              "⚡",
    "Chimica":             "🧪",
    "Biologia":            "🧬",
    "Scienze della Terra": "🌍",
    "Italiano":            "📖",
    "Storia":              "🏛️",
    "Geografia":           "🗺️",
    "Latino":              "🦅",
    "Greco":               "🏺",
    "Inglese":             "🇬🇧",
    "Francese":            "🗼",
    "Spagnolo":            "☀️",
    "Tedesco":             "🦁",
    "Filosofia":           "🤔",
    "Storia dell'Arte":    "🎨",
    "Musica":              "🎵",
    "Informatica":         "💻",
    "Economia":            "📊",
    "Diritto":             "⚖️",
    "Educazione Civica":   "🏛️",
    "Scienze Motorie":     "⚽",
    "Altra materia":       "✏️",
}

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
