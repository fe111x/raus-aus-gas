"""
Raus aus Gas – Wiener Wärmeversorgung bis 2040.
Strava-inspiriertes Design, sauberes Szenario-Management.
Start: streamlit run app/dashboard.py
"""

import copy
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

# Core-Logik
from core.config import BASISJAHR, ZIELJAHR, KORRIDOR_RELATIV, default_params, GEBAEUDETYPEN, GEBIETSTYPEN
from core.data_loader import load_data
from core.scenario_engine import build_projection, build_projection_by_type, jahr_dekarbonisierung

# Theme
from theme import get_css, COLORS


def apply_plot_theme(fig, title_text=""):
    """Plotly-Theme mit App-Farben."""
    c = COLORS
    fig.update_layout(
        title=dict(text=title_text or " ", font=dict(size=14, color=c["text"], family="Inter"), x=0.02, xanchor="left", y=0.98),
        paper_bgcolor=c["bg_card"],
        plot_bgcolor=c["bg_card"],
        font=dict(family="Inter", size=11, color=c["text"]),
        margin=dict(t=48, b=80, l=56, r=40),
        legend=dict(
            font=dict(size=11, color=c["text"]),
            bgcolor=c["bg_card"],
            bordercolor=c["border"],
            borderwidth=1,
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="left",
            x=0,
        ),
        xaxis=dict(showgrid=True, gridcolor=c["border"], zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=c["border"], zeroline=False),
        hoverlabel=dict(bgcolor=c["bg_card"], bordercolor=c["border"], font=dict(color=c["text"])),
    )
    return fig


# ==================== Session State ====================

def init_session():
    if "szenarien" not in st.session_state:
        st.session_state["szenarien"] = []
    if "selected_szenario" not in st.session_state:
        st.session_state["selected_szenario"] = None
    if "show_create" not in st.session_state:
        st.session_state["show_create"] = False


# ==================== Header ====================

def render_header():
    st.markdown(get_css(), unsafe_allow_html=True)
    st.markdown(
        """
        <div class="raus-header">
            <div>
                <h1>Raus aus Gas</h1>
                <p>Wiener Wärmeversorgung bis 2040 · Historie, Ziele und modellierte Szenarien</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==================== Seite: Historie ====================

def page_historie(data):
    df = data.get("fernwaerme")
    if df is None or df.empty:
        st.info("Keine historischen Daten.")
        return

    df_hist = df[df["jahr"] <= BASISJAHR].copy().sort_values("jahr")
    c = COLORS

    st.subheader("Entwicklung seit 2010")
    st.markdown("Fernwärme, Gas-Heizung und Netzausbau. Quelle: Stadt Wien / Wien Energie.")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=df_hist["jahr"], y=df_hist["fernwaerme_haushalte"], name="Fernwärme", line=dict(color=c["chart_2"], width=2.5), mode="lines+markers"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df_hist["jahr"], y=df_hist["gas_heizung_haushalte"], name="Gas-Heizung", line=dict(color=c["warning"], width=2), mode="lines+markers"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df_hist["jahr"], y=df_hist["fernwaerme_anteil_pct"], name="Fernwärme-Anteil (%)", line=dict(color=c["chart_3"], width=2, dash="dot"), mode="lines+markers"),
        secondary_y=True,
    )
    fig.update_xaxes(title_text="Jahr")
    fig.update_yaxes(title_text="Haushalte", secondary_y=False)
    fig.update_yaxes(title_text="Fernwärme-Anteil (%)", secondary_y=True, range=[0, 60])
    apply_plot_theme(fig, "Fernwärme und Gas – historische Entwicklung")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(x=df_hist["jahr"], y=df_hist["fernwaerme_leitungen_km"], name="Leitungen (km)", marker_color=c["chart_3"], text=df_hist["fernwaerme_leitungen_km"].astype(int), textposition="outside")
    )
    fig2.update_layout(xaxis_title="Jahr", yaxis_title="km")
    apply_plot_theme(fig2, "Fernwärme-Netz – Leitungsänge")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown(
        '<div class="raus-card"><h3>Hintergrund</h3>'
        '<p>Fernwärme-Haushalte: von ca. 342.000 (2010) auf 460.000 (2023). Ziel 2040: <strong>56 %</strong> Fernwärmeanteil. '
        '<a href="https://www.wien.gv.at/umwelt/waermeplan-2040" target="_blank">Wiener Wärmeplan 2040</a></p></div>',
        unsafe_allow_html=True,
    )


# ==================== Seite: Themenschwerpunkte ====================

def page_themen(data):
    st.subheader("Ziele & Wärmequellen")
    c = COLORS

    df_q = data.get("quellen")
    if df_q is not None and not df_q.empty:
        df_23 = df_q[df_q["jahr"] == 2023].copy().sort_values("anteil_pct", ascending=True)
        colors_chart = [c["chart_1"], c["chart_2"], c["chart_3"], c["chart_5"], c["chart_6"]]
        fig = go.Figure()
        for i, (_, row) in enumerate(df_23.iterrows()):
            fig.add_trace(go.Bar(y=[row["quelle"]], x=[row["anteil_pct"]], orientation="h", marker_color=colors_chart[i % len(colors_chart)]))
        fig.update_layout(xaxis_title="Anteil (%)", barmode="overlay")
        apply_plot_theme(fig, "Wärmequellen der Fernwärme 2023")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('<div class="raus-card"><p>~50 % Erdgas-KWK heute. Ziel 2040: klimaneutral.</p></div>', unsafe_allow_html=True)

    z = data.get("ziele")
    if z:
        st.markdown("**Ziele des Programms „Raus aus Gas“**")
        for item in z.get("ziele", []):
            st.markdown(
                f'<div class="raus-card"><strong>{item["kennzahl"]}</strong><br>'
                f'Aktuell: {item["aktuell"]} {item["einheit"]} → Ziel 2040: {item["ziel_2040"]} {item["einheit"]}</div>',
                unsafe_allow_html=True,
            )

    df_p = data.get("pioniergebiete")
    if df_p is not None and not df_p.empty:
        st.dataframe(df_p, use_container_width=True, hide_index=True)

    st.markdown(
        '<div class="raus-card"><h3>Links</h3><ul>'
        '<li><a href="https://www.wien.gv.at/umwelt/programm-raus-aus-gas" target="_blank">Programm Raus aus Gas</a></li>'
        '<li><a href="https://www.wien.gv.at/umwelt/waermeplan-2040" target="_blank">Wiener Wärmeplan 2040</a></li>'
        '<li><a href="https://www.wien.gv.at/umwelt/foerderungen-raus-aus-gas" target="_blank">Förderungen</a></li>'
        '<li><a href="https://www.wien.gv.at/spezial/energiebericht/" target="_blank">Energiebericht</a></li></ul></div>',
        unsafe_allow_html=True,
    )


# ==================== Seite: Szenarien (sauberes Management) ====================

def page_szenarien(data):
    init_session()
    df_hist = data.get("fernwaerme")
    if df_hist is None or df_hist.empty:
        st.warning("Keine Basisdaten (Fernwärme-Historie) geladen.")
        return

    c = COLORS
    szenarien = st.session_state["szenarien"]

    # ----- Szenario-Management: Übersicht & Aktionen -----
    st.subheader("Szenarien")
    st.markdown("Szenarien anlegen, bearbeiten und löschen. Alle Parameter sind frei anpassbar.")

    # Szenario-Liste
    if szenarien:
        st.markdown("**Ihre Szenarien**")
        for i, sz in enumerate(szenarien):
            jd = sz.get("jahr_dekarbonisierung") or "–"
            cols = st.columns([3, 1, 0.5])
            with cols[0]:
                st.markdown(f"**{sz['name']}** · Dekarbonisierung: {jd}")
            with cols[1]:
                if st.button("Bearbeiten", key=f"edit_{i}"):
                    st.session_state["selected_szenario"] = sz["name"]
                    st.rerun()
            with cols[2]:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state["szenarien"] = [s for s in szenarien if s["name"] != sz["name"]]
                    if st.session_state.get("selected_szenario") == sz["name"]:
                        st.session_state["selected_szenario"] = None
                    st.rerun()
        st.markdown("---")

    # Neues Szenario oder Bearbeiten
    namen = [s["name"] for s in szenarien]
    selected = st.session_state.get("selected_szenario")

    if selected and selected in namen:
        idx = namen.index(selected)
        params = copy.deepcopy(szenarien[idx]["params"])
        szenario_name = st.text_input("Szenario-Name", value=selected, key="sz_name")
        is_edit = True
    else:
        params = default_params()
        szenario_name = st.text_input("Szenario-Name", value=f"Szenario {len(szenarien)+1}", key="sz_name")
        is_edit = False

    # Dekarbonisierungsregeln (Info)
    st.markdown(
        '<div class="raus-info"><strong>Dekarbonisierungsregeln (Wärmeplan 2040)</strong><ul style="margin:0.4rem 0 0 1rem;">'
        '<li>Einfamilienhäuser → nur Wärmepumpen</li>'
        '<li>Zentral beheizt (FW-Heute) → Fernwärme</li>'
        '<li>Gas + Fernwärme → immer Fernwärme</li>'
        '<li>Dezentral → erst Zentralisierung</li></ul></div>',
        unsafe_allow_html=True,
    )

    # Parameter: Gebäudebestand
    with st.expander("Gebäudebestand – Gas-Zählpunkte", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            params["gas_zaehlpunkte_einfamilienhauser"] = st.number_input("Einfamilienhäuser", 0, 100_000, params["gas_zaehlpunkte_einfamilienhauser"], 1000, key="gb_efh")
            params["gas_zaehlpunkte_zentral_beheizt"] = st.number_input("Zentral beheizt", 0, 600_000, params["gas_zaehlpunkte_zentral_beheizt"], 5000, key="gb_z")
            params["gas_zaehlpunkte_dezentral_beheizt"] = st.number_input("Dezentral beheizt", 0, 400_000, params["gas_zaehlpunkte_dezentral_beheizt"], 5000, key="gb_d")
        with c2:
            params["gas_zaehlpunkte_gas_und_fernwaerme"] = st.number_input("Gas + Fernwärme", 0, 200_000, params["gas_zaehlpunkte_gas_und_fernwaerme"], 1000, key="gb_gf")
            params["gas_zaehlpunkte_dienstleistung"] = st.number_input("Dienstleistung", 0, 200_000, params["gas_zaehlpunkte_dienstleistung"], 1000, key="gb_dl")
            params["gas_zaehlpunkte_sonstige_nichtwohn"] = st.number_input("Sonstige Nichtwohn", 0, 100_000, params["gas_zaehlpunkte_sonstige_nichtwohn"], 1000, key="gb_s")

    # Parameter: Umstellung nach Gebietstyp
    with st.expander("Umstellung nach Gebietstyp – Anteil Fernwärme", expanded=True):
        for key, label, _ in GEBIETSTYPEN:
            param_key = f"umstellung_{key}_fernwaerme_pct"
            if param_key in params:
                params[param_key] = st.slider(label, 0, 100, params[param_key], 5, key=f"um_{param_key}")

    # Parameter: Ausbau
    with st.expander("Ausbauparameter", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            params["fernwaerme_anschluss_bis_2030"] = st.slider("FW-Anschlüsse/Jahr bis 2030", 5_000, 25_000, params["fernwaerme_anschluss_bis_2030"], 1_000, key="fw30")
            params["fernwaerme_anschluss_ab_2030"] = st.slider("FW-Anschlüsse/Jahr ab 2030", 15_000, 45_000, params["fernwaerme_anschluss_ab_2030"], 1_000, key="fw40")
            params["heizungstausch_pro_jahr"] = st.slider("Heizungstausch/Jahr", 5_000, 35_000, params["heizungstausch_pro_jahr"], 1_000, key="ht")
            params["anteil_gas_zu_wasserstoff"] = st.slider("Anteil Gas → H2 (%)", 0, 40, params["anteil_gas_zu_wasserstoff"], 5, key="h2")
        with c2:
            params["waermepumpen_pro_jahr"] = st.slider("Wärmepumpen/Jahr", 1_000, 15_000, params["waermepumpen_pro_jahr"], 500, key="wp")
            params["kochgas_austausch_pro_jahr"] = st.slider("Kochgas-Austausch/Jahr", 5_000, 25_000, params["kochgas_austausch_pro_jahr"], 1_000, key="kg")
            params["wachstum_wohnungen_pro_jahr"] = st.slider("Wachstum Wohnungen (%/Jahr)", 0.0, 1.5, params["wachstum_wohnungen_pro_jahr"], 0.1, key="wg")

    # Speichern
    if st.button("Szenario speichern" if is_edit else "Neues Szenario anlegen", type="primary"):
        if not szenario_name.strip():
            st.error("Bitte einen Namen eingeben.")
        else:
            proj = build_projection(params, df_hist)
            jahr_dec = jahr_dekarbonisierung(proj)
            entry = {"name": szenario_name.strip(), "params": copy.deepcopy(params), "proj_df": proj, "jahr_dekarbonisierung": jahr_dec}
            if is_edit:
                st.session_state["szenarien"][idx] = entry
            else:
                st.session_state["szenarien"] = st.session_state["szenarien"] + [entry]
            st.session_state["selected_szenario"] = None
            st.rerun()

    if is_edit:
        if st.button("Abbrechen"):
            st.session_state["selected_szenario"] = None
            st.rerun()

    st.markdown("---")

    # ----- KPIs und Grafiken -----
    if not szenarien:
        st.info("Legen Sie oben mindestens ein Szenario an.")
        return

    sz_choice = st.selectbox("Szenario für KPIs & Grafiken", [s["name"] for s in szenarien], key="sz_choice")
    idx_sz = next(i for i, s in enumerate(szenarien) if s["name"] == sz_choice)
    proj = szenarien[idx_sz]["proj_df"]
    target = proj[proj["jahr"] == ZIELJAHR].iloc[0]
    latest = df_hist[df_hist["jahr"] == BASISJAHR].iloc[0]
    jd = szenarien[idx_sz].get("jahr_dekarbonisierung")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="raus-kpi"><div class="value">{int(latest["fernwaerme_haushalte"]):,}</div><div class="label">Fernwärme heute</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="raus-kpi"><div class="value">{int(target["fernwaerme_haushalte"]):,}</div><div class="label">Fernwärme 2040</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="raus-kpi"><div class="value">{target["fernwaerme_anteil_pct"]:.1f} %</div><div class="label">FW-Anteil 2040</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="raus-kpi"><div class="value">{jd or "–"}</div><div class="label">Dekarbonisierung</div></div>', unsafe_allow_html=True)

    st.subheader("Dekarbonisierungspfade pro Gebäudetyp")
    df_typ = build_projection_by_type(szenarien[idx_sz]["params"])
    colors_typ = [c["chart_1"], c["chart_2"], c["chart_3"], c["chart_5"], c["chart_4"], c["chart_6"]]
    fig_typ = go.Figure()
    for i, typ in enumerate(df_typ["typ"].unique()):
        d = df_typ[df_typ["typ"] == typ]
        fig_typ.add_trace(go.Scatter(x=d["jahr"], y=d["gas_verbleibend"], name=typ, line=dict(color=colors_typ[i % len(colors_typ)], width=2), mode="lines+markers"))
    fig_typ.update_layout(xaxis_title="Jahr", yaxis_title="Gas-Zählpunkte verbleibend")
    apply_plot_theme(fig_typ, f"Dekarbonisierung – {sz_choice}")
    st.plotly_chart(fig_typ, use_container_width=True)

    st.subheader("Entwicklungspfade Fernwärme & Gas")
    df_hist_plot = df_hist[df_hist["jahr"] <= BASISJAHR].copy().sort_values("jahr")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_hist_plot["jahr"], y=df_hist_plot["fernwaerme_haushalte"], name="Fernwärme (Historie)", line=dict(color=c["chart_2"], width=2.5), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=df_hist_plot["jahr"], y=df_hist_plot["gas_heizung_haushalte"], name="Gas (Historie)", line=dict(color=c["warning"], width=2), mode="lines+markers"))

    sc_colors = [c["chart_1"], c["chart_2"], c["chart_3"], c["chart_5"], c["chart_4"]]
    for i, sz in enumerate(szenarien):
        pdf = sz["proj_df"]
        if pdf is None or pdf.empty:
            continue
        col = sc_colors[i % len(sc_colors)]
        proj_lo = build_projection(sz["params"], df_hist, faktor=1.0 - KORRIDOR_RELATIV)
        proj_hi = build_projection(sz["params"], df_hist, faktor=1.0 + KORRIDOR_RELATIV)
        jahre = pdf["jahr"].tolist()
        fig.add_trace(go.Scatter(x=jahre, y=proj_hi["fernwaerme_haushalte"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=jahre, y=proj_lo["fernwaerme_haushalte"], fill="tonexty", fillcolor=f"rgba(252,82,0,0.1)", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=jahre, y=pdf["fernwaerme_haushalte"], name=f"{sz['name']} (FW)", line=dict(color=col, width=2, dash="dash"), mode="lines+markers"))
        fig.add_trace(go.Scatter(x=jahre, y=pdf["gas_heizung_haushalte"], name=f"{sz['name']} (Gas)", line=dict(color=col, width=1.5, dash="dot"), mode="lines+markers"))

    fig.update_layout(xaxis_title="Jahr", yaxis_title="Haushalte")
    apply_plot_theme(fig, f"Fernwärme & Gas – Korridor ±{int(KORRIDOR_RELATIV*100)} %")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_hist_plot["jahr"], y=df_hist_plot["fernwaerme_anteil_pct"], name="Historie", line=dict(color=c["chart_3"], width=2), mode="lines+markers"))
    for i, sz in enumerate(szenarien):
        pdf = sz["proj_df"]
        if pdf is None or pdf.empty:
            continue
        col = sc_colors[i % len(sc_colors)]
        proj_lo = build_projection(sz["params"], df_hist, faktor=1.0 - KORRIDOR_RELATIV)
        proj_hi = build_projection(sz["params"], df_hist, faktor=1.0 + KORRIDOR_RELATIV)
        jahre = pdf["jahr"].tolist()
        fig2.add_trace(go.Scatter(x=jahre, y=proj_hi["fernwaerme_anteil_pct"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig2.add_trace(go.Scatter(x=jahre, y=proj_lo["fernwaerme_anteil_pct"], fill="tonexty", fillcolor="rgba(59,130,246,0.15)", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig2.add_trace(go.Scatter(x=jahre, y=pdf["fernwaerme_anteil_pct"], name=sz["name"], line=dict(color=col, width=2, dash="dash"), mode="lines+markers"))
    fig2.update_layout(xaxis_title="Jahr", yaxis_title="Fernwärme-Anteil (%)")
    apply_plot_theme(fig2, "Fernwärmeanteil – Szenarien")
    st.plotly_chart(fig2, use_container_width=True)

    rows = [{"Szenario": s["name"], "Dekarbonisierung (Jahr)": s.get("jahr_dekarbonisierung") or "–"} for s in szenarien]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ==================== Main ====================

def main():
    st.set_page_config(page_title="Raus aus Gas – Wien", page_icon="🌡️", layout="wide", initial_sidebar_state="expanded")
    render_header()
    data = load_data()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Bereich",
        ["Historie", "Themenschwerpunkte", "Szenarien"],
        label_visibility="collapsed",
    )

    if page == "Historie":
        page_historie(data)
    elif page == "Themenschwerpunkte":
        page_themen(data)
    else:
        page_szenarien(data)

    st.sidebar.caption("Stadt Wien · Wien Energie · Stand 2024")


if __name__ == "__main__":
    main()
