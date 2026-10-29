"""The four analyses from the part 3 notebook, written as reusable functions.

The notebook versions print their numbers. These return them instead, so the
app can show them with st.metric and the page decides how they look.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

# The reservoir statistics are weekly, so one full year is 52 points.
WEEKS_PER_YEAR = 52


def precipitation_outliers(weather, cutoff=25, n_sigma=3.0,
                           column="precipitation"):
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

    figure, axes = plt.subplots(figsize=(11, 4.5))
    axes.plot(series.index, values, linewidth=0.6, color="steelblue",
              label="Average precipitation")
    axes.plot(series.index, upper, linewidth=1.0, color="grey",
              label=f"SPC limits ({n_sigma} sigma)")
    axes.plot(series.index, lower, linewidth=1.0, color="grey")
    axes.scatter(series.index[is_outlier], values[is_outlier],
                 s=14, color="crimson", zorder=3, label="Outliers")

    axes.set_title(f"Precipitation with SPC limits "
                   f"(cutoff {cutoff}, {n_sigma} sigma)")
    axes.set_xlabel("Time")
    axes.set_ylabel("Precipitation (mm)")
    axes.grid(alpha=0.3)
    axes.legend(fontsize=8)
    figure.autofmt_xdate()
    figure.tight_layout()

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
                          column="temperature_2m"):
    """Plot temperature and mark anomalies found by Local Outlier Factor.

    proportion is the share of points that should be flagged, so 0.01 marks
    the one percent that look most out of place.

    n_neighbors is how many nearby points each point is compared against. A
    small number reacts to short events, a large one only to longer ones.

    Returns the figure, a table of the anomalies and a dictionary of numbers.
    """
    series = weather.set_index("time")[column]
    values = series.to_numpy()

    # Time has to be a number for the distance calculation. Both features are
    # scaled, or the hour count would completely dominate the temperature.
    hours = np.arange(len(values), dtype=float)
    features = np.column_stack([
        (hours - hours.mean()) / hours.std(),
        (values - values.mean()) / values.std(),
    ])

    detector = LocalOutlierFactor(
        n_neighbors=n_neighbors, contamination=proportion
    )
    labels = detector.fit_predict(features)

    # fit_predict marks anomalies with -1. The score says how isolated each
    # point is, where a higher number is more unusual.
    is_anomaly = labels == -1
    score = -detector.negative_outlier_factor_

    figure, axes = plt.subplots(figsize=(11, 4.5))
    axes.plot(series.index, values, linewidth=0.6, color="steelblue",
              label="Average temperature")
    axes.scatter(series.index[is_anomaly], values[is_anomaly],
                 s=14, color="crimson", zorder=3, label="Anomalies")

    axes.set_title(f"Temperature with LOF anomalies "
                   f"({100 * proportion:.1f} percent flagged)")
    axes.set_xlabel("Time")
    axes.set_ylabel("Temperature (degrees C)")
    axes.grid(alpha=0.3)
    axes.legend(fontsize=8)
    figure.autofmt_xdate()
    figure.tight_layout()

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

    figure, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True)

    axes[0].plot(series.index, series.to_numpy(), linewidth=0.8,
                 color="steelblue")
    axes[0].set_ylabel("Observed")

    axes[1].plot(series.index, result.trend, linewidth=1.0, color="darkorange")
    axes[1].set_ylabel("Trend")

    axes[2].plot(series.index, result.seasonal, linewidth=0.8, color="seagreen")
    axes[2].set_ylabel("Seasonal")

    axes[3].plot(series.index, result.resid, linewidth=0.6, color="grey")
    axes[3].set_ylabel("Remainder")
    axes[3].set_xlabel("Date")

    for one_axis in axes:
        one_axis.grid(alpha=0.3)

    figure.autofmt_xdate()
    figure.tight_layout()

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


def reservoir_spectrogram(series, window_weeks=208, overlap_weeks=156):
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

    figure, axes = plt.subplots(figsize=(11, 4.5))

    # Power is drawn in decibels, because the yearly cycle is so much stronger
    # than everything else that a linear scale would show one line only.
    mesh = axes.pcolormesh(times, periods, 10 * np.log10(power),
                           shading="auto", cmap="magma")

    axes.set_yscale("log")
    axes.set_yticks([8, 13, 26, 52, 104, 208])
    axes.set_yticklabels(["8", "13", "26", "52", "104", "208"])
    axes.set_ylabel("Period (weeks)")
    axes.set_xlabel("Date")
    axes.set_title(f"Spectrogram (window {window_weeks} weeks, "
                   f"overlap {overlap_weeks})")
    figure.colorbar(mesh, ax=axes, label="Power (dB)")
    figure.autofmt_xdate()
    figure.tight_layout()

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