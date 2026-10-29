"""IND320 project app. Entry point: defines the pages, the sidebar and navigation."""

import pandas as pd
import streamlit as st

from modules.data import FIRST_YEAR

# Must run before any other Streamlit content in the app.
st.set_page_config(
    page_title="IND320 Reservoirs",
    page_icon="💧",
    layout="wide",
)

# NVE's own numbering. NO is the country as one area, EL are the five
# electricity price areas and VASS are the three watercourse areas.
AREA_NUMBERS = {
    "NO": [0],
    "EL": [1, 2, 3, 4, 5],
    "VASS": [1, 2, 3],
}

# --- Global area selector -------------------------------------------------

# This block is written before nav.run(), so it appears in the sidebar on
# every page. The area is a global setting because the reservoir pages and
# the weather pages have to describe the same place. Choosing it separately
# on each page would let them drift apart without the user noticing.

with st.sidebar:
    st.subheader("Area")

    # EL 3 is the default because that is the area the notebook downloaded
    # weather for, so every page has something to show on the first visit.
    area_type = st.radio(
        "Area type",
        options=list(AREA_NUMBERS),
        index=1,
        horizontal=True,
        help="NO is the country as a whole, EL are the electricity price "
        "areas, VASS are the watercourse areas.",
    )

    numbers = AREA_NUMBERS[area_type]

    if area_type == "EL":
        default_number = numbers.index(3)
    else:
        default_number = 0

    area_number = st.selectbox(
        "Area number",
        options=numbers,
        index=default_number,
    )

    last_year = pd.Timestamp.now().year

    start_year, end_year = st.select_slider(
        "Download interval",
        options=list(range(FIRST_YEAR, last_year + 1)),
        value=(last_year - 14, last_year),
        help="Which years of reservoir statistics to download. The weather "
        "data has its own period, set on the weather page.",
    )

    st.caption(f"Selected: {area_type} {area_number}, {start_year} to {end_year}")

# The pages read the choices from here instead of taking them as arguments,
# since st.Page runs a file rather than calling a function.
st.session_state["area_type"] = area_type
st.session_state["area_number"] = area_number
st.session_state["start_year"] = start_year
st.session_state["end_year"] = end_year

# --- Pages ----------------------------------------------------------------

# st.Page links a .py file to a title and an icon in the sidebar menu.
home = st.Page("views/home.py", title="Home", icon=":material/home:", default=True)

reservoirs = st.Page(
    "views/reservoirs.py", title="Reservoir levels", icon=":material/water_drop:"
)
cycles = st.Page(
    "views/cycles.py", title="Reservoir cycles", icon=":material/show_chart:"
)
weather = st.Page(
    "views/weather.py", title="Weather quality", icon=":material/rainy:"
)
crossborder = st.Page(
    "views/crossborder.py", title="Cross-border flow", icon=":material/bolt:"
)
about = st.Page("views/about.py", title="About", icon=":material/info:")

# The grouping follows the subject rather than the order the pages were made
# in. The two reservoir pages belong together, the weather describes the same
# areas, and the power flow is a separate subject.
nav = st.navigation(
    {
        "Start": [home],
        "Reservoirs": [reservoirs, cycles],
        "Weather": [weather],
        "Power flow": [crossborder],
        "Info": [about],
    }
)

nav.run()