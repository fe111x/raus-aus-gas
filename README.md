# Raus aus Gas – Dashboard

Dashboard zur **Wiener Wärmeversorgung** und zur Strategie **„Raus aus Gas“** der Stadt Wien: Historie, Themenschwerpunkte und modellierte **Szenarien** mit Gebäudebestand, Umstellung nach **Gebietstypen (Wärmeplan 2040)** und Ausbaupfaden.

## Design

Strava-inspiriertes UI: klare Typografie (Inter), kräftige Akzentfarben, viel Weißraum. Farbpalette: Orange (#FC5200), Grün für positive Metriken, neutrale Grautöne.

## Inhalt

- **Historie**: Fernwärme vs. Gas-Heizung, Leitungsnetz (km) seit 2010
- **Themenschwerpunkte**: Wärmequellen, Ziele 2040, Pioniergebiete, Links
- **Szenarien**: Sauberes Management (Anlegen, Bearbeiten, Löschen), Gebäudebestand, Umstellung nach Gebietstyp, Ausbauparameter, KPIs, Dekarbonisierungspfade mit Korridoren

## Start

```bash
cd raus-aus-gas
pip install -r requirements.txt
streamlit run app/dashboard.py
```

Browser: **http://localhost:8501**

## Projektstruktur

```
raus-aus-gas/
├── README.md
├── requirements.txt
├── core/                         # Szenario-Logik (anpassbar)
│   ├── config.py                 # Konstanten, Default-Parameter, Gebäudetypen
│   ├── scenario_engine.py        # Projektionslogik (build_projection, build_projection_by_type)
│   └── data_loader.py            # Daten laden
├── app/
│   ├── dashboard.py              # Haupt-App
│   └── theme.py                  # Design-System (Farben, CSS)
├── assets/
└── data/
    ├── fernwaerme_haushalte.csv
    ├── waermeversorgung_quellen.csv
    ├── ziele_raus_aus_gas.json
    └── pioniergebiete.csv
```

## Szenario-Rechner anpassen

- **`core/config.py`**: BASISJAHR, ZIELJAHR, default_params(), GEBAEUDETYPEN, GEBIETSTYPEN
- **`core/scenario_engine.py`**: build_projection(), build_projection_by_type(), Dekarbonisierungsregeln

## Datenquellen

- [Stadt Wien – Raus aus Gas](https://www.wien.gv.at/umwelt/programm-raus-aus-gas)
- [Wiener Wärmeplan 2040](https://www.wien.gv.at/umwelt/waermeplan-2040)
- [Energiebericht Stadt Wien](https://www.wien.gv.at/spezial/energiebericht/)
- Wien Energie
