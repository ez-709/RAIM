import csv
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def ecef_to_latlon(x, y, z):
    lat = np.degrees(np.arctan2(z, np.sqrt(x * x + y * y)))
    lon = np.degrees(np.arctan2(y, x))
    return lat, lon


def split_at_wrap(lons, lats):
    segments = []
    start = 0
    for k in range(1, len(lons)):
        if abs(lons[k] - lons[k - 1]) > 180.0:
            segments.append((lons[start:k], lats[start:k]))
            start = k
    segments.append((lons[start:], lats[start:]))
    return segments


def load_orbits(ecef_path, duration_hours=None):
    with open(ecef_path, "r") as f:
        rows = [(float(r["t"]), int(r["prn"]),
                 float(r["x"]), float(r["y"]), float(r["z"]))
                for r in csv.DictReader(f)]

    if duration_hours is not None:
        t0    = min(r[0] for r in rows)
        t_max = t0 + duration_hours * 3600.0
        rows  = [r for r in rows if r[0] <= t_max]

    orbits = {}
    for t, prn, x, y, z in rows:
        orbits.setdefault(prn, []).append((x, y, z))
    return orbits


def plot_satellites(ecef_path, duration_hours=None):
    orbits = load_orbits(ecef_path, duration_hours)

    plt.figure(figsize=(14, 7))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_global()
    ax.add_feature(cfeature.LAND,      alpha=0.3)
    ax.add_feature(cfeature.OCEAN,     alpha=0.3)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.5)

    cmap = plt.get_cmap("tab20")
    for i, (prn, traj) in enumerate(sorted(orbits.items())):
        xyz        = np.array(traj)
        lats, lons = ecef_to_latlon(xyz[:, 0], xyz[:, 1], xyz[:, 2])
        color      = cmap(i % 20)
        for seg_lons, seg_lats in split_at_wrap(lons, lats):
            ax.plot(seg_lons, seg_lats, "-", color=color, linewidth=0.7,
                    transform=ccrs.PlateCarree())
        ax.plot(lons[0], lats[0], "o", color=color, markersize=4,
                transform=ccrs.PlateCarree(), label=f"G{prn:02d}")

    title = f"GPS ground tracks ({duration_hours} h)" if duration_hours else "GPS ground tracks"
    ax.set_title(title)
    ax.legend(loc="lower left", fontsize="x-small", ncol=4, framealpha=0.7)

    plt.show()