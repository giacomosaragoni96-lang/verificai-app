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

    # ═══════════════════════════════════════════════════════════════════════
    #  OSSIDIANA — Deep Indigo Slate  (professional, Figma-dark inspired)
    #  Palette: Blue-slate bg · Indigo 500 accent · cool near-white text
    # ═══════════════════════════════════════════════════════════════════════
    "ossidiana": {
        "bg":         "#0D0E14",
        "bg2":        "#13141C",
        "card":       "#1A1B26",
        "card2":      "#21222E",
        "text":       "#E8E9F0",
        "text2":      "#8B8FA8",
        "muted":      "#5C6080",
        "border":     "#25273A",
        "border2":    "#32344E",
        "accent":       "#6366F1",
        "accent2":      "#818CF8",
        "accent_light": "#1A1B38",
        "hover":      "#1C1D2A",
        "success":    "#34D399",
        "warn":       "#FBBF24",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(13,14,20,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #09090F 0%, #0D0E14 100%)",
        "sidebar_border":   "#25273A",
        "sidebar_accent":   "#818CF8",
        "sidebar_input_bg":  "#13141C",
        "sidebar_input_text": "#E8E9F0",
        "hint_bg":      "#1A1B38",
        "hint_border":  "#3A3D7A",
        "hint_text":    "#818CF8",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  RAME — Warm Copper Editorial  (espresso bg · copper accent · cream text)
    # ═══════════════════════════════════════════════════════════════════════
    "rame": {
        "bg":         "#0C0A08",
        "bg2":        "#151210",
        "card":       "#1E1916",
        "card2":      "#262118",
        "text":       "#F5EDE6",
        "text2":      "#B09880",
        "muted":      "#7A6655",
        "border":     "#352A22",
        "border2":    "#4A3A2E",
        "accent":       "#C87C3C",
        "accent2":      "#E09550",
        "accent_light": "#2A1A08",
        "hover":      "#1C1510",
        "success":    "#4ADE80",
        "warn":       "#EAA030",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(12,10,8,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #060402 0%, #0C0A08 100%)",
        "sidebar_border":   "#352A22",
        "sidebar_accent":   "#E09550",
        "sidebar_input_bg":  "#151210",
        "sidebar_input_text": "#F5EDE6",
        "hint_bg":      "#2A1A08",
        "hint_border":  "#6A3C10",
        "hint_text":    "#E09550",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  AURORA — Northern Lights  (night blue bg · teal accent · blue-white text)
    # ═══════════════════════════════════════════════════════════════════════
    "aurora": {
        "bg":         "#08090F",
        "bg2":        "#0E1018",
        "card":       "#141622",
        "card2":      "#1A1E2C",
        "text":       "#E4EAF5",
        "text2":      "#7A90B8",
        "muted":      "#4A5C80",
        "border":     "#1E2438",
        "border2":    "#28304A",
        "accent":       "#2DD4BF",
        "accent2":      "#5EEAD4",
        "accent_light": "#0A201E",
        "hover":      "#141826",
        "success":    "#34D399",
        "warn":       "#FBBF24",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(8,9,15,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #040407 0%, #08090F 100%)",
        "sidebar_border":   "#1E2438",
        "sidebar_accent":   "#5EEAD4",
        "sidebar_input_bg":  "#0E1018",
        "sidebar_input_text": "#E4EAF5",
        "hint_bg":      "#0A201E",
        "hint_border":  "#1A504A",
        "hint_text":    "#2DD4BF",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  ARDESIA — Warm Rose Slate  (dark slate bg · rose accent · warm white text)
    # ═══════════════════════════════════════════════════════════════════════
    "ardesia": {
        "bg":         "#100E0E",
        "bg2":        "#181515",
        "card":       "#201C1C",
        "card2":      "#282222",
        "text":       "#F0EAEA",
        "text2":      "#A89090",
        "muted":      "#6A5858",
        "border":     "#2E2828",
        "border2":    "#3E3434",
        "accent":       "#FB7185",
        "accent2":      "#FDA4AF",
        "accent_light": "#2A0E14",
        "hover":      "#1C1818",
        "success":    "#34D399",
        "warn":       "#FBBF24",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(16,14,14,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #080606 0%, #100E0E 100%)",
        "sidebar_border":   "#2E2828",
        "sidebar_accent":   "#FDA4AF",
        "sidebar_input_bg":  "#181515",
        "sidebar_input_text": "#F0EAEA",
        "hint_bg":      "#2A0E14",
        "hint_border":  "#6A2030",
        "hint_text":    "#FDA4AF",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  AMETISTA — Soft Violet  (deep purple bg · amethyst accent · lavender text)
    # ═══════════════════════════════════════════════════════════════════════
    "ametista": {
        "bg":         "#0C0B12",
        "bg2":        "#131120",
        "card":       "#1A1830",
        "card2":      "#22203E",
        "text":       "#EEEAF8",
        "text2":      "#9990C0",
        "muted":      "#5E5888",
        "border":     "#242045",
        "border2":    "#302C5E",
        "accent":       "#A78BFA",
        "accent2":      "#C4B5FD",
        "accent_light": "#1E1640",
        "hover":      "#18163A",
        "success":    "#34D399",
        "warn":       "#FBBF24",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(12,11,18,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #060510 0%, #0C0B12 100%)",
        "sidebar_border":   "#242045",
        "sidebar_accent":   "#C4B5FD",
        "sidebar_input_bg":  "#131120",
        "sidebar_input_text": "#EEEAF8",
        "hint_bg":      "#1E1640",
        "hint_border":  "#453A80",
        "hint_text":    "#C4B5FD",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  GHIACCIO — Arctic Sky  (dark navy bg · sky-blue accent · cool white text)
    # ═══════════════════════════════════════════════════════════════════════
    "ghiaccio": {
        "bg":         "#080C14",
        "bg2":        "#0E1420",
        "card":       "#141E30",
        "card2":      "#1A2640",
        "text":       "#E0EAF8",
        "text2":      "#7098C8",
        "muted":      "#3D6090",
        "border":     "#1C2C44",
        "border2":    "#263A58",
        "accent":       "#38BDF8",
        "accent2":      "#7DD3FC",
        "accent_light": "#082040",
        "hover":      "#121A2C",
        "success":    "#34D399",
        "warn":       "#FBBF24",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(8,12,20,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #040709 0%, #080C14 100%)",
        "sidebar_border":   "#1C2C44",
        "sidebar_accent":   "#7DD3FC",
        "sidebar_input_bg":  "#0E1420",
        "sidebar_input_text": "#E0EAF8",
        "hint_bg":      "#082040",
        "hint_border":  "#1A4070",
        "hint_text":    "#38BDF8",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  PETROLIO — Teal & Amber  (dark teal bg · amber accent · pale teal text)
    # ═══════════════════════════════════════════════════════════════════════
    "petrolio": {
        "bg":         "#060F0E",
        "bg2":        "#0A1816",
        "card":       "#0E2220",
        "card2":      "#122C28",
        "text":       "#E8F5EE",
        "text2":      "#70A890",
        "muted":      "#3A7060",
        "border":     "#0E3030",
        "border2":    "#154040",
        "accent":       "#F59E0B",
        "accent2":      "#FCD34D",
        "accent_light": "#2A1E00",
        "hover":      "#0A1E1C",
        "success":    "#34D399",
        "warn":       "#FB923C",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(6,15,14,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #030907 0%, #060F0E 100%)",
        "sidebar_border":   "#0E3030",
        "sidebar_accent":   "#FCD34D",
        "sidebar_input_bg":  "#0A1816",
        "sidebar_input_text": "#E8F5EE",
        "hint_bg":      "#2A1E00",
        "hint_border":  "#6A4A00",
        "hint_text":    "#F59E0B",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CENERE — Ash Lavender  (neutral dark-gray bg · soft lilac accent · near-white)
    # ═══════════════════════════════════════════════════════════════════════
    "cenere": {
        "bg":         "#0E0E10",
        "bg2":        "#161618",
        "card":       "#1E1E22",
        "card2":      "#24242A",
        "text":       "#EAEAEE",
        "text2":      "#8888A0",
        "muted":      "#555568",
        "border":     "#28283C",
        "border2":    "#343450",
        "accent":       "#C4B5FD",
        "accent2":      "#DDD6FE",
        "accent_light": "#1A1830",
        "hover":      "#1C1C22",
        "success":    "#34D399",
        "warn":       "#FBBF24",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(14,14,16,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #08080A 0%, #0E0E10 100%)",
        "sidebar_border":   "#28283C",
        "sidebar_accent":   "#DDD6FE",
        "sidebar_input_bg":  "#161618",
        "sidebar_input_text": "#EAEAEE",
        "hint_bg":      "#1A1830",
        "hint_border":  "#383870",
        "hint_text":    "#C4B5FD",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  MOGANO — Mahogany  (deep warm-brown bg · amber gold accent · cream text)
    # ═══════════════════════════════════════════════════════════════════════
    "mogano": {
        "bg":         "#0D0906",
        "bg2":        "#160E09",
        "card":       "#1E1510",
        "card2":      "#261B14",
        "text":       "#F5EDDE",
        "text2":      "#C0986A",
        "muted":      "#7A5E3C",
        "border":     "#32200C",
        "border2":    "#462C10",
        "accent":       "#F59E0B",
        "accent2":      "#FBB03B",
        "accent_light": "#2A1600",
        "hover":      "#18120A",
        "success":    "#4ADE80",
        "warn":       "#FB923C",
        "error":      "#EF4444",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(13,9,6,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #060402 0%, #0D0906 100%)",
        "sidebar_border":   "#32200C",
        "sidebar_accent":   "#FBB03B",
        "sidebar_input_bg":  "#160E09",
        "sidebar_input_text": "#F5EDDE",
        "hint_bg":      "#2A1600",
        "hint_border":  "#6A3E00",
        "hint_text":    "#FBB03B",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CARBONE — Carbon Blue  (near-black neutral bg · sky-blue accent · cool white)
    # ═══════════════════════════════════════════════════════════════════════
    "carbone": {
        "bg":         "#0A0A0C",
        "bg2":        "#111114",
        "card":       "#18181E",
        "card2":      "#1E1E26",
        "text":       "#E8E9EE",
        "text2":      "#8A90A8",
        "muted":      "#585E78",
        "border":     "#22242E",
        "border2":    "#2E3040",
        "accent":       "#0EA5E9",
        "accent2":      "#38BDF8",
        "accent_light": "#061828",
        "hover":      "#161620",
        "success":    "#34D399",
        "warn":       "#FBBF24",
        "error":      "#F87171",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(10,10,12,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #050506 0%, #0A0A0C 100%)",
        "sidebar_border":   "#22242E",
        "sidebar_accent":   "#38BDF8",
        "sidebar_input_bg":  "#111114",
        "sidebar_input_text": "#E8E9EE",
        "hint_bg":      "#061828",
        "hint_border":  "#0C3A5A",
        "hint_text":    "#0EA5E9",
    },
}

THEME_LABELS = {
    "notte":     "🌙 Notte",
    "chiaro":    "☀️ Giorno",
    "foresta":   "🌿 Foresta",
    "ossidiana": "🔮 Ossidiana",
    "rame":      "🟤 Rame",
    "aurora":    "✨ Aurora",
    "ardesia":   "🌹 Ardesia",
    "ametista":  "💜 Ametista",
    "ghiaccio":  "❄️ Ghiaccio",
    "petrolio":  "🌿 Petrolio",
    "cenere":    "🌫️ Cenere",
    "mogano":    "🪵 Mogano",
    "carbone":   "⚫ Carbone",
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
