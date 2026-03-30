import numpy as np
import os

from core.calculation import *
from core.parsers import *
from utils import *

PATH = os.getcwd()
eph_PATH = os.path.join(PATH, 'data', 'ephemeris.json')
ref_PATH = os.path.join(PATH, 'data', 'reference_positions.json')

calc_PATH = os.path.join(PATH, 'data', 'calculated_data')

eph = json_to_py(eph_PATH)
ref = json_to_py(ref_PATH)

t_points = [int(k) for k in ref.keys()]

res_PATH = make_csv_of_ECI_from_t_points(t_points, eph, calc_PATH)

sats_coords = csv_to_py(res_PATH)

for entry in sats_coords:
    t = entry['time']
    r = ref[str(t)]
    
    dx = entry['X'] - r['x']
    dy = entry['Y'] - r['y']
    dz = entry['Z'] - r['z']
    err = np.sqrt(dx**2 + dy**2 + dz**2)
    
    print(f"t={t}: dX={dx:8.3f} m, dY={dy:8.3f} m, dZ={dz:8.3f} m | error={err:.4f} m")