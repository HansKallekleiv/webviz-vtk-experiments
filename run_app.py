from dash import Dash

from polydata_app_class import PolyDataApp
from mesh_app_class import MeshApp

VTU_FILE = "./data/eclgrid-70729.vtu"
# VTU_FILE = "./data/geogrid-652508.vtu"

# PLUGIN = PolyDataApp(VTU_FILE)
PLUGIN = MeshApp(VTU_FILE)


app = Dash()
app.layout = PLUGIN.layout
app.run_server(debug=True)