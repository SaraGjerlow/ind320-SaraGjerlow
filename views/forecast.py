"""Forecast page: the River model from the notebook, and the currency rates."""

import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from river import linear_model, optim, preprocessing, time_series

from modules.data import load_currency, load_weekly_frame
from modules.theme import PALETTE, tint

st.title("Forecast")

area = st.session_state["area"]

# Which columns each data source contributes as exogenous variables.
SOURCES = {
    "weather": ["temperature_2m_mean", "precipitation_sum", "snowfall_sum"],
    "currency": ["EUR", "USD"],
    "lagged snow": ["snow_lagged"],
}

# The band width, and the quantile each edge is trained on.
BANDS = {"Off": None, "80 %": 0.10, "90 %": 0.05, "95 %": 0.025}

forecast_tab, currency_tab = st.tabs(["Reservoir filling", "Currency"])


def train_model(train, exogenous, p, d, q, m, sp, sd, sq, alpha=None):
    """Fit one SNARIMAX on the training weeks.

    With an alpha the model is fitted with quantile loss instead, which is
    what gives one edge of the confidence band rather than the middle line.
    """
    if alpha is None:
        model = time_series.SNARIMAX(p=p, d=d, q=q, m=m, sp=sp, sd=sd, sq=sq)
    else:
        regressor = (
            preprocessing.StandardScaler()
            | linear_model.LinearRegression(
                optimizer=optim.SGD(0.01),
                loss=optim.losses.Quantile(alpha=alpha),
            )
        )
        model = time_series.SNARIMAX(p=p, d=d, q=q, m=m, sp=sp, sd=sd, sq=sq,
                                     regressor=regressor)

    # River learns one observation at a time, which is what makes it online.
    for stamp, row in train.iterrows():
        x = None
        if exogenous:
            x = {}
            for column in exogenous:
                x[column] = float(row[column])

        model.learn_one(y=float(row["fill_level"]), x=x)

    return model


@st.cache_data(ttl=3600, show_spinner="Training the model")
def run_forecast(area, horizon, history_weeks, sources, p, d, q, m, sp, sd, sq,
                 last_week, band_alpha):
    """Train River's SNARIMAX on one area and predict the weeks held back.

    The same model as in the part 4 notebook, with the figure left out so the
    result can be cached. last_week decides where the forecast ends.
    """
    weekly = load_weekly_frame(area)
    weekly = weekly[weekly.index <= last_week]

    exogenous = []
    for source in sources:
        exogenous = exogenous + SOURCES[source]

    # Rows without every needed column are dropped, then the tail is kept.
    used = weekly[["fill_level"] + exogenous].dropna()
    used = used.tail(history_weeks + horizon)

    # Too few weeks left to both train and hold something back.
    if len(used) < horizon + 60:
        return None, None, None

    train = used.iloc[:-horizon]
    test = used.iloc[-horizon:]

    started = time.time()

    model = train_model(train, exogenous, p, d, q, m, sp, sd, sq)

    # The forecast needs the exogenous values for the weeks ahead as well.
    xs = None
    if exogenous:
        xs = []
        for stamp, row in test.iterrows():
            values = {}
            for column in exogenous:
                values[column] = float(row[column])
            xs.append(values)

    predicted = model.forecast(horizon=horizon, xs=xs)

    # A fill level cannot be below zero or above a hundred percent.
    predicted = np.clip(np.array(predicted, dtype=float), 0, 100)
    actual = test["fill_level"].to_numpy()

    result = pd.DataFrame(
        {"actual": actual.round(1), "predicted": predicted.round(1)},
        index=test.index,
    )
    result["error"] = (result["predicted"] - result["actual"]).round(1)

    # One extra model per edge of the band, each with its own quantile.
    if band_alpha is not None:
        for name, alpha in [("lower", band_alpha), ("upper", 1 - band_alpha)]:
            edge = train_model(train, exogenous, p, d, q, m, sp, sd, sq, alpha)
            values = edge.forecast(horizon=horizon, xs=xs)
            values = np.clip(np.array(values, dtype=float), 0, 100)
            result[name] = values.round(1)

    seconds = time.time() - started

    summary = {
        "training weeks": len(train),
        "exogenous variables": len(exogenous),
        "seconds to fit": round(seconds, 2),
        "MAE": round(float(np.mean(np.abs(predicted - actual))), 2),
    }

    # Two years of history behind the forecast, so the season is visible.
    recent = used["fill_level"].iloc[-104:]

    return result, summary, recent


# --- Forecast -------------------------------------------------------------

with forecast_tab:
    st.write(
        f"River's SNARIMAX is trained one week at a time on the filling of "
        f"**{area}**, and the last weeks are held back, so the error is "
        f"measured on weeks the model never saw."
    )

    # The week chosen on the Home page decides where the forecast ends.
    last_week = st.session_state.get("week")
    if last_week is None:
        last_week = pd.Timestamp.today()

    st.caption(
        f"The forecast ends on {last_week:%d %B %Y}, the week chosen with the "
        f"slider on the Home page."
    )

    left, middle, right, far = st.columns(4)

    with left:
        horizon = st.slider(
            "Weeks to forecast", min_value=4, max_value=52, value=12, step=1,
            help="How many weeks are held back and predicted.",
        )

    with middle:
        history_weeks = st.slider(
            "Weeks of history", min_value=104, max_value=1600, value=520,
            step=52,
            help="How much of the past the model is trained on. 520 weeks is "
            "ten years.",
        )

    with right:
        sources = st.multiselect(
            "Extra variables", options=list(SOURCES), default=[],
            help="Columns fed to the model besides the filling itself.",
        )

    with far:
        band_name = st.select_slider(
            "Confidence band", options=list(BANDS), value="90 %",
            help="Two extra models are trained with quantile loss, one for "
            "each edge of the band.",
        )

    with st.expander("Model parameters"):
        st.write(
            "p, d and q are the autoregressive, differencing and moving "
            "average orders. m is the season length in weeks, and sp, sd and "
            "sq are the same three orders for the seasonal part."
        )

        one, two, three, four = st.columns(4)
        p = one.number_input("p", min_value=0, max_value=5, value=2)
        d = two.number_input("d", min_value=0, max_value=2, value=1)
        q = three.number_input("q", min_value=0, max_value=5, value=1)
        m = four.number_input("m", min_value=1, max_value=52, value=52)

        five, six, seven = st.columns(3)
        sp = five.number_input("sp", min_value=0, max_value=3, value=1)
        sd = six.number_input("sd", min_value=0, max_value=2, value=1)
        sq = seven.number_input("sq", min_value=0, max_value=3, value=0)

    result, summary, recent = run_forecast(
        area, horizon, history_weeks, tuple(sources),
        int(p), int(d), int(q), int(m), int(sp), int(sd), int(sq),
        pd.Timestamp(last_week),
        BANDS[band_name],
    )

    if result is None:
        st.warning(
            "Not enough weeks with every chosen variable to both train and "
            "forecast. Remove an extra variable or shorten the horizon."
        )
    else:
        st.subheader(f"{horizon} weeks ahead for {area}")

        figure = go.Figure()

        # The band is drawn first, so it sits behind the two lines.
        if "lower" in result.columns:
            figure.add_trace(go.Scatter(
                x=result.index, y=result["upper"], name="Upper",
                mode="lines", line=dict(width=0),
                showlegend=False, hoverinfo="skip",
            ))
            figure.add_trace(go.Scatter(
                x=result.index, y=result["lower"], name=f"{band_name} band",
                mode="lines", line=dict(width=0),
                fill="tonexty", fillcolor=tint(PALETTE[0], 0.18),
                hoverinfo="skip",
            ))

        figure.add_trace(go.Scatter(
            x=recent.index, y=recent.to_numpy(), name="Observed",
            line=dict(color=PALETTE[1], width=1.5),
        ))

        # The frames below animate whichever trace the forecast ends up being.
        forecast_index = len(figure.data)

        figure.add_trace(go.Scatter(
            x=result.index[:1], y=result["predicted"].to_numpy()[:1],
            name="Forecast",
            line=dict(color=PALETTE[0], width=2.5, dash="dash"),
        ))

        frames = []
        slider_steps = []
        step = 1
        while step <= len(result):
            frames.append(go.Frame(
                name=str(step),
                data=[go.Scatter(
                    x=result.index[:step],
                    y=result["predicted"].to_numpy()[:step],
                )],
                traces=[forecast_index],
            ))

            slider_steps.append(dict(
                label=f"{result.index[step - 1]:%d %b}",
                method="animate",
                args=[[str(step)], dict(mode="immediate",
                                        frame=dict(duration=0, redraw=True))],
            ))
            step += 1

        figure.frames = frames

        # The axes are locked, or the animation rescales them to the forecast
        # alone and the observed history disappears.
        low = float(recent.min())
        high = float(recent.max())
        for column in ["predicted", "lower", "upper"]:
            if column in result.columns:
                low = min(low, float(result[column].min()))
                high = max(high, float(result[column].max()))

        padding = 0.05 * (high - low)

        figure.update_xaxes(range=[recent.index[0], result.index[-1]])
        figure.update_yaxes(range=[low - padding, high + padding])

        figure.update_layout(
            xaxis_title="Date",
            yaxis_title="Fill level (%)",
            hovermode="x unified",
            height=500,
            margin=dict(l=70, r=20, t=150, b=50),
            updatemenus=[dict(
                type="buttons",
                direction="left",
                x=0,
                y=1.34,
                xanchor="left",
                showactive=False,
                buttons=[
                    dict(label="Play", method="animate",
                         args=[None, dict(frame=dict(duration=250,
                                                     redraw=True),
                                          fromcurrent=True)]),
                    dict(label="Pause", method="animate",
                         args=[[None], dict(mode="immediate",
                                            frame=dict(duration=0,
                                                       redraw=True))]),
                ],
            )],
            sliders=[dict(
                active=0,
                x=0.18,
                y=1.34,
                len=0.82,
                currentvalue=dict(prefix="Week ", font=dict(size=12)),
                steps=slider_steps,
            )],
        )

        st.plotly_chart(figure, width="stretch")

        one, two, three, four = st.columns(4)
        one.metric("MAE", summary["MAE"])
        two.metric("Training weeks", summary["training weeks"])
        three.metric("Extra variables", summary["exogenous variables"])
        four.metric("Seconds to fit", summary["seconds to fit"])

        st.caption(
            "MAE is the mean absolute error in percentage points, measured on "
            "the weeks that were held back. The band comes from two more "
            "models fitted with quantile loss, one per edge."
        )

        with st.expander("Week by week"):
            st.dataframe(result, width="stretch")

# --- Currency -------------------------------------------------------------

with currency_tab:
    st.write(
        "Daily rates for EUR and USD against NOK from Norges Bank. They are "
        "one of the extra variables the model can be given, because the power "
        "price follows the exchange rate and the filling follows the price."
    )

    left, right = st.columns(2)

    with left:
        start_date = st.date_input("From", value=pd.Timestamp("2015-01-01"))

    with right:
        end_date = st.date_input("To", value=pd.Timestamp.today())

    rates = load_currency(str(start_date), str(end_date))

    if len(rates) == 0:
        st.info("No rates in this period.")
    else:
        rate_figure = go.Figure()

        position = 0
        for column in rates.columns:
            rate_figure.add_trace(go.Scatter(
                x=rates.index, y=rates[column], name=f"{column} to NOK",
                line=dict(color=PALETTE[position], width=1.4),
            ))
            position += 1

        rate_figure.update_layout(
            title="Exchange rates against NOK",
            xaxis_title="Date",
            yaxis_title="NOK per unit",
            hovermode="x unified",
            height=430,
        )

        st.plotly_chart(rate_figure, width="stretch")

        one, two = st.columns(2)
        one.metric("Trading days", len(rates))
        two.metric("EUR at the end", f"{rates['EUR'].iloc[-1]:.2f}")

# --- Documentation --------------------------------------------------------

with st.expander("About the model on this page"):
    st.write(
        "SNARIMAX from the River library is a seasonal ARIMA that learns "
        "online, one observation at a time, instead of being fitted to the "
        "whole series at once. That suits a weekly series that keeps growing."
    )
    st.write(
        "The confidence band is the bonus task. River normally fits towards "
        "the squared error, which lands on the average. With quantile loss it "
        "fits towards a percentile instead, so one model draws the lower edge "
        "and one the upper. The band widens further ahead, because the "
        "uncertainty grows."
    )
    st.write(
        "The weekly table behind it is built in modules/data.py and holds the "
        "filling from NVE, the weather from open-meteo averaged over the area, "
        "and the rates from Norges Bank, all on the same Sunday dated weeks."
    )
    st.write(
        "Lagged snow is the snowfall shifted twenty weeks forward. The "
        "Weather vs reservoirs page is what found that lag, and it is the "
        "single variable that improves the forecast the most."
    )