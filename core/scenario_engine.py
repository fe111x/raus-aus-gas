"""
Szenario-Rechner – Kernlogik für Projektionen.

Diese Datei ist bewusst modular und gut anpassbar:
- build_projection() – aggregierte Projektion Fernwärme vs. Gas
- build_projection_by_type() – Pfade pro Gebäudetyp
- Konstanten und Regeln (z.B. dezentral_verzögerung) hier anpassen
"""

import pandas as pd

from .config import BASISJAHR, ZIELJAHR, GEBAEUDETYPEN


def build_projection(params: dict, df_hist: pd.DataFrame, faktor: float = 1.0) -> pd.DataFrame:
    """
    Projektion von BASISJAHR bis ZIELJAHR (aggregiert).
    Ergebnis: jahr, fernwaerme_haushalte, gas_heizung_haushalte, gesamt_wohnungen,
              fernwaerme_anteil_pct, fernwaerme_leitungen_km
    """
    base = df_hist[df_hist["jahr"] == BASISJAHR].iloc[0]
    fw = int(base["fernwaerme_haushalte"])
    gas = int(base["gas_heizung_haushalte"])
    gesamt = int(base["gesamt_wohnungen"])
    leitungen = float(base["fernwaerme_leitungen_km"])

    def scale(x):
        return int(round(x * faktor)) if isinstance(x, (int, float)) else x

    anschluss_bis_2030 = scale(params.get("fernwaerme_anschluss_bis_2030", 12_000))
    anschluss_ab_2030 = scale(params.get("fernwaerme_anschluss_ab_2030", 30_000))
    heizungstausch = scale(params.get("heizungstausch_pro_jahr", 15_000))
    anteil_h2 = (params.get("anteil_gas_zu_wasserstoff", 5) or 0) / 100.0
    wp_jahr = scale(params.get("waermepumpen_pro_jahr", 4_000))
    wachstum = params.get("wachstum_wohnungen_pro_jahr", 0.4)

    rows = []
    for jahr in range(BASISJAHR, ZIELJAHR + 1):
        if jahr == BASISJAHR:
            rows.append({
                "jahr": jahr,
                "fernwaerme_haushalte": fw,
                "gas_heizung_haushalte": gas,
                "gesamt_wohnungen": gesamt,
                "fernwaerme_anteil_pct": round(100 * fw / gesamt, 1),
                "fernwaerme_leitungen_km": leitungen,
            })
            continue

        gesamt = int(gesamt * (1 + wachstum / 100.0))
        neu_fw = anschluss_bis_2030 if jahr <= 2030 else anschluss_ab_2030
        fw = min(fw + neu_fw, gesamt)
        gas_aus = min(gas, heizungstausch)
        zu_h2 = int(gas_aus * anteil_h2)
        zu_wp = min(wp_jahr, max(0, gas_aus - zu_h2))
        zu_sonstige = max(0, gas_aus - zu_h2 - zu_wp)
        gas = max(0, gas - gas_aus)
        fw = min(fw + zu_sonstige, gesamt)
        leitungen = leitungen + (neu_fw / 1500.0) * 2.5
        anteil = round(100 * fw / gesamt, 1) if gesamt else 0
        rows.append({
            "jahr": jahr,
            "fernwaerme_haushalte": fw,
            "gas_heizung_haushalte": gas,
            "gesamt_wohnungen": gesamt,
            "fernwaerme_anteil_pct": anteil,
            "fernwaerme_leitungen_km": round(leitungen, 0),
        })

    return pd.DataFrame(rows)


def build_projection_by_type(params: dict) -> pd.DataFrame:
    """
    Dekarbonisierungspfade pro Gebäudetyp (Gas-Zählpunkte verbleibend).
    Regeln (Wärmeplan 2040):
    - EFH: nur Wärmepumpen
    - Gas+FW: immer Fernwärme (zuerst)
    - Zentral: Rest-Fernwärme
    - Dezentral: erst nach Verzögerung
    """
    def get(key: str, default: int = 0) -> int:
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

    # Anpassbar: wie viele Jahre Verzögerung für dezentral
    dezentral_verzögerung = 5

    typ_labels = [t[1] for t in GEBAEUDETYPEN]
    counts = {
        typ_labels[0]: n_efh,
        typ_labels[1]: n_zentral,
        typ_labels[2]: n_dezentral,
        typ_labels[3]: n_gasfw,
        typ_labels[4]: n_dl,
        typ_labels[5]: n_sonst,
    }

    rows = []
    for jahr in range(BASISJAHR, ZIELJAHR + 1):
        if jahr == BASISJAHR:
            for typ, n in counts.items():
                rows.append({"jahr": jahr, "typ": typ, "gas_verbleibend": n})
            continue

        fw_jahr = fw_bis_30 if jahr <= 2030 else fw_ab_30
        delta = jahr - BASISJAHR

        # Gas+FW → immer Fernwärme (zuerst)
        abzug_gasfw = min(n_gasfw, fw_jahr)
        n_gasfw = max(0, n_gasfw - abzug_gasfw)
        fw_rest = fw_jahr - abzug_gasfw

        # Zentral → Rest-Fernwärme
        abzug_zentral = min(n_zentral, fw_rest)
        n_zentral = max(0, n_zentral - abzug_zentral)

        # EFH → nur Wärmepumpen
        n_efh = max(0, n_efh - min(n_efh, wp_jahr))

        # Dezentral → erst nach Verzögerung
        if delta >= dezentral_verzögerung:
            abzug_dez = min(n_dezentral, fw_jahr // 4)
            n_dezentral = max(0, n_dezentral - abzug_dez)

        n_dl = max(0, n_dl - min(n_dl, (fw_jahr + wp_jahr) // 12))
        n_sonst = max(0, n_sonst - min(n_sonst, (fw_jahr + wp_jahr) // 15))

        counts = {
            typ_labels[0]: n_efh,
            typ_labels[1]: n_zentral,
            typ_labels[2]: n_dezentral,
            typ_labels[3]: n_gasfw,
            typ_labels[4]: n_dl,
            typ_labels[5]: n_sonst,
        }
        for typ, n in counts.items():
            rows.append({"jahr": jahr, "typ": typ, "gas_verbleibend": n})

    return pd.DataFrame(rows)


def jahr_dekarbonisierung(proj_df: pd.DataFrame, schwellwert: int = 0) -> int | None:
    """Jahr, ab dem Gas-Heizung <= schwellwert."""
    if proj_df is None or proj_df.empty:
        return None
    rest = proj_df[proj_df["gas_heizung_haushalte"] <= schwellwert]
    return int(rest["jahr"].min()) if not rest.empty else None
