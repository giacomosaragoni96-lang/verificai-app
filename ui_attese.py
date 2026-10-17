"""
ui_attese.py — le schede di attesa: solo interfaccia. Sono i momenti in cui il docente guarda la pagina ferma, quindi devono mostrare che
qualcosa succede: una piccola animazione (pagina che si scrive, foto che si legge, copie che si moltiplicano, matita che corregge), i passi che
si accendono uno dopo l'altro e, per le attese lunghe, un consiglio che cambia ogni pochi secondi.

Due modi di usarle:
- `card_html(T, ..., attivo=N)`: l'HTML con il passo N acceso (quando il codice sa a che punto è: creazione della verifica, impagina);
- `attesa(T, ...)`: un blocco `with` per le attese senza avanzamento reale: i passi si accendono da soli, uno ogni `durata_passo` secondi
  (l'ultimo resta acceso finché il lavoro finisce).
"""
from contextlib import contextmanager
import html

import streamlit as st

_TIPI = ("pagina", "foto", "copie", "matita", "word")

CONSIGLI = [
    "Dopo la verifica puoi creare con un tocco la Fila B, la versione BES/DSA e le soluzioni.",
    "Il logo della tua scuola e lo stile del PDF si impostano una volta sola, in «Impostazioni predefinite».",
    "Con «Più facile» e «Più difficile» cambi un solo esercizio, senza rifare la verifica.",
    "Hai già una verifica scritta male? Caricala e la impagino identica, in pochi minuti.",
    "Puoi fotografare un esercizio del libro: lo riporto identico nella verifica.",
    "Scrivere nella descrizione numero di esercizi, punti e tipo di richieste rende la verifica più vicina a come la vuoi.",
]


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _figura(tipo: str) -> str:
    if tipo == "foto":
        return ('<div class="att-fig att-foto"><i class="c1"></i><i class="c2"></i><i class="c3"></i><i class="c4"></i>'
                '<span class="sole"></span><span class="monte"></span><span class="monte m2"></span><u class="lama-o"></u></div>')
    if tipo == "copie":
        return ('<div class="att-fig att-copie"><div class="p p3"></div><div class="p p2"></div>'
                '<div class="p p1"><b></b><b></b><b></b><b></b><b></b></div></div>')
    if tipo == "matita":
        return ('<div class="att-fig att-pag"><b></b><b></b><b></b><b></b><b></b><b></b><span class="matita">✏️</span></div>')
    if tipo == "word":
        return ('<div class="att-fig att-pag"><span class="w">W</span><b></b><b></b><b></b><b></b><u></u></div>')
    return '<div class="att-fig att-pag"><b></b><b></b><b></b><b></b><b></b><b></b><u></u></div>'


def _css(T: dict, n_passi: int, durata: float, n_consigli: int) -> str:
    acc, tx, t2 = T["accent"], T["text"], T["text2"]
    giro_consigli = 7.0
    tot = giro_consigli * max(n_consigli, 1)
    return (
        "<style>"
        "@keyframes att-scan{0%{top:8%;opacity:0}10%{opacity:1}50%{top:82%}90%{opacity:1}100%{top:8%;opacity:0}}"
        "@keyframes att-riga{0%{width:12%}60%{width:var(--w)}100%{width:12%}}"
        "@keyframes att-gira{to{transform:rotate(360deg)}}"
        "@keyframes att-on{to{opacity:1}}@keyframes att-off{to{opacity:0}}"
        "@keyframes att-lama{0%{left:6%;opacity:0}10%{opacity:1}50%{left:84%}90%{opacity:1}100%{left:6%;opacity:0}}"
        "@keyframes att-batte{0%,100%{opacity:.35}50%{opacity:1}}"
        "@keyframes att-fan1{0%,100%{transform:translate(0,0) rotate(0)}50%{transform:translate(9px,-3px) rotate(5deg)}}"
        "@keyframes att-fan2{0%,100%{transform:translate(0,0) rotate(0)}50%{transform:translate(-9px,-1px) rotate(-5deg)}}"
        "@keyframes att-matita{0%{transform:translate(0,0) rotate(-8deg)}25%{transform:translate(1.6rem,.2rem) rotate(-2deg)}"
        "50%{transform:translate(.4rem,1.1rem) rotate(-8deg)}75%{transform:translate(1.8rem,1.3rem) rotate(-2deg)}100%{transform:translate(0,0) rotate(-8deg)}}"
        "@keyframes att-consiglio{0%{opacity:0;transform:translateY(4px)}4%{opacity:1;transform:none}"
        f"{100 / max(n_consigli, 1) - 4:.1f}%{{opacity:1}}{100 / max(n_consigli, 1):.1f}%,100%{{opacity:0}}}}"
        f".att-card{{display:flex;gap:1.4rem;align-items:center;margin:.8rem 0 .6rem;padding:1.2rem 1.4rem;border-radius:20px;"
        f"background:linear-gradient(160deg,{T['card']} 0%,{acc}12 100%);border:1px solid {acc}33;box-shadow:0 12px 30px {acc}22;"
        "font-family:'DM Sans',sans-serif;}"
        ".att-fig{position:relative;flex:0 0 5.8rem;height:7.4rem;border-radius:12px;background:#fff;border:1.5px solid #CBD5E1;"
        "box-shadow:0 8px 18px rgba(15,23,42,.14);padding:.8rem .6rem;overflow:hidden;}"
        ".att-pag b{display:block;height:.32rem;border-radius:3px;background:#CBD5E1;margin-bottom:.42rem;animation:att-riga 2.6s ease-in-out infinite;}"
        ".att-pag b:nth-child(1){--w:80%}.att-pag b:nth-child(2){--w:94%;animation-delay:.2s}.att-pag b:nth-child(3){--w:70%;animation-delay:.4s}"
        ".att-pag b:nth-child(4){--w:88%;animation-delay:.6s}.att-pag b:nth-child(5){--w:60%;animation-delay:.8s}.att-pag b:nth-child(6){--w:90%;animation-delay:1s}"
        f".att-pag u{{position:absolute;left:0;right:0;height:.18rem;background:linear-gradient(90deg,transparent,{acc},transparent);"
        f"box-shadow:0 0 12px {acc};animation:att-scan 2.6s ease-in-out infinite;text-decoration:none;}}"
        ".att-pag .matita{position:absolute;left:.5rem;top:.5rem;font-size:1.5rem;animation:att-matita 3.2s ease-in-out infinite;}"
        f".att-pag .w{{position:absolute;right:.4rem;bottom:.4rem;width:1.7rem;height:1.7rem;border-radius:7px;background:{acc};color:#fff;"
        "font-weight:800;font-size:1rem;display:flex;align-items:center;justify-content:center;}"
        ".att-foto{padding:0;background:linear-gradient(180deg,#E0F2FE 0%,#F8FAFC 100%);}"
        ".att-foto .sole{position:absolute;right:.9rem;top:1rem;width:1rem;height:1rem;border-radius:50%;background:#FBBF24;}"
        ".att-foto .monte{position:absolute;left:-.2rem;bottom:0;width:0;height:0;border-left:2.4rem solid transparent;border-right:2.4rem solid transparent;"
        "border-bottom:3.2rem solid #94A3B8;}.att-foto .monte.m2{left:2rem;border-bottom:2.3rem solid #CBD5E1;}"
        f".att-foto i{{position:absolute;width:.9rem;height:.9rem;border:3px solid {acc};animation:att-batte 1.6s ease-in-out infinite;}}"
        ".att-foto .c1{left:.45rem;top:.45rem;border-right:0;border-bottom:0}.att-foto .c2{right:.45rem;top:.45rem;border-left:0;border-bottom:0}"
        ".att-foto .c3{left:.45rem;bottom:.45rem;border-right:0;border-top:0}.att-foto .c4{right:.45rem;bottom:.45rem;border-left:0;border-top:0}"
        f".att-foto .lama-o{{position:absolute;top:8%;bottom:8%;width:.18rem;background:linear-gradient(180deg,transparent,{acc},transparent);"
        f"box-shadow:0 0 12px {acc};animation:att-lama 2.4s ease-in-out infinite;text-decoration:none;}}"
        ".att-copie{background:transparent;border:0;box-shadow:none;padding:0;overflow:visible;}"
        ".att-copie .p{position:absolute;left:.4rem;top:.3rem;width:4.6rem;height:6.4rem;border-radius:9px;background:#fff;border:1.5px solid #CBD5E1;"
        "box-shadow:0 6px 14px rgba(15,23,42,.14);padding:.7rem .5rem;}"
        ".att-copie .p3{animation:att-fan2 2.8s ease-in-out infinite;opacity:.7}.att-copie .p2{animation:att-fan1 2.8s ease-in-out infinite;opacity:.85}"
        ".att-copie .p b{display:block;height:.28rem;border-radius:3px;background:#CBD5E1;margin-bottom:.4rem;}"
        ".att-copie .p b:nth-child(odd){width:85%}.att-copie .p b:nth-child(even){width:65%}"
        f".att-t{{font-weight:800;font-size:1.1rem;color:{tx};margin-bottom:.1rem;}}"
        f".att-s{{font-size:.86rem;color:{t2};margin-bottom:.65rem;}}"
        ".att-card ul{list-style:none;margin:0;padding:0;}"
        ".att-card li{display:flex;gap:.6rem;align-items:center;font-size:.93rem;padding:.15rem 0;}"
        ".att-ic{position:relative;flex:0 0 1.1rem;height:1.1rem;}.att-ic>*{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;"
        "font-weight:800;line-height:1;}"
        ".att-ok{color:#15803D}.att-da{opacity:.45}.att-ora{color:" + tx + ";font-weight:700}"
        f".att-giro{{width:.85rem;height:.85rem;margin:auto;border-radius:50%;border:2px solid {acc}44;border-top-color:{acc};"
        "animation:att-gira .8s linear infinite;}"
        ".att-auto li{opacity:.45;font-weight:400}"
        f".att-auto .att-ic .i-att{{opacity:0}}.att-auto .att-ic .i-ok{{opacity:0;color:#15803D}}"
        f".att-tip{{position:relative;min-height:2.4rem;margin-top:.8rem;padding-top:.6rem;border-top:1px dashed {acc}44;"
        f"font-size:.84rem;color:{t2};}}"
        ".att-tip span{position:absolute;left:0;right:0;top:.6rem;opacity:0;"
        f"animation:att-consiglio {tot:.0f}s linear infinite;}}"
        f".att-tip b{{color:{acc};letter-spacing:.06em;text-transform:uppercase;font-size:.68rem;margin-right:.4rem;}}"
        "@media (max-width:640px){.att-card{flex-direction:column;text-align:left;align-items:flex-start}}"
        "@media (prefers-reduced-motion:reduce){.att-card *{animation:none !important}.att-card .att-auto li{opacity:1}"
        ".att-card .att-auto .att-ic .i-att{opacity:0 !important}.att-card .att-auto li:first-child{font-weight:700}}"
        "</style>"
    )


def _css_auto(n: int, durata: float) -> str:
    """Le regole per far accendere i passi da soli: il passo k si accende dopo k*durata e si spegne (diventa «fatto») dopo (k+1)*durata."""
    r = []
    for k in range(n):
        a, b = k * durata, (k + 1) * durata
        base = f".att-auto li:nth-child({k + 1})"
        r.append(f"{base}{{animation:att-on .01s {a:.1f}s forwards}}")
        r.append(f"{base} .i-da{{animation:att-off .01s {a:.1f}s forwards}}")
        if k == 0:
            r.append(f"{base} .i-att{{opacity:1}}")
        else:
            r.append(f"{base} .i-att{{animation:att-on .01s {a:.1f}s forwards}}")
        if k < n - 1:
            r.append(f"{base} .i-att{{animation:{'att-on .01s ' + format(a, '.1f') + 's forwards,' if k else ''}att-off .01s {b:.1f}s forwards}}")
            r.append(f"{base} .i-ok{{animation:att-on .01s {b:.1f}s forwards}}")
    return "<style>" + "".join(r) + "</style>"


def card_html(T: dict, tipo: str, titolo: str, sotto: str = "", passi: list | None = None, attivo: int | None = None,
              durata_passo: float = 8.0, extra_html: str = "", consigli: bool = False) -> str:
    """
    La scheda di attesa. Con `attivo` = indice del passo in corso (0, 1, 2…) i passi prima sono «fatti» e quelli dopo «da fare»;
    senza `attivo` i passi si accendono da soli, uno ogni `durata_passo` secondi.
    `extra_html` va sotto i passi (per esempio la bozza degli esercizi); `consigli=True` aggiunge un suggerimento che cambia ogni 7 secondi.
    """
    tipo = tipo if tipo in _TIPI else "pagina"
    passi = list(passi or [])
    righe = ""
    auto = attivo is None and len(passi) > 0
    for k, voce in enumerate(passi):
        if auto:
            icone = '<span class="i-da">○</span><span class="i-att"><i class="att-giro"></i></span><span class="i-ok">✓</span>'
            righe += f'<li><span class="att-ic">{icone}</span>{_esc(voce)}</li>'
        else:
            if k < (attivo or 0):
                ic, cl = "✓", "att-ok"
            elif k == (attivo or 0):
                ic, cl = '<i class="att-giro"></i>', "att-ora"
            else:
                ic, cl = "○", "att-da"
            righe += f'<li class="{cl}"><span class="att-ic"><span>{ic}</span></span>{_esc(voce)}</li>'
    tip = ""
    if consigli:
        tip = ('<div class="att-tip">' + "".join(f'<span style="animation-delay:{i * 7}s"><b>Lo sapevi?</b>{_esc(c)}</span>'
                                                  for i, c in enumerate(CONSIGLI)) + "</div>")
    return (
        _css(T, len(passi), durata_passo, len(CONSIGLI) if consigli else 1)
        + (_css_auto(len(passi), durata_passo) if auto else "")
        + f'<div class="att-card" role="status" aria-live="polite">{_figura(tipo)}<div style="flex:1;min-width:0;">'
        f'<div class="att-t">{_esc(titolo)}</div>'
        + (f'<div class="att-s">{_esc(sotto)}</div>' if sotto else "")
        + (f'<ul class="{"att-auto" if auto else ""}">{righe}</ul>' if passi else "")
        + extra_html + tip + "</div></div>"
    )


@contextmanager
def attesa(T: dict, tipo: str, titolo: str, passi: list | None = None, sotto: str = "", durata_passo: float = 8.0, consigli: bool = False):
    """`with attesa(T, "foto", "Sto leggendo l'esercizio", [...]):` mostra la scheda mentre il codice lavora e la toglie alla fine (anche in caso di errore)."""
    ph = st.empty()
    ph.markdown(card_html(T, tipo, titolo, sotto, passi, None, durata_passo, consigli=consigli), unsafe_allow_html=True)
    try:
        yield ph
    finally:
        ph.empty()
