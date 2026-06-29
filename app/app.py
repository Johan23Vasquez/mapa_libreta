from shiny import App, ui, reactive
from shinywidgets import render_widget, output_widget
import xarray as xr
import pandas as pd
from pathlib import Path
import ipyleaflet as L
import numpy as np
from PIL import Image
import io
import base64
import matplotlib.pyplot as plt
import geopandas as gpd
import json


BASEMAPS = {
    "OpenStreetMap": L.basemaps.OpenStreetMap.Mapnik,
    "DarkMatter": L.basemaps.CartoDB.DarkMatter,
    "Positron": L.basemaps.CartoDB.Positron,
    "WorldImagery": L.basemaps.Esri.WorldImagery,
}

BASE_DIR = Path(__file__).resolve().parent.parent


shp = gpd.read_file(BASE_DIR / "data" / "001_raw" / "INEGI" / "00ent.shp")
shp = shp.to_crs(epsg=4326)

geojson_data = json.loads(shp.to_json())


def select_country(ds, lat1 = 33, lat2 = 14, lon1=-118, lon2=-86):
    """choose dimensions to define the investigation area

    Args:
        ds (.nc): the file which have the data 
        lat1 (int, optional): the first latitude point to define the area. Defaults to 33.
        lat2 (int, optional): the second latitude point to define the area. Defaults to 14.
        lon1 (int, optional): the first longitude point to define the area. Defaults to -118.
        lon2 (int, optional): the second longitude point to define the area. Defaults to -86.

    Returns:
        Dataset: Dataset sliced to the specified geographic bounding box. 
    """
    return ds.sel(lat=slice(lat1, lat2), lon=slice(lon1, lon2))


def to_celsius(ds):
    """Convert a temperature variable in the dataset from Kelvin to Celsius

    Args:
        ds (Dataset): the dataset with a variable in Kelvin

    Returns:
        Dataset: Dataset with 'the variable converted to degrees Celsius and updated units attribute.
    """
    ds = ds.copy()
    ds["utci"] = ds["utci"] - 273.15
    ds["utci"].attrs["units"] = "°C"
    return ds


def to_local_time(ds, offset):
    """Shift the dataset time coordinate by a UTC offset to get local time.

    Args:
        ds (xr.Dataset): Dataset with a 'time' coordinate in UTC.
        offset (int): Hours to add to UTC. Negative for west of UTC
                      (e.g., -6 for Mexico City CST).

    Returns:
        xr.Dataset: Same dataset but with the time coordinate shifted.
    """
    return ds.assign_coords(time=ds.time + pd.Timedelta(hours=offset))


def get_utci(ds, date, hour):
    """Extract a 2D grid of UTCI values for a specific date and hour.

    Args:
        ds (xr.Dataset): Dataset with a 'utci' variable and 'time' dimension.
        date (str): Date in 'YYYY-MM-DD' format.
        hour (int): Hour of the day (0-23).

    Returns:
        np.ndarray: 2D array of UTCI values (lat x lon) for that timestep.
    """
    return ds.sel(time=f"{date}T{hour:02d}:00:00", method="nearest")["utci"].values


def load_year(year):
    """Load and preprocess the annual UTCI file for a given year.

    Applies the full pipeline: open file -> clip to Mexico -> 
    convert to Celsius -> shift to local time (UTC-6).

    Args:
        year (str or int): Year of the file to load (e.g., 2023).

    Returns:
        xr.Dataset: Preprocessed dataset ready for visualization.
    """
    f = BASE_DIR / "data" / "001_raw" / f"ECMWF_utci_{year}_mexico_anual.nc"

    ds = xr.open_dataset(f)
    ds = select_country(ds, 33, 14, -118, -86)
    ds = to_celsius(ds)
    ds = to_local_time(ds, -6)

    return ds


def to_png(data, mode="smooth"):
    """Convert a 2D UTCI array to a base64 PNG image for the map overlay.

    Normalizes values between 0 and 46 °C and applies the RdYlGn_r colormap
    (red = hot, green = comfortable). Returns a data URI string that
    ipyleaflet's ImageOverlay can use directly.

    Args:
        data (np.ndarray): 2D array of UTCI values in Celsius.
        mode (str): 'smooth' for native resolution, 'pixel' to upscale 8x
                    so individual grid cells are visible. Defaults to 'smooth'.

    Returns:
        str: Base64-encoded PNG as a data URI ('data:image/png;base64,...').
    """
    vmin, vmax = 0, 46

    norm = (data - vmin) / (vmax - vmin)
    norm = np.clip(norm, 0, 1)
    norm = np.nan_to_num(norm)

    cmap = plt.get_cmap("RdYlGn_r")
    colored = cmap(norm)

    rgb = (colored[:, :, :3] * 255).astype(np.uint8)
    img = Image.fromarray(rgb)

    if mode == "pixel":
        img = img.resize((img.width * 8, img.height * 8), Image.Resampling.NEAREST)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return "data:image/png;base64," + base64.b64encode(buffer.read()).decode()





app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_date("date", "Select date", value="2023-01-01"),
        ui.input_select("hour", "Hour (UTC)", {str(h): f"{h:02d}:00" for h in range(24)}, selected="10"),
        ui.input_select("basemap", "Basemap", list(BASEMAPS.keys())),
        ui.input_select("render_mode", "Visual mode", {"smooth": "Smooth", "pixel": "Pixel"}),
        ui.input_checkbox("show_shapefile", "Show INEGI borders", False),
        open="desktop"
    ),
    output_widget("map", height="600px")
)

def server(input, output, session):

    @reactive.calc
    def dataset():
        date = str(input.date())
        year = date[:4]

        return load_year(year)

    @render_widget
    def map():
        m = L.Map(center=(23.5, -102.0), zoom=4, layout={"height": "600px"})
        return m

    @reactive.effect
    def update_layers():
        widget = map.widget
        if widget is None:
            return

        widget.layers = ()

        basemap = input.basemap()
        mode = input.render_mode()
        date = str(input.date())
        hour = int(input.hour())

        ds = dataset()

        data = get_utci(ds, date, hour)

        img_url = to_png(data, mode)

        bounds = [
            [float(ds.lat.min()), float(ds.lon.min())],
            [float(ds.lat.max()), float(ds.lon.max())]
]
        widget.add_layer(L.basemap_to_tiles(BASEMAPS[basemap]))
        widget.add_layer(L.ImageOverlay(url=img_url, bounds=bounds, opacity=0.6))

        if input.show_shapefile():
            widget.add_layer(
                L.GeoJSON(
                    data=geojson_data,
                    style={"color": "red", "weight": 2, "fillOpacity": 0}
                )
            )

app = App(app_ui, server)