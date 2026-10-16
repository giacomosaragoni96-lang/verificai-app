"""
strumenti/schermate.py — scatta le schermate chiave dell'app in locale (solo per lo sviluppo, non fa parte dell'app).

Uso (con l'app già avviata, es. `streamlit run main.py --server.port 8501`, e playwright installato in locale):
    python strumenti/schermate.py http://localhost:8501 uscita/ [larghezza ...]
Salva una PNG per ogni larghezza (di default 1300 e 390 px): servono a confrontare a occhio il prima e il dopo di una modifica di stile,
soprattutto per le sovrapposizioni su telefono. Non installa niente e non è importato da nessun file dell'app.
"""
import os
import sys

from playwright.sync_api import sync_playwright


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
    cartella = sys.argv[2] if len(sys.argv) > 2 else "schermate_uscita"
    larghezze = [int(x) for x in sys.argv[3:]] or [1300, 390]
    os.makedirs(cartella, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for w in larghezze:
            pg = b.new_page(viewport={"width": w, "height": 900})
            pg.goto(url, wait_until="domcontentloaded")
            pg.wait_for_selector('[data-testid="stApp"]', timeout=60000)
            pg.wait_for_timeout(8000)
            pg.screenshot(path=os.path.join(cartella, f"home_{w}.png"), full_page=True)
            pg.close()
        b.close()
    print("fatto:", cartella)


if __name__ == "__main__":
    main()
