import logging

from vtk.util.numpy_support import vtk_to_numpy
import pyvista
from dash import Dash, html, dcc, callback, Input, Output, no_update
import dash_vtk
from dash_vtk.utils import to_mesh_state
from webviz_config._plugin_abc import WebvizPluginABC
from webviz_subsurface._utils.perf_timer import PerfTimer

TIMER = PerfTimer()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def time_it(text: str) -> str:
    return print(f"TIME: {text} {TIMER.lap_s():.2f}s")


class MeshApp(WebvizPluginABC):
    """Testing vtk performance"""

    def __init__(
        self,
        vtu_file,
    ) -> None:
        super().__init__(self)
        time_it("Initializing app")

        self.grid = pyvista.read(vtu_file)
        time_it("Read unstructured grid")

        @callback(
            Output("vtk-mesh", "state"),
            Output("vtk-view", "triggerResetCamera"),
            Input("click", "n_clicks"),
        )
        def _update(nclicks):
            # Flipping z to trigger a change
            self.grid.flip_z(inplace=True)
            TIMER.lap_s()
            mesh_state = to_mesh_state(self.grid, field_to_keep="scalar")
            time_it("TO MESH STATE")
            return mesh_state, nclicks

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
                            children=[dash_vtk.Mesh(id="vtk-mesh", state={})],
                            property={"edgeVisibility": True},
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
