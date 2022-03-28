import logging

import xtgeo
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy
import pyvista
from dash import Dash, html, dcc, callback, Input, Output, no_update
import dash_vtk
from dash_vtk.utils import to_mesh_state
from webviz_config._plugin_abc import WebvizPluginABC
from webviz_subsurface._utils.perf_timer import PerfTimer

from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkFiltersGeometry import vtkExplicitStructuredGridSurfaceFilter

TIMER = PerfTimer()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def time_it(text: str) -> str:
    return print(f"TIME: {text} {TIMER.lap_s():.2f}s")


class SurfaceApp(WebvizPluginABC):
    """Testing vtk performance"""

    def __init__(
        self,
        irap_file,
    ) -> None:
        super().__init__(self)
        time_it("Initializing app")

        surface = xtgeo.surface_from_file(irap_file)
        surface.values = surface.values * -1
        self.value_range = [np.min(surface.values), np.max(surface.values)]
        time_it("Read xtgeo surface")

        # surface.coarsen(4)
        time_it("Reduce resolution")

        xi, yi = surface.get_xy_values(asmasked=False)
        zi = surface.values
        zif = np.ma.filled(zi, fill_value=np.nan)
        time_it("Extract xyz from surface")

        self.sgrid = pyvista.StructuredGrid(xi, yi, zif)
        self.sgrid["Elevation"] = zif.flatten(order="F")
        time_it("Convert to structured grid")

        @callback(
            Output("vtk-mesh", "state"),
            Output("vtk-contours-mesh", "state"),
            Output("vtk-view", "triggerResetCamera"),
            Input("click", "n_clicks"),
        )
        def _update(nclicks):
            # Flipping z to trigger a change
            self.sgrid.flip_z(inplace=True)
            # sgrid = self.sgrid.decimate_boundary(0.75)
            # time_it("Decimate")
            TIMER.lap_s()
            contours = self.sgrid.contour()
            time_it("Make contours")

            mesh_state = to_mesh_state(self.sgrid, field_to_keep="Elevation")

            time_it("TO MESH STATE")
            contours_mesh_state = to_mesh_state(contours, field_to_keep="Elevation")
            time_it("CONTOURS TO MESH STATE")
            return mesh_state, contours_mesh_state, nclicks

        @callback(
            Output("dummy", "data"),
            Input("vtk-mesh", "state"),
        )
        def _update(_):
            time_it("Package delivered")
            return no_update

    @property
    def layout(self) -> html.Div:
        return html.Div(
            style={"height": "90vh"},
            children=[
                dash_vtk.View(
                    id="vtk-view",
                    children=[
                        dash_vtk.GeometryRepresentation(
                            id="vtk-representation",
                            children=[
                                dash_vtk.Mesh(id="vtk-mesh", state={}),
                            ],
                            property={"edgeVisibility": True},
                            colorDataRange=self.value_range,
                        ),
                        dash_vtk.GeometryRepresentation(
                            id="vtk-contours-representation",
                            children=[
                                dash_vtk.Mesh(id="vtk-contours-mesh", state={}),
                            ],
                            property={
                                "color": "black",
                                "width": 5,
                                "opacity": 1,
                            },
                        ),
                    ],
                ),
                html.Button(
                    id="click",
                    style={"fontSize": "10em"},
                    children="click",
                ),
                dcc.Store(id="dummy"),
            ],
        )
