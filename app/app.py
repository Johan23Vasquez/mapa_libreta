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
f = BASE_DIR / "data" / "001_raw" / "ECMWF_utci_2023_mexico_anual.nc"

utci = xr.open_dataset(f)

shp = gpd.read_file(BASE_DIR / "data" / "001_raw" / "INEGI" / "00ent.shp")
shp = shp.to_crs(epsg=4326)

geojson_data = json.loads(shp.to_json())


def select_country(ds, lat1, lat2, lon1, lon2):
    return ds.sel(lat=slice(lat1, lat2), lon=slice(lon1, lon2))


def to_celsius(ds):
    ds = ds.copy()
    ds["utci"] = ds["utci"] - 273.15
    ds["utci"].attrs["units"] = "°C"
    return ds


def to_local_time(ds, offset):
    return ds.assign_coords(time=ds.time + pd.Timedelta(hours=offset))


def get_utci(ds, date, hour):
    return ds.sel(time=f"{date}T{hour:02d}:00:00", method="nearest")["utci"].values


mexico = select_country(utci, 33, 14, -118, -86)
mexico = to_celsius(mexico)
mexico = to_local_time(mexico, -6)


def to_png(data, mode="smooth"):
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
        ui.input_select("hour", "Hour (UTC)", {str(h): f"{h:02d}:00" for h in range(24)}, selected="18"),
        ui.input_select("basemap", "Basemap", list(BASEMAPS.keys())),
        ui.input_select("render_mode", "Visual mode", {"smooth": "Smooth", "pixel": "Pixel"}),
        ui.input_checkbox("show_shapefile", "Show INEGI borders", False),
        open="desktop"
    ),
    output_widget("map", height="600px")
)

def server(input, output, session):

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

        data = get_utci(mexico, date, hour)

        img_url = to_png(data, mode)

        bounds = [
            [float(mexico.lat.min()), float(mexico.lon.min())],
            [float(mexico.lat.max()), float(mexico.lon.max())]
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