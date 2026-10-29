"""Data access for the IND320 app.

Part 1 read a local CSV file. Part 2 reads the reservoir data straight from
NVE's API and the cross-border flow data from MongoDB, which is filled by the
Jupyter Notebook. Part 3 adds the sampled coordinates and the weather that
belongs to each area, both stored in MongoDB as well.
"""

import time

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
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

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

# The weather variables the notebook downloads, in the same order.
HOURLY_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "snowfall",
    "relative_humidity_2m",
    "wind_speed_10m",
]

# Open-meteo rejects a request that asks for too many locations at once.
LOCATIONS_PER_REQUEST = 25


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

    areas = pd.DataFrame(rows)

    # The area endpoint uses Norwegian field names, so they are translated
    # the same way the measurement columns are.
    areas = areas.rename(columns={
        "navn": "Name",
        "navn_langt": "Long name",
        "beskrivelse": "Description",
        "omrType": "Area type",
        "omrnr": "Area number",
        "group": "Group",
    })

    return areas


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


# --- Part 3: sampled coordinates and the weather for each area ------------


@st.cache_data(ttl=600)
def load_area_points(area_type: str, area_number: int) -> pd.DataFrame:
    """Read the coordinates the notebook sampled inside one area.

    The points were drawn from NVE's shapefiles in the notebook and stored in
    MongoDB, so the app never has to read a shapefile or install geopandas.
    """
    client = get_mongo_client()
    collection = client["ind320"]["area_points"]

    documents = collection.find(
        {"area_type": area_type, "area_number": int(area_number)},
        {"_id": 0, "latitude": 1, "longitude": 1},
    )

    return pd.DataFrame(list(documents))


@st.cache_data(ttl=600)
def load_area_weather(area_type: str, area_number: int) -> pd.DataFrame:
    """Read the stored weather for one area, averaged over its locations.

    Returns an empty table if the area has not been downloaded yet. The page
    then offers to download it.
    """
    client = get_mongo_client()
    collection = client["ind320"]["area_weather"]

    documents = list(collection.find(
        {"area_type": area_type, "area_number": int(area_number)},
        {"_id": 0, "area_type": 0, "area_number": 0},
    ))

    if len(documents) == 0:
        return pd.DataFrame()

    weather = pd.DataFrame(documents)
    weather["time"] = pd.to_datetime(weather["time"])
    return weather.sort_values("time").reset_index(drop=True)


def fetch_batch(parameters, attempts=4, pause_seconds=65):
    """Ask open-meteo for one batch of locations.

    Open-meteo limits how much data can be asked for per minute, per hour and
    per day. A rejected request is not an error, it only means waiting, so the
    request is repeated a few times before giving up.
    """
    for attempt in range(attempts):
        response = requests.get(ARCHIVE_URL, params=parameters, timeout=180)

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            # The body says which of the three limits was reached.
            reason = response.json().get("reason", "rate limited")

            # The daily limit will not clear by waiting a minute.
            if "aily" in reason:
                raise RuntimeError(reason)

            time.sleep(pause_seconds)
            continue

        response.raise_for_status()

    raise RuntimeError("Open-meteo kept refusing the request. Try again later.")


def download_area_weather(area_type, area_number, start_date, end_date,
                          locations, progress=None):
    """Download weather for one area, average it and store it in MongoDB.

    The coordinates come from the points the notebook sampled. Only the first
    `locations` of them are used, because open-meteo limits how much can be
    downloaded per day.

    progress is an optional function called with a number between 0 and 1, so
    the page can show a progress bar.
    """
    coordinates = load_area_points(area_type, area_number).head(locations)

    if len(coordinates) == 0:
        raise RuntimeError(
            "No sampled coordinates for this area. Run the part 3 notebook "
            "first, so the points are written to MongoDB."
        )

    total = None
    done = 0

    for start in range(0, len(coordinates), LOCATIONS_PER_REQUEST):
        batch = coordinates.iloc[start:start + LOCATIONS_PER_REQUEST]

        parameters = {
            "latitude": ",".join(batch["latitude"].astype(str)),
            "longitude": ",".join(batch["longitude"].astype(str)),
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(HOURLY_VARIABLES),
            "models": "era5",
        }

        results = fetch_batch(parameters)

        # One location comes back as a dictionary, several as a list.
        if isinstance(results, dict):
            results = [results]

        # The series are added up as they arrive and divided at the end, so
        # only one table is kept in memory instead of one per location.
        for result in results:
            hourly = pd.DataFrame(result["hourly"])
            hourly["time"] = pd.to_datetime(hourly["time"])
            hourly = hourly.set_index("time")

            if total is None:
                total = hourly
            else:
                total = total + hourly

            done = done + 1

        if progress is not None:
            progress(done / len(coordinates))

    weather = (total / done).reset_index()

    store_area_weather(area_type, area_number, weather)

    return weather


def store_area_weather(area_type, area_number, weather):
    """Write one area's averaged weather to MongoDB, replacing what was there."""
    client = get_mongo_client()
    collection = client["ind320"]["area_weather"]

    collection.delete_many(
        {"area_type": area_type, "area_number": int(area_number)}
    )

    documents = []
    for row in weather.to_dict("records"):
        row["area_type"] = area_type
        row["area_number"] = int(area_number)
        documents.append(row)

    collection.insert_many(documents)

    # The stored weather has changed, so the cached read has to go.
    load_area_weather.clear()