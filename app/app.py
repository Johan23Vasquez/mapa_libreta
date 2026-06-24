from shiny import App, ui, render
import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

#from app.shared import obtener_utci, mexico


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






app_ui = ui.page_fluid(

    ui.h2("Mapa UTCI México"),

    ui.row(

        ui.column(
            6,

            ui.input_date(
                "fecha",
                "Seleccione una fecha",
                value="2023-01-01"
            )
        ),

        ui.column(
            6,

            ui.input_slider(
                "hora",
                "Hora UTC",
                min=0,
                max=23,
                value=18
            )
        )
    ),

    ui.hr(),

    ui.output_plot("mapa_utci")
)


def server(input, output, session):

    @render.plot
    def mapa_utci():

        fecha = str(input.fecha())
        hora = input.hora()

        data = obtener_utci(
            mexico,
            fecha,
            hora
        )

        fig, ax = plt.subplots(
            figsize=(10, 6)
        )

        im = ax.imshow(
            data,
            extent=[
                float(mexico.lon.min()),
                float(mexico.lon.max()),
                float(mexico.lat.min()),
                float(mexico.lat.max())
            ],
            origin="upper",
            cmap="RdYlGn_r",
            vmin=0,
            vmax=46,
        )

        ax.set_title(
            f"UTCI México - {fecha} {hora:02d}:00 UTC"
        )

        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")

        fig.colorbar(
            im,
            ax=ax,
            label="UTCI (°C)"
        )

        return fig


app = App(app_ui, server)

# from matplotlib import pyplot as plt
# from shiny import App, ui, render
# from components.paneles import panel_prueba 
# from app.shared import mexico, obtener_utci
# from components.server import server   





# app_ui = ui.page_fluid(
# panel_prueba()
    
# )




# app = App(app_ui, server)