"""Cross-border page: pie chart and line plot side by side, read from MongoDB."""

import matplotlib.pyplot as plt
import streamlit as st

from modules.data import load_flows

st.title("Cross-border power flow")

flows = load_flows()

connections = sorted(flows["connection"].unique())
years = sorted(flows["timestamp"].dt.year.unique())

# Readable labels for the two flow directions.
DIRECTION_LABELS = {"export": "Out of Norway", "import": "Into Norway"}

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Split the view into two columns.
left, right = st.columns(2)

# --- Left column: pie chart ----------------------------------------------

with left:
    st.subheader("Energy in and out of Norway")

    connection = st.radio("Connection", options=connections)
    year = st.selectbox("Year", options=years, index=len(years) - 1)

    year_data = flows[
        (flows["connection"] == connection)
        & (flows["timestamp"].dt.year == year)
    ]

    # The data is hourly, so each value in MW represents one MWh of energy.
    totals = year_data.groupby("direction")["flow_mw"].sum()

    if totals.empty:
        st.info("No data for this combination.")
    else:
        labels = []
        for direction in totals.index:
            labels.append(DIRECTION_LABELS[direction])

        fig, ax = plt.subplots(figsize=(5, 5))
        ax.pie(totals, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title(f"{connection}, {year}")
        st.pyplot(fig)

        st.caption(
            f"Out of Norway: {totals.get('export', 0):,.0f} MWh. "
            f"Into Norway: {totals.get('import', 0):,.0f} MWh."
        )

# --- Right column: line plot ---------------------------------------------

with right:
    st.subheader("Flow over time")

    # Pills allow any set of months to be selected.
    selected_names = st.pills(
        "Months",
        options=MONTH_NAMES,
        selection_mode="multi",
        default=["January"],
    )

    # Turn the month names back into month numbers.
    selected_months = []
    for name in selected_names:
        selected_months.append(MONTH_NAMES.index(name) + 1)

    if not selected_months:
        st.info("Select at least one month.")
    else:
        subset = flows[
            (flows["timestamp"].dt.year == year)
            & (flows["timestamp"].dt.month.isin(selected_months))
        ]

        fig, ax = plt.subplots(figsize=(7, 5))

        # Two lines per connection: one for each direction.
        for name in connections:
            for direction in ["export", "import"]:
                series = subset[
                    (subset["connection"] == name)
                    & (subset["direction"] == direction)
                ].sort_values("timestamp")

                # Resampling to a continuous hourly index leaves gaps as NaN,
                # so the line breaks instead of jumping across unselected months.
                series = series.set_index("timestamp")["flow_mw"].resample("1h").mean()

                ax.plot(
                    series.index,
                    series.values,
                    linewidth=0.7,
                    label=f"{name}, {direction}",
                )

        ax.set_title(f"Cross-border flow, {year}")
        ax.set_xlabel("Time")
        ax.set_ylabel("Flow (MW)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=6, ncol=2)
        fig.autofmt_xdate()

        st.pyplot(fig)

# --- Documentation --------------------------------------------------------

with st.expander("About the data on this page"):
    st.write(
        "Source: the ENTSO-E Transparency Platform, which publishes the "
        "physical power flow across every border in Europe. The four "
        "connections shown are the subsea interconnectors running from bidding "
        "zone NO2 to Denmark, the Netherlands, Germany and Great Britain."
    )
    st.write(
        "The data was retrieved in the Jupyter Notebook for the last two years, "
        "resampled to hourly resolution, written to a local Cassandra database "
        "through Spark, read back out with Spark SQL and inserted into MongoDB. "
        "This page reads the MongoDB collection, since the Cassandra instance "
        "runs only on the development machine."
    )
    st.write(
        "Flow has a direction: one query gives power leaving Norway and the "
        "opposite query gives power entering it, which is what the two slices "
        "of the pie chart show. Both plots use the year selected on the left."
    )