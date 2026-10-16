"""
docx_import.py — legge un file Word (.docx) per «Impagina la mia verifica» (senza Streamlit).

Pandoc converte il documento in LaTeX (le equazioni di Word diventano formule) ed estrae le immagini incluse. Il modello riceve il TESTO
(con segnaposto [[IMMAGINE n]] dove stava ogni immagine) più le immagini nello stesso ordine: così le figure si possono ritagliare come
quelle di una foto (l'immagine intera = pagina n). Serve `pandoc` (già in packages.txt). Qualsiasi problema = None: il file si rifiuta con un messaggio.
"""
import io
import os
import re
import shutil
import subprocess
import tempfile

MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_BYTE = 15 * 1024 * 1024
MAX_IMMAGINI = 12
MAX_TESTO = 40_000


def e_docx(f: dict) -> bool:
    nome = (f.get("name") or "").lower()
    return (f.get("mime_type") or "") == MIME_DOCX or nome.endswith(".docx")


def disponibile() -> bool:
    return shutil.which("pandoc") is not None


def _png(dati: bytes):
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(dati))
        im.load()
        im = im.convert("RGB")
        if max(im.size) > 1600:
            k = 1600 / max(im.size)
            im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
        b = io.BytesIO()
        im.save(b, "PNG", optimize=True)
        return b.getvalue()
    except Exception:
        return None


def leggi_docx(dati: bytes):
    """{"testo": str, "immagini": [PNG]} dal file Word, oppure None se non si riesce (pandoc assente, file rovinato, vuoto)."""
    if not dati or len(dati) > MAX_BYTE or not disponibile():
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "v.docx")
            with open(src, "wb") as f:
                f.write(dati)
            r = subprocess.run(["pandoc", src, "-t", "latex", "--wrap=none", "--extract-media=" + os.path.join(tmp, "m")],
                               capture_output=True, text=True, timeout=60, cwd=tmp)
            if r.returncode != 0 or not r.stdout.strip():
                return None
            tex = r.stdout
            immagini, ordine = [], {}

            def _sost(m):
                perc = m.group(1)
                if perc not in ordine:
                    p = perc if os.path.isabs(perc) else os.path.join(tmp, perc)
                    png = _png(open(p, "rb").read()) if os.path.exists(p) else None     # emf/wmf e simili: non leggibili, si saltano
                    if png is None or len(immagini) >= MAX_IMMAGINI:
                        ordine[perc] = None
                    else:
                        immagini.append(png)
                        ordine[perc] = len(immagini)
                n = ordine[perc]
                return f"\n[[IMMAGINE {n}]]\n" if n else "\n"
            tex = re.sub(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", _sost, tex)
            tex = re.sub(r"\\(?:pandocbounded|tightlist|noindent)\b\{?", "", tex)
            tex = re.sub(r"\n{3,}", "\n\n", tex).strip()
            if len(tex) < 20:
                return None
            return {"testo": tex[:MAX_TESTO], "immagini": immagini}
    except Exception:
        return None


def espandi_file(immagini: list) -> list:
    """
    I file caricati come elenco di «parti» per il modello e per il ritaglio: immagini e PDF restano come sono; ogni .docx diventa una parte di testo
    ({"testo": …}) seguita dalle sue immagini ({"data", "mime_type": "image/png"}), nell'ordine in cui compaiono.
    """
    out = []
    for f in immagini or []:
        if e_docx(f):
            r = leggi_docx(f.get("data") or b"")
            if r is None:
                continue
            out.append({"testo": "FILE WORD (testo estratto; le formule sono in LaTeX; [[IMMAGINE n]] segna dove sta l'immagine n, "
                                 "numerate da 1 in ordine tra le immagini che seguono):\n" + r["testo"]})
            out += [{"data": p, "mime_type": "image/png", "name": f"immagine{k}.png"} for k, p in enumerate(r["immagini"], 1)]
        else:
            out.append(f)
    return out
