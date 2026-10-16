"""Reservoir page: area type, download interval, table and plot in one view."""
 
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
 
from modules.data import FIRST_YEAR, MEASUREMENT_COLUMNS, load_areas, load_reservoirs
 
st.title("Reservoirs")
 
# --- Controls -------------------------------------------------------------
 
# NVE groups its areas into three types, so one radio button per type.
area_type = st.radio(
    "Area type",
    options=["NO", "EL", "VASS"],
    horizontal=True,
    help="NO is the country as a whole, EL are the electricity price areas, "
    "VASS are the watercourse areas.",
)
 
last_year = pd.Timestamp.now().year
 
# The slider decides which years are downloaded. Because it is passed to the
# cached loading function, moving it triggers a new download.
start_year, end_year = st.select_slider(
    "Download interval",
    options=list(range(FIRST_YEAR, last_year + 1)),
    value=(last_year - 4, last_year),
)
 
data = load_reservoirs(start_year, end_year)
 
# Keep the areas belonging to the selected type.
selected = data[data["Area type"] == area_type]
area_numbers = sorted(selected["Area number"].unique())
 
st.caption(
    f"{len(selected)} weekly observations from {start_year} to {end_year}, "
    f"covering {len(area_numbers)} area(s) of type {area_type}."
)
 
# --- Table ----------------------------------------------------------------
 
st.subheader("Measurements per area")
 
st.write(
    "One row per area number of the selected type, and one line chart per "
    "measurement column over the downloaded interval."
)
 
# Build the table one row at a time: one row per area, and one list of values
# per measurement column, which is what LineChartColumn draws.
rows = []
for area_number in area_numbers:
    area_rows = selected[selected["Area number"] == area_number].sort_values("Date")
 
    row = {"Area": f"{area_type} {area_number}"}
    for column in MEASUREMENT_COLUMNS:
        row[column] = list(area_rows[column])
 
    rows.append(row)
 
table = pd.DataFrame(rows).set_index("Area")
 
# Every measurement column is displayed as a small line chart.
column_config = {}
for column in MEASUREMENT_COLUMNS:
    column_config[column] = st.column_config.LineChartColumn(column)
 
st.dataframe(table, column_config=column_config, use_container_width=True)
 
# --- Plot -----------------------------------------------------------------
 
st.subheader("One measurement over time")
 
column_choice = st.selectbox("Column to plot", options=MEASUREMENT_COLUMNS)
 
fig, ax = plt.subplots(figsize=(11, 4))
 
# One line per area number, so the areas of the chosen type can be compared.
for area_number in area_numbers:
    area_rows = selected[selected["Area number"] == area_number].sort_values("Date")
    ax.plot(
        area_rows["Date"],
        area_rows[column_choice],
        linewidth=0.9,
        label=f"{area_type} {area_number}",
    )
 
ax.set_title(f"{column_choice}, area type {area_type}")
ax.set_xlabel("Date")
ax.set_ylabel(column_choice)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
fig.autofmt_xdate()
 
st.pyplot(fig)
 
# --- Documentation --------------------------------------------------------
 
with st.expander("About the data on this page"):
    st.write(
        "Source: NVE Magasinstatistikk, read from "
        "https://biapi.nve.no/magasinstatistikk/ . The API has no parameters "
        "for dates, so the whole series is requested and the selected interval "
        "is applied immediately afterwards. The result is cached per interval, "
        "so moving the slider triggers a new download."
    )
    st.write(
        "The five measurement columns are charted above. The remaining imported "
        "columns are identifiers and metadata rather than measurements, and are "
        "shown in the raw data below."
    )
 
    st.write(
        "Areas defined by the API. The column names are translated, but the "
        "names and descriptions are quoted from NVE and stay in Norwegian."
    )
    st.dataframe(load_areas(), use_container_width=True)
 
    st.write("Raw downloaded data, all columns:")
    st.dataframe(data.head(200), use_container_width=True)