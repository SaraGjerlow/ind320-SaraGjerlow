"""IND320 project app. Entry point: defines pages and navigation."""
 
import streamlit as st
 
# Must run before any other Streamlit content in the app.
st.set_page_config(
    page_title="IND320 Reservoirs",
    page_icon="💧",
    layout="wide",
)
 
# st.Page links a .py file to a title and an icon in the sidebar menu.
home = st.Page("views/home.py", title="Home", icon=":material/home:", default=True)
reservoirs = st.Page(
    "views/reservoirs.py", title="Reservoirs", icon=":material/water_drop:"
)
crossborder = st.Page(
    "views/crossborder.py", title="Cross-border flow", icon=":material/bolt:"
)
about = st.Page("views/about.py", title="About", icon=":material/info:")
 
# Passing a dict groups the pages into labelled sections in the sidebar.
nav = st.navigation(
    {
        "Start": [home],
        "Data": [reservoirs, crossborder],
        "Info": [about],
    }
)
 
nav.run()