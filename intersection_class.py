import logging
import json
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy
import pyvista
from dash import (
    Dash,
    html,
    dcc,
    callback,
    Input,
    Output,
    no_update,
    State,
    callback_context,
)
import dash_vtk
from dash_vtk.utils import to_mesh_state
from webviz_config._plugin_abc import WebvizPluginABC
from webviz_subsurface._utils.perf_timer import PerfTimer
import webviz_core_components as wcc
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkFiltersGeometry import vtkExplicitStructuredGridSurfaceFilter

TIMER = PerfTimer()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def time_it(text: str) -> str:
    return print(f"TIME: {text} {TIMER.lap_s():.2f}s")


class IntersectionApp(WebvizPluginABC):
    """Testing vtk performance"""

    def __init__(
        self,
        vtu_file,
    ) -> None:
        super().__init__(self)
        time_it("Initializing app")

        # Preparing 3D grid
        self.grid = pyvista.read(vtu_file)
        time_it(f"Read unstructured grid, type={type(self.grid)}")

        TIMER.lap_s()
        self.grid = self.grid.cast_to_explicit_structured_grid()
        self.grid.ComputeFacesConnectivityFlagsArray()
        self.grid.scale([1, 1, 5], inplace=True)
        extractSkinFilter = vtkExplicitStructuredGridSurfaceFilter()

        print("Num grid cells: ", self.grid.GetNumberOfCells())

        extractSkinFilter.SetInputData(self.grid)
        extractSkinFilter.Update()
        polydata = extractSkinFilter.GetOutput()
        TIMER.lap_s()
        self.mesh_state = to_mesh_state(polydata, field_to_keep="scalar")
        time_it("TO MESH STATE")

        # --------------------------
        # Callback to store edited polyline
        @callback(
            Output("stored-polyline", "children"),
            Input("vtk-3d-view", "clickInfo"),
            Input("clear", "n_clicks"),
            State("stored-polyline", "children"),
        )
        def _store_polyline(clickdata, _n_clicks, stored_polyline):
            stored_polyline = json.loads(stored_polyline)
            if "n_clicks" in callback_context.triggered[0]["prop_id"]:
                return json.dumps([])
            if clickdata:
                if (
                    "representationId" in clickdata
                    and clickdata["representationId"] == "vtk-3d-grid-representation"
                ):
                    stored_polyline.append(clickdata["worldPosition"])

                    return json.dumps(stored_polyline, indent=2)
            return no_update

        # --------------------------
        # Callback to slice grid from polyline and update intersection mesh in both views
        @callback(
            Output("vtk-intersection-mesh", "state"),
            Output("vtk-intersection-view", "cameraPosition"),
            Output("vtk-3d-intersection-mesh", "state"),
            Input("stored-polyline", "children"),
        )
        def _store_polyline(stored_polyline):
            stored_polyline = json.loads(stored_polyline)
            if len(stored_polyline) < 2:
                return {}, no_update, {}

            # Had to make a `pyvista.Spline` to be able to slice...
            spline_from_polyline = pyvista.Spline(
                np.array(stored_polyline),
                n_points=None,  # Increase points to e.g. 1000 to simulate well path
            )

            TIMER.lap_s()
            intersection = self.grid.slice_along_line(spline_from_polyline)
            time_it("Slicing grid")

            # Using pyvista plotter to calculate camera position...
            pll = pyvista.Plotter()
            pll.add_mesh(intersection)
            camera_position = pll.camera.position

            mesh_state = to_mesh_state(intersection, field_to_keep="scalar")

            return mesh_state, camera_position, mesh_state

    @property
    def layout(self) -> html.Div:
        return wcc.FlexBox(
            children=[
                html.Div(
                    style={"flex": 5, "height": "90vh"},
                    children=[
                        wcc.Frame(
                            style={"height": "40vh"},
                            children=dash_vtk.View(
                                id="vtk-3d-view",
                                pickingModes=["click"],
                                children=[
                                    dash_vtk.GeometryRepresentation(
                                        id="vtk-3d-grid-representation",
                                        children=[
                                            dash_vtk.Mesh(
                                                id="vtk-3d-grid-mesh",
                                                state=self.mesh_state,
                                            )
                                        ],
                                        property={"edgeVisibility": True},
                                    ),
                                    dash_vtk.GeometryRepresentation(
                                        id="vtk-3d-intersect-representation",
                                        children=[
                                            dash_vtk.Mesh(
                                                id="vtk-3d-intersection-mesh",
                                                state={},
                                            )
                                        ],
                                        property={"edgeVisibility": True},
                                    ),
                                ],
                            ),
                        ),
                        wcc.Frame(
                            style={"height": "40vh"},
                            children=dash_vtk.View(
                                id="vtk-intersection-view",
                                interactorSettings=[
                                    {
                                        "button": 1,
                                        "action": "Pan",
                                    },
                                    {
                                        "button": 2,
                                        "action": "Pan",
                                    },
                                    {
                                        "button": 3,
                                        "action": "Zoom",
                                        "scrollEnabled": True,
                                    },
                                    {
                                        "button": 1,
                                        "action": "Pan",
                                        "shift": True,
                                    },
                                    {
                                        "button": 1,
                                        "action": "Zoom",
                                        "alt": True,
                                    },
                                ],
                                cameraViewUp=(0, 0, -1),
                                cameraParallelProjection=True,
                                children=[
                                    dash_vtk.GeometryRepresentation(
                                        id="vtk-intersection-representation",
                                        children=[
                                            dash_vtk.Mesh(
                                                id="vtk-intersection-mesh",
                                                state={},
                                            )
                                        ],
                                        property={"edgeVisibility": False},
                                    ),
                                ],
                            ),
                        ),
                        html.Button(
                            id="clear",
                            style={"fontSize": "10em"},
                            children="clear polyline",
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": 1},
                    children=html.Pre(id="stored-polyline", children=json.dumps([])),
                ),
            ],
        )
