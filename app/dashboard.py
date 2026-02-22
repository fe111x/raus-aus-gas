"""
Raus aus Gas – Dashboard Wiener Wärmeversorgung.
Gebäudebestand (Gas-Zählpunkte), Dekarbonisierungsregeln, Umstellung nach Gebietstyp.
Szenarien inkl. Löschen; Grafik Dekarbonisierungspfade pro Gebäudetyp.
Design: Lesbarkeit (Kontrast), Morgenrot, Logo immer sichtbar.
Start: streamlit run app/dashboard.py
"""

from pathlib import Path
import base64
import json
import copy
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "assets"

CD = {
    "morgenrot": "#FF5A64",
    "weiss": "#FFFFFF",
    "nebelgrau": "#D6D1CA",
    "text_dunkel": "#1a1a1a",
    "text_hell": "#444444",
    "wasserblau": "#83d0f5",
    "frischgruen": "#82D282",
    "goldgelb": "#E6C828",
    "border": "#e0e0e0",
    "card_bg": "#ffffff",
}
CD_FONT = '"Lucida Grande", "Lucida Sans Unicode", Lucida, sans-serif'

GEBIETSTYPEN = [
    ("Fernwärme Heute", "Bereits erschlossen oder zeitnah"),
    ("Fernwärme Zukunft", "Geplanter flächendeckender Ausbau"),
    ("Pioniergebiete", "Strategischer Fernwärme-Ausbau"),
    ("Lokale Wärme gemeinsam", "Nachbarschaftliche Wärmenetze"),
    ("Lokale Wärme individuell", "Wärmepumpen, Solar, Biomasse"),
]

# Gebäudetypen für Dekarbonisierungspfade (Keys für Params + Anzeige)
GEBAEUDETYPEN = [
    ("einfamilienhauser", "Einfamilienhäuser (nur Wärmepumpen)"),
    ("zentral_beheizt", "Zentral beheizt (in FW-Heute: immer Fernwärme)"),
    ("dezentral_beheizt", "Dezentral beheizt (erst Zentralisierung)"),
    ("gas_und_fernwaerme", "Gas und Fernwärme (immer → Fernwärme)"),
    ("dienstleistung", "Dienstleistungsgebäude"),
    ("sonstige_nichtwohn", "Sonstige Nichtwohngebäude"),
]

BASISJAHR = 2023
ZIELJAHR = 2040
KORRIDOR_RELATIV = 0.12


def load_data():
    dfs = {}
    if (DATA_DIR / "fernwaerme_haushalte.csv").exists():
        dfs["fernwaerme"] = pd.read_csv(DATA_DIR / "fernwaerme_haushalte.csv")
    if (DATA_DIR / "waermeversorgung_quellen.csv").exists():
        dfs["quellen"] = pd.read_csv(DATA_DIR / "waermeversorgung_quellen.csv")
    if (DATA_DIR / "pioniergebiete.csv").exists():
        dfs["pioniergebiete"] = pd.read_csv(DATA_DIR / "pioniergebiete.csv")
    if (DATA_DIR / "ziele_raus_aus_gas.json").exists():
        with open(DATA_DIR / "ziele_raus_aus_gas.json", encoding="utf-8") as f:
            dfs["ziele"] = json.load(f)
    return dfs


def build_projection(params, df_hist, faktor=1.0):
    """Projektion von BASISJAHR bis ZIELJAHR (aggregiert)."""
    base = df_hist[df_hist["jahr"] == BASISJAHR].iloc[0]
    fw = int(base["fernwaerme_haushalte"])
    gas = int(base["gas_heizung_haushalte"])
    gesamt = int(base["gesamt_wohnungen"])
    leitungen = float(base["fernwaerme_leitungen_km"])

    def f(x):
        return int(round(x * faktor)) if isinstance(x, (int, float)) else x

    anschluss_bis_2030 = f(params.get("fernwaerme_anschluss_bis_2030", 12_000))
    anschluss_ab_2030 = f(params.get("fernwaerme_anschluss_ab_2030", 30_000))
    heizungstausch_pro_jahr = f(params.get("heizungstausch_pro_jahr", 15_000))
    anteil_gas_zu_h2 = (params.get("anteil_gas_zu_wasserstoff", 5) or 0) / 100.0
    waermepumpen_pro_jahr = f(params.get("waermepumpen_pro_jahr", 4_000))
    wachstum_wohnungen = params.get("wachstum_wohnungen_pro_jahr", 0.4)

    rows = []
    for jahr in range(BASISJAHR, ZIELJAHR + 1):
        if jahr == BASISJAHR:
            rows.append({"jahr": jahr, "fernwaerme_haushalte": fw, "gas_heizung_haushalte": gas, "gesamt_wohnungen": gesamt, "fernwaerme_anteil_pct": round(100 * fw / gesamt, 1), "fernwaerme_leitungen_km": leitungen})
            continue
        gesamt = int(gesamt * (1 + wachstum_wohnungen / 100.0))
        neu_fw = anschluss_bis_2030 if jahr <= 2030 else anschluss_ab_2030
        fw = min(fw + neu_fw, gesamt)
        gas_aus = min(gas, heizungstausch_pro_jahr)
        zu_h2 = int(gas_aus * anteil_gas_zu_h2)
        zu_wp = min(waermepumpen_pro_jahr, max(0, gas_aus - zu_h2))
        zu_sonstige = max(0, gas_aus - zu_h2 - zu_wp)
        gas = max(0, gas - gas_aus)
        fw = min(fw + zu_sonstige, gesamt)
        leitungen = leitungen + (neu_fw / 1500.0) * 2.5
        anteil = round(100 * fw / gesamt, 1) if gesamt else 0
        rows.append({"jahr": jahr, "fernwaerme_haushalte": fw, "gas_heizung_haushalte": gas, "gesamt_wohnungen": gesamt, "fernwaerme_anteil_pct": anteil, "fernwaerme_leitungen_km": round(leitungen, 0)})
    return pd.DataFrame(rows)


def build_projection_by_typ(params):
    """Dekarbonisierungspfade pro Gebäudetyp (Gas-Zählpunkte verbleibend). Regeln: EFH nur WP; Gas+FW immer FW; Zentral in FW-Heute immer FW; Dezentral erst Zentralisierung."""
    def get(key, default=0):
        return int(params.get(key, default) or 0)

    n_efh = get("gas_zaehlpunkte_einfamilienhauser", 25_000)
    n_zentral = get("gas_zaehlpunkte_zentral_beheizt", 420_000)
    n_dezentral = get("gas_zaehlpunkte_dezentral_beheizt", 180_000)
    n_gasfw = get("gas_zaehlpunkte_gas_und_fernwaerme", 85_000)
    n_dl = get("gas_zaehlpunkte_dienstleistung", 95_000)
    n_sonst = get("gas_zaehlpunkte_sonstige_nichtwohn", 35_000)

    wp_jahr = params.get("waermepumpen_pro_jahr", 4_000)
    fw_bis_30 = params.get("fernwaerme_anschluss_bis_2030", 12_000)
    fw_ab_30 = params.get("fernwaerme_anschluss_ab_2030", 30_000)
    dezentral_verzögerung = 5

    rows = []
    for jahr in range(BASISJAHR, ZIELJAHR + 1):
        if jahr == BASISJAHR:
            rows.append({"jahr": jahr, "typ": "Einfamilienhäuser", "gas_verbleibend": n_efh})
            rows.append({"jahr": jahr, "typ": "Zentral beheizt", "gas_verbleibend": n_zentral})
            rows.append({"jahr": jahr, "typ": "Dezentral beheizt", "gas_verbleibend": n_dezentral})
            rows.append({"jahr": jahr, "typ": "Gas + Fernwärme", "gas_verbleibend": n_gasfw})
            rows.append({"jahr": jahr, "typ": "Dienstleistung", "gas_verbleibend": n_dl})
            rows.append({"jahr": jahr, "typ": "Sonstige Nichtwohn", "gas_verbleibend": n_sonst})
            continue
        fw_jahr = fw_bis_30 if jahr <= 2030 else fw_ab_30
        delta = jahr - BASISJAHR
        # Gas+FW: immer Fernwärme (zuerst abgebaut)
        abzug_gasfw = min(n_gasfw, fw_jahr)
        n_gasfw = max(0, n_gasfw - abzug_gasfw)
        fw_rest = fw_jahr - abzug_gasfw
        # Zentral: Rest-Fernwärme
        abzug_zentral = min(n_zentral, fw_rest)
        n_zentral = max(0, n_zentral - abzug_zentral)
        # EFH: nur Wärmepumpen
        n_efh = max(0, n_efh - min(n_efh, wp_jahr))
        # Dezentral: erst nach Verzögerung
        if delta >= dezentral_verzögerung:
            abzug_dez = min(n_dezentral, fw_jahr // 4)
            n_dezentral = max(0, n_dezentral - abzug_dez)
        n_dl = max(0, n_dl - min(n_dl, (fw_jahr + wp_jahr) // 12))
        n_sonst = max(0, n_sonst - min(n_sonst, (fw_jahr + wp_jahr) // 15))
        rows.append({"jahr": jahr, "typ": "Einfamilienhäuser", "gas_verbleibend": n_efh})
        rows.append({"jahr": jahr, "typ": "Zentral beheizt", "gas_verbleibend": n_zentral})
        rows.append({"jahr": jahr, "typ": "Dezentral beheizt", "gas_verbleibend": n_dezentral})
        rows.append({"jahr": jahr, "typ": "Gas + Fernwärme", "gas_verbleibend": n_gasfw})
        rows.append({"jahr": jahr, "typ": "Dienstleistung", "gas_verbleibend": n_dl})
        rows.append({"jahr": jahr, "typ": "Sonstige Nichtwohn", "gas_verbleibend": n_sonst})
    return pd.DataFrame(rows)


def jahr_dekarbonisierung(proj_df, schwellwert=0):
    if proj_df is None or proj_df.empty:
        return None
    rest = proj_df[proj_df["gas_heizung_haushalte"] <= schwellwert]
    return int(rest["jahr"].min()) if not rest.empty else None


def init_szenarien():
    if "szenarien" not in st.session_state:
        st.session_state["szenarien"] = []


def default_params():
    p = {
        "fernwaerme_anschluss_bis_2030": 12_000,
        "fernwaerme_anschluss_ab_2030": 30_000,
        "heizungstausch_pro_jahr": 15_000,
        "anteil_gas_zu_wasserstoff": 5,
        "waermepumpen_pro_jahr": 4_000,
        "kochgas_austausch_pro_jahr": 12_000,
        "wachstum_wohnungen_pro_jahr": 0.4,
    }
    # Gas-Zählpunkte pro Gebäudetyp
    p["gas_zaehlpunkte_einfamilienhauser"] = 25_000
    p["gas_zaehlpunkte_zentral_beheizt"] = 420_000
    p["gas_zaehlpunkte_dezentral_beheizt"] = 180_000
    p["gas_zaehlpunkte_gas_und_fernwaerme"] = 85_000
    p["gas_zaehlpunkte_dienstleistung"] = 95_000
    p["gas_zaehlpunkte_sonstige_nichtwohn"] = 35_000
    p["umstellung_fernwaerme_heute_fernwaerme_pct"] = 95
    p["umstellung_fernwaerme_zukunft_fernwaerme_pct"] = 88
    p["umstellung_pioniergebiete_fernwaerme_pct"] = 85
    p["umstellung_lokale_gemeinsam_fernwaerme_pct"] = 45
    p["umstellung_lokale_individuell_fernwaerme_pct"] = 15
    return p


# Logo als SVG (immer sichtbar, auch ohne Datei)
LOGO_SVG = base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 44" width="140" height="44">'
    b'<rect width="140" height="44" rx="6" fill="#FF5A64"/>'
    b'<text x="70" y="28" font-family="Arial,sans-serif" font-size="14" font-weight="bold" fill="white" text-anchor="middle">Stadt Wien</text>'
    b'</svg>'
).decode()

CD_CSS = f"""
<style>
    :root {{
        --morgenrot: {CD["morgenrot"]};
        --weiss: {CD["weiss"]};
        --text: {CD["text_dunkel"]};
        --muted: {CD["text_hell"]};
        --bg: #f5f6f8;
        --card-bg: {CD["card_bg"]};
        --border: {CD["border"]};
    }}
    .stApp {{ background: var(--bg); }}
    .main .block-container {{ padding-top: 1.25rem; padding-bottom: 2.5rem; max-width: 1320px; }}
    h1, h2, h3 {{ font-family: {CD_FONT} !important; color: var(--text) !important; font-weight: 700; }}
    h1 {{ font-size: 1.6rem !important; }}
    h2 {{ font-size: 1.28rem !important; margin-top: 1.5rem !important; }}
    h3 {{ font-size: 1.05rem !important; }}
    p, li, span, .stMarkdown {{ font-family: {CD_FONT}; color: var(--text) !important; }}
    /* Lesbarkeit: alle Labels und Texte auf hellem Grund dunkel */
    label {{ color: var(--text) !important; }}
    .stSelectbox label, .stSlider label, .stNumberInput label, .stExpander label {{ color: var(--text) !important; }}
    [data-testid="stExpander"] label, [data-testid="stExpander"] p {{ color: var(--text) !important; }}
    .stCaption {{ color: var(--muted) !important; }}
    .stSidebar label, .stSidebar p, .stSidebar span {{ color: var(--text) !important; }}
    .app-header {{
        background: linear-gradient(135deg, var(--morgenrot) 0%, #e84a54 100%);
        color: var(--weiss) !important;
        padding: 1.25rem 1.75rem;
        margin-bottom: 1.5rem;
        border-radius: 14px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        gap: 1.25rem;
        flex-wrap: wrap;
    }}
    .app-header h1 {{ color: var(--weiss) !important; margin: 0 !important; font-size: 1.5rem !important; }}
    .app-header p {{ color: rgba(255,255,255,0.95) !important; margin: 0.25rem 0 0 0 !important; font-size: 0.9rem; }}
    .app-header .logo-wrap {{ flex-shrink: 0; }}
    .app-header .logo-wrap img {{ height: 46px; width: auto; display: block; }}
    .card-modern {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.15rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        font-family: {CD_FONT};
        color: var(--text) !important;
    }}
    .card-modern h3 {{ margin-top: 0 !important; color: var(--text) !important; }}
    .card-modern p {{ color: var(--text) !important; }}
    .kpi-modern {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.1rem;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        color: var(--text) !important;
    }}
    .kpi-modern .value {{ font-size: 1.5rem; font-weight: 700; color: var(--text) !important; }}
    .kpi-modern .label {{ font-size: 0.78rem; color: var(--muted) !important; margin-top: 0.2rem; }}
    a {{ color: var(--morgenrot) !important; font-weight: 600; }}
    .stSidebar {{
        background: var(--card-bg);
        border-right: 1px solid var(--border);
    }}
    .stSidebar .stMarkdown {{ color: var(--text) !important; }}
    [data-testid="stExpander"] {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        color: var(--text) !important;
    }}
    .info-box {{ background: #f0f7ff; border-left: 4px solid var(--morgenrot); padding: 0.9rem 1.1rem; margin: 0.75rem 0; border-radius: 0 8px 8px 0; color: var(--text) !important; }}
</style>
"""


def apply_plot_theme(fig, title_text=""):
    fig.update_layout(
        title=dict(text=title_text or " ", font=dict(size=14, color=CD["text_dunkel"], family=CD_FONT), x=0.02, xanchor="left", y=0.98, yanchor="top"),
        paper_bgcolor=CD["weiss"],
        plot_bgcolor=CD["weiss"],
        font=dict(family=CD_FONT, size=11, color=CD["text_dunkel"]),
        margin=dict(t=52, b=88, l=56, r=40),
        legend=dict(
            font=dict(size=11, color=CD["text_dunkel"]),
            bgcolor=CD["weiss"],
            bordercolor=CD["border"],
            borderwidth=1,
            orientation="h",
            yanchor="top",
            y=-0.16,
            xanchor="left",
            x=0,
        ),
        xaxis=dict(showgrid=True, gridcolor=CD["border"], zeroline=False, title_font=dict(color=CD["text_dunkel"])),
        yaxis=dict(showgrid=True, gridcolor=CD["border"], zeroline=False, title_font=dict(color=CD["text_dunkel"])),
        hoverlabel=dict(bgcolor=CD["weiss"], bordercolor=CD["border"], font=dict(color=CD["text_dunkel"])),
    )
    return fig


def render_header():
    st.markdown(CD_CSS, unsafe_allow_html=True)
    LOGO_PATH = ASSETS_DIR / "logo.png"
    if LOGO_PATH.exists():
        try:
            logo_bytes = LOGO_PATH.read_bytes()
            b64 = base64.b64encode(logo_bytes).decode()
            suffix = LOGO_PATH.suffix.lower()
            mime = "image/png" if suffix == ".png" else "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/svg+xml"
            logo_html = f'<div class="logo-wrap"><img src="data:{mime};base64,{b64}" alt="Stadt Wien" /></div>'
        except Exception:
            logo_html = f'<div class="logo-wrap"><img src="data:image/svg+xml;base64,{LOGO_SVG}" alt="Stadt Wien" /></div>'
    else:
        logo_html = f'<div class="logo-wrap"><img src="data:image/svg+xml;base64,{LOGO_SVG}" alt="Stadt Wien" /></div>'
    st.markdown(
        f"""
        <div class="app-header">
            {logo_html}
            <div>
                <h1>Raus aus Gas</h1>
                <p>Wiener Wärmeversorgung bis 2040 – Historie, Themenschwerpunkte und modellierte Ausbaupfade</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_historie(data):
    df = data.get("fernwaerme")
    if df is None or df.empty:
        st.info("Keine historischen Daten geladen.")
        return
    df_hist = df[df["jahr"] <= BASISJAHR].copy().sort_values("jahr")

    st.subheader("Blick auf das Historische")
    st.markdown("Entwicklung der Fernwärme- und Gas-Heizung in Wien seit 2010. Datenbasis: Stadt Wien / Wien Energie.")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=df_hist["jahr"], y=df_hist["fernwaerme_haushalte"], name="Fernwärme-Haushalte", line=dict(color=CD["frischgruen"], width=2.5), mode="lines+markers"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df_hist["jahr"], y=df_hist["gas_heizung_haushalte"], name="Gas-Heizung (Haushalte)", line=dict(color=CD["morgenrot"], width=2), mode="lines+markers"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df_hist["jahr"], y=df_hist["fernwaerme_anteil_pct"], name="Fernwärme-Anteil (%)", line=dict(color=CD["wasserblau"], width=2, dash="dot"), mode="lines+markers"),
        secondary_y=True,
    )
    fig.update_xaxes(title_text="Jahr")
    fig.update_yaxes(title_text="Haushalte", secondary_y=False)
    fig.update_yaxes(title_text="Fernwärme-Anteil (%)", secondary_y=True, range=[0, 55])
    fig = apply_plot_theme(fig, title_text="Fernwärme und Gas-Heizung – historische Entwicklung")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(x=df_hist["jahr"], y=df_hist["fernwaerme_leitungen_km"], name="Fernwärme-Leitungen (km)", marker_color=CD["wasserblau"], text=df_hist["fernwaerme_leitungen_km"].astype(int), textposition="outside")
    )
    fig2.update_layout(xaxis_title="Jahr", yaxis_title="Leitungen (km)")
    fig2 = apply_plot_theme(fig2, title_text="Fernwärme-Netz – Leitungsänge (km)")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown(
        '<div class="card-modern"><h3>Hintergrund</h3>'
        '<p>Seit 2010 ist die Zahl der Fernwärme-Haushalte von etwa 342.000 auf über 460.000 (2023) gestiegen. '
        'Ziel bis 2040: Fernwärmeanteil <strong>56 %</strong>. '
        '<a href="https://www.wien.gv.at/umwelt/waermeplan-2040" target="_blank">Wiener Wärmeplan 2040</a>.</p></div>',
        unsafe_allow_html=True,
    )


def page_themenschwerpunkte(data):
    st.subheader("Themenschwerpunkte")
    st.markdown("Ziele, Wärmequellen, Pioniergebiete und Links.")

    df_q = data.get("quellen")
    if df_q is not None and not df_q.empty:
        df_23 = df_q[df_q["jahr"] == 2023].copy().sort_values("anteil_pct", ascending=True)
        farben = [CD["morgenrot"], CD["frischgruen"], CD["wasserblau"], CD["goldgelb"], CD["nebelgrau"]]
        fig = go.Figure()
        for i, (_, row) in enumerate(df_23.iterrows()):
            fig.add_trace(go.Bar(y=[row["quelle"]], x=[row["anteil_pct"]], orientation="h", name=row["quelle"], marker_color=farben[i % len(farben)]))
        fig.update_layout(xaxis_title="Anteil (%)", yaxis_title="", barmode="overlay", showlegend=True)
        fig = apply_plot_theme(fig, title_text="Wärmequellen der Fernwärme – Anteile 2023")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            '<div class="card-modern"><p>Derzeit stammt etwa die Hälfte der Wiener Fernwärme aus <strong>Erdgas-KWK</strong>. Bis 2040 klimaneutral.</p></div>',
            unsafe_allow_html=True,
        )

    z = data.get("ziele")
    if z:
        st.markdown("**Ziele des Programms „Raus aus Gas“**")
        for item in z.get("ziele", []):
            st.markdown(
                f'<div class="card-modern"><strong>{item["kennzahl"]}</strong><br>'
                f'Aktuell: {item["aktuell"]} {item["einheit"]} → Ziel 2040: {item["ziel_2040"]} {item["einheit"]}</div>',
                unsafe_allow_html=True,
            )

    df_p = data.get("pioniergebiete")
    if df_p is not None and not df_p.empty:
        st.dataframe(df_p, use_container_width=True, hide_index=True)

    st.markdown(
        '<div class="card-modern"><h3>Links</h3><ul>'
        '<li><a href="https://www.wien.gv.at/umwelt/programm-raus-aus-gas" target="_blank">Programm Raus aus Gas</a></li>'
        '<li><a href="https://www.wien.gv.at/umwelt/waermeplan-2040" target="_blank">Wiener Wärmeplan 2040</a></li>'
        '<li><a href="https://www.wien.gv.at/umwelt/foerderungen-raus-aus-gas" target="_blank">Förderungen</a></li>'
        '<li><a href="https://www.wien.gv.at/spezial/energiebericht/" target="_blank">Energiebericht Stadt Wien</a></li></ul></div>',
        unsafe_allow_html=True,
    )


def page_szenarien(data):
    init_szenarien()
    df_hist = data.get("fernwaerme")
    if df_hist is None or df_hist.empty:
        st.warning("Keine Basisdaten – bitte Fernwärme-Historie laden.")
        return

    st.subheader("Ausbaupfade modellieren")
    st.markdown("Szenarien anlegen: Gas-Zählpunkte pro Gebäudetyp, Umstellung nach Gebietstyp (Wärmeplan 2040) und Ausbauparameter.")

    # —— Szenarien verwalten: Löschen klar angeboten ——
    szenarien = st.session_state["szenarien"]
    if szenarien:
        with st.expander("Szenarien verwalten – Szenario löschen", expanded=False):
            st.caption("Wählen Sie ein Szenario und klicken Sie auf Löschen.")
            to_delete = st.selectbox("Szenario zum Löschen wählen", [s["name"] for s in szenarien], key="del_sel")
            if st.button("Ausgewähltes Szenario löschen", type="secondary", key="del_btn"):
                st.session_state["szenarien"] = [s for s in szenarien if s["name"] != to_delete]
                st.rerun()

    namen = [s["name"] for s in st.session_state["szenarien"]]
    optionen = ["Neues Szenario"] + namen
    auswahl = st.selectbox("Szenario zum Bearbeiten / Speichern wählen", optionen, key="szenario_auswahl")
    if auswahl == "Neues Szenario":
        szenario_name = st.text_input("Name des neuen Szenarios", value="Szenario 1", key="new_name")
        params = default_params()
    else:
        szenario_name = auswahl
        idx = namen.index(auswahl)
        params = copy.deepcopy(st.session_state["szenarien"][idx]["params"])

    # —— Dekarbonisierungsregeln (Info) ——
    st.markdown(
        '<div class="info-box">'
        '<strong>Dekarbonisierungsregeln (Wärmeplan 2040):</strong><ul style="margin:0.5rem 0 0 1rem;">'
        '<li><strong>Einfamilienhäuser</strong> werden ausschließlich mittels Wärmepumpen decarbonisiert.</li>'
        '<li><strong>Zentral beheizte Gebäude</strong> in „Fernwärme Heute“-Gebieten werden immer an die Fernwärme angeschlossen.</li>'
        '<li><strong>Gebäude mit Gas und Fernwärme</strong> werden immer auf Fernwärme umgestellt.</li>'
        '<li><strong>Dezentral beheizte Gebäude</strong> müssen in einem ersten Schritt zentralisiert werden (danach Anschluss Fernwärme bzw. lokale Wärme).</li>'
        '</ul></div>',
        unsafe_allow_html=True,
    )

    # —— Gebäudebestand: Gas-Zählpunkte ——
    with st.expander("Gebäudebestand – Anzahl Gas-Zählpunkte pro Gebäudetyp", expanded=True):
        st.caption("Eingabe in Anzahl Gas-Zählpunkte (Zähler) pro Kategorie.")
        c1, c2 = st.columns(2)
        with c1:
            params["gas_zaehlpunkte_einfamilienhauser"] = st.number_input("Einfamilienhäuser (Gas-Zählpunkte)", 0, 100_000, params.get("gas_zaehlpunkte_einfamilienhauser", 25_000), 1000, key="gb_efh")
            params["gas_zaehlpunkte_zentral_beheizt"] = st.number_input("Zentral beheizte Gebäude (Gas-Zählpunkte)", 0, 600_000, params.get("gas_zaehlpunkte_zentral_beheizt", 420_000), 5000, key="gb_zentral")
            params["gas_zaehlpunkte_dezentral_beheizt"] = st.number_input("Dezentral beheizte Gebäude (Gas-Zählpunkte)", 0, 400_000, params.get("gas_zaehlpunkte_dezentral_beheizt", 180_000), 5000, key="gb_dezentral")
        with c2:
            params["gas_zaehlpunkte_gas_und_fernwaerme"] = st.number_input("Gas und Fernwärme (Gas-Zählpunkte)", 0, 200_000, params.get("gas_zaehlpunkte_gas_und_fernwaerme", 85_000), 1000, key="gb_gasfw")
            params["gas_zaehlpunkte_dienstleistung"] = st.number_input("Dienstleistungsgebäude (Gas-Zählpunkte)", 0, 200_000, params.get("gas_zaehlpunkte_dienstleistung", 95_000), 1000, key="gb_dl")
            params["gas_zaehlpunkte_sonstige_nichtwohn"] = st.number_input("Sonstige Nichtwohngebäude (Gas-Zählpunkte)", 0, 100_000, params.get("gas_zaehlpunkte_sonstige_nichtwohn", 35_000), 1000, key="gb_sonst")

    # —— Umstellung nach Gebietstyp ——
    with st.expander("Umstellung nach Gebietstyp (Wiener Wärmeplan 2040)", expanded=True):
        st.caption("Anteil Umstellung auf Fernwärme (Rest: Wärmepumpen / lokale Wärme).")
        st.markdown("[Wiener Wärmeplan 2040](https://www.wien.gv.at/umwelt/waermeplan-2040)")
        umstellung_keys = [
            ("umstellung_fernwaerme_heute_fernwaerme_pct", "Fernwärme Heute"),
            ("umstellung_fernwaerme_zukunft_fernwaerme_pct", "Fernwärme Zukunft"),
            ("umstellung_pioniergebiete_fernwaerme_pct", "Pioniergebiete"),
            ("umstellung_lokale_gemeinsam_fernwaerme_pct", "Lokale Wärme gemeinsam"),
            ("umstellung_lokale_individuell_fernwaerme_pct", "Lokale Wärme individuell"),
        ]
        for key, label in umstellung_keys:
            params[key] = st.slider(f"{label} – Anteil Fernwärme (%)", 0, 100, params.get(key, 50), 5, key=f"um_{key}")

    # —— Ausbauparameter ——
    with st.expander("Ausbauparameter (Fernwärme, Heizungstausch, Wärmepumpen)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            params["fernwaerme_anschluss_bis_2030"] = st.slider("Fernwärme-Anschlüsse/Jahr bis 2030", 5_000, 25_000, params.get("fernwaerme_anschluss_bis_2030", 12_000), 1_000)
            params["fernwaerme_anschluss_ab_2030"] = st.slider("Fernwärme-Anschlüsse/Jahr ab 2030", 15_000, 45_000, params.get("fernwaerme_anschluss_ab_2030", 30_000), 1_000)
            params["heizungstausch_pro_jahr"] = st.slider("Heizungstausch (Gas raus) pro Jahr", 5_000, 35_000, params.get("heizungstausch_pro_jahr", 15_000), 1_000)
            params["anteil_gas_zu_wasserstoff"] = st.slider("Anteil Gas → Wasserstoff (%)", 0, 40, params.get("anteil_gas_zu_wasserstoff", 5), 5)
        with c2:
            params["waermepumpen_pro_jahr"] = st.slider("Wärmepumpen pro Jahr", 1_000, 15_000, params.get("waermepumpen_pro_jahr", 4_000), 500)
            params["kochgas_austausch_pro_jahr"] = st.slider("Kochgas-Austausch pro Jahr", 5_000, 25_000, params.get("kochgas_austausch_pro_jahr", 12_000), 1_000)
            params["wachstum_wohnungen_pro_jahr"] = st.slider("Wachstum Wohnungen (%/Jahr)", 0.0, 1.5, params.get("wachstum_wohnungen_pro_jahr", 0.4), 0.1)

    col_save, _ = st.columns(2)
    with col_save:
        if st.button("Szenario speichern / aktualisieren"):
            proj = build_projection(params, df_hist)
            jahr_dec = jahr_dekarbonisierung(proj)
            entry = {"name": szenario_name, "params": copy.deepcopy(params), "proj_df": proj, "jahr_dekarbonisierung": jahr_dec}
            if auswahl == "Neues Szenario":
                st.session_state["szenarien"] = st.session_state["szenarien"] + [entry]
            else:
                idx = namen.index(auswahl)
                st.session_state["szenarien"][idx] = entry
            st.rerun()

    szenarien = st.session_state["szenarien"]
    if not szenarien:
        st.info("Legen Sie oben mindestens ein Szenario an, um KPIs und Entwicklungspfade zu sehen.")
        return

    st.markdown("---")
    st.markdown("**KPI und Entwicklungspfade**")
    kpi_szenario = st.selectbox("KPIs anzeigen für", [s["name"] for s in szenarien], key="kpi_szenario")
    idx_kpi = next((i for i, s in enumerate(szenarien) if s["name"] == kpi_szenario), 0)
    proj = szenarien[idx_kpi]["proj_df"]
    if not proj.empty:
        target = proj[proj["jahr"] == ZIELJAHR].iloc[0]
        latest_hist = df_hist[df_hist["jahr"] == BASISJAHR].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="kpi-modern"><div class="value">{int(latest_hist["fernwaerme_haushalte"]):,}</div><div class="label">Fernwärme heute ({BASISJAHR})</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="kpi-modern"><div class="value">{int(target["fernwaerme_haushalte"]):,}</div><div class="label">Fernwärme 2040 ({kpi_szenario})</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="kpi-modern"><div class="value">{target["fernwaerme_anteil_pct"]:.1f} %</div><div class="label">Fernwärmeanteil 2040</div></div>', unsafe_allow_html=True)
        with c4:
            jd = szenarien[idx_kpi].get("jahr_dekarbonisierung")
            st.markdown(f'<div class="kpi-modern"><div class="value">{jd or "–"}</div><div class="label">Dekarbonisierung (Jahr)</div></div>', unsafe_allow_html=True)

    # —— Grafik: Gebäudetypen und Dekarbonisierungspfade (ausgewähltes Szenario) ——
    st.subheader("Gebäudetypen und Dekarbonisierungspfade")
    sz_for_typ = st.selectbox("Szenario für Gebäudetypen-Grafik", [s["name"] for s in szenarien], key="typ_szenario")
    idx_typ = next((i for i, s in enumerate(szenarien) if s["name"] == sz_for_typ), 0)
    df_typ = build_projection_by_typ(szenarien[idx_typ]["params"])
    farben_typ = [CD["morgenrot"], CD["frischgruen"], CD["wasserblau"], CD["goldgelb"], CD["nebelgrau"], "#888"]
    fig_typ = go.Figure()
    for i, typ in enumerate(df_typ["typ"].unique()):
        d = df_typ[df_typ["typ"] == typ]
        fig_typ.add_trace(
            go.Scatter(x=d["jahr"], y=d["gas_verbleibend"], name=typ, line=dict(color=farben_typ[i % len(farben_typ)], width=2), mode="lines+markers")
        )
    fig_typ.update_layout(xaxis_title="Jahr", yaxis_title="Gas-Zählpunkte (verbleibend)")
    fig_typ = apply_plot_theme(fig_typ, title_text="Dekarbonisierungspfade pro Gebäudetyp – Gas-Zählpunkte verbleibend (" + sz_for_typ + ")")
    st.plotly_chart(fig_typ, use_container_width=True)

    szenario_farben = [CD["morgenrot"], CD["frischgruen"], CD["wasserblau"], CD["goldgelb"], CD["nebelgrau"]]
    df_hist_plot = df_hist[df_hist["jahr"] <= BASISJAHR].copy().sort_values("jahr")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df_hist_plot["jahr"], y=df_hist_plot["fernwaerme_haushalte"], name="Fernwärme (Historie)", line=dict(color=CD["frischgruen"], width=2.5), mode="lines+markers")
    )
    fig.add_trace(
        go.Scatter(x=df_hist_plot["jahr"], y=df_hist_plot["gas_heizung_haushalte"], name="Gas-Heizung (Historie)", line=dict(color=CD["morgenrot"], width=2), mode="lines+markers")
    )
    for i, sz in enumerate(szenarien):
        proj_df = sz["proj_df"]
        if proj_df is None or proj_df.empty:
            continue
        farbe = szenario_farben[i % len(szenario_farben)]
        proj_lo = build_projection(sz["params"], df_hist, faktor=1.0 - KORRIDOR_RELATIV)
        proj_hi = build_projection(sz["params"], df_hist, faktor=1.0 + KORRIDOR_RELATIV)
        jahre = proj_df["jahr"].tolist()
        fig.add_trace(
            go.Scatter(x=jahre, y=proj_hi["fernwaerme_haushalte"], line=dict(width=0), showlegend=False, hoverinfo="skip")
        )
        fig.add_trace(
            go.Scatter(x=jahre, y=proj_lo["fernwaerme_haushalte"], fill="tonexty", fillcolor="rgba(255,90,100,0.12)", line=dict(width=0), showlegend=False, hoverinfo="skip")
        )
        fig.add_trace(
            go.Scatter(x=jahre, y=proj_df["fernwaerme_haushalte"], name=sz["name"] + " (Fernwärme)", line=dict(color=farbe, width=2, dash="dash"), mode="lines+markers")
        )
        fig.add_trace(
            go.Scatter(x=jahre, y=proj_df["gas_heizung_haushalte"], name=sz["name"] + " (Gas)", line=dict(color=farbe, width=1.5, dash="dot"), mode="lines+markers")
        )
    fig.update_layout(xaxis_title="Jahr", yaxis_title="Haushalte")
    fig = apply_plot_theme(fig, title_text="Entwicklungspfade: Fernwärme und Gas – Szenarien mit Schwankungsbreite (±12 %)")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(x=df_hist_plot["jahr"], y=df_hist_plot["fernwaerme_anteil_pct"], name="Fernwärme-Anteil (Historie)", line=dict(color=CD["wasserblau"], width=2), mode="lines+markers")
    )
    for i, sz in enumerate(szenarien):
        proj_df = sz["proj_df"]
        if proj_df is None or proj_df.empty:
            continue
        farbe = szenario_farben[i % len(szenario_farben)]
        proj_lo = build_projection(sz["params"], df_hist, faktor=1.0 - KORRIDOR_RELATIV)
        proj_hi = build_projection(sz["params"], df_hist, faktor=1.0 + KORRIDOR_RELATIV)
        jahre = proj_df["jahr"].tolist()
        fig2.add_trace(go.Scatter(x=jahre, y=proj_hi["fernwaerme_anteil_pct"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig2.add_trace(go.Scatter(x=jahre, y=proj_lo["fernwaerme_anteil_pct"], fill="tonexty", fillcolor="rgba(131,208,245,0.18)", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig2.add_trace(
            go.Scatter(x=jahre, y=proj_df["fernwaerme_anteil_pct"], name=sz["name"], line=dict(color=farbe, width=2, dash="dash"), mode="lines+markers")
        )
    fig2.update_layout(xaxis_title="Jahr", yaxis_title="Fernwärme-Anteil (%)")
    fig2 = apply_plot_theme(fig2, title_text="Fernwärmeanteil – Szenarien mit Korridor")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Dekarbonisierung (Jahr: Gas-Heizung ≈ 0)**")
    rows = [{"Szenario": s["name"], "Dekarbonisierung (Jahr)": s.get("jahr_dekarbonisierung") or "–"} for s in szenarien]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown(
        '<div class="card-modern"><h3>Zum Modell</h3>'
        '<p>Korridore: ±12 % Schwankungsbreite. Umstellung nach <strong>Wiener Wärmeplan 2040</strong>. '
        'Gebäudetypen: Einfamilienhäuser nur Wärmepumpen; Gas+Fernwärme immer Fernwärme; Zentral in Fernwärme-Heute-Gebieten immer Fernwärme; Dezentral erst Zentralisierung.</p></div>',
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="Raus aus Gas – Wien", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")
    render_header()
    data = load_data()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Bereich",
        ["Historie", "Themenschwerpunkte", "Szenarien & Ausbaupfade"],
        label_visibility="collapsed",
    )

    if page == "Historie":
        page_historie(data)
    elif page == "Themenschwerpunkte":
        page_themenschwerpunkte(data)
    else:
        page_szenarien(data)

    st.sidebar.caption("Stadt Wien, Wien Energie. Stand 2024.")


if __name__ == "__main__":
    main()
