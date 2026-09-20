"""Data access for the IND320 reservoir app.

Part 1 reads from a local CSV. In part 2 this module will read from MongoDB
instead, and nothing outside this file should need to change.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

# Resolve relative to this file so the path works locally and on Streamlit Cloud.
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "reservoirs.csv"

# Norwegian source headers -> English, matching the notebook exactly.
COLUMN_NAMES_EN = {
    "fyllingsgrad": "Fill level (fraction)",
    "kapasitet_TWh": "Capacity (TWh)",
    "fylling_TWh": "Stored energy (TWh)",
    "fyllingsgrad_forrige_uke": "Fill level previous week (fraction)",
    "endring_fyllingsgrad": "Change in fill level (fraction)",
}


@st.cache_data
def load_reservoirs() -> pd.DataFrame:
    """Return the national-total series, weekly, indexed by date.

    The raw file is in long format with one row per (area, week). NO/0 is the
    national total; EL 1-5 are price areas and VASS 1-3 are watercourse areas.
    """
    raw = pd.read_csv(DATA_PATH)

    national = raw[(raw["omrType"] == "NO") & (raw["omrnr"] == 0)].copy()
    national["dato_Id"] = pd.to_datetime(national["dato_Id"])
    national = national.sort_values("dato_Id").set_index("dato_Id")

    return national[list(COLUMN_NAMES_EN)].rename(columns=COLUMN_NAMES_EN)