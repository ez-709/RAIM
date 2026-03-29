import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


COLORS = [
    "#D40A0A", "#E25C04", "#F1B501", "#C1B202", "#6E9E03",
    "#007034", "#055F54", "#0A4E75", "#2800BA", "#5A00B0",
    "#8C00A5", "#A23B72", "#896284", "#6F8996", "#00DCBF",
    "#00BFB3", "#00A2A6", "#008599", "#00688C", "#004B7F",
    "#002E72", "#000000", "#201203", "#402406", "#603609",
]


def plot_satellites_3d(positions: list[dict], title: str = "ГЛОНАСС — координаты спутников (ECEF)"):
    fig = plt.figure(figsize=(12, 10))
    ax  = fig.add_subplot(111, projection='3d')

    R = 6371
    u = np.linspace(0, 2 * np.pi, 50)
    v = np.linspace(0, np.pi, 25)
    ax.plot_surface(
        R * np.outer(np.cos(u), np.sin(v)),
        R * np.outer(np.sin(u), np.sin(v)),
        R * np.outer(np.ones(np.size(u)), np.cos(v)),
        color='lightblue', alpha=0.3, linewidth=0
    )

    lat = np.linspace(-np.pi / 2, np.pi / 2, 100)
    ax.plot(R * np.cos(lat), np.zeros(100), R * np.sin(lat),
            color='black', linewidth=1.5, linestyle='--', label='Нулевой меридиан')

    for idx, sat in enumerate(sorted(positions, key=lambda s: s['prn'])):
        color = COLORS[idx % len(COLORS)]
        ax.scatter(sat['x'], sat['y'], sat['z'], color=color, s=60)
        ax.text(sat['x'], sat['y'], sat['z'], f"  R{sat['prn']:02d}", fontsize=8, color=color)

    ax.set_xlabel('X (км)')
    ax.set_ylabel('Y (км)')
    ax.set_zlabel('Z (км)')
    ax.set_title(title)
    plt.tight_layout()
    plt.legend()
    return fig, ax
