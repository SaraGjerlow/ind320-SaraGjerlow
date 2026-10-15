"""Data access for the IND320 app.
 
Part 1 read a local CSV file. Part 2 reads the reservoir data straight from
NVE's API and the cross-border flow data from MongoDB, which is filled by the
Jupyter Notebook.
"""
 
import pandas as pd
import requests
import streamlit as st
from pymongo import MongoClient
 
NVE_DATA_URL = (
    "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
)
NVE_AREAS_URL = (
    "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOmr%C3%A5der"
)
 
# Norwegian source headers -> English, the same names used in the notebook.
COLUMN_NAMES_EN = {
    "dato_Id": "Date",
    "omrType": "Area type",
    "omrnr": "Area number",
    "iso_aar": "ISO year",
    "iso_uke": "ISO week",
    "fyllingsgrad": "Fill level (fraction)",
    "kapasitet_TWh": "Capacity (TWh)",
    "fylling_TWh": "Stored energy (TWh)",
    "neste_Publiseringsdato": "Next publication date",
    "fyllingsgrad_forrige_uke": "Fill level previous week (fraction)",
    "endring_fyllingsgrad": "Change in fill level (fraction)",
}
 
# The columns that hold measurements. The rest are identifiers or metadata.
MEASUREMENT_COLUMNS = [
    "Fill level (fraction)",
    "Capacity (TWh)",
    "Stored energy (TWh)",
    "Fill level previous week (fraction)",
    "Change in fill level (fraction)",
]
 
# NVE has published the statistics since 1995.
FIRST_YEAR = 1995
 
 
@st.cache_data
def load_reservoirs(start_year: int, end_year: int) -> pd.DataFrame:
    """Download the reservoir statistics for the chosen interval of years.
 
    The cache key includes the interval, so changing the slider triggers a new
    download rather than reusing the previous result. NVE's API has no date
    parameters, so the interval is applied immediately after the request.
    """
    response = requests.get(NVE_DATA_URL)
    response.raise_for_status()
 
    data = pd.DataFrame(response.json())
    data = data.rename(columns=COLUMN_NAMES_EN)
 
    data["Date"] = pd.to_datetime(data["Date"])
    data = data.sort_values("Date")
 
    # Keep the selected interval of years.
    years = data["Date"].dt.year
    return data[(years >= start_year) & (years <= end_year)]
 
 
@st.cache_data
def load_areas() -> pd.DataFrame:
    """Download NVE's list of areas, used to label the area numbers."""
    areas_raw = requests.get(NVE_AREAS_URL).json()[0]
 
    rows = []
    for group_name, group in areas_raw.items():
        for area in group:
            area["group"] = group_name
            rows.append(area)
 
    return pd.DataFrame(rows)
 
 
@st.cache_resource
def get_mongo_client() -> MongoClient:
    """Open one MongoDB connection and reuse it across reruns.
 
    The connection string is read from Streamlit's secrets, which are entered
    on streamlit.io and never committed to GitHub.
    """
    return MongoClient(st.secrets["mongo"]["uri"])
 
 
@st.cache_data(ttl=600)
def load_flows() -> pd.DataFrame:
    """Read the cross-border flow data written to MongoDB by the notebook."""
    client = get_mongo_client()
    collection = client["ind320"]["crossborder_flows"]
 
    # _id is MongoDB's own key and is not needed here.
    documents = list(collection.find({}, {"_id": 0}))
 
    flows = pd.DataFrame(documents)
    flows["timestamp"] = pd.to_datetime(flows["timestamp"])
    return flows