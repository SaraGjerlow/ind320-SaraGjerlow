import matplotlib.pyplot as plt
import streamlit as st

from modules.data import load_flows

# Readable labels instead of the raw values stored in the database.
DIRECTION_LABELS = {
    "export": "Out of Norway",
    "import": "Into Norway",
}

# Used both for the month selector and to convert a name to a month number.
MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

st.title("Cross-border power flow")
st.write(
    "Hourly cross-border flows between Norway (NO2) and four neighbouring "
    "areas. The data was collected from ENTSO-E in the notebook for part 2 "
    "and is read here from MongoDB."
)

# One document per hour, connection and direction.
flows = load_flows()

connection_names = sorted(flows["connection"].unique())
years = sorted(flows["timestamp"].dt.year.unique())

left, right = st.columns(2)

with left:
    st.subheader("Direction of flow")

    connection = st.radio("Connection", options=connection_names)
    year = st.selectbox("Year", options=years, index=len(years) - 1)

    # Keep only the rows for the selected connection and year.
    year_data = flows[
        (flows["connection"] == connection)
        & (flows["timestamp"].dt.year == year)
    ]

    # Only full calendar years are comparable, and the two year download
    # window cuts the first and the last year short.
    months_present = year_data["timestamp"].dt.month.nunique()
    if months_present < 12:
        st.warning(
            f"{year} is incomplete in this dataset: only {months_present} of "
            "12 months are covered."
        )

    # Every row is an hourly mean in MW, so summing the rows of one year
    # gives the energy in MWh.
    totals = year_data.groupby("direction")["flow_mw"].sum()

    # Translate the index values to the labels defined at the top.
    pie_labels = []
    for direction in totals.index:
        pie_labels.append(DIRECTION_LABELS[direction])

    pie_figure, pie_axes = plt.subplots()
    pie_axes.pie(totals.values, labels=pie_labels, autopct="%1.1f%%")
    pie_axes.set_title(f"{connection}, {year}")
    st.pyplot(pie_figure)

    # The percentages alone hide the size of the flows, so the totals are
    # written out below the chart.
    caption_parts = []
    for direction in totals.index:
        caption_parts.append(
            f"{DIRECTION_LABELS[direction]}: {totals[direction]:,.0f} MWh"
        )
    st.caption("   |   ".join(caption_parts))

with right:
    st.subheader("Flow over time")

    selected_months = st.pills(
        "Months",
        options=MONTH_NAMES,
        selection_mode="multi",
        default=["January"],
    )

    # The pills return month names, while the data holds month numbers.
    month_numbers = []
    for name in selected_months:
        month_numbers.append(MONTH_NAMES.index(name) + 1)

    subset = year_data[year_data["timestamp"].dt.month.isin(month_numbers)]

    # Two different empty cases: nothing is selected, or the selected months
    # fall outside the two year download window.
    if len(selected_months) == 0:
        st.info("Select at least one month to draw the plot.")
    elif len(subset) == 0:
        st.info("No data for the selected months.")
    else:
        line_figure, line_axes = plt.subplots()

        # The same connection as on the left, so the two halves of the page
        # describe the same cable. Two lines keep the plot readable.
        for direction in ["export", "import"]:
            series = subset[subset["direction"] == direction]
            series = series.sort_values("timestamp")

            # Resampling to a continuous hourly index leaves the unselected
            # months as NaN, so the line breaks instead of jumping across them.
            series = series.set_index("timestamp")["flow_mw"].resample("1h").mean()

            line_axes.plot(
                series.index,
                series.values,
                linewidth=0.7,
                label=DIRECTION_LABELS[direction],
            )

        line_axes.set_xlabel("Time")
        line_axes.set_ylabel("Flow (MW)")
        line_axes.set_title(f"{connection}, {year}")
        line_axes.legend()
        line_figure.autofmt_xdate()
        st.pyplot(line_figure)

with st.expander("About the data on this page"):
    st.write(
        "The flows come from the ENTSO-E Transparency Platform, which "
        "publishes the physical cross-border flows between European bidding "
        "zones. Norway is represented here by the bidding zone NO2, which "
        "holds all four interconnectors to other countries: Skagerrak to "
        "Denmark (DK1), NorNed to the Netherlands (NL), NordLink to Germany "
        "(DE-LU) and North Sea Link to Great Britain (GB)."
    )
    st.write(
        "The two most recent years were downloaded in the notebook, written "
        "to a local Cassandra database with Spark, read back out with Spark "
        "SQL and finally inserted into MongoDB. This app reads the documents "
        "from MongoDB, so the pipeline built in the notebook is what feeds "
        "the charts on this page."
    )
    st.write(
        "ENTSO-E reports each direction as its own time series, so every "
        "connection has one series out of Norway and one into Norway. The "
        "values are hourly averages in MW. Because the download window is "
        "the last two years rather than whole calendar years, the first and "
        "the last year in the selector cover only part of the year."
    )