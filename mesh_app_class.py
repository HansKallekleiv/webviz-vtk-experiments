import logging

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


class MeshApp(WebvizPluginABC):
    """Testing vtk performance"""

    def __init__(
        self,
        vtu_file,
    ) -> None:
        super().__init__(self)
        time_it("Initializing app")

        self.grid = pyvista.read(vtu_file)
        time_it(f"Read unstructured grid, type={type(self.grid)}")

        TIMER.lap_s()
        self.grid = self.grid.cast_to_explicit_structured_grid()
        self.grid.ComputeFacesConnectivityFlagsArray()
        time_it("Cast to ExplicitStructuredGrid")


        @callback(
            Output("vtk-mesh", "state"),
            Output("vtk-view", "triggerResetCamera"),
            Input("click", "n_clicks"),
        )
        def _update(nclicks):
            # Flipping z to trigger a change
            self.grid.flip_z(inplace=True)

            TIMER.lap_s()

            if self.grid.IsA("vtkUnstructuredGrid"):
                print("it is a vtkUnstructuredGrid")
                extractSkinFilter = vtkGeometryFilter()
            elif self.grid.IsA("vtkExplicitStructuredGrid"):
                print("it is a vtkExplicitStructuredGrid")
                extractSkinFilter = vtkExplicitStructuredGridSurfaceFilter()
            else:
                print("TROUBLE!!!!!!!!!!!!!!!")

            print("Num grid cells: ", self.grid.GetNumberOfCells())

            extractSkinFilter.SetInputData(self.grid)
            extractSkinFilter.Update()
            polydata = extractSkinFilter.GetOutput()

            time_it("CREATE POLYDATA")

            TIMER.lap_s()
            mesh_state = to_mesh_state(polydata, field_to_keep="scalar")
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
