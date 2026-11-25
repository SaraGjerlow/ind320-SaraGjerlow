"""IND320 project app. Defines the theme, the shared choices and the pages."""

from datetime import date

import streamlit as st

from modules.data import FIRST_YEAR
from modules.theme import page_style, use_theme
from modules.data import DataSourceError

st.set_page_config(
    page_title="IND320 Hydropower",
    page_icon="💧",
    layout="wide",
)

# Gives every Plotly figure in the app the same colours as the page.
use_theme()

# NVE's own numbering. NO is the country as one area, EL the five price areas
# and VASS the three watercourse areas.
AREA_NUMBERS = {
    "NO": [0],
    "EL": [1, 2, 3, 4, 5],
    "VASS": [1, 2, 3],
}

THIS_YEAR = date.today().year

# --- The shared choices --------------------------------------------------

# The area and the period live in session_state, so every page reads the same
# values. The area can also be changed by clicking the map on the Home page.

if "area_type" not in st.session_state:
    st.session_state["area_type"] = "EL"

if "area_number" not in st.session_state:
    st.session_state["area_number"] = 3

# A click in the map leaves the area name here, and it is used before the
# sidebar is drawn. Streamlit does not allow changing a widget after it exists.
if "clicked_area" in st.session_state:
    clicked_type, clicked_number = st.session_state.pop("clicked_area").split()
    st.session_state["area_type"] = clicked_type
    st.session_state["area_number"] = int(clicked_number)

with st.sidebar:
    st.subheader("Area")

    area_type = st.radio(
        "Area type",
        options=list(AREA_NUMBERS),
        horizontal=True,
        key="area_type",
        help="NO is the whole country, EL the price areas, VASS the "
             "watercourse areas.",
    )

    # A number from the old type may not exist in the new one, so it is reset
    # before the selectbox is drawn.
    numbers = AREA_NUMBERS[area_type]
    if st.session_state["area_number"] not in numbers:
        st.session_state["area_number"] = numbers[0]

    st.selectbox("Area number", options=numbers, key="area_number")

    st.caption("Or click an area in the map on the Home page.")

    # Says plainly which areas have weather, so an empty weather page reads as
    # a documented limit rather than something that is broken.
    st.caption(
        "Daily weather covers the five EL areas. Hourly weather covers EL 3, "
        "averaged over 1000 locations. Other areas can be downloaded on the "
        "weather page."
    )

    st.subheader("Period")

    # The reservoir pages download only the years chosen here.
    years = st.slider(
        "Years",
        min_value=FIRST_YEAR,
        max_value=THIS_YEAR,
        value=(THIS_YEAR - 5, THIS_YEAR),
        key="years",
    )

    st.caption("Used by Overview and Cycles.")

# One string, since that is how the data is labelled: "EL 3".
st.session_state["area"] = (
    f"{st.session_state['area_type']} {st.session_state['area_number']}"
)

st.session_state["start_year"] = years[0]
st.session_state["end_year"] = years[1]

# --- Pages ---------------------------------------------------------------

home = st.Page("views/home.py", title="Home", icon=":material/home:",
               default=True)

overview = st.Page("views/overview.py", title="Overview",
                   icon=":material/table_chart:")
cycles = st.Page("views/cycles.py", title="Cycles",
                 icon=":material/show_chart:")

anomalies = st.Page("views/weather.py", title="Outliers and anomalies",
                    icon=":material/rainy:")

crossborder = st.Page("views/crossborder.py", title="Power exchange",
                      icon=":material/bolt:")

about = st.Page("views/about.py", title="About", icon=":material/info:")

forecast = st.Page("views/forecast.py", title="Forecast",
                   icon=":material/trending_up:")

correlation = st.Page("views/correlation.py", title="Weather vs reservoirs",
                      icon=":material/compare_arrows:")

page = st.navigation(
    {
        "Start": [home],
        "Reservoirs": [overview, cycles, forecast],
        "Weather": [anomalies, correlation],
        "Electricity": [crossborder],
        "Utilities": [about],
    }
)

# The open page decides the colours on headings, buttons and plots.
page_style(page.title)

# One place to catch a source that is down, instead of one per page.
try:
    page.run()
except DataSourceError as error:
    st.error(str(error))
    st.info(
        "This page needs a source that is not answering right now. Try again "
        "in a moment, or open a page that uses another source. Anything "
        "already cached still works."
    )

    # The original error is kept out of the way, so the page stays readable
    # but the cause is still one click away when something is actually wrong.
    if error.detail:
        with st.expander("Technical detail"):
            st.code(error.detail)