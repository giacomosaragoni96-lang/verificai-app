"""
ui_profilo.py — la pagina «Il mio profilo» (stage PROFILO): solo interfaccia. I dati e le funzioni vengono da main.py tramite `ctx`
(profilo, salvataggi, elenco delle verifiche, eliminazione dell'account…); la logica dei numeri sta in profilo.py.

Quattro sezioni: Le mie classi · Le mie preferenze · La mia attività · Account.
"""
from datetime import date, datetime, timezone
import html

import streamlit as st

import profilo
from ui_impostazioni import riepilogo

SEZIONI = ["👥 Le mie classi", "⚙️ Impostazioni predefinite", "📈 La mia attività", "🔑 Account"]
_SWATCH = ["🔵", "🟣", "🔴", "🟠", "🟡", "🟢", "⚫", "🟤"]
_NOMI_EVENTI = {"verifica": "Verifiche create", "fila_b": "Fila B", "fila_extra": "File C, D, E", "recupero": "Versioni di recupero", "bes": "Versioni BES/DSA",
                "soluzioni": "Soluzioni", "scheda": "Schede di allenamento", "word": "File Word", "griglia": "Griglie di valutazione", "modifica": "Modifiche con l'AI",
                "impagina": "Verifiche impaginate", "foto_esercizio": "Esercizi dal libro", "ritaglio_figura": "Figure ritagliate"}


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _quando(d) -> str:
    if not d:
        return "—"
    giorni = (datetime.now(timezone.utc).date() - d).days
    if giorni <= 0:
        return "oggi"
    if giorni == 1:
        return "ieri"
    if giorni < 7:
        return f"{giorni} giorni fa"
    if giorni < 30:
        return f"{giorni // 7} settimane fa" if giorni >= 14 else "1 settimana fa"
    return d.strftime("%d/%m/%Y")


def _css(T: dict) -> str:
    acc = T["accent"]
    return f"""<style>
.pf-testa{{display:flex;gap:1.1rem;align-items:center;flex-wrap:wrap;background:linear-gradient(135deg,{acc}18 0%,{acc}08 100%);border:1px solid {acc}33;border-radius:22px;padding:1.2rem 1.4rem;
  box-shadow:0 10px 28px rgba(15,23,42,.08);font-family:'DM Sans',sans-serif;margin:.2rem 0 1rem;}}
.pf-av{{flex:0 0 4rem;height:4rem;border-radius:50%;background:linear-gradient(135deg,{acc},{T.get('accent2',acc)});color:#fff;display:flex;align-items:center;justify-content:center;
  font-size:1.7rem;font-weight:800;box-shadow:0 6px 16px {acc}55;}}
.pf-nome{{font-size:1.25rem;font-weight:800;color:{T['text']};line-height:1.2;}}
.pf-mail{{font-size:.88rem;color:{T['text2']};}}
.pf-pill{{display:inline-block;background:{acc}1F;color:{acc};border-radius:999px;padding:.12rem .65rem;font-size:.74rem;font-weight:800;letter-spacing:.04em;margin-left:.4rem;vertical-align:middle;}}
.pf-num{{margin-left:auto;display:flex;gap:.8rem;}}
.pf-n{{text-align:center;background:linear-gradient(160deg,{T['card']} 0%,{acc}14 100%);border:1px solid {acc}40;border-radius:16px;padding:.65rem 1.4rem;min-width:8.2rem;
  box-shadow:0 8px 20px {acc}26,0 2px 5px rgba(15,23,42,.06);}}
.pf-n b{{display:block;font-size:2.5rem;color:{T['text']};line-height:1.1;letter-spacing:-.03em;}}
.pf-n span{{font-size:.8rem;font-weight:700;color:{T['text2']};}}
.pf-n-main{{background:linear-gradient(145deg,{acc},{T.get('accent2',acc)});border:none;padding:.65rem 1.4rem;min-width:8.2rem;box-shadow:0 10px 24px {acc}55,0 2px 6px rgba(15,23,42,.12);transform:translateY(-3px);}}
.pf-n-main b{{font-size:2.5rem;color:#fff;letter-spacing:-.03em;}}
.pf-n-main span{{font-size:.8rem;font-weight:700;color:#fff;opacity:.92;}}
html body .stApp .pf-n-main b, html body .stApp .pf-n-main span{{color:#fff !important;-webkit-text-fill-color:#fff !important;}}
.pf-sez{{font-family:'DM Sans',sans-serif;font-size:1.7rem;font-weight:800;letter-spacing:-.025em;line-height:1.15;color:{T['text']};margin:.5rem 0 .25rem;}}
.pf-sez::after{{content:"";display:block;width:3.4rem;height:.3rem;border-radius:99px;margin-top:.5rem;background:linear-gradient(90deg,{acc},{T.get('accent2',acc)});}}
.pf-sub{{font-family:'DM Sans',sans-serif;font-size:.88rem;color:{T['text2']};margin:0 0 .8rem;line-height:1.45;}}
.pf-classe{{display:flex;gap:.7rem;align-items:center;font-family:'DM Sans',sans-serif;}}
.pf-dot{{flex:0 0 3.2rem;height:3.2rem;border-radius:14px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:1.15rem;box-shadow:0 6px 14px rgba(15,23,42,.22);}}
.pf-ct{{font-weight:800;font-size:1.35rem;line-height:1.15;color:{T['text']};letter-spacing:-.01em;}} .pf-cs{{font-size:.95rem;color:{T['text2']};margin-top:.1rem;}}
html body .stApp div[class*="st-key-classe_card_"] [data-testid="stWidgetLabel"] p{{font-size:.92rem !important;font-weight:700 !important;color:{T['text']} !important;}}
.pf-mesi{{display:flex;gap:.7rem;align-items:flex-end;height:11rem;padding:.4rem .2rem 0;font-family:'DM Sans',sans-serif;}}
.pf-mese{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;}}
.pf-mese .v{{font-weight:800;font-size:.95rem;color:{T['text']};margin-bottom:.2rem;}}
.pf-mese .barra{{width:100%;max-width:3.6rem;border-radius:10px 10px 4px 4px;background:linear-gradient(180deg,{acc},{T.get('accent2',acc)});min-height:.3rem;}}
.pf-mese.zero .barra{{background:{T['border']};}}
.pf-mese .m{{margin-top:.4rem;font-size:.82rem;color:{T['text2']};text-transform:capitalize;}}
.pf-kpi{{display:flex;gap:.7rem;flex-wrap:wrap;margin:.4rem 0 .9rem;font-family:'DM Sans',sans-serif;}}
.pf-kpi div{{background:{T['card']};border:1px solid {T['border']};border-radius:14px;padding:.55rem 1rem;min-width:7.5rem;}}
.pf-kpi b{{display:block;font-size:1.5rem;line-height:1.1;color:{T['text']};}} .pf-kpi span{{font-size:.78rem;color:{T['text2']};}}
.pf-cal{{display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,12px);grid-auto-columns:12px;gap:3px;overflow-x:auto;padding:.3rem 0 .5rem;}}
.pf-cal i{{width:12px;height:12px;border-radius:3px;display:block;}}
.pf-l0{{background:{T['border']};}} .pf-l1{{background:{acc}40;}} .pf-l2{{background:{acc}70;}} .pf-l3{{background:{acc}B0;}} .pf-l4{{background:{acc};}} .pf-lx{{background:transparent;}}
.pf-bar{{display:flex;align-items:center;gap:.6rem;margin:.28rem 0;font-family:'DM Sans',sans-serif;font-size:.88rem;color:{T['text']};}}
.pf-bar .e{{flex:0 0 9.5rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}} .pf-bar .b{{flex:1;background:{T['border']};border-radius:99px;height:9px;overflow:hidden;}}
.pf-bar .b i{{display:block;height:100%;background:linear-gradient(90deg,{acc},{T.get('accent2',acc)});border-radius:99px;}} .pf-bar .v{{flex:0 0 2.2rem;text-align:right;font-weight:800;}}
.pf-ult{{display:flex;gap:.7rem;align-items:center;padding:.5rem 0;border-top:1px solid {T['border']};font-family:'DM Sans',sans-serif;font-size:.9rem;color:{T['text']};}}
.pf-ult small{{color:{T['text2']};margin-left:auto;}}
html body .stApp div[class*="st-key-classe_card_"]:not(#vf){{background:{T['card']};border:1px solid {T['border2']};border-radius:18px;padding:1rem 1.2rem 1rem;margin-bottom:.8rem;box-shadow:0 6px 18px rgba(15,23,42,.07);}}
html body .stApp .st-key-pericolo:not(#vf){{border:1.5px solid #FCA5A5;background:rgba(220,38,38,.05);border-radius:16px;padding:1rem 1.2rem;}}
</style>"""


def _testa(T, ctx, stats) -> None:
    nome = (ctx["email"].split("@")[0] if ctx.get("email") else "Docente").replace(".", " ").replace("_", " ").title()
    dal = stats["dal"].strftime("%d/%m/%Y") if stats.get("dal") else "da poco"
    st.markdown(
        _css(T) + f'<div class="pf-testa"><div class="pf-av">{_esc(nome[:1])}</div><div><div class="pf-nome">{_esc(nome)}<span class="pf-pill">{_esc(ctx.get("piano", "free").upper())}</span></div>'
        f'<div class="pf-mail">{_esc(ctx.get("email", ""))} · con noi dal {_esc(dal)}</div></div>'
        f'<div class="pf-num"><div class="pf-n pf-n-main"><b>{stats["totale"]}</b><span>verifiche create</span></div>'
        f'<div class="pf-n"><b>{len(ctx["profilo"].get("classi", []))}</b><span>classi</span></div></div></div>', unsafe_allow_html=True)


def _sezione_classi(T, ctx, stats) -> None:
    p = ctx["profilo"]
    st.markdown('<div class="pf-sez">Le mie classi</div><div class="pf-sub">Ogni classe ha la sua scuola e le sue note: scegliendola quando crei una verifica '
                'si precompila tutto.</div>', unsafe_allow_html=True)
    classi = p.get("classi", [])
    if not classi:
        st.info("Non hai ancora aggiunto classi. Aggiungine una qui sotto: ti basta il nome (es. «3ªB»).", icon="👥")
    for i, c in enumerate(classi):
        info = stats["classi"].get(c["nome"].lower(), {"n": 0, "ultima": None, "ultima_titolo": ""})
        with st.container(key=f"classe_card_{i}"):
            st.markdown(
                f'<div class="pf-classe"><div class="pf-dot" style="background:{c["colore"]};">{_esc(c["nome"][:2])}</div><div>'
                f'<div class="pf-ct">{_esc(c["nome"])}</div><div class="pf-cs">{_esc(c["scuola"] or "Scuola non indicata")} · {info["n"]} '
                f'{"verifica" if info["n"] == 1 else "verifiche"}' + (f' · ultima: {_esc(info["ultima_titolo"][:40])} ({_quando(info["ultima"])})' if info["ultima"] else "") + '</div></div></div>',
                unsafe_allow_html=True)
            sc_opz = [""] + list(ctx["scuole"])
            scuola = st.selectbox("Scuola", sc_opz, index=sc_opz.index(c["scuola"]) if c["scuola"] in sc_opz else 0, key=f"cl_sc_{i}", format_func=lambda x: x or "Non indicata")
            note = st.text_area("Note per questa classe", value=c["note"], key=f"cl_nt_{i}", height=80, max_chars=profilo.MAX_NOTE,
                                placeholder="Es.: ritmo lento, molte lacune sulle frazioni, evitare i problemi di realtà")
            b1, b2, b3, b4 = st.columns([1.1, 1.8, 1.6, .5], gap="small", vertical_alignment="center")
            _cambiata = (scuola != c["scuola"]) or ((note or "").strip() != (c["note"] or "").strip())
            if b1.button("Salva", key=f"cl_salva_{i}", type="primary", icon=":material/check:", use_container_width=True, disabled=not _cambiata,
                         help=None if _cambiata else "Nessuna modifica da salvare"):
                nuove = [dict(x) for x in classi]
                nuove[i] = {**c, "scuola": scuola, "note": note}
                ctx["salva"]({**p, "classi": nuove})
                ctx["conferma"](f"Classe {c['nome']} salvata")
                st.rerun()
            if b2.button(f"Nuova verifica per la {c['nome']}", key=f"cl_nuova_{i}", icon=":material/add:", use_container_width=True):
                ctx["nuova_per_classe"](c["nome"])
            if b3.button("Vedi le sue verifiche", key=f"cl_elenco_{i}", type="tertiary", icon=":material/folder_open:", use_container_width=True):
                ctx["elenco_classe"](c["nome"])
            with b4.popover("⋯", help="Elimina la classe"):
                st.caption("Le verifiche non si cancellano: restano senza classe.")
                if st.button("Elimina la classe", key=f"cl_del_{i}", type="primary", use_container_width=True):
                    ctx["salva"]({**p, "classi": [x for k, x in enumerate(classi) if k != i]})
                    ctx["conferma"]("Classe eliminata")
                    st.rerun()
    _salvate = {c["nome"].lower() for c in classi}
    _extra = [d for k, d in stats["classi"].items() if k not in _salvate and profilo.pulisci_nome(d["nome"])]
    if _extra:
        st.markdown('<div class="pf-sub" style="margin-top:.8rem">Nelle tue verifiche compaiono anche queste classi, scritte a mano e non ancora tra le tue classi. '
                    'Aggiungile per averle con scuola e note.</div>', unsafe_allow_html=True)
        for j, d in enumerate(_extra):
            e1, e2 = st.columns([3, 2], vertical_alignment="center", gap="small")
            e1.markdown(f'**{_esc(d["nome"])}** · {d["n"]} {"verifica" if d["n"] == 1 else "verifiche"}')
            if e2.button("Aggiungi alle mie classi", key=f"cl_agg_{j}", icon=":material/add:", use_container_width=True):
                ctx["salva"]({**p, "classi": classi + [{"nome": profilo.pulisci_nome(d["nome"]), "scuola": "", "note": "",
                                                       "colore": profilo.COLORI[len(classi) % len(profilo.COLORI)]}]})
                ctx["conferma"](f"Classe {profilo.pulisci_nome(d['nome'])} aggiunta")
                st.rerun()
    with st.expander("＋ Aggiungi una classe", expanded=not classi):
        a, b = st.columns([2, 3], gap="medium")
        nome = a.text_input("Nome della classe", key="cl_new_nome", placeholder="Es. 3ªB", max_chars=24)
        scuola = b.selectbox("Scuola (facoltativa)", [""] + list(ctx["scuole"]), key="cl_new_scuola", format_func=lambda x: x or "Non indicata")
        colore = st.segmented_control("Colore", _SWATCH, default=_SWATCH[len(classi) % len(_SWATCH)], key="cl_new_col") or _SWATCH[0]
        if st.button("Aggiungi", key="cl_new_ok", type="primary", icon=":material/add:", disabled=not profilo.pulisci_nome(nome)):
            if profilo.pulisci_nome(nome).lower() in {c["nome"].lower() for c in classi}:
                st.warning("Hai già una classe con questo nome.")
            else:
                ctx["salva"]({**p, "classi": classi + [{"nome": profilo.pulisci_nome(nome), "scuola": scuola, "note": "", "colore": profilo.COLORI[_SWATCH.index(colore)]}]})
                ctx["conferma"](f"Classe {profilo.pulisci_nome(nome)} aggiunta")
                st.rerun()


def _sezione_preferenze(T, ctx) -> None:
    p = ctx["profilo"]
    st.markdown('<div class="pf-sez">Impostazioni predefinite</div><div class="pf-sub">Preferenze di scrittura, stile del PDF e logo della scuola: '
                'si salvano e valgono per ogni verifica finché non le cambi.</div>', unsafe_allow_html=True)
    nomi = {"": "Classico (predefinito)", **{k: n for k, n in ctx["stili"]}}
    riepilogo(T, ctx, profilo.frasi_preferenze(p), nomi.get(p.get("stile", "") or "", "Classico"), False)
    st.button("Apri le impostazioni predefinite", key="pf_apri_imp", type="primary", icon=":material/tune:", on_click=ctx["apri_impostazioni"])


_MESI_BREVI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def _per_mese(cal: list, quanti: int = 6) -> list:
    """[(etichetta, n)] delle verifiche degli ultimi `quanti` mesi (il mese corrente per ultimo), dal calendario giornaliero."""
    giorni = [g for g in cal if g["n"] is not None]
    if not giorni:
        return []
    oggi = giorni[-1]["data"]
    mesi = []
    anno, mese = oggi.year, oggi.month
    for _ in range(quanti):
        mesi.append((anno, mese))
        mese -= 1
        if mese == 0:
            anno, mese = anno - 1, 12
    mesi.reverse()
    conta = {k: 0 for k in mesi}
    for g in giorni:
        k = (g["data"].year, g["data"].month)
        if k in conta:
            conta[k] += g["n"] or 0
    return [(_MESI_BREVI[m - 1] + (f" {str(a)[2:]}" if m == 1 else ""), conta[(a, m)]) for a, m in mesi]


def _sezione_attivita(T, ctx, stats) -> None:
    st.markdown('<div class="pf-sez">La mia attività</div><div class="pf-sub">Quante verifiche hai creato negli ultimi mesi.</div>',
                unsafe_allow_html=True)
    cal = stats["calendario"]
    mesi = _per_mese(cal)
    if mesi:
        ultimo, precedente = mesi[-1][1], mesi[-2][1] if len(mesi) > 1 else 0
        anno = sum(g["n"] or 0 for g in cal)
        st.markdown(f'<div class="pf-kpi"><div><b>{ultimo}</b><span>questo mese</span></div><div><b>{precedente}</b><span>mese scorso</span></div>'
                    f'<div><b>{anno}</b><span>nell\'ultimo anno</span></div></div>', unsafe_allow_html=True)
        massimo = max([n for _e, n in mesi] + [1])
        st.markdown('<div class="pf-mesi">' + "".join(
            f'<div class="pf-mese{" zero" if n == 0 else ""}"><span class="v">{n}</span><div class="barra" style="height:{max(3, 78 * n / massimo):.0f}%"></div>'
            f'<span class="m">{_esc(e)}</span></div>' for e, n in mesi) + '</div>', unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("**Per materia**")
        tot = max([n for _m, n in stats["materie"]] + [1])
        st.markdown("".join(f'<div class="pf-bar"><span class="e">{_esc(m)}</span><span class="b"><i style="width:{100 * n / tot:.0f}%"></i></span><span class="v">{n}</span></div>'
                            for m, n in stats["materie"][:7]) or '<div class="pf-cs">Ancora nessuna verifica.</div>', unsafe_allow_html=True)
    with b:
        st.markdown("**Cosa usi di più**")
        ev = [(k, n) for k, n in ctx.get("eventi", {}).items() if k in _NOMI_EVENTI]
        ev.sort(key=lambda x: -x[1])
        tot = max([n for _k, n in ev] + [1])
        st.markdown("".join(f'<div class="pf-bar"><span class="e">{_esc(_NOMI_EVENTI[k])}</span><span class="b"><i style="width:{100 * n / tot:.0f}%"></i></span><span class="v">{n}</span></div>'
                            for k, n in ev[:7]) or '<div class="pf-cs">Ancora nessun dato.</div>', unsafe_allow_html=True)
    st.markdown("**Le ultime verifiche**")
    for v in stats["ultime"]:
        g = profilo._giorno(v.get("created_at"))
        st.markdown(f'<div class="pf-ult"><b>{_esc(v.get("argomento") or "Verifica")}</b><span>{_esc(v.get("materia") or "")}</span>'
                    f'{("<span>· " + _esc(v["classe"]) + "</span>") if v.get("classe") else ""}<small>{_quando(g)}</small></div>', unsafe_allow_html=True)
    st.button("Vedi tutte le verifiche", key="pf_tutte", type="tertiary", icon=":material/folder_open:", on_click=ctx["apri_elenco"])


def _sezione_account(T, ctx) -> None:
    st.markdown('<div class="pf-sez">Account</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(f"**Piano:** {ctx.get('piano', 'free').capitalize()} · **Verifiche questo mese:** {ctx.get('verifiche_mese', 0)}" + (f" · **Verifiche complete disponibili:** {ctx['crediti']}" if ctx.get("crediti") else ""))
        st.button("Invita un collega", key="pf_invita", icon=":material/group_add:", on_click=ctx["invita"], help="Ogni collega che crea la sua prima verifica ti regala verifiche complete.")
    with st.expander("Impostazioni avanzate", expanded=False, icon=":material/settings:"):
        scuro = st.toggle("Tema scuro", value=ctx["tema_scuro"], key="pf_tema", help="Colori scuri, più riposanti la sera. La verifica stampata resta sempre uguale.")
        if scuro != ctx["tema_scuro"]:
            ctx["imposta_tema"](scuro)
            st.rerun()
    with st.container(key="pericolo"):
        st.markdown("**Elimina il mio account**")
        st.caption("Cancella per sempre il tuo account, le tue verifiche, le classi e le preferenze. Non si può annullare. "
                   "Se hai un abbonamento attivo, scrivici prima.")
        if ctx.get("e_admin"):
            st.info("L'account amministratore non si elimina da qui.")
        else:
            conferma = st.text_input("Per confermare scrivi ELIMINA", key="pf_del_txt", placeholder="ELIMINA")
            if st.button("Elimina definitivamente il mio account", key="pf_del_ok", type="primary", icon=":material/delete_forever:", disabled=(conferma or "").strip() != "ELIMINA"):
                ok, msg = ctx["elimina_account"]()
                if not ok:
                    st.error(msg)


def render_profilo(T: dict, ctx: dict) -> None:
    if st.button("← Indietro", key="pf_indietro", type="tertiary"):
        ctx["indietro"]()
    stats = profilo.statistiche(ctx["verifiche"])
    _testa(T, ctx, stats)
    sez = st.segmented_control("Sezione", SEZIONI, default=SEZIONI[0], key="sez_profilo", label_visibility="collapsed") or SEZIONI[0]
    if sez == SEZIONI[0]:
        _sezione_classi(T, ctx, stats)
    elif sez == SEZIONI[1]:
        _sezione_preferenze(T, ctx)
    elif sez == SEZIONI[2]:
        _sezione_attivita(T, ctx, stats)
    else:
        _sezione_account(T, ctx)
