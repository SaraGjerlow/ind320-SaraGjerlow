"""About page: project metadata, data sources and links."""

import streamlit as st

st.title("About")

st.write("IND320 Data to Decision, project work part 2.")

st.subheader("Data sources")
st.markdown(
    "- [NVE Magasinstatistikk]"
    "(https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/), "
    "weekly reservoir statistics, read from NVE's API\n"
    "- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), "
    "hourly cross-border power flow"
)

st.subheader("How the data reaches this app")
st.write(
    "The reservoir data is requested from NVE's API every time the download "
    "interval changes. The cross-border data is retrieved from ENTSO-E in the "
    "Jupyter Notebook, stored in a local Cassandra database through Spark, read "
    "back with Spark SQL and written to MongoDB, which this app reads from."
)

st.subheader("Links")
st.markdown(
    "- [GitHub repository](https://github.com/SaraGjerlow/ind320-SaraGjerlow)"
)