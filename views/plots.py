"""Page 3: plot of the data, with a column selector and a month range slider."""
 
import matplotlib.pyplot as plt
import streamlit as st
 
from modules.data import load_reservoirs
 
st.title("Plots")
 
data = load_reservoirs()
 
# Turn every row's date into a "YYYY-MM" string. month_options is the list of
# months the slider can choose between.
row_months = data.index.strftime("%Y-%m")
month_options = sorted(set(row_months))
 
# Drop-down menu: one single column, or all of them together.
column_choice = st.selectbox(
    "Column",
    options=["All columns"] + list(data.columns),
)
 
# Giving select_slider a pair of values turns it into a range slider with two
# handles. Both start on the first month, as the assignment asks for.
start_month, end_month = st.select_slider(
    "Month range",
    options=month_options,
    value=(month_options[0], month_options[0]),
)
 
# Keep the rows whose month falls inside the selected range.
subset = data[(row_months >= start_month) & (row_months <= end_month)]
 
st.caption(f"{len(subset)} weekly observations from {start_month} to {end_month}.")
 
fig, ax = plt.subplots(figsize=(10, 4))
 
if column_choice == "All columns":
    # The columns use different units, so each one is rescaled to 0-1 first.
    # Capacity is constant and has no range to divide by, so it is left out.
    columns_to_plot = [
        "Fill level (fraction)",
        "Stored energy (TWh)",
        "Fill level previous week (fraction)",
        "Change in fill level (fraction)",
    ]
    for column in columns_to_plot:
        values = subset[column]
        normalised = (values - values.min()) / (values.max() - values.min())
        ax.plot(subset.index, normalised, linewidth=1.2, label=column)
 
    ax.set_title("All columns, min-max normalised")
    ax.set_ylabel("Normalised value (0 to 1)")
    ax.legend(fontsize=8)
else:
    ax.plot(subset.index, subset[column_choice], linewidth=1.2)
    ax.set_title(column_choice)
    ax.set_ylabel(column_choice)
 
ax.set_xlabel("Date")
ax.grid(alpha=0.3)
fig.autofmt_xdate()
 
st.pyplot(fig)