"""Weather vs reservoirs page: sliding correlation and the best lag."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.data import RESERVOIR_COLUMNS, WEATHER_COLUMNS, load_weekly_frame
from modules.theme import page_colours

st.title("Weather vs reservoirs")

area = st.session_state["area"]

# The colour of this page, and a warm one for the bar that wins.
DEEP, PALE = page_colours("Weather vs reservoirs")
FLAG = "#E07A5F"

st.write(
    f"How closely the weather over **{area}** follows what happens in the "
    f"reservoirs, measured on a window that slides through the years rather "
    f"than on the whole period at once."
)

weekly = load_weekly_frame(area)

# Weather is only stored for the areas the notebook downloaded it for.
if "precipitation_sum" not in weekly.columns:
    st.info(
        f"No weather stored for {area}. Choose an area that has weather, or "
        f"download it on the Outliers and anomalies page."
    )
    st.stop()


def sliding_correlation(weekly, weather_column, reservoir_column, lag, window):
    """Rolling correlation between weather and the reservoir data.

    lag shifts the weather backwards in weeks, and window is how many weeks go
    into each correlation.
    """
    pair = pd.DataFrame({
        "weather": weekly[weather_column].shift(lag),
        "reservoir": weekly[reservoir_column],
    }).dropna()

    correlation = pair["weather"].rolling(window).corr(pair["reservoir"])
    return correlation.dropna()


@st.cache_data(ttl=3600, show_spinner="Trying every lag")
def correlation_by_lag(area, weather_column, reservoir_column, max_lag, window):
    """Run the correlation once per lag, to see which delay fits best."""
    weekly = load_weekly_frame(area)

    rows = []
    for lag in range(0, max_lag + 1):
        correlation = sliding_correlation(
            weekly, weather_column, reservoir_column, lag, window
        )
        rows.append({
            "lag": lag,
            "mean correlation": round(float(correlation.mean()), 3),
        })

    return pd.DataFrame(rows).set_index("lag")


# --- The controls ---------------------------------------------------------

left, middle, right, far = st.columns(4)

with left:
    weather_name = st.selectbox(
        "Weather", options=list(WEATHER_COLUMNS),
        help="The weekly weather averaged over the area.",
    )

with middle:
    reservoir_name = st.selectbox(
        "Reservoir", options=list(RESERVOIR_COLUMNS), index=1,
        help="Rain adds water, so it shows up in the weekly change rather "
        "than in the level itself.",
    )

with right:
    lag = st.slider(
        "Lag (weeks)", min_value=0, max_value=40, value=0, step=1,
        help="How many weeks the weather is shifted forward before it is "
        "compared. Snow needs a long lag, rain almost none.",
    )

with far:
    window = st.slider(
        "Window (weeks)", min_value=13, max_value=208, value=52, step=13,
        help="How many weeks go into each correlation. 52 weeks is one year.",
    )

weather_column = WEATHER_COLUMNS[weather_name]
reservoir_column = RESERVOIR_COLUMNS[reservoir_name]

# --- The sliding correlation ----------------------------------------------

st.subheader("Correlation through the years")

correlation = sliding_correlation(
    weekly, weather_column, reservoir_column, lag, window
)

if len(correlation) == 0:
    st.warning("The window is longer than the data that is left after the lag.")
    st.stop()

figure = go.Figure()

figure.add_trace(go.Scatter(
    x=correlation.index, y=correlation.to_numpy(), name="Correlation",
    line=dict(color=DEEP, width=1.6),
))

# A line at zero, so it is easy to see where the sign flips.
figure.add_hline(y=0, line_width=1, line_dash="dot")

figure.update_layout(
    xaxis_title="Date",
    yaxis_title="Correlation",
    yaxis_range=[-1, 1],
    hovermode="x unified",
    height=400,
    margin=dict(l=70, r=20, t=30, b=50),
)

st.plotly_chart(figure, width="stretch")

one, two, three, four = st.columns(4)
one.metric("Windows", len(correlation))
two.metric("Mean", round(float(correlation.mean()), 3))
three.metric("Lowest", round(float(correlation.min()), 3))
four.metric("Highest", round(float(correlation.max()), 3))

st.caption(
    "A correlation near zero does not mean the weather does not matter. It "
    "means it does not matter in the same week."
)

# --- The best lag ---------------------------------------------------------

st.subheader("Which delay fits best")

st.write(
    "The same correlation is run once per lag, from no delay up to the "
    "longest one chosen below. The tallest bar is the delay where the weather "
    "and the reservoirs move together the most."
)

max_lag = st.slider(
    "Longest lag to try", min_value=8, max_value=40, value=26, step=1,
)

table = correlation_by_lag(
    area, weather_column, reservoir_column, max_lag, window
)

# The lag with the strongest correlation, whichever sign it has.
best_lag = int(table["mean correlation"].abs().idxmax())

colours = []
for lag_value in table.index:
    if lag_value == best_lag:
        colours.append(FLAG)
    else:
        colours.append(PALE)

bar_figure = go.Figure(go.Bar(
    x=table.index, y=table["mean correlation"],
    marker=dict(color=colours, line=dict(color=DEEP, width=1)),
    hovertemplate="Lag %{x} weeks<br>%{y:.3f}<extra></extra>",
))

bar_figure.add_hline(y=0, line_width=1, line_dash="dot")

bar_figure.update_layout(
    xaxis_title="Lag (weeks)",
    yaxis_title="Mean correlation",
    height=380,
    margin=dict(l=70, r=20, t=30, b=50),
)

st.plotly_chart(bar_figure, width="stretch")

st.metric(
    f"Strongest at {best_lag} weeks",
    f"{table.loc[best_lag, 'mean correlation']:+.3f}",
)

st.caption(
    "Snowfall against the weekly change peaks around twenty weeks, which is "
    "roughly how long it takes for snow to melt and reach the reservoirs. "
    "That is where the lagged snow column on the Forecast page comes from."
)

# --- Documentation --------------------------------------------------------

with st.expander("About the data on this page"):
    st.write(
        "Both series come from the weekly table built in modules/data.py: the "
        "filling from NVE and the weather from open-meteo, averaged over the "
        "locations sampled inside the area and resampled to the same Sunday "
        "dated weeks."
    )
    st.write(
        "A rolling correlation is used rather than one number for the whole "
        "period, because the relationship is not the same all year. A single "
        "number over thirty years would average the winters and the summers "
        "into something close to nothing."
    )
    st.write("The correlation per lag:")
    st.dataframe(table.T, width="stretch")