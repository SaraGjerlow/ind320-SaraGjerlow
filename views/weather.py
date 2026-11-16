"""Weather quality page: SPC outliers and LOF anomalies in two tabs."""

import pandas as pd
import streamlit as st

from modules.analysis import precipitation_outliers, temperature_anomalies
from modules.data import download_area_weather, load_area_points, load_area_weather
from modules.theme import page_colours

@st.cache_data(ttl=3600, show_spinner="Finding outliers")
def run_spc(weather, cutoff, n_sigma, column, colour):
    """Cache one SPC run, so changing a slider back is instant."""
    return precipitation_outliers(weather, cutoff, n_sigma, column, colour)


@st.cache_data(ttl=3600, show_spinner="Looking for anomalies")
def run_lof(weather, proportion, n_neighbors, column, colour):
    """Cache one LOF run. This is the slowest analysis in the app."""
    return temperature_anomalies(weather, proportion, n_neighbors, column,
                                 colour)

st.title("Weather quality")

# The area comes from the sidebar, the same selector the reservoir pages use.
# That is what ties the weather to the reservoir statistics: the locations
# were sampled inside exactly these areas.
area_type = st.session_state["area_type"]
area_number = st.session_state["area_number"]

# The colour of this page, passed to both plots below.
PAGE = page_colours("Outliers and anomalies")[0]

# The five downloaded variables, with names that read better in a selector.
WEATHER_VARIABLES = {
    "Precipitation (mm)": "precipitation",
    "Temperature (degrees C)": "temperature_2m",
    "Snowfall (cm)": "snowfall",
    "Relative humidity (percent)": "relative_humidity_2m",
    "Wind speed (m/s)": "wind_speed_10m",
}

st.write(
    f"Hourly weather for **{area_type} {area_number}**, averaged over random "
    f"locations drawn inside the area. Change the area in the sidebar."
)

# NVE reports the country as a whole as its own area, but there are no
# sampled locations for it, since it is not a shape in the shapefiles.
if area_type == "NO":
    st.info(
        "The country as a whole has no sampled locations. Choose an EL or a "
        "VASS area in the sidebar to see weather."
    )
    st.stop()

weather = load_area_weather(area_type, area_number)

# --- Download control -----------------------------------------------------

# The download is part of this page rather than a page of its own. It only
# appears when the area has no stored weather, so it stays out of the way
# once the data is in place. The button is the confirmation step.

if len(weather) == 0:
    st.warning(f"No weather stored for {area_type} {area_number} yet.")

    points = load_area_points(area_type, area_number)

    if len(points) == 0:
        st.error(
            "There are no sampled coordinates for this area either. Run the "
            "part 3 notebook first, so the points are written to MongoDB."
        )
        st.stop()

    st.write(
        f"{len(points)} locations were sampled inside this area. Downloading "
        f"weather for them takes a while, and open-meteo limits how much can "
        f"be fetched per day, so start with a small number."
    )

    left, middle, right = st.columns(3)

    with left:
        locations = st.slider(
            "Locations to download",
            min_value=25, max_value=min(200, len(points)), value=25, step=25,
            help="The weather is averaged over this many locations. More "
            "locations is a better average but uses more of the daily limit.",
        )

    with middle:
        start_date = st.date_input(
            "From", value=pd.Timestamp("2024-01-01")
        )

    with right:
        end_date = st.date_input(
            "To", value=pd.Timestamp("2024-12-31")
        )

    if st.button("Download weather for this area", type="primary"):
        bar = st.progress(0.0, text="Asking open-meteo")

        try:
            weather = download_area_weather(
                area_type,
                area_number,
                str(start_date),
                str(end_date),
                locations=locations,
                progress=lambda share: bar.progress(
                    share, text=f"{int(100 * share)} percent of the locations"
                ),
            )
        except RuntimeError as error:
            bar.empty()
            st.error(f"Open-meteo refused the download: {error}")
            st.stop()

        bar.empty()
        st.success(f"Downloaded and stored {len(weather)} hours.")
    else:
        st.stop()

# --- The two analyses -----------------------------------------------------

first_hour = weather["time"].min()
last_hour = weather["time"].max()

st.caption(
    f"{len(weather)} hours, from {first_hour:%Y-%m-%d} to {last_hour:%Y-%m-%d}."
)

spc_tab, lof_tab = st.tabs(["Outliers (SPC)", "Anomalies (LOF)"])

# --- SPC ------------------------------------------------------------------

with spc_tab:
    st.write(
        "The seasonal shape is found with a cosine transform and subtracted. "
        "The limits are calculated on what is left and then drawn back onto "
        "the original curve, so they follow the season instead of being two "
        "straight lines."
    )

    left, middle, right = st.columns(3)

    with left:
        spc_name = st.selectbox(
            "Weather variable",
            options=list(WEATHER_VARIABLES),
            key="spc_variable",
            help="The same method is used for every variable.",
        )

    with middle:
        cutoff = st.slider(
            "Seasonal cutoff",
            min_value=2, max_value=60, value=25, step=1,
            help="How many of the slowest frequencies count as seasonal. A "
            "low number keeps only the slowest shape.",
        )

    with right:
        n_sigma = st.slider(
            "Limit (sigma)",
            min_value=1.0, max_value=8.0, value=3.0, step=0.5,
            help="How far from the seasonal level a point has to be before it "
            "counts as an outlier.",
        )

    spc_column = WEATHER_VARIABLES[spc_name]

    figure, outliers, statistics = run_spc(
        weather, cutoff, n_sigma, spc_column, PAGE
    )

    st.plotly_chart(figure, width="stretch")

    one, two, three = st.columns(3)
    one.metric("Outliers", statistics["outliers"])
    two.metric("Share of hours", f"{statistics['percent']:.2f} %")
    three.metric("Robust standard deviation",
                 f"{statistics['robust_sigma']:.4f}")

    st.write("The ten largest outliers:")
    st.dataframe(
        outliers.nlargest(10, spc_column),
        width="stretch", hide_index=True,
    )

    # Three of the variables cannot go below zero, so half the band is unused.
    if spc_column in ("precipitation", "snowfall", "wind_speed_10m"):
        st.caption(
            "The limits are symmetric around the seasonal level, so the lower "
            "one ends up below zero. This variable cannot be negative, so in "
            "practice only the upper limit ever flags anything."
        )

# --- LOF ------------------------------------------------------------------

with lof_tab:
    st.write(
        "Local Outlier Factor compares how tightly packed each point is "
        "against its neighbours in time. It finds hours that break away from "
        "the hours around them, rather than the highest or lowest hours of "
        "the year."
    )

    left, middle, right = st.columns(3)

    with left:
        lof_name = st.selectbox(
            "Weather variable",
            options=list(WEATHER_VARIABLES),
            index=1,
            key="lof_variable",
            help="The same method is used for every variable.",
        )

    with middle:
        proportion = st.slider(
            "Share flagged",
            min_value=0.001, max_value=0.05, value=0.01, step=0.001,
            format="%.3f",
            help="LOF has no natural threshold, so it is told what share of "
            "the points should be marked.",
        )

    with right:
        n_neighbors = st.slider(
            "Neighbours",
            min_value=5, max_value=100, value=20, step=5,
            help="How many nearby points each point is compared against. A "
            "small number reacts to shorter events.",
        )

    lof_column = WEATHER_VARIABLES[lof_name]

    figure, anomalies, statistics = run_lof(
        weather, proportion, n_neighbors, lof_column, PAGE
    )

    st.plotly_chart(figure, width="stretch")

    one, two, three = st.columns(3)
    one.metric("Anomalies", statistics["anomalies"])
    two.metric("Lowest flagged", f"{statistics['coldest']:.1f}")
    three.metric("Highest flagged", f"{statistics['warmest']:.1f}")

    st.write("The ten most isolated points:")
    st.dataframe(
        anomalies.nlargest(10, "lof_score"),
        width="stretch", hide_index=True,
    )

# --- Documentation --------------------------------------------------------

with st.expander("About the data on this page"):
    st.write(
        "Source: the open-meteo Archive API, ERA5 reanalysis. The notebook "
        "draws 1000 random locations inside each NVE area from the shapefiles "
        "and stores the coordinates in MongoDB. The weather is downloaded for "
        "those coordinates and averaged, so one row is one hour for the whole "
        "area."
    )
    st.write(
        "The averaged weather is stored in MongoDB as well. The app reads it "
        "from there rather than downloading it again on every rerun, because "
        "open-meteo limits how much can be fetched per day. The download "
        "control above only appears for an area that has not been downloaded "
        "yet, so it does not need a page of its own."
    )
    st.write("The stored weather for this area:")
    st.dataframe(weather.head(200), width="stretch")