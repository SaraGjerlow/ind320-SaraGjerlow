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
table = st.Page("views/table.py", title="Data table", icon=":material/table:")
plots = st.Page("views/plots.py", title="Plots", icon=":material/show_chart:")
about = st.Page("views/about.py", title="About", icon=":material/info:")

# Passing a dict groups the pages into labelled sections in the sidebar.
nav = st.navigation(
    {
        "Start": [home],
        "Reservoirs": [table, plots],
        "Info": [about],
    }
)

nav.run()