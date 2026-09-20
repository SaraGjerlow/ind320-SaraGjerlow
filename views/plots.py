"""Page 3: interactive plot with column and month-range selection."""

import matplotlib.pyplot as plt
import streamlit as st

from modules.data import load_reservoirs

st.title("Plots")

reservoirs = load_reservoirs()

# Build a list of months present in the data, as period labels like "1995-01".
months = sorted(reservoirs.index.to_period("M").unique())
month_labels = [str(m) for m in months]

column_choice = st.selectbox(
    "Column",
    options=["All columns"] + list(reservoirs.columns),
    help="Choose a single variable or plot all of them together.",
)

# select_slider returns a (start, end) tuple when given a two-element value.
# Default is the first month only, as required by the assignment.
start_label, end_label = st.select_slider(
    "Month range",
    options=month_labels,
    value=(month_labels[0], month_labels[0]),
)

# Filter rows whose month falls inside the selected range.
row_months = reservoirs.index.to_period("M").astype(str)
mask = (row_months >= start_label) & (row_months <= end_label)
subset = reservoirs.loc[mask]

st.caption(f"{len(subset)} weekly observations from {start_label} to {end_label}.")

fig, ax = plt.subplots(figsize=(10, 4))

if column_choice == "All columns":
    # Columns use different units, so normalise to make the shapes comparable.
    value_range = subset.max() - subset.min()
    varying = subset.loc[:, value_range > 0]
    normalised = (varying - varying.min()) / (varying.max() - varying.min())

    for col in normalised.columns:
        ax.plot(normalised.index, normalised[col], linewidth=1.2, label=col)

    ax.set_ylabel("Normalised value (0-1)")
    ax.set_title("All columns, min-max normalised")
    ax.legend(fontsize=8)
else:
    ax.plot(subset.index, subset[column_choice], linewidth=1.2)
    ax.set_ylabel(column_choice)
    ax.set_title(column_choice)

ax.set_xlabel("Date")
ax.grid(alpha=0.3)
fig.autofmt_xdate()

st.pyplot(fig)