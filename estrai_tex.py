"""
estrai_tex.py — legge il codice LaTeX di schede e verifiche e ne ricava esercizi e struttura.

Nessuna AI, nessun import di streamlit: testo in ingresso, dati in uscita (testabile da solo).
Riconosce tre tipi di file:
  • VERIFICA: \\subsection*{Esercizio N} + elenco con \\item; opzioni con \\scelte{}{}{} o
    \\opzioni{}{}{}{}; (*) = facoltativo; punti dalla riga "Max" della tabella finale.
  • SCHEDA:   \\section*{Livello N -- titolo} con esercizi \\es{...} o \\item.
  • APPUNTI:  teoria con riquadri (tcolorbox), esempi svolti, esercizi: non hanno una struttura fissa,
              vanno letti con l'AI (importa_esercizi.py lo fa passando il sorgente LaTeX).
"""
import re

_ENV = r"(?:enumerate|itemize)"


# ── utilità sul testo LaTeX ───────────────────────────────────────────────────

def corpo_documento(tex: str) -> str:
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", tex, re.DOTALL)
    return m.group(1) if m else tex


def togli_commenti(tex: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", tex)


def leggi_gruppo(testo: str, pos: int):
    """Da testo[pos] == '{' restituisce (contenuto, posizione dopo la '}') con graffe bilanciate."""
    livello = 0
    for i in range(pos, len(testo)):
        c = testo[i]
        if c == "{" and (i == 0 or testo[i - 1] != "\\"):
            livello += 1
        elif c == "}" and testo[i - 1] != "\\":
            livello -= 1
            if livello == 0:
                return testo[pos + 1:i], i + 1
    return testo[pos + 1:], len(testo)


def argomenti_macro(testo: str, nome: str, n: int) -> list:
    """Trova \\nome{..}{..} con n gruppi e restituisce [(inizio, fine, [gruppi])]."""
    trovati = []
    for m in re.finditer(r"\\" + nome + r"(?![A-Za-z])", testo):
        pos, gruppi = m.end(), []
        for _ in range(n):
            while pos < len(testo) and testo[pos] in " \n\t":
                pos += 1
            if pos >= len(testo) or testo[pos] != "{":
                break
            g, pos = leggi_gruppo(testo, pos)
            gruppi.append(g.strip())
        if len(gruppi) == n:
            trovati.append((m.start(), pos, gruppi))
    return trovati


def pulisci(testo: str) -> str:
    """Testo di un esercizio: spazi e righe vuote ripuliti, formule intatte."""
    testo = re.sub(r"\\vspace\*?\{[^}]*\}|\\vfill|\\newpage|\\bigskip|\\medskip|\\smallskip", "", testo)
    testo = re.sub(r"[ \t]+\n", "\n", testo)
    testo = re.sub(r"\n{2,}", "\n", testo)
    return testo.strip()


def _senza_comandi(latex: str) -> str:
    t = re.sub(r"\\textbf\{([^}]*)\}|\\textit\{([^}]*)\}|\\emph\{([^}]*)\}",
               lambda m: m.group(1) or m.group(2) or m.group(3) or "", latex)
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", "", t)
    return re.sub(r"[{}]", "", t)


def solo_testo(latex: str) -> str:
    """Versione leggibile (senza comandi) per titoli e consegne. Le formule $...$ restano intatte."""
    pezzi = re.split(r"(\$[^$]*\$)", latex)
    return "".join(p if p.startswith("$") else _senza_comandi(p) for p in pezzi).strip()


# ── elenchi (enumerate / itemize) ─────────────────────────────────────────────

def trova_elenco(testo: str, da: int = 0):
    """Primo elenco di livello alto: (inizio, fine, opzioni, interno, ambiente) oppure None."""
    m = re.search(r"\\begin\{(" + _ENV + r")\}(\[[^\]]*\])?", testo[da:])
    if not m:
        return None
    inizio = da + m.start()
    livello = 0
    for t in re.finditer(r"\\begin\{" + _ENV + r"\}|\\end\{" + _ENV + r"\}", testo[inizio:]):
        livello += 1 if t.group(0).startswith("\\begin") else -1
        if livello == 0:
            interno = testo[da + m.end():inizio + t.start()]
            return inizio, inizio + t.end(), m.group(2) or "", interno, m.group(1)
    return None


def tutti_gli_elenchi(testo: str) -> list:
    """Tutti gli elenchi di primo livello di un blocco."""
    elenchi, pos = [], 0
    while True:
        e = trova_elenco(testo, pos)
        if not e:
            return elenchi
        elenchi.append(e)
        pos = e[1]


def dividi_item(interno: str) -> list:
    """Spezza il contenuto di un elenco sugli \\item di primo livello."""
    pezzi, livello, inizio = [], 0, None
    for t in re.finditer(r"\\begin\{" + _ENV + r"\}|\\end\{" + _ENV + r"\}|\\item(?![A-Za-z])", interno):
        s = t.group(0)
        if s.startswith("\\begin"):
            livello += 1
        elif s.startswith("\\end"):
            livello -= 1
        elif livello == 0:
            if inizio is not None:
                pezzi.append(interno[inizio:t.start()])
            inizio = t.end()
    if inizio is not None:
        pezzi.append(interno[inizio:])
    return pezzi


def etichette_elenco(opzioni: str, n: int) -> list:
    """a) b) c) / i. ii. iii. / 1. 2. 3. a seconda di [label=...]."""
    o = opzioni.lower()
    romani = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv"]
    m = re.search(r"label\s*=\s*(.*?)(?:,|\]|$)", o)
    stile = m.group(1) if m else ""
    chiusura = ")" if ")" in stile else ("." if "." in stile else ")")
    if "\\roman" in stile:
        return [(romani[i] if i < len(romani) else str(i + 1)) + chiusura for i in range(n)]
    if "\\arabic" in stile:
        return [str(i + 1) + chiusura for i in range(n)]
    if "\\alph" in stile or not stile:
        return [chr(97 + i) + ")" for i in range(n)]
    return [str(i + 1) + chiusura for i in range(n)]


# ── quesiti ───────────────────────────────────────────────────────────────────

def _quesito(testo_item: str, etichetta: str) -> dict:
    opzioni = []
    for nome, n in (("scelte", 3), ("opzioni", 4)):
        trovate = argomenti_macro(testo_item, nome, n)
        if trovate:
            a, b, gruppi = trovate[0]
            opzioni = list(gruppi)
            testo_item = testo_item[:a] + testo_item[b:]
            break
    testo = pulisci(testo_item)
    marca = re.compile(r"^\(\s*\\?\*\s*\)\s*|^\(\\textbf\{\*\}\)\s*")
    facoltativo = bool(marca.match(testo))
    testo = marca.sub("", testo)
    return {"etichetta": etichetta, "testo_latex": testo, "opzioni": opzioni, "facoltativo": facoltativo}


def _tipo_sezione(quesiti: list) -> str:
    con_opzioni = sum(1 for q in quesiti if q["opzioni"])
    if con_opzioni == len(quesiti):
        return "scelta_multipla"
    return "misto" if con_opzioni else "aperto"


def _punti_da_tabella(corpo: str):
    """Valori della riga 'Max' della tabella finale: [(punti, con_asterisco), ...] o None."""
    m = re.search(r"\\textbf\{Max\}(.*?)\\\\", corpo, re.DOTALL)
    if not m:
        return None
    valori = []
    for c in (x.strip() for x in m.group(1).split("&")):
        c = re.sub(r"\\textbf\{([^}]*)\}", r"\1", c)
        mm = re.fullmatch(r"(\d+)\s*(\*?)", c)
        if mm:
            valori.append((int(mm.group(1)), bool(mm.group(2))))
    return valori[:-1] if len(valori) >= 2 else None    # l'ultima cella è il totale


# ── lettura di una VERIFICA ───────────────────────────────────────────────────

def leggi_verifica(tex: str) -> dict:
    sorgente = togli_commenti(tex)
    corpo = corpo_documento(sorgente)

    titolo = ""
    m = re.search(r"\\textbf\{([^}]*(?:Verifica|VERIFICA)[^}]*)\}", corpo)
    if m:
        titolo = solo_testo(m.group(1))
    m2 = re.search(r"\\normalsize\s*\\textbf\{(.+?)\}\}", corpo, re.DOTALL)
    argomento_titolo = solo_testo(m2.group(1)) if m2 else ""

    istruzioni = ""
    mi = re.search(r"\\textbf\{Istruzioni:\}(.*?)\}\s*\n", corpo, re.DOTALL)
    if mi:
        istruzioni = solo_testo(mi.group(1))

    parti = re.split(r"\\subsection\*\{([^}]*)\}", corpo)
    if len(parti) > 1:
        blocchi = [(parti[i], parti[i + 1]) for i in range(1, len(parti) - 1, 2)]
    else:
        blocchi = [("Quesiti", corpo)]          # test senza sezioni: un solo elenco

    sezioni = []
    for nome, testo in blocchi:
        nome_pulito = solo_testo(nome)
        facolt_sezione = "*" in nome
        elenchi = tutti_gli_elenchi(testo)
        scelti = [e for e in elenchi if e[4] == "enumerate"] or elenchi[:1]   # i puntati sono consegna
        quesiti = []
        consegna = ""
        if scelti:
            consegna = testo
            for (ini, fin, _o, _i, _a) in reversed(scelti):
                consegna = consegna[:ini] + consegna[fin:]
            for (ini, fin, opz, interno, amb) in scelti:
                item = dividi_item(interno)
                quesiti += [_quesito(it, et) for it, et in zip(item, etichette_elenco(opz, len(item)))]
        else:
            q = _quesito(re.split(r"\\vfill|\\begin\{center\}", testo)[0], "—")
            if q["testo_latex"]:
                quesiti = [q]
        consegna = pulisci(re.split(r"\\vfill|\\begin\{center\}", consegna)[0])
        if facolt_sezione:
            for q in quesiti:
                q["facoltativo"] = True
        if quesiti:
            sezioni.append({"nome": nome_pulito, "consegna": solo_testo(consegna),
                            "tipo": _tipo_sezione(quesiti), "quesiti": quesiti})

    punti = _punti_da_tabella(corpo)
    piatti = [q for s in sezioni for q in s["quesiti"]]
    punti_ok = bool(punti) and len(punti) == len(piatti)
    if punti_ok:
        for q, (p, ast) in zip(piatti, punti):
            q["punti"] = p
            q["facoltativo"] = q["facoltativo"] or ast
    base = sum(q.get("punti", 0) for q in piatti if not q["facoltativo"])
    extra = sum(q.get("punti", 0) for q in piatti if q["facoltativo"])
    m82 = re.search(r"su\s+(\d+)\s+punti", istruzioni)

    return {
        "tipo_file": "verifica", "titolo": titolo, "argomento_titolo": argomento_titolo,
        "istruzioni": istruzioni, "sezioni": sezioni,
        "punti_letti": punti_ok, "punti_base": base, "punti_extra": extra, "totale": base + extra,
        "base_pdp_dsa": int(m82.group(1)) if m82 else None,
        "stile": {
            "scelte_su_colonne": 3 if "\\scelte" in sorgente else (4 if "\\opzioni" in sorgente else 0),
            "logo": "\\includegraphics" in sorgente and "logo" in sorgente,
            "tabella_punteggi": punti is not None,
        },
    }


# ── lettura di una SCHEDA ─────────────────────────────────────────────────────

def leggi_scheda(tex: str) -> dict:
    """Esercizi di una scheda divisa in livelli (\\section*{Livello N -- ...}) con \\es{} o \\item."""
    corpo = corpo_documento(togli_commenti(tex))
    titolo = ""
    m = re.search(r"\\bfseries\s*([^}]*)\}|\\textbf\{([^}]*)\}", corpo)
    if m:
        titolo = solo_testo(m.group(1) or m.group(2) or "")
    parti = re.split(r"\\(?:sub)*section\*?\{([^}]*)\}", corpo)
    esercizi, livelli, numero = [], [], 0
    for i in range(1, len(parti) - 1, 2):
        nome, testo = solo_testo(parti[i]), parti[i + 1]
        mlev = re.match(r"Livello\s+(\d+)", nome, re.IGNORECASE)
        livello = int(mlev.group(1)) if mlev else None
        if livello is not None:
            livelli.append(livello)
        # \es{formula}: macro che mette la formula in un \item matematico → la racchiudo in $...$
        voci = [("$" + g[2][0] + "$") for g in argomenti_macro(testo, "es", 1)]
        if not voci:
            e = trova_elenco(testo)
            if e:
                voci = [v.strip() for v in dividi_item(e[3]) if v.strip()]
        for v in voci:
            numero += 1
            esercizi.append({"numero": str(numero), "testo_latex": pulisci(v),
                             "livello_numero": livello, "titolo_sezione": nome})
    totali = max(livelli) if livelli else None
    for e in esercizi:
        e["livelli_totali"] = totali
    return {"tipo_file": "scheda", "titolo": titolo, "esercizi": esercizi, "livelli_totali": totali}


def leggi_tex(tex: str) -> dict:
    """Sceglie il formato: scheda a livelli, appunti (da leggere con l'AI) o verifica."""
    corpo = corpo_documento(togli_commenti(tex))
    if re.search(r"\\(?:sub)*section\*?\{\s*Livello\s+\d", corpo, re.IGNORECASE) or "\\newcommand{\\es}" in tex:
        return leggi_scheda(tex)
    if ("\\newtcolorbox" in tex or "\\tableofcontents" in corpo or "\\begin{multicols}" in corpo
            or "\\begin{esempio}" in corpo):
        return {"tipo_file": "appunti", "titolo": "", "nota": "appunti o scheda didattica: va letta con l'AI"}
    return leggi_verifica(tex)
