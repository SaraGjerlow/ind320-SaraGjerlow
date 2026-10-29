# IND320 Project Work, Sara Christine Gjerløw

Course project for IND320 Data to Decision at NMBU, autumn 2026. The project
is a Streamlit app that shows Norwegian hydropower and energy data, with the
data collection and analysis done in Jupyter Notebooks.

Live app: https://ind320-saragjerlow.streamlit.app

## Data sources

- **NVE Magasinstatistikk**, weekly reservoir statistics, read straight from
  NVE's open API. No key needed.
- **ENTSO-E Transparency Platform**, hourly cross-border power flow between
  Norway and its neighbours. Needs a free API token.
- **open-meteo Archive API**, hourly historical weather from the ERA5
  reanalysis model. No key needed, but there is a limit on how much can be
  downloaded per day.
- **NVE shapefiles**, the borders of the electricity price areas and the
  watercourse regions, used to draw random sampling locations.

## Required software

Python 3.12 or newer, and the packages in `requirements.txt`:

```
pip install -r requirements.txt
```

The notebooks need a few packages that the app does not, because the app
reads the finished results from MongoDB instead of recomputing them:

```
pip install geopandas requests-cache pyspark
```

Part 2 also needs a local Cassandra database and Java, which Spark uses. The
app itself does not touch Cassandra.

## Configuration

Create `.streamlit/secrets.toml` in the project root. This file is listed in
`.gitignore` and is never committed.

```toml
[mongo]
uri = "mongodb+srv://USER:PASSWORD@CLUSTER.mongodb.net/?retryWrites=true&w=majority"

[entsoe]
token = "YOUR-ENTSOE-TOKEN"
```

The deployed app does not read this file. Its secrets are pasted into
Settings and then Secrets on Streamlit Community Cloud.

MongoDB Atlas has to allow connections from the app. For local use that means
adding your own address to the IP access list, and for the deployed app it
means allowing 0.0.0.0/0, since Streamlit Cloud has no fixed address.

The shapefiles are downloaded from NVE's map service and unpacked into
`shapefiles/`, one folder per area set. All four files of each shapefile are
needed, not only the `.shp`.

## Running the app

```
streamlit run app.py
```

## Order of execution

The notebooks fill the databases that the app reads from, so they have to be
run before the app shows anything on the pages that depend on them.

1. **`notebooks/part1.ipynb`** reads the weather CSV and makes the first
   plots. Nothing else depends on it.
2. **`notebooks/part2.ipynb`** downloads cross-border flow from ENTSO-E,
   writes it to Cassandra through Spark, reads it back and stores it in the
   MongoDB collection `crossborder_flows`. The Cross-border flow page reads
   that collection.
3. **`notebooks/part3.ipynb`** samples locations inside the NVE areas, stores
   them in the MongoDB collection `area_points`, downloads weather from
   open-meteo for those locations and runs the four analyses.

Part 3 has to be run over more than one day if the full thousand locations per
area are wanted. Open-meteo limits how much data can be downloaded per day,
and the responses are cached on disk, so re-running the download cell on a new
day continues where the previous run stopped instead of starting over.

## Project layout

```
app.py                  Entry point, defines the pages and the sidebar menu
modules/data.py         All data loading, cached per page rerun
views/                  One file per page in the app
notebooks/              One notebook per project part
shapefiles/             NVE area borders, used by part 3
requirements.txt        Packages needed by the app
```