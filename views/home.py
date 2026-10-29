"""Landing page. Introduces the app and its data sources."""

import streamlit as st

st.title("IND320 Reservoirs")

st.write(
    "Norwegian hydropower, the power flow across the borders, and the weather "
    "over the same areas. Pick an area in the sidebar. The choice follows you "
    "from page to page, so the reservoir pages and the weather page always "
    "describe the same place."
)

st.subheader("Reservoir levels")
st.write(
    "Weekly reservoir statistics for Norwegian hydropower, read directly from "
    "NVE's API. The areas of the chosen type are compared against each other, "
    "and the area chosen in the sidebar is drawn thicker."
)

st.subheader("Reservoir cycles")
st.write(
    "The same series taken apart. STL splits it into a trend, a yearly cycle "
    "and a remainder. The spectrogram shows whether the cycles themselves "
    "change over the years."
)

st.subheader("Weather quality")
st.write(
    "Hourly weather from the ERA5 reanalysis, averaged over random locations "
    "drawn inside the chosen area. Two ways of finding unusual weather: "
    "control limits that follow the season, and Local Outlier Factor."
)

st.subheader("Cross-border flow")
st.write(
    "Hourly power flow between Norway and its neighbours, retrieved from the "
    "ENTSO-E API, stored in Cassandra through Spark and loaded into MongoDB, "
    "which is what this app reads."
)