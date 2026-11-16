"""One place for the app's colours, used by the page and by every plot."""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# The same values as in .streamlit/config.toml.
PRIMARY = "#C9709C"
ACCENT = "#3F72AF"
INK = "#2E2A3B"
MUTED = "#7A7490"
GRID = "#EDE6EC"
PAPER = "#FDFBFC"

# Pastel pink, blue, turquoise and purple, used when a plot draws several series.
PALETTE = ["#C45B8B", "#3F72AF", "#3E9AA3", "#8663B0", "#7FAFD6", "#E2A3C0"]

# Pale to deep pink, used for colouring the map and the spectrogram.
SEQUENTIAL = [
    "#FBEFF5", "#F3D4E3", "#E6AFCB", "#D383AE", "#BC5B8E", "#9B3E72",
]

# The headings above the controls in the sidebar, such as Area and Period.
SIDEBAR_HEADING = "#8A8FA8"
# The sidebar keeps the pink, now that the general one is neutral.
SIDEBAR_BACKGROUND = "#F8EFF4"

# One colour per section in the sidebar menu, in the order they are listed.
NAV_COLOURS = ["#C45B8B", "#3F72AF", "#3E9AA3", "#8663B0", "#8A8FA8"]

# One deep and one pale colour per page, looked up by the page title.
PAGE_COLOURS = {
    "Home": ("#C45B8B", "#FAE7F0"),
    "Overview": ("#3F72AF", "#E6EEF9"),
    "Cycles": ("#5A96C4", "#E9F2FA"),
    "Forecast": ("#6FA6CE", "#EDF4FB"),
    "Outliers and anomalies": ("#3E9AA3", "#E1F1F2"),
    "Weather vs reservoirs": ("#5FB0B8", "#E7F4F5"),
    "Power exchange": ("#8663B0", "#F0E9F8"),
    "About": ("#7E829E", "#EFF0F6"),
}

TEMPLATE_NAME = "ind320"

def tint(colour, alpha):
    """The same colour as a see-through rgba string, used for hover states."""
    red = int(colour[1:3], 16)
    green = int(colour[3:5], 16)
    blue = int(colour[5:7], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"

def page_colours(title):
    """The deep and the pale colour of one page, found by its title."""
    return PAGE_COLOURS.get(title, (PRIMARY, "#FAE7F0"))


def use_theme():
    """Register the Plotly template and colour the sidebar."""
    pio.templates[TEMPLATE_NAME] = go.layout.Template(
        layout=dict(
            colorway=PALETTE,
            paper_bgcolor=PAPER,
            plot_bgcolor="#FFFFFF",
            font=dict(color=INK, size=13),
            title=dict(font=dict(size=17, color=INK), x=0, xanchor="left"),
            xaxis=dict(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID),
            yaxis=dict(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=55, r=20, t=55, b=45),
            colorscale=dict(sequential=SEQUENTIAL),
        )
    )

    # Built on plotly_white, so anything not set above still looks sensible.
    pio.templates.default = f"plotly_white+{TEMPLATE_NAME}"

    # Every section in the menu is one div, so they are coloured by position.
    rules = ""
    position = 1
    for colour in NAV_COLOURS:
        rules += (
            f'[data-testid="stSidebarNavItems"] > div:nth-child({position}) '
            f'[data-testid="stNavSectionHeader"] p '
            f"{{ color: {colour}; font-weight: 600; }}"
        )
        position += 1

    # The headings below the menu, which belong to no single page.
    side = '[data-testid="stSidebar"]'
    rules += (
        f"{side} {{ background-color: {SIDEBAR_BACKGROUND}; }}"
        f"{side} h1, {side} h2, {side} h3 "
        f"{{ color: {SIDEBAR_HEADING}; }}"
    )

    st.html(f"<style>{rules}</style>")


def page_style(title):
    """Give the open page its own colour on headings, controls and plots."""
    deep, pale = page_colours(title)

    # Only the main area, so the sidebar looks the same on every page.
    main = '[data-testid="stMain"]'

    rules = (
        f"{main} h1, {main} h2, {main} h3 {{ color: {deep}; }}"
        f"{main} .stButton > button {{ background-color: {pale}; "
        f"color: {deep}; border: 1px solid {deep}; }}"
        f"{main} .stButton > button:hover {{ background-color: {deep}; "
        f"color: #FFFFFF; border-color: {deep}; }}"
        f'{main} [data-testid="stMetricValue"] {{ color: {deep}; }}'
        f'{main} [data-testid="stSlider"] div[style*="position: relative"] '
        f"> div:first-child "
        f"{{ background-image: none; background-color: {pale}; }}"
        f'{main} [data-testid="stSlider"] div[style*="translate"] '
        f"{{ background-color: {deep}; }}"
        f'{main} [data-testid="stSlider"] div[data-orientation="horizontal"] p '
        f"{{ color: {deep}; }}"
        f'{main} [data-testid="stRadioOption"]:has(input:checked) '
        f"> div > div:not([data-testid]) "
        f"{{ background-color: {deep}; border-color: {deep}; }}"
        f'{main} label:has(input[type="checkbox"]:checked) '
        f"> div:not([data-testid]) "
        f"{{ background-color: {deep}; border-color: {deep}; }}"
        f"{main} div:focus-within {{ border-color: {deep}; }}"
        f'{main} [data-testid="stSelectbox"] div[role="group"] '
        f"{{ background-color: {pale}; }}"
        f'{main} button[data-variant="pills"][data-selected="true"] '
        f"{{ background-color: {pale}; color: {deep}; "
        f"border-color: {deep}; }}"
        f'{main} [data-testid="stTab"][data-selected="true"], '
        f'{main} [data-testid="stTab"]:hover '
        f"{{ color: {deep}; }}"
        f'{main} [data-testid="stExpander"] details '
        f"{{ background-color: {pale}; }}"
        f'{main} [data-testid="stExpander"] summary:hover '
        f"{{ background-color: {tint(deep, 0.15)}; }}"
        f"{main} .react-aria-SelectionIndicator "
        f"{{ background-color: {deep} !important; }}"
    )

    st.html(f"<style>{rules}</style>")

    # The page colour also leads in every plot drawn on that page.
    colourway = [deep]
    for colour in PALETTE:
        if colour != deep:
            colourway.append(colour)

    pio.templates[TEMPLATE_NAME].layout.colorway = colourway