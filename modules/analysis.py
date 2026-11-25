"""The four analyses from the part 3 notebook, written as reusable functions.

The notebook versions print their numbers. These return them instead, so the
app can show them with st.metric and the page decides how they look.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

# The reservoir statistics are weekly, so one full year is 52 points.
WEEKS_PER_YEAR = 52

# The same colours as in modules/theme.py, repeated so this file imports nothing.
BLUE = "#3F72AF"
PINK = "#C45B8B"
TURQUOISE = "#3E9AA3"
PURPLE = "#8663B0"
GREY = "#9A93A8"
# Warm colour for the points that are flagged, so they stand out on any page.
FLAG = "#E07A5F"
# The pastel colours from modules/theme.py, for plots that draw several lines.
PALETTE = [PINK, BLUE, TURQUOISE, PURPLE, "#7FAFD6", "#E2A3C0"]


def precipitation_outliers(weather, cutoff=25, n_sigma=3.0,
                           column="precipitation", colour=BLUE):
    """Plot precipitation with SPC limits and mark the outliers.

    cutoff is how many low DCT frequencies count as seasonal. A low number
    keeps only the slowest shape, a high number follows the curve more closely.

    n_sigma is how many robust standard deviations away from the seasonal
    level a point has to be before it counts as an outlier.

    Returns the figure, a table of the outliers and a dictionary of numbers.
    """
    series = weather.set_index("time")[column]
    values = series.to_numpy()

    # Split into frequencies, keep only the slowest ones, and transform back.
    # What is left is the seasonal shape of the year.
    coefficients = dct(values, norm="ortho")
    coefficients[cutoff:] = 0.0
    seasonal = idct(coefficients, norm="ortho")

    # SATV is what remains when the season is removed. It is only used to find
    # the limits, it is never plotted.
    satv = values - seasonal

    # Robust statistics, so that the outliers do not widen their own limits.
    median = np.median(satv)
    mad = np.median(np.abs(satv - median))
    robust_sigma = 1.4826 * mad

    distance = n_sigma * robust_sigma
    is_outlier = np.abs(satv - median) > distance

    # The limits are drawn on the original curve, so they follow the season.
    upper = seasonal + median + distance
    lower = seasonal + median - distance

    figure = go.Figure()

    figure.add_trace(go.Scatter(
        x=series.index, y=values, name=f"Average {column}",
        line=dict(color=BLUE, width=1.0),
    ))
    figure.add_trace(go.Scatter(
        x=series.index, y=upper, name=f"SPC limits ({n_sigma} sigma)",
        line=dict(color=GREY, width=1.2),
    ))
    figure.add_trace(go.Scatter(
        x=series.index, y=lower, name="Lower limit",
        line=dict(color=GREY, width=1.2), showlegend=False,
    ))
    figure.add_trace(go.Scatter(
        x=series.index[is_outlier], y=values[is_outlier], name="Outliers",
        mode="markers", marker=dict(color=PINK, size=5),
    ))

    figure.update_layout(
        title=f"{column} with SPC limits (cutoff {cutoff}, {n_sigma} sigma)",
        xaxis_title="Time",
        yaxis_title=column,
        height=460,
        hovermode="x unified",
    )

    outliers = pd.DataFrame({
        "time": series.index[is_outlier],
        column: values[is_outlier],
    })

    statistics = {
        "hours": len(values),
        "outliers": int(is_outlier.sum()),
        "percent": 100 * float(is_outlier.mean()),
        "robust_sigma": float(robust_sigma),
    }

    return figure, outliers, statistics


def temperature_anomalies(weather, proportion=0.01, n_neighbors=20,
                          column="temperature_2m", colour=BLUE,
                          time_feature="Day of year"):
    """Plot a weather variable and mark anomalies found by Local Outlier Factor.

    proportion is the share of points that should be flagged, so 0.01 marks
    the one percent that look most out of place.

    n_neighbors is how many nearby points each point is compared against. A
    small number reacts to short events, a large one only to longer ones.

    time_feature decides what the neighbours are. "Day of year" compares a
    point against the same time of year in every year, "Hour index" against
    the hours right before and after it.

    Returns the figure, a table of the anomalies and a dictionary of numbers.
    """
    series = weather.set_index("time")[column]
    values = series.to_numpy()

    # The value is scaled, so no feature dominates the distance calculation.
    scaled = (values - values.mean()) / values.std()

    if time_feature == "Day of year":
        # Written as a sine and a cosine, so the last day of December lies
        # next to the first day of January instead of a whole year away.
        day = series.index.dayofyear.to_numpy(dtype=float)
        angle = 2 * np.pi * day / 365.25

        # Both already lie between -1 and 1, close to the scaled values.
        features = np.column_stack([np.sin(angle), np.cos(angle), scaled])
    else:
        # The plain hour count, scaled the same way as the values.
        hours = np.arange(len(values), dtype=float)
        features = np.column_stack([
            (hours - hours.mean()) / hours.std(),
            scaled,
        ])

    detector = LocalOutlierFactor(
        n_neighbors=n_neighbors, contamination=proportion
    )
    labels = detector.fit_predict(features)

    # fit_predict marks anomalies with -1. The score says how isolated each
    # point is, where a higher number is more unusual.
    is_anomaly = labels == -1
    score = -detector.negative_outlier_factor_

    figure = go.Figure()

    figure.add_trace(go.Scatter(
        x=series.index, y=values, name=f"Average {column}",
        line=dict(color=BLUE, width=1.0),
    ))
    figure.add_trace(go.Scatter(
        x=series.index[is_anomaly], y=values[is_anomaly], name="Anomalies",
        mode="markers", marker=dict(color=PINK, size=5),
    ))

    figure.update_layout(
        title=f"{column} with LOF anomalies "
              f"({100 * proportion:.1f} percent flagged, "
              f"time as {time_feature.lower()})",
        xaxis_title="Time",
        yaxis_title=column,
        height=460,
        hovermode="x unified",
    )

    anomalies = pd.DataFrame({
        "time": series.index[is_anomaly],
        column: values[is_anomaly],
        "lof_score": score[is_anomaly].round(3),
    })

    statistics = {
        "hours": len(values),
        "anomalies": int(is_anomaly.sum()),
        "percent": 100 * float(is_anomaly.mean()),
        "coldest": float(anomalies[column].min()),
        "warmest": float(anomalies[column].max()),
    }

    return figure, anomalies, statistics

def shades(colour, count):
    """Make count colours out of one, from the colour itself to a pale tint."""
    red = int(colour[1:3], 16)
    green = int(colour[3:5], 16)
    blue = int(colour[5:7], 16)

    result = []
    step = 0
    while step < count:
        # Each step mixes a little more white into the original colour.
        mix = 0.5 * step / max(count - 1, 1)
        result.append("#{:02X}{:02X}{:02X}".format(
            round(red + (255 - red) * mix),
            round(green + (255 - green) * mix),
            round(blue + (255 - blue) * mix),
        ))
        step += 1

    return result

def reservoir_series(reservoirs, area_type, area_number,
                     column="Fill level (fraction)"):
    """Pick out one area and return its filling as a weekly series."""
    area = reservoirs[(reservoirs["Area type"] == area_type) &
                      (reservoirs["Area number"] == area_number)]
    area = area.sort_values("Date")

    series = area.set_index("Date")[column]

    # A repeated date would break both analyses below, so only the first of
    # any duplicate is kept.
    return series[~series.index.duplicated(keep="first")]


def reservoir_cycles(series, seasonal_smoother=13, trend_smoother=105,
                     robust=False):
    """Split one area's reservoir filling into trend, season and remainder.

    seasonal_smoother and trend_smoother are the two window lengths STL uses.
    Both have to be odd numbers. robust tells STL to downweight single weeks
    that stick out instead of letting them pull the trend.

    Returns the figure, a table with the three parts and a dictionary of
    numbers.
    """
    result = STL(series, period=WEEKS_PER_YEAR, seasonal=seasonal_smoother,
                 trend=trend_smoother, robust=robust).fit()

    # One row per part, drawn above each other on a shared date axis.
    names = ["Observed", "Trend", "Seasonal", "Remainder"]
    parts_to_plot = [series.to_numpy(), result.trend, result.seasonal,
                     result.resid]
    colours = PALETTE
    widths = [1.0, 1.4, 1.0, 0.8]

    figure = make_subplots(rows=4, cols=1, shared_xaxes=True,
                           vertical_spacing=0.04)

    position = 1
    for name in names:
        figure.add_trace(
            go.Scatter(
                x=series.index,
                y=parts_to_plot[position - 1],
                name=name,
                line=dict(color=colours[position - 1],
                          width=widths[position - 1]),
                showlegend=False,
            ),
            row=position, col=1,
        )
        figure.update_yaxes(title_text=name, title_font_size=11,
                            row=position, col=1)
        position += 1

    figure.update_xaxes(title_text="Date", row=4, col=1)
    figure.update_layout(height=820, hovermode="x unified",
                         margin=dict(l=70, r=20, t=40, b=50))

    parts = pd.DataFrame({
        "trend": result.trend,
        "seasonal": result.seasonal,
        "remainder": result.resid,
    }, index=series.index)

    # How much of the movement each part explains, as a rough share.
    total = series.var()

    statistics = {
        "weeks": len(series),
        "seasonal_share": float(result.seasonal.var() / total),
        "trend_share": float(result.trend.var() / total),
        "remainder_sd": float(result.resid.std()),
    }

    return figure, parts, statistics


def reservoir_spectrogram(series, window_weeks=208, overlap_weeks=156,
                          colour=BLUE):
    """Show how the cycles in one area's reservoir filling change over time.

    window_weeks is the length of each slice and overlap_weeks is how much two
    neighbouring slices share. The overlap has to be smaller than the window.

    Returns the figure, a table of the strongest cycle per window and a
    dictionary of numbers.
    """
    values = series.to_numpy()

    # One sample per week, so fs is 1 and the frequencies come out in cycles
    # per week.
    frequencies, window_centres, power = spectrogram(
        values, fs=1.0, nperseg=window_weeks, noverlap=overlap_weeks
    )

    # The first frequency is zero, which is just the average level and would
    # give a period of infinity. It is dropped before converting.
    frequencies = frequencies[1:]
    power = power[1:, :]
    periods = 1.0 / frequencies

    # scipy counts the window centres in samples, so one sample is seven days.
    times = series.index[0] + pd.to_timedelta(window_centres * 7, unit="D")

    # Power is drawn in decibels, because the yearly cycle is so much stronger
    # than everything else that a linear scale would show one line only.
    decibels = 10 * np.log10(power)

    figure = go.Figure(go.Heatmap(
        x=times, y=periods, z=decibels,
        colorscale=[[0.0, "#FFFFFF"], [1.0, colour]],
        colorbar=dict(title="Power (dB)"),
        hovertemplate="%{x|%d %b %Y}<br>%{y:.0f} weeks<br>%{z:.1f} dB"
                      "<extra></extra>",
    ))

    # A log scale, so the short periods are not squeezed into one stripe.
    figure.update_yaxes(
        type="log",
        tickvals=[8, 13, 26, 52, 104, 208],
        ticktext=["8", "13", "26", "52", "104", "208"],
        title_text="Period (weeks)",
    )

    figure.update_layout(
        title=f"Spectrogram (window {window_weeks} weeks, "
              f"overlap {overlap_weeks})",
        xaxis_title="Date",
        height=460,
    )

    # The bin closest to one year, so its strength can be followed separately.
    yearly_bin = int(np.argmin(np.abs(periods - WEEKS_PER_YEAR)))

    rows = []
    for window in range(power.shape[1]):
        strongest = int(np.argmax(power[:, window]))
        rows.append({
            "window_centre": times[window],
            "strongest_period_weeks": round(periods[strongest], 1),
            "yearly_power_db": round(
                10 * np.log10(power[yearly_bin, window]), 1
            ),
        })

    summary = pd.DataFrame(rows)

    statistics = {
        "windows": int(power.shape[1]),
        "shortest_period": float(periods.min()),
        "longest_period": float(periods.max()),
    }

    return figure, summary, statistics