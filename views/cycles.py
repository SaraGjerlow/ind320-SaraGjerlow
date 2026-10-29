"""Reservoir cycles page: STL decomposition and spectrogram in two tabs."""

import streamlit as st

from modules.analysis import (
    WEEKS_PER_YEAR,
    reservoir_cycles,
    reservoir_series,
    reservoir_spectrogram,
)
from modules.data import load_reservoirs

st.title("Reservoir cycles")

# The area and the interval come from the sidebar, so this page and the
# weather page always describe the same place.
area_type = st.session_state["area_type"]
area_number = st.session_state["area_number"]
start_year = st.session_state["start_year"]
end_year = st.session_state["end_year"]

st.write(
    f"Two ways of looking at the yearly cycle in the reservoir filling of "
    f"**{area_type} {area_number}**. Change the area in the sidebar."
)

data = load_reservoirs(start_year, end_year)
series = reservoir_series(data, area_type, area_number)

# Both analyses need at least two full years to have anything to work with.
if len(series) < 2 * WEEKS_PER_YEAR:
    st.warning(
        f"Only {len(series)} weeks of data for this area and interval. Both "
        f"analyses need at least {2 * WEEKS_PER_YEAR} weeks, which is two "
        f"full years. Widen the download interval in the sidebar."
    )
    st.stop()

st.caption(f"{len(series)} weekly observations from {start_year} to {end_year}.")

stl_tab, spectrogram_tab = st.tabs(["STL decomposition", "Spectrogram"])

# --- STL ------------------------------------------------------------------

with stl_tab:
    st.write(
        "STL splits the series into a trend, a repeating yearly pattern and a "
        "remainder of whatever is left over."
    )

    left, middle, right = st.columns(3)

    # Both smoothers have to be odd numbers, so the sliders step by two.
    with left:
        seasonal_smoother = st.slider(
            "Seasonal smoother (weeks)",
            min_value=7, max_value=35, value=13, step=2,
            help="How much the shape of the yearly cycle may change from one "
            "year to the next. A small number follows each year closely.",
        )

    with middle:
        # The trend smoother cannot be longer than the series itself.
        longest_trend = min(401, len(series) - 1)
        if longest_trend % 2 == 0:
            longest_trend = longest_trend - 1

        trend_smoother = st.slider(
            "Trend smoother (weeks)",
            min_value=53, max_value=longest_trend,
            value=min(105, longest_trend), step=2,
            help="How long a movement has to last before it counts as trend "
            "rather than season.",
        )

    with right:
        robust = st.checkbox(
            "Robust",
            value=False,
            help="Downweight single weeks that stick out, so one unusual year "
            "does not bend the trend around itself.",
        )

    figure, parts, statistics = reservoir_cycles(
        series,
        seasonal_smoother=seasonal_smoother,
        trend_smoother=trend_smoother,
        robust=robust,
    )

    st.pyplot(figure)

    first, second, third = st.columns(3)
    first.metric("Seasonal share of variance",
                 f"{statistics['seasonal_share']:.2f}")
    second.metric("Trend share of variance",
                  f"{statistics['trend_share']:.2f}")
    third.metric("Remainder standard deviation",
                 f"{statistics['remainder_sd']:.4f}")

    with st.expander("The three parts as numbers"):
        st.dataframe(parts, use_container_width=True)

# --- Spectrogram ----------------------------------------------------------

with spectrogram_tab:
    st.write(
        "The STL above assumes one yearly pattern for the whole period. A "
        "spectrogram does not. It looks at one window of weeks at a time, so "
        "a cycle that appears or disappears shows up as a band that changes "
        "brightness."
    )

    left, right = st.columns(2)

    with left:
        longest_window = min(312, len(series))

        window_weeks = st.slider(
            "Window length (weeks)",
            min_value=104, max_value=longest_window,
            value=min(208, longest_window), step=4,
            help="A long window separates close periods better. A short one "
            "says more precisely when something changed.",
        )

    with right:
        overlap_weeks = st.slider(
            "Overlap (weeks)",
            min_value=0, max_value=window_weeks - 4,
            value=min(156, window_weeks - 4), step=4,
            help="How much two neighbouring windows share. More overlap gives "
            "a smoother picture but no new information.",
        )

    figure, summary, statistics = reservoir_spectrogram(
        series,
        window_weeks=window_weeks,
        overlap_weeks=overlap_weeks,
    )

    st.pyplot(figure)

    first, second = st.columns(2)
    first.metric("Windows", statistics["windows"])
    second.metric(
        "Periods covered",
        f"{statistics['shortest_period']:.0f} to "
        f"{statistics['longest_period']:.0f} weeks",
    )

    st.write("The strongest cycle in each window:")
    st.dataframe(summary, use_container_width=True, hide_index=True)

# --- Documentation --------------------------------------------------------

with st.expander("About the data on this page"):
    st.write(
        "Source: NVE Magasinstatistikk, the same weekly series as on the "
        "reservoir levels page. The column used here is the fill level as a "
        "fraction between zero and one."
    )
    st.write(
        "Both analyses treat the series as one sample per week, so a period "
        "of 52 points is one year. The weeks are not perfectly even, because "
        "some years have 53 ISO weeks, but neither method depends on that."
    )