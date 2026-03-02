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
# Solo 2 temi: Slate Carbon (dark, default) e Arctic Blue (chiaro).
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

    # ── SCURO — Slate Carbon (default) ───────────────────────────────────────
    "slate_carbon": {
        "bg":           "#161618",
        "bg2":          "#1C1C1F",
        "card":         "#232326",
        "card2":        "#2C2C30",
        "border":       "#35353A",
        "border2":      "#46464C",
        "text":         "#F0F0F8",
        "text2":        "#C8C8D8",
        "muted":        "#82828E",
        "accent":       "#3B9EFF",
        "accent_light": "#001530",
        "accent2":      "#30D158",
        "success":      "#30D158",
        "warn":         "#FFB340",
        "err":          "#FF4545",
        "shadow":       "0 2px 8px rgba(0,0,0,.55)",
        "shadow_md":    "0 6px 22px rgba(0,0,0,.65)",
        "input_bg":     "#2C2C30",
        "hover":        "#3A3A40",
        "hint_bg":      "#0A1E38",
        "hint_text":    "#6AAEE0",
        "hint_border":  "#1A4F82",
        "sidebar_bg":     "linear-gradient(180deg, #0C0C0E 0%, #080808 100%)",
        "sidebar_border": "#252528",
        "sidebar_accent": "#5CA8E0",
    },

    # ── CHIARO — Arctic Blue ─────────────────────────────────────────────────
    "chiaro🌕": {
        "bg":           "#E8F4FD",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FFF9ED",
        "border":       "#B8D4E8",
        "border2":      "#E5AF3C",
        "text":         "#0B2540",
        "text2":        "#1E4D75",
        "muted":        "#4A7A9B",
        "accent":       "#C96B00",
        "accent_light": "#FEF0D9",
        "accent2":      "#F59E0B",
        "success":      "#05875A",
        "warn":         "#A84400",
        "err":          "#C81C1C",
        "shadow":       "0 1px 4px rgba(0,0,0,.10), 0 1px 2px rgba(0,0,0,.06)",
        "shadow_md":    "0 4px 16px rgba(201,107,0,.18)",
        "input_bg":     "#F2F8FD",
        "hover":        "#FEF0D9",
        "hint_bg":      "#FEF0D9",
        "hint_text":    "#6B2800",
        "hint_border":  "#E5943C",
        "sidebar_bg":     "linear-gradient(180deg, #0B1E30 0%, #071525 100%)",
        "sidebar_border": "#183048",
        "sidebar_accent": "#E09A30",
    },

    # ── LAVANDA ──────────────────────────────────────────────────────────────
    "lavanda": {
        "bg":           "#F5F0FF",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#EDE8FF",
        "border":       "#D4C9F5",
        "border2":      "#B8A8F0",
        "text":         "#1E0B4B",
        "text2":        "#4A3580",
        "muted":        "#7B6BA8",
        "accent":       "#7C3AED",
        "accent_light": "#EDE9FE",
        "accent2":      "#A78BFA",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(124,58,237,.1)",
        "shadow_md":    "0 4px 16px rgba(124,58,237,.18)",
        "input_bg":     "#F9F6FF",
        "hover":        "#EDE9FE",
        "hint_bg":      "#EDE9FE",
        "hint_text":    "#4C1D95",
        "hint_border":  "#A78BFA",
        "sidebar_bg":     "linear-gradient(180deg, #1E0B4B 0%, #150832 100%)",
        "sidebar_border": "#3D2580",
        "sidebar_accent": "#A78BFA",
    },

    # ── MENTA ────────────────────────────────────────────────────────────────
    "menta": {
        "bg":           "#ECFDF5",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#D1FAE5",
        "border":       "#A7F3D0",
        "border2":      "#6EE7B7",
        "text":         "#052E16",
        "text2":        "#065F46",
        "muted":        "#6B7280",
        "accent":       "#059669",
        "accent_light": "#D1FAE5",
        "accent2":      "#10B981",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(5,150,105,.1)",
        "shadow_md":    "0 4px 16px rgba(5,150,105,.18)",
        "input_bg":     "#F0FDF9",
        "hover":        "#D1FAE5",
        "hint_bg":      "#D1FAE5",
        "hint_text":    "#065F46",
        "hint_border":  "#6EE7B7",
        "sidebar_bg":     "linear-gradient(180deg, #052E16 0%, #031B0E 100%)",
        "sidebar_border": "#0D4A28",
        "sidebar_accent": "#34D399",
    },

    # ── PESCA ─────────────────────────────────────────────────────────────────
    "pesca": {
        "bg":           "#FFF7ED",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FFEDD5",
        "border":       "#FED7AA",
        "border2":      "#FDBA74",
        "text":         "#431407",
        "text2":        "#9A3412",
        "muted":        "#78350F",
        "accent":       "#EA580C",
        "accent_light": "#FFEDD5",
        "accent2":      "#F97316",
        "success":      "#16A34A",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(234,88,12,.1)",
        "shadow_md":    "0 4px 16px rgba(234,88,12,.18)",
        "input_bg":     "#FFF5EC",
        "hover":        "#FFEDD5",
        "hint_bg":      "#FFEDD5",
        "hint_text":    "#7C2D12",
        "hint_border":  "#FDBA74",
        "sidebar_bg":     "linear-gradient(180deg, #431407 0%, #2C0D04 100%)",
        "sidebar_border": "#7C2D12",
        "sidebar_accent": "#FB923C",
    },

    # ── OCEANO ───────────────────────────────────────────────────────────────
    "oceano": {
        "bg":           "#EFF6FF",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#DBEAFE",
        "border":       "#BFDBFE",
        "border2":      "#93C5FD",
        "text":         "#1E3A5F",
        "text2":        "#1D4ED8",
        "muted":        "#3B82F6",
        "accent":       "#2563EB",
        "accent_light": "#DBEAFE",
        "accent2":      "#60A5FA",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(37,99,235,.1)",
        "shadow_md":    "0 4px 16px rgba(37,99,235,.18)",
        "input_bg":     "#F0F6FF",
        "hover":        "#DBEAFE",
        "hint_bg":      "#DBEAFE",
        "hint_text":    "#1E40AF",
        "hint_border":  "#93C5FD",
        "sidebar_bg":     "linear-gradient(180deg, #1E3A5F 0%, #112240 100%)",
        "sidebar_border": "#1D4ED8",
        "sidebar_accent": "#60A5FA",
    },

    # ── ROSA ─────────────────────────────────────────────────────────────────
    "rosa": {
        "bg":           "#FFF1F5",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FCE7F3",
        "border":       "#FBCFE8",
        "border2":      "#F9A8D4",
        "text":         "#500724",
        "text2":        "#9D174D",
        "muted":        "#BE185D",
        "accent":       "#DB2777",
        "accent_light": "#FCE7F3",
        "accent2":      "#F472B6",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(219,39,119,.1)",
        "shadow_md":    "0 4px 16px rgba(219,39,119,.18)",
        "input_bg":     "#FFF5F8",
        "hover":        "#FCE7F3",
        "hint_bg":      "#FCE7F3",
        "hint_text":    "#831843",
        "hint_border":  "#F9A8D4",
        "sidebar_bg":     "linear-gradient(180deg, #500724 0%, #3A0519 100%)",
        "sidebar_border": "#9D174D",
        "sidebar_accent": "#F472B6",
    },

    # ── SALVIA ───────────────────────────────────────────────────────────────
    "salvia": {
        "bg":           "#F1F5EE",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#E4EDE0",
        "border":       "#C5D9BC",
        "border2":      "#A0C496",
        "text":         "#1A2E16",
        "text2":        "#2D5228",
        "muted":        "#557A4E",
        "accent":       "#3A7D34",
        "accent_light": "#E4EDE0",
        "accent2":      "#5BA854",
        "success":      "#16A34A",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(58,125,52,.1)",
        "shadow_md":    "0 4px 16px rgba(58,125,52,.18)",
        "input_bg":     "#EFF5EC",
        "hover":        "#E4EDE0",
        "hint_bg":      "#E4EDE0",
        "hint_text":    "#1A4016",
        "hint_border":  "#A0C496",
        "sidebar_bg":     "linear-gradient(180deg, #1A2E16 0%, #0F1D0D 100%)",
        "sidebar_border": "#2D5228",
        "sidebar_accent": "#7EC878",
    },

    # ── AMBRA ────────────────────────────────────────────────────────────────
    "ambra": {
        "bg":           "#FFFBEB",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FEF3C7",
        "border":       "#FDE68A",
        "border2":      "#FCD34D",
        "text":         "#451A03",
        "text2":        "#92400E",
        "muted":        "#B45309",
        "accent":       "#D97706",
        "accent_light": "#FEF3C7",
        "accent2":      "#F59E0B",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(217,119,6,.1)",
        "shadow_md":    "0 4px 16px rgba(217,119,6,.2)",
        "input_bg":     "#FFFCF0",
        "hover":        "#FEF3C7",
        "hint_bg":      "#FEF3C7",
        "hint_text":    "#78350F",
        "hint_border":  "#FCD34D",
        "sidebar_bg":     "linear-gradient(180deg, #451A03 0%, #2D1102 100%)",
        "sidebar_border": "#92400E",
        "sidebar_accent": "#FCD34D",
    },

    # ── SMERALDO ─────────────────────────────────────────────────────────────
    "smeraldo": {
        "bg":           "#ECFDF5",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#CCFBF1",
        "border":       "#99F6E4",
        "border2":      "#5EEAD4",
        "text":         "#042F2E",
        "text2":        "#0F766E",
        "muted":        "#0D9488",
        "accent":       "#0F766E",
        "accent_light": "#CCFBF1",
        "accent2":      "#14B8A6",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(15,118,110,.1)",
        "shadow_md":    "0 4px 16px rgba(15,118,110,.18)",
        "input_bg":     "#F0FDF9",
        "hover":        "#CCFBF1",
        "hint_bg":      "#CCFBF1",
        "hint_text":    "#134E4A",
        "hint_border":  "#5EEAD4",
        "sidebar_bg":     "linear-gradient(180deg, #042F2E 0%, #021E1D 100%)",
        "sidebar_border": "#0F766E",
        "sidebar_accent": "#2DD4BF",
    },

    # ── MATTONE ──────────────────────────────────────────────────────────────
    "mattone": {
        "bg":           "#FEF2F0",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FCE4E0",
        "border":       "#F8C5BE",
        "border2":      "#F4A49A",
        "text":         "#420E08",
        "text2":        "#9B2335",
        "muted":        "#B45063",
        "accent":       "#C0392B",
        "accent_light": "#FCE4E0",
        "accent2":      "#E74C3C",
        "success":      "#27AE60",
        "warn":         "#F39C12",
        "err":          "#C0392B",
        "shadow":       "0 1px 3px rgba(192,57,43,.1)",
        "shadow_md":    "0 4px 16px rgba(192,57,43,.18)",
        "input_bg":     "#FEF5F4",
        "hover":        "#FCE4E0",
        "hint_bg":      "#FCE4E0",
        "hint_text":    "#6B0F1A",
        "hint_border":  "#F4A49A",
        "sidebar_bg":     "linear-gradient(180deg, #420E08 0%, #2B0905 100%)",
        "sidebar_border": "#7F1D1D",
        "sidebar_accent": "#F4A49A",
    },

    # ── GHIACCIO ─────────────────────────────────────────────────────────────
    "ghiaccio": {
        "bg":           "#F0F9FF",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#E0F2FE",
        "border":       "#BAE6FD",
        "border2":      "#7DD3FC",
        "text":         "#0C2340",
        "text2":        "#0369A1",
        "muted":        "#0284C7",
        "accent":       "#0369A1",
        "accent_light": "#E0F2FE",
        "accent2":      "#38BDF8",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(3,105,161,.1)",
        "shadow_md":    "0 4px 16px rgba(3,105,161,.18)",
        "input_bg":     "#F5FCFF",
        "hover":        "#E0F2FE",
        "hint_bg":      "#E0F2FE",
        "hint_text":    "#075985",
        "hint_border":  "#7DD3FC",
        "sidebar_bg":     "linear-gradient(180deg, #0C2340 0%, #071828 100%)",
        "sidebar_border": "#0369A1",
        "sidebar_accent": "#38BDF8",
    },

    # ── INDACO ───────────────────────────────────────────────────────────────
    "indaco": {
        "bg":           "#EEF2FF",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#E0E7FF",
        "border":       "#C7D2FE",
        "border2":      "#A5B4FC",
        "text":         "#1E1B4B",
        "text2":        "#3730A3",
        "muted":        "#4F46E5",
        "accent":       "#4338CA",
        "accent_light": "#E0E7FF",
        "accent2":      "#818CF8",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(67,56,202,.1)",
        "shadow_md":    "0 4px 16px rgba(67,56,202,.18)",
        "input_bg":     "#F5F7FF",
        "hover":        "#E0E7FF",
        "hint_bg":      "#E0E7FF",
        "hint_text":    "#312E81",
        "hint_border":  "#A5B4FC",
        "sidebar_bg":     "linear-gradient(180deg, #1E1B4B 0%, #130F35 100%)",
        "sidebar_border": "#3730A3",
        "sidebar_accent": "#818CF8",
    },

    # ── CORALLO ──────────────────────────────────────────────────────────────
    "corallo": {
        "bg":           "#FFF5F3",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FFE8E3",
        "border":       "#FECACA",
        "border2":      "#FDA4AF",
        "text":         "#4C0519",
        "text2":        "#BE123C",
        "muted":        "#E11D48",
        "accent":       "#E11D48",
        "accent_light": "#FFE8E3",
        "accent2":      "#FB7185",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(225,29,72,.1)",
        "shadow_md":    "0 4px 16px rgba(225,29,72,.18)",
        "input_bg":     "#FFF8F7",
        "hover":        "#FFE8E3",
        "hint_bg":      "#FFE8E3",
        "hint_text":    "#881337",
        "hint_border":  "#FDA4AF",
        "sidebar_bg":     "linear-gradient(180deg, #4C0519 0%, #360312 100%)",
        "sidebar_border": "#9F1239",
        "sidebar_accent": "#FB7185",
    },

    # ── GRAFITE ──────────────────────────────────────────────────────────────
    "grafite": {
        "bg":           "#F8F7F5",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#F0EDE8",
        "border":       "#D9D4CC",
        "border2":      "#C2BBB0",
        "text":         "#1C1917",
        "text2":        "#44403C",
        "muted":        "#78716C",
        "accent":       "#57534E",
        "accent_light": "#F0EDE8",
        "accent2":      "#A8A29E",
        "success":      "#16A34A",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(87,83,78,.1)",
        "shadow_md":    "0 4px 12px rgba(87,83,78,.15)",
        "input_bg":     "#F5F3F0",
        "hover":        "#F0EDE8",
        "hint_bg":      "#F0EDE8",
        "hint_text":    "#292524",
        "hint_border":  "#C2BBB0",
        "sidebar_bg":     "linear-gradient(180deg, #1C1917 0%, #0C0A09 100%)",
        "sidebar_border": "#44403C",
        "sidebar_accent": "#D6D3D1",
    },

    # ── TURCHESE ─────────────────────────────────────────────────────────────
    "turchese": {
        "bg":           "#ECFDFD",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#CFFAFE",
        "border":       "#A5F3FC",
        "border2":      "#67E8F9",
        "text":         "#083344",
        "text2":        "#0E7490",
        "muted":        "#0891B2",
        "accent":       "#0E7490",
        "accent_light": "#CFFAFE",
        "accent2":      "#22D3EE",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(14,116,144,.1)",
        "shadow_md":    "0 4px 16px rgba(14,116,144,.18)",
        "input_bg":     "#F0FEFF",
        "hover":        "#CFFAFE",
        "hint_bg":      "#CFFAFE",
        "hint_text":    "#164E63",
        "hint_border":  "#67E8F9",
        "sidebar_bg":     "linear-gradient(180deg, #083344 0%, #05202B 100%)",
        "sidebar_border": "#0E7490",
        "sidebar_accent": "#22D3EE",
    },

    # ── CILIEGIO ─────────────────────────────────────────────────────────────
    "ciliegio": {
        "bg":           "#FFF5F5",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FFE4E4",
        "border":       "#FFC2C2",
        "border2":      "#FFA0A0",
        "text":         "#3D0000",
        "text2":        "#8B0000",
        "muted":        "#B22222",
        "accent":       "#9B0000",
        "accent_light": "#FFE4E4",
        "accent2":      "#DC143C",
        "success":      "#2E7D32",
        "warn":         "#D97706",
        "err":          "#C62828",
        "shadow":       "0 1px 3px rgba(155,0,0,.1)",
        "shadow_md":    "0 4px 16px rgba(155,0,0,.18)",
        "input_bg":     "#FFF8F8",
        "hover":        "#FFE4E4",
        "hint_bg":      "#FFE4E4",
        "hint_text":    "#5D0000",
        "hint_border":  "#FFA0A0",
        "sidebar_bg":     "linear-gradient(180deg, #3D0000 0%, #260000 100%)",
        "sidebar_border": "#8B0000",
        "sidebar_accent": "#FF6B6B",
    },

    # ── FORESTA ──────────────────────────────────────────────────────────────
    "foresta": {
        "bg":           "#F1F8F2",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#DCF0DF",
        "border":       "#BBE0C0",
        "border2":      "#93CCA0",
        "text":         "#0C2210",
        "text2":        "#1B5E20",
        "muted":        "#388E3C",
        "accent":       "#2E7D32",
        "accent_light": "#DCF0DF",
        "accent2":      "#4CAF50",
        "success":      "#2E7D32",
        "warn":         "#E65100",
        "err":          "#C62828",
        "shadow":       "0 1px 3px rgba(46,125,50,.1)",
        "shadow_md":    "0 4px 16px rgba(46,125,50,.18)",
        "input_bg":     "#F5FAF6",
        "hover":        "#DCF0DF",
        "hint_bg":      "#DCF0DF",
        "hint_text":    "#0C2210",
        "hint_border":  "#93CCA0",
        "sidebar_bg":     "linear-gradient(180deg, #0C2210 0%, #081508 100%)",
        "sidebar_border": "#1B5E20",
        "sidebar_accent": "#81C784",
    },

    # ── GIRASOLE ─────────────────────────────────────────────────────────────
    "girasole": {
        "bg":           "#FFFDE7",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FFF9C4",
        "border":       "#FFF176",
        "border2":      "#FFEE58",
        "text":         "#33280A",
        "text2":        "#F57F17",
        "muted":        "#F9A825",
        "accent":       "#F57F17",
        "accent_light": "#FFF9C4",
        "accent2":      "#FFCA28",
        "success":      "#388E3C",
        "warn":         "#EF6C00",
        "err":          "#D32F2F",
        "shadow":       "0 1px 3px rgba(245,127,23,.12)",
        "shadow_md":    "0 4px 16px rgba(245,127,23,.2)",
        "input_bg":     "#FFFEF5",
        "hover":        "#FFF9C4",
        "hint_bg":      "#FFF9C4",
        "hint_text":    "#4E2C00",
        "hint_border":  "#FFEE58",
        "sidebar_bg":     "linear-gradient(180deg, #33280A 0%, #201905 100%)",
        "sidebar_border": "#F57F17",
        "sidebar_accent": "#FFCA28",
    },

    # ── NEBBIA ───────────────────────────────────────────────────────────────
    "nebbia": {
        "bg":           "#F7F8FA",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#EAEEF3",
        "border":       "#CDD5E0",
        "border2":      "#B0BDCe",
        "text":         "#1A2330",
        "text2":        "#374151",
        "muted":        "#6B7280",
        "accent":       "#374151",
        "accent_light": "#EAEEF3",
        "accent2":      "#9CA3AF",
        "success":      "#16A34A",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(0,0,0,.08)",
        "shadow_md":    "0 4px 12px rgba(0,0,0,.12)",
        "input_bg":     "#F3F5F8",
        "hover":        "#EAEEF3",
        "hint_bg":      "#EAEEF3",
        "hint_text":    "#374151",
        "hint_border":  "#B0BDCe",
        "sidebar_bg":     "linear-gradient(180deg, #1A2330 0%, #111820 100%)",
        "sidebar_border": "#374151",
        "sidebar_accent": "#9CA3AF",
    },

    # ── PAPAVERO ─────────────────────────────────────────────────────────────
    "papavero": {
        "bg":           "#FFF3F3",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#FFE0E0",
        "border":       "#FFBCBC",
        "border2":      "#FF9494",
        "text":         "#3B0000",
        "text2":        "#7F0000",
        "muted":        "#CC0000",
        "accent":       "#CC0000",
        "accent_light": "#FFE0E0",
        "accent2":      "#FF4444",
        "success":      "#2E7D32",
        "warn":         "#E65100",
        "err":          "#B71C1C",
        "shadow":       "0 1px 3px rgba(204,0,0,.1)",
        "shadow_md":    "0 4px 16px rgba(204,0,0,.18)",
        "input_bg":     "#FFF8F8",
        "hover":        "#FFE0E0",
        "hint_bg":      "#FFE0E0",
        "hint_text":    "#5C0000",
        "hint_border":  "#FF9494",
        "sidebar_bg":     "linear-gradient(180deg, #3B0000 0%, #250000 100%)",
        "sidebar_border": "#7F0000",
        "sidebar_accent": "#FF6666",
    },

    # ── CREPUSCOLO ───────────────────────────────────────────────────────────
    "crepuscolo": {
        "bg":           "#F5F0FF",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#EAE0FF",
        "border":       "#D8C8F8",
        "border2":      "#C4ACEF",
        "text":         "#200040",
        "text2":        "#6D28D9",
        "muted":        "#7C3AED",
        "accent":       "#7C3AED",
        "accent_light": "#EAE0FF",
        "accent2":      "#A855F7",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(124,58,237,.1)",
        "shadow_md":    "0 4px 16px rgba(124,58,237,.2)",
        "input_bg":     "#F9F5FF",
        "hover":        "#EAE0FF",
        "hint_bg":      "#EAE0FF",
        "hint_text":    "#4C1D95",
        "hint_border":  "#C4ACEF",
        "sidebar_bg":     "linear-gradient(180deg, #200040 0%, #15002A 100%)",
        "sidebar_border": "#6D28D9",
        "sidebar_accent": "#C084FC",
    },
}

# ── Etichette leggibili per il menu a tendina ──────────────────────────────────
THEME_LABELS = {
    "chiaro":       "☀️  Chiaro (Blu Artico)",
    "slate_carbon": "🌙  Scuro (Slate Carbon)",
    "lavanda":      "💜  Lavanda",
    "menta":        "🌿  Menta",
    "pesca":        "🍑  Pesca",
    "oceano":       "🌊  Oceano",
    "rosa":         "🌸  Rosa",
    "salvia":       "🌾  Salvia",
    "ambra":        "✨  Ambra",
    "smeraldo":     "💎  Smeraldo",
    "mattone":      "🧱  Mattone",
    "ghiaccio":     "❄️  Ghiaccio",
    "indaco":       "🫐  Indaco",
    "corallo":      "🪸  Corallo",
    "grafite":      "🪨  Grafite",
    "turchese":     "🐬  Turchese",
    "ciliegio":     "🍒  Ciliegio",
    "foresta":      "🌲  Foresta",
    "girasole":     "🌻  Girasole",
    "nebbia":       "☁️  Nebbia",
    "papavero":     "🌺  Papavero",
    "crepuscolo":   "🌇  Crepuscolo",
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
