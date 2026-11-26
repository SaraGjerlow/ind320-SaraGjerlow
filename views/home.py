"""Home: key figures for the chosen area, and the map that chooses it."""

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.data import load_all_reservoirs, load_daily_weather, load_geojson
from modules.theme import ACCENT, INK, NAV_COLOURS, SEQUENTIAL, tint

st.title("Norwegian hydropower")

st.write(
    "Most of Norway's electricity comes from water stored in reservoirs. This "
    "app follows how full they are, the weather over the same areas, the power "
    "traded across the borders, and a forecast of the weeks ahead."
)

area = st.session_state["area"]
area_type = st.session_state["area_type"]

reservoirs = load_all_reservoirs()

# --- Key figures ---------------------------------------------------------

area_rows = reservoirs[reservoirs["area"] == area].sort_values("Date")
# Two weeks are needed to show a change from last week.
if len(area_rows) < 2:
    st.info(f"NVE has no measurements for {area} yet.")
    st.stop()
latest = area_rows.iloc[-1]
previous = area_rows.iloc[-2]

st.subheader(f"Latest measurement for {area}, week of "
             f"{latest['Date']:%d %B %Y}")

fill, stored, capacity = st.columns(3)

change = (latest["Fill level (fraction)"] - previous["Fill level (fraction)"]) * 100
fill.metric(
    "Fill level",
    f"{latest['Fill level (fraction)'] * 100:.1f} %",
    delta=f"{change:+.1f} points from last week",
)
stored.metric("Stored energy", f"{latest['Stored energy (TWh)']:.2f} TWh")
capacity.metric("Capacity", f"{latest['Capacity (TWh)']:.2f} TWh")

# --- Map -----------------------------------------------------------------

st.subheader("Map")

st.write(
    "Click an area to select it. The choice follows you to every other page, "
    "and the sidebar always shows which one is active."
)

# Fill level comes from NVE and exists for every area. The weather values are
# only there for the areas the notebook has downloaded weather for.
COLOUR_CHOICES = {
    "Fill level (%)": ("reservoir", "Fill level (fraction)"),
    "Temperature (degrees C)": ("weather", "temperature_2m_mean"),
    "Precipitation (mm)": ("weather", "precipitation_sum"),
    "Snowfall (cm)": ("weather", "snowfall_sum"),
}

left, right = st.columns([1, 2])

with left:
    colour_name = st.selectbox("Colour the areas by", list(COLOUR_CHOICES))

with right:
    weeks = reservoirs["Date"].drop_duplicates().sort_values()
    week = st.slider(
        "Week",
        min_value=weeks.min().to_pydatetime(),
        max_value=weeks.max().to_pydatetime(),
        value=weeks.max().to_pydatetime(),
        step=pd.Timedelta(weeks=1).to_pytimedelta(),
        format="YYYY-MM-DD",
    )

# The forecast page starts its training window here, so the two agree.
st.session_state["week"] = pd.Timestamp(week)

source, column = COLOUR_CHOICES[colour_name]


def reservoir_values(area_type, week_end):
    """Fill level of every area of one type, in the week ending on week_end."""
    chosen = reservoirs[
        (reservoirs["Area type"] == area_type)
        & (reservoirs["Date"] == week_end)
    ]
    return pd.DataFrame({
        "area": chosen["area"].to_numpy(),
        "value": chosen["Fill level (fraction)"].to_numpy() * 100,
    })


def weather_values(area_type, numbers, column, week_end):
    """One weather value per area, over the seven days ending on week_end.

    Also returns the last day any area has weather for, so an empty result can
    say whether the weather is missing or only ends earlier than the week.
    """
    rows = []
    last_day = None

    for number in numbers:
        daily = load_daily_weather(area_type, number)
        if len(daily) == 0:
            continue

        # The newest day across the areas, used by the message below.
        newest = daily["time"].max()
        if last_day is None or newest > last_day:
            last_day = newest

        window = daily[
            (daily["time"] > week_end - pd.Timedelta(days=7))
            & (daily["time"] <= week_end)
        ]
        if len(window) == 0:
            continue

        # Temperature is an average over the week, the other two are totals.
        if column == "temperature_2m_mean":
            value = window[column].mean()
        else:
            value = window[column].sum()

        rows.append({"area": f"{area_type} {number}", "value": value})

    return pd.DataFrame(rows), last_day


borders = load_geojson(area_type)
numbers = [feature["properties"]["area_number"] for feature in borders["features"]]

# Only the weather branch reports a last day, so this starts empty.
last_day = None

if source == "reservoir":
    values = reservoir_values(area_type, pd.Timestamp(week))
else:
    values, last_day = weather_values(area_type, numbers, column,
                                      pd.Timestamp(week))

if len(values) == 0 and last_day is None:
    st.info(
        f"No weather stored for the {area_type} areas yet. Run the part 4 "
        f"notebook for these areas, or colour by fill level."
    )
elif len(values) == 0:
    st.info(
        f"The weather for the {area_type} areas ends on "
        f"{last_day:%d %B %Y}, and ERA5 always lags a few days behind NVE. "
        f"Drag the week back to {last_day:%d %B %Y} or earlier, or colour by "
        f"fill level."
    )
else:
    figure = px.choropleth_map(
        values,
        geojson=borders,
        locations="area",
        featureidkey="properties.area",
        color="value",
        color_continuous_scale=SEQUENTIAL,
        map_style="carto-positron",
        center={"lat": 65, "lon": 15},
        zoom=3.1,
        opacity=0.55,
        height=620,
        labels={"value": colour_name},
    )

    # The selected area gets a thick contrasting outline, the rest a thin one.
    widths = []
    colours = []
    for name in values["area"]:
        widths.append(3.5 if name == area else 0.8)
        colours.append(ACCENT if name == area else INK)

    figure.update_traces(marker_line_width=widths, marker_line_color=colours)
    figure.update_layout(margin=dict(l=0, r=0, t=0, b=0))

    # The key holds the area, so the map starts fresh whenever the area changes.
    event = st.plotly_chart(
        figure,
        width="stretch",
        on_select="rerun",
        key=f"area_map {area}",
    )

    # A click gives back which row of the table was hit, so the area name is
    # looked up there. Nothing happens if the same area is clicked again.
    points = []
    if event is not None and event.selection is not None:
        points = event.selection["points"]

    if len(points) > 0:
        index = points[0]["point_index"]
        clicked = values["area"].iloc[index]

        if clicked != area:
            # app.py picks this up before the sidebar is drawn on the next run.
            st.session_state["clicked_area"] = clicked
            st.rerun()

    if len(values) < len(numbers):
        missing = len(numbers) - len(values)
        st.caption(
            f"{missing} of the {area_type} areas have no weather stored yet, "
            "so they are left uncoloured."
        )

st.caption("Area borders from NVE, converted to GeoJSON in the part 4 notebook.")

# --- Where to go next ----------------------------------------------------

st.subheader("Where to go next")

st.write(
    f"Every page below follows the area selected above, which is **{area}** "
    f"right now."
)

# Weather is only stored for the EL areas, and the hourly weather that the
# anomalies page needs only for EL 3. Said here as well as in the sidebar, so
# the limit is visible before a page turns out to be empty.
if area_type != "EL":
    st.warning(
        f"{area} has no weather stored, so the two Weather pages below will "
        f"be empty for it. The reservoir pages work for every area."
    )
elif area != "EL 3":
    st.info(
        f"{area} has daily weather, so Weather vs reservoirs works. "
        f"Outliers and anomalies needs hourly weather, which is stored "
        f"for EL 3 only. That page will offer to download it for {area}."
    )

# The three menu groups, with the same colours as the sidebar headings. The
# key is what the CSS below uses to find each box again.
GROUPS = [
    {
        "key": "card_reservoirs",
        "title": "Reservoirs",
        "colour": NAV_COLOURS[1],
        "text": "How full the magazines are, their yearly cycle, and a "
                "forecast of the weeks ahead.",
        "pages": [
            ("views/overview.py", "Overview", ":material/table_chart:"),
            ("views/cycles.py", "Cycles", ":material/show_chart:"),
            ("views/forecast.py", "Forecast", ":material/trending_up:"),
        ],
    },
    {
        "key": "card_weather",
        "title": "Weather",
        "colour": NAV_COLOURS[2],
        "text": "Outliers and anomalies in the weather over the area, and "
                "how the weather lines up with the reservoirs.",
        "pages": [
            ("views/weather.py", "Outliers and anomalies",
             ":material/rainy:"),
            ("views/correlation.py", "Weather vs reservoirs",
             ":material/compare_arrows:"),
        ],
    },
    {
        "key": "card_electricity",
        "title": "Electricity",
        "colour": NAV_COLOURS[3],
        "text": "Power traded across the borders, by direction and by month.",
        "pages": [
            ("views/crossborder.py", "Power exchange", ":material/bolt:"),
        ],
    },
]

# A pale wash of the group colour behind each box, and a slightly stronger
# version of the same colour on the border.
rules = ""
for group in GROUPS:
    rules += (
        f'.st-key-{group["key"]} {{'
        f'background: {tint(group["colour"], 0.10)};'
        f'border-color: {tint(group["colour"], 0.35)};'
        f'border-radius: 10px;'
        f'}}'
    )

st.html(f"<style>{rules}</style>")

columns = st.columns(3)

position = 0
for group in GROUPS:
    # height="stretch" makes all three boxes as tall as the tallest one.
    box = columns[position].container(
        border=True, key=group["key"], height="stretch"
    )

    box.markdown(
        f"<h4 style='color:{group['colour']};margin:0'>{group['title']}</h4>",
        unsafe_allow_html=True,
    )
    box.caption(group["text"])

    for path, label, icon in group["pages"]:
        box.page_link(path, label=label, icon=icon)

    position = position + 1