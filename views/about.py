"""About page: project metadata, data sources and links."""

import streamlit as st

st.title("About")

st.write("IND320 Data to Decision, project work part 3.")

st.subheader("Data sources")
st.markdown(
    "- [NVE Magasinstatistikk]"
    "(https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/), "
    "weekly reservoir statistics, read from NVE's API\n"
    "- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), "
    "hourly cross-border power flow\n"
    "- [open-meteo Archive API](https://open-meteo.com/en/docs/historical-weather-api), "
    "hourly historical weather from the ERA5 reanalysis model\n"
    "- NVE's shapefiles for the electricity price areas and the watercourse "
    "regions, used to draw the sampling locations"
)

st.subheader("How the data reaches this app")
st.write(
    "The reservoir data is requested from NVE's API every time the download "
    "interval changes. The cross-border data is retrieved from ENTSO-E in the "
    "Jupyter Notebook, stored in a local Cassandra database through Spark, read "
    "back with Spark SQL and written to MongoDB, which this app reads from."
)
st.write(
    "The weather works the same way. The notebook draws 1000 random locations "
    "inside each NVE area from the shapefiles and writes the coordinates to "
    "MongoDB. The weather for those coordinates is downloaded from open-meteo, "
    "averaged over the area and stored in MongoDB as well. The app reads the "
    "finished average, so it never has to install geopandas or read a "
    "shapefile, and it does not spend the daily open-meteo limit on every "
    "rerun."
)

st.subheader("Links")
st.markdown(
    "- [GitHub repository](https://github.com/SaraGjerlow/ind320-SaraGjerlow)"
)