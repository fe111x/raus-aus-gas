"""
Konfiguration für den Szenario-Rechner.
Hier alle Konstanten, Parameter-Defaults und Gebäudetypen anpassen.
"""

BASISJAHR = 2023
ZIELJAHR = 2040
KORRIDOR_RELATIV = 0.12  # ±12 % Schwankungsbreite bei Projektionen

# Gebäudetypen (key, label) – für Dekarbonisierungspfade
GEBAEUDETYPEN = [
    ("einfamilienhauser", "Einfamilienhäuser", "Nur Wärmepumpen"),
    ("zentral_beheizt", "Zentral beheizt", "In FW-Heute: immer Fernwärme"),
    ("dezentral_beheizt", "Dezentral beheizt", "Erst Zentralisierung"),
    ("gas_und_fernwaerme", "Gas + Fernwärme", "Immer → Fernwärme"),
    ("dienstleistung", "Dienstleistungsgebäude", "Fernwärme + WP"),
    ("sonstige_nichtwohn", "Sonstige Nichtwohngebäude", "Fernwärme + WP"),
]

# Gebietstypen (Wärmeplan 2040)
GEBIETSTYPEN = [
    ("fernwaerme_heute", "Fernwärme Heute", "Bereits erschlossen"),
    ("fernwaerme_zukunft", "Fernwärme Zukunft", "Geplanter Ausbau"),
    ("pioniergebiete", "Pioniergebiete", "Strategischer Ausbau"),
    ("lokale_gemeinsam", "Lokale Wärme gemeinsam", "Nachbarschaftliche Netze"),
    ("lokale_individuell", "Lokale Wärme individuell", "WP, Solar, Biomasse"),
]


def default_params() -> dict:
    """Standard-Parameter für ein neues Szenario. Hier Logik anpassen."""
    return {
        # Ausbauparameter
        "fernwaerme_anschluss_bis_2030": 12_000,
        "fernwaerme_anschluss_ab_2030": 30_000,
        "heizungstausch_pro_jahr": 15_000,
        "anteil_gas_zu_wasserstoff": 5,
        "waermepumpen_pro_jahr": 4_000,
        "kochgas_austausch_pro_jahr": 12_000,
        "wachstum_wohnungen_pro_jahr": 0.4,
        # Gas-Zählpunkte pro Gebäudetyp
        "gas_zaehlpunkte_einfamilienhauser": 25_000,
        "gas_zaehlpunkte_zentral_beheizt": 420_000,
        "gas_zaehlpunkte_dezentral_beheizt": 180_000,
        "gas_zaehlpunkte_gas_und_fernwaerme": 85_000,
        "gas_zaehlpunkte_dienstleistung": 95_000,
        "gas_zaehlpunkte_sonstige_nichtwohn": 35_000,
        # Umstellung nach Gebietstyp (Anteil Fernwärme %)
        "umstellung_fernwaerme_heute_fernwaerme_pct": 95,
        "umstellung_fernwaerme_zukunft_fernwaerme_pct": 88,
        "umstellung_pioniergebiete_fernwaerme_pct": 85,
        "umstellung_lokale_gemeinsam_fernwaerme_pct": 45,
        "umstellung_lokale_individuell_fernwaerme_pct": 15,
    }
