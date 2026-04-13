import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def ecef_to_latlon(x, y, z):
    lon = np.degrees(np.arctan2(y, x))
    lat = np.degrees(np.arctan2(z, np.sqrt(x * x + y * y)))
    return lat, lon


def _load_ecef(path):
    rows = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                't': float(r['t']),
                'prn': int(r['prn']),
                'x': float(r['x']),
                'y': float(r['y']),
                'z': float(r['z']),
            })
    return rows


def plot_satellites(ecef_csv):
    data = _load_ecef(ecef_csv)
    times = sorted(set(r['t'] for r in data))
    by_time = {}
    for r in data:
        by_time.setdefault(r['t'], []).append(r)

    fig = plt.figure(figsize=(15, 9))
    ax = fig.add_axes([0.05, 0.12, 0.9, 0.83], projection=ccrs.PlateCarree())
    ax.set_global()
    ax.add_feature(cfeature.LAND, facecolor='#e8e8e8')
    ax.add_feature(cfeature.OCEAN, facecolor='#d4e9f7')
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, linestyle=':')
    ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.5)

    scatter = ax.scatter([], [], transform=ccrs.PlateCarree(),
                         s=50, c='red', edgecolors='darkred', linewidths=0.5, zorder=5)
    labels = []
    title = ax.set_title("", fontsize=12)

    slider_ax = fig.add_axes([0.15, 0.03, 0.7, 0.025])
    step = times[1] - times[0] if len(times) > 1 else 600
    slider = Slider(slider_ax, 't [s]', times[0], times[-1],
                    valinit=times[0], valstep=step)

    def update(val):
        t = slider.val
        closest = min(times, key=lambda x: abs(x - t))
        rows = by_time.get(closest, [])

        lons, lats = [], []
        for r in rows:
            lat, lon = ecef_to_latlon(r['x'], r['y'], r['z'])
            lats.append(lat)
            lons.append(lon)

        scatter.set_offsets(np.column_stack([lons, lats]) if lons else np.empty((0, 2)))

        for lb in labels:
            lb.remove()
        labels.clear()

        for i, r in enumerate(rows):
            lb = ax.text(lons[i] + 1.5, lats[i], f"G{r['prn']:02d}",
                         transform=ccrs.PlateCarree(), fontsize=7,
                         color='darkred', weight='bold', zorder=6)
            labels.append(lb)

        h = int(closest // 3600)
        m = int((closest % 3600) // 60)
        title.set_text(f"GPS satellites | t = {closest:.0f} s  ({h:02d}:{m:02d} UTC)")
        fig.canvas.draw_idle()

    slider.on_changed(update)
    update(times[0])
    plt.show()