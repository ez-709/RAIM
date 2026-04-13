import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from math_model import Ephemeris, GPSSatellite, C

eph = Ephemeris(
    prn=14,
    toc=504000.0,
    toe=504000.0,
    sqrt_a=5.153494356155e+03,
    eccentricity=4.552247002721e-03,
    inclination=9.607443114283e-01,
    ascending_node=7.384895693748e-01,
    perigee=2.885975350835e+00,
    mean_anomaly=-8.892370366347e-01,
    mean_motion_corr=4.259106000000e-09,
    ascending_node_rate=-7.866756253000e-09,
    inclination_rate=1.275053100000e-10,
    cuc=-1.117587100000e-07,
    cus=1.188553900000e-05,
    crc=1.480625000000e+02,
    crs=1.125000000000e+00,
    cic=-1.862645100000e-09,
    cis=-1.080334200000e-07,
    clock_bias=1.832102425396e-04,
    clock_drift=3.410605100000e-13,
    clock_drift_rate=0.0,
)

ref = [
    (496800, -1.925132225385e+07,  5.287213520833e+06,  1.758197241879e+07, 1.832174931499e-04),
    (497400, -1.852325341598e+07,  4.111140955354e+06,  1.863191927798e+07, 1.832179922371e-04),
    (498000, -1.779609748114e+07,  2.847861255577e+06,  1.953977263714e+07, 1.832184150563e-04),
    (498600, -1.708115246527e+07,  1.505145628662e+06,  2.029843978735e+07, 1.832187598536e-04),
    (499200, -1.638891257552e+07,  9.219638541095e+04,  2.090194872206e+07, 1.832190254656e-04),
    (499800, -1.572888937811e+07, -1.380481227134e+06,  2.134549869009e+07, 1.832192111317e-04),
    (500400, -1.510945030926e+07, -2.901230212362e+06,  2.162550232157e+07, 1.832193175004e-04),
    (501000, -1.453767741057e+07, -4.457413637737e+06,  2.173961885040e+07, 1.832193446327e-04),
]

sat = GPSSatellite(eph)
t_tr = 24_000_000.0 / C

print("IS-GPS-200 Table C-1 | PRN 14")
print(f"a = {sat.a:.6e}   ref = 2.655850407893e+07")
print(f"n = {sat.n:.12e}   ref = 1.458734269097e-04")
print()

for t, xr, yr, zr, clk_r in ref:
    pos, vel, clk = sat.ecef(t)
    pos, _ = GPSSatellite.sagnac(pos, vel, t_tr)

    print(f"t = {t}")
    print(f"  x:   {pos[0]:+.6e}   ref: {xr:+.6e}   dx: {pos[0]-xr:+.4f} m")
    print(f"  y:   {pos[1]:+.6e}   ref: {yr:+.6e}   dy: {pos[1]-yr:+.4f} m")
    print(f"  z:   {pos[2]:+.6e}   ref: {zr:+.6e}   dz: {pos[2]-zr:+.4f} m")
    print(f"  clk: {clk:.12e}   ref: {clk_r:.12e}   d: {(clk-clk_r)*1e9:+.4f} ns")
    print()