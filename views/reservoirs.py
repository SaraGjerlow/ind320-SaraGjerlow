"""Reservoir levels page: table and plots for the area chosen in the sidebar."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from modules.data import MEASUREMENT_COLUMNS, load_areas, load_reservoirs

st.title("Reservoir levels")

# The area type and the interval are set in the sidebar and shared with the
# other pages. This page compares all the areas of the chosen type against
# each other, and draws the chosen number with a thicker line.
area_type = st.session_state["area_type"]
area_number = st.session_state["area_number"]
start_year = st.session_state["start_year"]
end_year = st.session_state["end_year"]

data = load_reservoirs(start_year, end_year)

# Keep the areas belonging to the selected type.
selected = data[data["Area type"] == area_type]
area_numbers = sorted(selected["Area number"].unique())

st.caption(
    f"{len(selected)} weekly observations from {start_year} to {end_year}, "
    f"covering {len(area_numbers)} area(s) of type {area_type}. "
    f"{area_type} {area_number} is drawn thicker."
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
for number in area_numbers:
    area_rows = selected[selected["Area number"] == number].sort_values("Date")

    row = {"Area": f"{area_type} {number}"}
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

st.subheader("Measurements over time")

ALL_COLUMNS = "All columns"

column_choice = st.selectbox(
    "Column to plot",
    options=[ALL_COLUMNS] + MEASUREMENT_COLUMNS,
    help="Plot one measurement, or all five stacked above each other.",
)

# One chart for a single column, or one chart per column when all are chosen.
# The columns do not share a unit, so they cannot go in the same axes.
if column_choice == ALL_COLUMNS:
    columns_to_plot = MEASUREMENT_COLUMNS
else:
    columns_to_plot = [column_choice]

figure, axes = plt.subplots(
    len(columns_to_plot),
    1,
    figsize=(11, 3.2 * len(columns_to_plot)),
    sharex=True,
    squeeze=False,
)

# squeeze=False always gives a grid, so the first column of it is the list of
# axes. That way the loop below works for one column and for five.
axes = axes[:, 0]

for position, column in enumerate(columns_to_plot):
    one_axis = axes[position]

    # One line per area number, so the areas of the chosen type can be
    # compared against each other.
    for number in area_numbers:
        area_rows = selected[selected["Area number"] == number].sort_values("Date")

        # The area chosen in the sidebar is drawn thicker, so it can be
        # followed from page to page.
        if number == area_number:
            width = 2.2
        else:
            width = 0.9

        one_axis.plot(
            area_rows["Date"],
            area_rows[column],
            linewidth=width,
            label=f"{area_type} {number}",
        )

    one_axis.set_ylabel(column, fontsize=8)
    one_axis.grid(alpha=0.3)

    # One legend is enough when the same areas are drawn in every chart.
    if position == 0:
        one_axis.legend(fontsize=8)

axes[0].set_title(f"{column_choice}, area type {area_type}")
axes[-1].set_xlabel("Date")
figure.autofmt_xdate()
figure.tight_layout()

st.pyplot(figure)

# --- Documentation --------------------------------------------------------

with st.expander("About the data on this page"):
    st.write(
        "Source: NVE Magasinstatistikk, read from "
        "https://biapi.nve.no/magasinstatistikk/ . The API has no parameters "
        "for dates, so the whole series is requested and the selected interval "
        "is applied immediately afterwards. The result is cached per interval, "
        "so moving the slider in the sidebar triggers a new download."
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