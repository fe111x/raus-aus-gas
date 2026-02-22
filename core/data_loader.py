"""Daten laden aus data/"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def load_data() -> dict:
    """Lädt alle verfügbaren Datensätze."""
    result = {}
    if (DATA_DIR / "fernwaerme_haushalte.csv").exists():
        result["fernwaerme"] = pd.read_csv(DATA_DIR / "fernwaerme_haushalte.csv")
    if (DATA_DIR / "waermeversorgung_quellen.csv").exists():
        result["quellen"] = pd.read_csv(DATA_DIR / "waermeversorgung_quellen.csv")
    if (DATA_DIR / "pioniergebiete.csv").exists():
        result["pioniergebiete"] = pd.read_csv(DATA_DIR / "pioniergebiete.csv")
    if (DATA_DIR / "ziele_raus_aus_gas.json").exists():
        with open(DATA_DIR / "ziele_raus_aus_gas.json", encoding="utf-8") as f:
            result["ziele"] = json.load(f)
    return result
