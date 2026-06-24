from shiny import App, ui
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



BASEMAPS = {
    "OpenStreetMap": L.basemaps.OpenStreetMap.Mapnik,
    "DarkMatter": L.basemaps.CartoDB.DarkMatter,
    "Positron": L.basemaps.CartoDB.Positron,
    "WorldImagery": L.basemaps.Esri.WorldImagery,
}
# =========================================================
# DATA LOAD
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent
f = BASE_DIR / "data" / "001_raw" / "ECMWF_utci_2023_prueba.nc"

utci = xr.open_dataset(f)


# =========================================================
# DATA PROCESSING FUNCTIONS
# =========================================================

def select_country(ds, lat1, lat2, lon1, lon2):
    """
    Recorta el dataset a una región geográfica específica.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset original.
    lat1, lat2 : float
        Límites de latitud.
    lon1, lon2 : float
        Límites de longitud.

    Returns
    -------
    xarray.Dataset
        Subconjunto del dataset.
    """
    return ds.sel(
        lat=slice(lat1, lat2),
        lon=slice(lon1, lon2)
    )


def to_celsius(ds):
    """
    Convierte la variable UTCI de Kelvin a Celsius.

    Parameters
    ----------
    ds : xarray.Dataset

    Returns
    -------
    xarray.Dataset
    """
    ds = ds.copy()
    ds["utci"] = ds["utci"] - 273.15
    ds["utci"].attrs["units"] = "°C"
    return ds


def to_local_time(ds, offset):
    """
    Ajusta la coordenada temporal a hora local.

    Parameters
    ----------
    ds : xarray.Dataset
    offset : int
        Diferencia horaria respecto a UTC.

    Returns
    -------
    xarray.Dataset
    """
    return ds.assign_coords(time=ds.time + pd.Timedelta(hours=offset))


def get_utci(ds, date, hour):
    """
    Extrae el raster UTCI para una fecha y hora específica.

    Parameters
    ----------
    ds : xarray.Dataset
    date : str
        Fecha en formato YYYY-MM-DD
    hour : int
        Hora (0-23)

    Returns
    -------
    numpy.ndarray
        Matriz 2D de UTCI.
    """
    return ds.sel(
        time=f"{date}T{hour:02d}:00:00",
        method="nearest"
    )["utci"].values


# =========================================================
# PREPROCESSING
# =========================================================
mexico = select_country(utci, 33, 14, -118, -86)
mexico = to_celsius(mexico)
mexico = to_local_time(mexico, -6)


# =========================================================
# RASTER → IMAGE (COLORMAP SCIENTIFIC)
# =========================================================
def to_png(data):
    """
    Convierte un raster numérico en una imagen PNG con colormap científico.

    - Normaliza valores
    - Aplica colormap RdYlGn_r
    - Convierte a imagen RGB
    - Codifica como base64 para ipyleaflet

    Parameters
    ----------
    data : numpy.ndarray

    Returns
    -------
    str
        Imagen en formato data URI (base64 PNG)
    """

    norm = (data - np.nanmin(data)) / (np.nanmax(data) - np.nanmin(data))
    norm = np.nan_to_num(norm)

    cmap = plt.get_cmap("RdYlGn_r")
    colored = cmap(norm)

    rgb = (colored[:, :, :3] * 255).astype(np.uint8)

    img = Image.fromarray(rgb)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    b64 = base64.b64encode(buffer.read()).decode()

    return f"data:image/png;base64,{b64}"


# =========================================================
# UI
# =========================================================
app_ui = ui.page_sidebar(

    ui.sidebar(
        ui.h4("Controls"),

        ui.input_date("date", "Select date", value="2023-01-01"),

        ui.input_select(
            "hour",
            "Hour (UTC)",
            {str(h): f"{h:02d}:00" for h in range(24)},
            selected="18"
        ),

        ui.input_select(
            "basemap",
            "Basemap",
            list(BASEMAPS.keys()),
            selected="OpenStreetMap"
        ),

        bg="#f8f8f8",
        open="desktop"
    ),

    output_widget("map")
)

# =========================================================
# SERVER
# =========================================================
def server(input, output, session):

    @render_widget
    def map():

        date = str(input.date())
        hour = int(input.hour())
        basemap_name = input.basemap()

        data = get_utci(mexico, date, hour)

        m = L.Map(
            center=(23.5, -102.0),
            zoom=4
        )

        # basemap dinámico
        m.add_layer(
            L.basemap_to_tiles(BASEMAPS[basemap_name])
        )

        # raster overlay
        img_url = to_png(data)

        bounds = [
            [float(mexico.lat.min()), float(mexico.lon.min())],
            [float(mexico.lat.max()), float(mexico.lon.max())]
        ]

        overlay = L.ImageOverlay(
            url=img_url,
            bounds=bounds,
            opacity=0.6
        )

        m.add_layer(overlay)

        return m
# =========================================================
# APP
# =========================================================
app = App(app_ui, server)