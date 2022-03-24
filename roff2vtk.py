import logging
from pathlib import Path

import numpy as np
import xtgeo
import pyvista

from webviz_subsurface._utils.perf_timer import PerfTimer


TIMER = PerfTimer()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def time_it(text: str) -> str:
    return print(f"TIME: {text} {TIMER.lap_s():.2f}s")


# Input data on Roxar open file format(ROFF)
# Geogrid is the originally constructed grid,
# used for geomodelling. Eclgrid is the upscaled
# grid used for simulation.

ROFFGRID = Path("./data/eclgrid.roff")
ROFFSCALAR = Path("./data/eclgrid--pressure.roff")
# ROFFGRID = Path("./data/geogrid.roff")
# ROFFSCALAR = Path("./data/geogrid--phit.roff")

# Adjust this integer to multiply number of layers(k)
# 1 is no refinement
REFINE_VERTICALLY = 1


xtg_grid = xtgeo.grid_from_file(ROFFGRID)
time_it("Reading xtgeo grid to roff")

prop = xtgeo.gridproperty_from_file(ROFFSCALAR)
scalar = prop.get_npvalues1d(order="F")
time_it("Reading xtgeo grid parameter to roff")

if REFINE_VERTICALLY > 1:
    xtg_grid.refine_vertically(REFINE_VERTICALLY)
    scalar = np.repeat(scalar, REFINE_VERTICALLY)
    time_it("Refining grid")

print(f"(Cells, total: {xtg_grid.ntotal}, active: {xtg_grid.nactive})")

dims, corners, inactive = xtg_grid.get_vtk_geometries()
time_it("Extracting corners and dimensions")

egrid = pyvista.ExplicitStructuredGrid(dims, corners)
time_it("Converting to explicit structured grid")

egrid.compute_connectivity(inplace=True)
time_it("Compute connectivity")

egrid.hide_cells(inactive, inplace=True)
time_it("Hide inactive cells")

egrid.flip_z(inplace=True)
time_it("Flip z")

egrid.cell_data["scalar"] = scalar
time_it("Add a scalar")

egrid.save(f"data/{ROFFGRID.stem}-{xtg_grid.nactive}.vtu")
time_it("Save to file")

print(f"TOTAL TIME: {TIMER.elapsed_s():.2f}s")
