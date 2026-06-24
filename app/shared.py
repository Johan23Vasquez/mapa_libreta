import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

f = BASE_DIR / "data" / "001_raw" / "ECMWF_utci_2023_prueba.nc"

utci = xr.open_dataset(f)


def seleccionar_pais(ds, lat1, lat2, lon1, lon2):

    return ds.sel(
        lat=slice(lat1, lat2),
        lon=slice(lon1, lon2)
    )


def convertir_a_celsius(ds):

    ds = ds.copy()

    ds["utci"] = ds["utci"] - 273.15

    ds["utci"].attrs["units"] = "°C"

    return ds
def convertir_a_hora_local(ds, offset_utc):
    ds = ds.copy()
    ds = ds.assign_coords(time=ds.time + pd.Timedelta(hours=offset_utc))
    return ds

mexico = seleccionar_pais(
    utci,
    33,
    14,
    -118,
    -86
)

mexico = convertir_a_celsius(mexico)
mexico = convertir_a_hora_local(mexico, -6)



def obtener_utci(ds, fecha, hora):

    fecha_hora = f"{fecha}T{hora:02d}:00:00"

    return ds.sel(
        time=fecha_hora,
        method="nearest"
    )["utci"].values