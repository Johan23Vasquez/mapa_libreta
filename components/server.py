from matplotlib import pyplot as plt
from shiny import render
from app.shared import obtener_utci, mexico


def server(input, output, session):

    @render.plot
    def mapa_utci():
        # 1. Captura de variables reactivas desde la UI
        fecha = str(input.fecha())
        hora = input.hora()

        # 2. Extracción de la matriz de datos UTCI
        data = obtener_utci(
            mexico,
            fecha,
            hora
        )

        # 3. Construcción del lienzo de Matplotlib
        fig, ax = plt.subplots(figsize=(10, 6))

        # 4. Renderizado del mapa georreferenciado
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

        # 5. Configuración de etiquetas y formato de hora (00:00)
        ax.set_title(
            f"UTCI México - {fecha} {hora:02d}:00 UTC",
            fontsize=14,
            pad=15
        )
        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")

        # 6. Barra de escala de temperatura
        fig.colorbar(
            im,
            ax=ax,
            label="UTCI (°C)"
        )

        fig.tight_layout()

        # 7. Liberación de memoria en el servidor y retorno
        plt.close(fig)
        return fig
