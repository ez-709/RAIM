import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from math_model import ecef_to_geodetic
from navigation_solution import ned_rotation


def _load_orbits(ecef_path, duration_hours=None):
    with open(ecef_path) as f:
        rows = [(float(r["t"]), int(r["prn"]),
                 float(r["x"]), float(r["y"]), float(r["z"]))
                for r in csv.DictReader(f)]
    if duration_hours is not None:
        t0 = min(r[0] for r in rows)
        rows = [r for r in rows if r[0] <= t0 + duration_hours*3600]
    orbits = {}
    for t, prn, x, y, z in rows:
        orbits.setdefault(prn, []).append((x, y, z))
    return orbits


def plot_satellites(ecef_path, duration_hours=None):
    orbits = _load_orbits(ecef_path, duration_hours)
    fig = plt.figure(figsize=(14, 6))
    ax  = plt.axes(projection=ccrs.PlateCarree())
    ax.set_global()
    ax.add_feature(cfeature.LAND,      alpha=0.3)
    ax.add_feature(cfeature.OCEAN,     alpha=0.3)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.5)
    cmap = plt.get_cmap("tab20")
    for i, (prn, traj) in enumerate(sorted(orbits.items())):
        xyz  = np.array(traj)
        lats = np.degrees(np.arctan2(xyz[:,2], np.sqrt(xyz[:,0]**2+xyz[:,1]**2)))
        lons = np.degrees(np.arctan2(xyz[:,1], xyz[:,0]))
        c    = cmap(i % 20)
        # wrap
        segs, s = [], 0
        for k in range(1, len(lons)):
            if abs(lons[k]-lons[k-1]) > 180:
                segs.append((lons[s:k], lats[s:k])); s = k
        segs.append((lons[s:], lats[s:]))
        for sl, sb in segs:
            ax.plot(sl, sb, '-', color=c, lw=0.7, transform=ccrs.PlateCarree())
        ax.plot(lons[0], lats[0], 'o', color=c, ms=4,
                transform=ccrs.PlateCarree(), label=f"G{prn:02d}")
    title = f"GPS ground tracks ({duration_hours} h)" if duration_hours else "GPS ground tracks"
    ax.set_title(title)
    ax.legend(loc="lower left", fontsize="x-small", ncol=4, framealpha=0.7)
    plt.tight_layout(); plt.show()

def plot_hpl(solutions, HAL=550, ref_xyz=None):
    data = [(s['time'], s['raim']) for s in solutions if s.get('raim')]
    if not data:
        return

    times     = [d[0] for d in data]
    hpls      = np.array([d[1]['HPL']           for d in data])
    available = np.array([d[1]['available']      for d in data])
    n_sats    = [len(s['prns']) for s in solutions if s.get('raim')]

    if ref_xyz is not None:
        ref = np.array(ref_xyz)
        r_arr = np.array([s['r_u'] for s in solutions if s.get('raim')])
        pes = np.linalg.norm(r_arr - ref, axis=1)
    else:
        pes = None

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True, 
                             gridspec_kw={'height_ratios': [3, 1]})

    ax = axes[0]

    ax.plot(times, hpls, color='blue', lw=1.5, label="HPL (Protection Level)")

    ax.axhline(HAL, color='red', lw=1.5, ls='--', label=f"HAL (Alert Limit) {HAL} m")

    if pes is not None:
        ax.plot(times, pes, color='green', lw=1.0, label="PE (Position Error)")

    ax.set_ylabel("Meters")
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize='small')

    avail_pct = 100 * available.mean()
    hpl_mean = hpls.mean()
    pe_mean = pes.mean() if pes is not None else 0
    
    title = f"Availability: {avail_pct:.1f}% | HPL mean: {hpl_mean:.0f} m"
    if pes is not None:
        title += f" | PE mean: {pe_mean:.1f} m"
    ax.set_title(title)

    ax = axes[1]
    ax.step(times, n_sats)
    ax.set_ylabel("Satellites")
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize='small')

    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30, ha='right')

    plt.tight_layout()
    plt.show()