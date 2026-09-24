"""Data access for the IND320 reservoir app.
 
Part 1 reads a local CSV file. In part 2 this module will read from MongoDB
instead, and nothing outside this file should need to change.
"""
 
from pathlib import Path
 
import pandas as pd
import streamlit as st
 
# The path is built from this file's own location, so it works both on a local
# machine and on Streamlit Cloud.
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "reservoirs.csv"
 
 
@st.cache_data
def load_reservoirs() -> pd.DataFrame:
    """Read the CSV file and return the national weekly series.
 
    This does the same steps as the Jupyter notebook: keep the national total,
    sort by date, keep the five measurement columns and rename them to English.
    Caching means the file is only read once per session instead of on every
    interaction with the app.
    """
    df = pd.read_csv(DATA_PATH)
 
    # The file holds nine areas stacked on top of each other. NO is the
    # national total and is the only area type with a single area.
    national = df[df["omrType"] == "NO"].copy()
 
    # Turn the date column into real dates, then sort the rows by date.
    national["dato_Id"] = pd.to_datetime(national["dato_Id"])
    national = national.sort_values("dato_Id")
 
    # Keep the date and the five measurement columns.
    data = national[[
        "dato_Id",
        "fyllingsgrad",
        "kapasitet_TWh",
        "fylling_TWh",
        "fyllingsgrad_forrige_uke",
        "endring_fyllingsgrad",
    ]]
 
    # Translate the Norwegian headers to English, same names as the notebook.
    data = data.rename(columns={
        "dato_Id": "Date",
        "fyllingsgrad": "Fill level (fraction)",
        "kapasitet_TWh": "Capacity (TWh)",
        "fylling_TWh": "Stored energy (TWh)",
        "fyllingsgrad_forrige_uke": "Fill level previous week (fraction)",
        "endring_fyllingsgrad": "Change in fill level (fraction)",
    })
 
    # Use the date as the row index, so it becomes the x-axis in the plots.
    return data.set_index("Date")