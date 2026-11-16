"""Reservoir levels page: table and plots for the area chosen in the sidebar."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from modules.data import MEASUREMENT_COLUMNS, load_areas, load_reservoirs
from modules.theme import PALETTE, page_colours

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

# The colour of this page, used for the small charts in the table.
DEEP = page_colours("Overview")[0]

# One colour per area, so an area keeps the same colour in every chart.
colours = {}
position = 0
for number in area_numbers:
    colours[number] = PALETTE[position % len(PALETTE)]
    position += 1

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
    column_config[column] = st.column_config.LineChartColumn(column, color=DEEP)

st.dataframe(table, column_config=column_config, width="stretch")

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

figure = make_subplots(
    rows=len(columns_to_plot),
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
)

position = 1
for column in columns_to_plot:
    # One line per area number, so the areas of the chosen type can be
    # compared against each other.
    for number in area_numbers:
        area_rows = selected[selected["Area number"] == number].sort_values("Date")

        # The area chosen in the sidebar is drawn thicker, so it can be
        # followed from page to page.
        if number == area_number:
            width = 2.6
        else:
            width = 1.0

        name = f"{area_type} {number}"

        figure.add_trace(
            go.Scatter(
                x=area_rows["Date"],
                y=area_rows[column],
                name=name,
                legendgroup=name,
                line=dict(color=colours[number], width=width),
                # The same areas are in every chart, so one legend is enough.
                showlegend=position == 1,
                hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}<extra>" + name + "</extra>",
            ),
            row=position,
            col=1,
        )

    figure.update_yaxes(title_text=column, title_font_size=11, row=position, col=1)
    position += 1

figure.update_xaxes(title_text="Date", row=len(columns_to_plot), col=1)

figure.update_layout(
    title=f"{column_choice}, area type {area_type}",
    height=300 * len(columns_to_plot),
    hovermode="x unified",
    margin=dict(l=70, r=20, t=60, b=50),
)

st.plotly_chart(figure, width="stretch")

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
    st.dataframe(load_areas(), width="stretch")

    st.write("Raw downloaded data, all columns:")
    st.dataframe(data.head(200), width="stretch")