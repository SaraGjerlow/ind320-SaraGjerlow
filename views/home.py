"""Landing page. Introduces the app and its two data sources."""
 
import streamlit as st
 
st.title("IND320 Reservoirs")
 
st.write(
    "Project work, part 2. Use the sidebar menu to navigate."
)
 
st.subheader("Reservoirs")
st.write(
    "Weekly reservoir statistics for Norwegian hydropower, read directly from "
    "NVE's API. Choose an area type and a download interval, then compare the "
    "area numbers belonging to that type."
)
 
st.subheader("Cross-border flow")
st.write(
    "Hourly power flow between Norway and its neighbours, retrieved from the "
    "ENTSO-E API, stored in Cassandra through Spark and loaded into MongoDB, "
    "which is what this app reads."
)