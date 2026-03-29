import os
import matplotlib.pyplot as plt

from core.fetcher       import get_glonass_rinex_url, fetch_or_cache
from core.parser        import parse_glonass_rinex, get_latest_positions
from visualization.plots import plot_satellites_3d


def print_table(positions: list[dict]) -> None:
    print(f"\n{'PRN':<5} {'Эпоха':<17} {'X, км':>12} {'Y, км':>12} {'Z, км':>12} {'freq':>5}")
    print("-" * 65)
    for s in sorted(positions, key=lambda x: x['prn']):
        print(f"R{s['prn']:<4} {s['epoch']:<17} "
              f"{s['x']:12.2f} {s['y']:12.2f} {s['z']:12.2f} {s['freq_num']:5}")
    print(f"\nВсего: {len(positions)} спутников")


def save_csv(positions: list[dict], path: str = "data/results/lr1_coords.csv") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("prn,epoch,x_km,y_km,z_km,vx,vy,vz,freq_num\n")
        for s in sorted(positions, key=lambda x: x['prn']):
            f.write(f"R{s['prn']:02d},{s['epoch']},"
                    f"{s['x']:.4f},{s['y']:.4f},{s['z']:.4f},"
                    f"{s['vx']:.6f},{s['vy']:.6f},{s['vz']:.6f},{s['freq_num']}\n")
    print(f"[OK] {path}")


if __name__ == '__main__':
    url  = get_glonass_rinex_url()
    text = fetch_or_cache(url, cache_dir="data/cache")

    if text is None:
        print("[ERR] Нет данных")
        exit(1)

    records   = parse_glonass_rinex(text)
    positions = get_latest_positions(records)

    print_table(positions)
    save_csv(positions)

    fig, ax = plot_satellites_3d(positions)
    plt.show()
