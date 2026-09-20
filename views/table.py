"""Page 2: one table row per data column, with a sparkline of the first month."""

import streamlit as st

from modules.data import load_reservoirs

st.title("Data table")

reservoirs = load_reservoirs()

# The assignment asks for the first month of the series. The data is weekly,
# so "first month" is every row in the same calendar month as the first row.
first_date = reservoirs.index.min()
first_month = reservoirs[
    (reservoirs.index.year == first_date.year)
    & (reservoirs.index.month == first_date.month)
]

st.caption(
    f"Showing {first_month.index.min():%Y-%m-%d} to {first_month.index.max():%Y-%m-%d} "
    f"({len(first_month)} weekly observations)."
)

# Transpose the layout: one row per variable, not per week. The sparkline
# column holds the list of values for that variable over the first month.
summary = first_month.T.apply(list, axis=1).rename("First month").to_frame()
summary.index.name = "Variable"

# Add the last observed value so the row is readable as a number, not just a shape.
summary["Last value"] = first_month.iloc[-1].values

st.dataframe(
    summary,
    column_config={
        "First month": st.column_config.LineChartColumn(
            "First month",
            help="Weekly values for the first calendar month of the series",
            width="medium",
        ),
        "Last value": st.column_config.NumberColumn("Last value", format="%.4f"),
    },
    use_container_width=True,
)