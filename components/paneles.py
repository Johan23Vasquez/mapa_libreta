from shiny import App, ui, render

def panel_prueba():
    return ui.TagList(
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
