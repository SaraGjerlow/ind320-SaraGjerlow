"""Page 2: one table row per data column, with a line chart of the first month."""
 
import pandas as pd
import streamlit as st
 
from modules.data import load_reservoirs
 
st.title("Data table")
 
data = load_reservoirs()
 
# The assignment asks for the first month of the series. The data is weekly,
# so this is every row in the same calendar month as the very first row.
first_date = data.index.min()
first_month = data[
    (data.index.year == first_date.year) & (data.index.month == first_date.month)
]
 
st.caption(
    f"Showing {first_month.index.min():%Y-%m-%d} to "
    f"{first_month.index.max():%Y-%m-%d} "
    f"({len(first_month)} weekly observations)."
)
 
# Build the table one row at a time. The raw data has one row per week, but the
# table needs one row per variable, so the loop goes over the columns.
rows = []
for column in data.columns:
    rows.append({
        "Variable": column,
        # A list of values in one cell is what LineChartColumn draws.
        "First month": list(first_month[column]),
        "Last value": first_month[column].iloc[-1],
    })
 
summary = pd.DataFrame(rows).set_index("Variable")
 
# column_config decides how each column is displayed: the list as a line chart,
# the number with four decimals.
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