# Raus aus Gas – Dashboard

Dashboard zur **Wiener Wärmeversorgung** und zur Strategie **„Raus aus Gas“** der Stadt Wien: Historie, Themenschwerpunkte und modellierte **Szenarien** mit Gebäudebestand, Umstellung nach **Gebietstypen (Wärmeplan 2040)** und Ausbaupfaden. Design: Morgenrot, Lucida, Stadt Wien Logo.

## Inhalt

- **Historie**: Fernwärme vs. Gas-Heizung, Leitungsnetz (km) seit 2010
- **Themenschwerpunkte**: Wärmequellen, Ziele 2040, Pioniergebiete, Links
- **Szenarien & Ausbaupfade**:  
  - **Gebäudebestand**: Einfamilienhäuser, zentral/dezentral beheizt, Gas+Fernwärme, Dienstleistungsgebäude, sonstige Nichtwohngebäude  
  - **Umstellung nach Gebietstyp (Wärmeplan 2040)**: Fernwärme Heute/Zukunft, Pioniergebiete, Lokale Wärme gemeinsam/individuell (Anteil Fernwärme vs. Wärmepumpen)  
  - Ausbauparameter, KPIs, Entwicklungspfade mit Korridoren

## Start

```bash
cd raus-aus-gas
pip install -r requirements.txt
streamlit run app/dashboard.py
```

Dann im Browser **http://localhost:8501** öffnen.

## Projektstruktur

```
raus-aus-gas/
├── README.md
├── requirements.txt
├── assets/
│   └── logo.png                  # Optional: Stadt Wien Logo (sonst Text-Badge)
├── data/
│   ├── fernwaerme_haushalte.csv
│   ├── waermeversorgung_quellen.csv
│   ├── ziele_raus_aus_gas.json
│   └── pioniergebiete.csv
└── app/
    └── dashboard.py
```

## Datenquellen

- [Stadt Wien – Raus aus Gas](https://www.wien.gv.at/umwelt/programm-raus-aus-gas)
- [Wiener Wärmeplan 2040](https://www.wien.gv.at/umwelt/waermeplan-2040)
- [Energiebericht der Stadt Wien](https://www.wien.gv.at/spezial/energiebericht/)
- Wien Energie (Fernwärme-Zahlen, Dekarbonisierung)

Die CSV/JSON-Daten in `data/` sind aus diesen Quellen abgeleitet; historische Reihen sind teils plausibel interpoliert, wo keine jährlichen Zeitreihen veröffentlicht sind.

## Lizenz

Projektbezogen.
