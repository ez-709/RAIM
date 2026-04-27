import sys
import os
import re
import gzip
from datetime import datetime, timezone, timedelta

import requests
import hatanaka

from parsers.rinex_parser import parse_rinex_nav, parse_rinex_obs, get_approx_position
from navigation_solution import ephemeris_solution, spp, save_pvt, report_pvt
from utils import read_config, DATA_DIR
from plots import plot_satellites


CONFIG_PATH = "config.json"

BRDC_URLS = [
    "https://igs.bkg.bund.de/root_ftp/IGS/BRDC/{year}/{doy:03d}/BRDC00IGS_R_{year}{doy:03d}0000_01D_MN.rnx.gz",
    "https://igs.bkg.bund.de/root_ftp/EUREF/BRDC/{year}/{doy:03d}/BRDC00WRD_S_{year}{doy:03d}0000_01D_MN.rnx.gz",
    "https://igs.bkg.bund.de/root_ftp/IGS/BRDC/{year}/{doy:03d}/brdc{doy:03d}0.{yy:02d}n.gz",
]


def download_brdc(days_back=1):
    if days_back > 5:
        return None
    date = datetime.now(timezone.utc) - timedelta(days=days_back)
    year, doy, yy = date.year, date.timetuple().tm_yday, date.year % 100

    for tmpl in BRDC_URLS:
        url = tmpl.format(year=year, doy=doy, yy=yy)
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 500:
                data = gzip.decompress(r.content)
                out_path = os.path.join(DATA_DIR, f"brdc_{year}_{doy:03d}.nav")
                with open(out_path, "wb") as f:
                    f.write(data)
                return out_path
        except Exception:
            pass
    return download_brdc(days_back + 1)


def download_obs(stations, output_dir, days_back, t_listing, t_file):
    if days_back > 5:
        return None
    date = datetime.now(timezone.utc) - timedelta(days=days_back)
    year, doy = date.year, date.timetuple().tm_yday
    base = f"https://igs.bkg.bund.de/root_ftp/IGS/obs/{year}/{doy:03d}/"

    try:
        listing = requests.get(base, timeout=t_listing).text
    except Exception:
        return download_obs(stations, output_dir, days_back + 1, t_listing, t_file)

    for station in stations:
        m = re.search(rf'href="({station.upper()[:4]}\w+\.(?:crx|rnx)\.gz)"',
                      listing, re.IGNORECASE)
        if not m:
            continue
        filename = m.group(1)
        try:
            data = requests.get(base + filename, timeout=t_file).content
            data = gzip.decompress(data)
            if filename.endswith(".crx.gz"):
                data = hatanaka.decompress(data)
        except Exception:
            continue
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir,
                                re.sub(r"\.(crx|rnx)\.gz$", ".rnx", filename))
        with open(out_path, "wb") as f:
            f.write(data)
        return out_path

    return download_obs(stations, output_dir, days_back + 1, t_listing, t_file)


def find_latest(directory, prefixes=("",), suffixes=("",)):
    if not os.path.isdir(directory):
        return None
    files = sorted(f for f in os.listdir(directory)
                   if any(f.startswith(p) for p in prefixes)
                   and any(f.endswith(s) for s in suffixes))
    return os.path.join(directory, files[-1]) if files else None


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    mode, days_back, output_dir, t_listing, t_file, stations = read_config(CONFIG_PATH)

    if len(sys.argv) >= 2:
        nav_path = sys.argv[1]
    else:
        nav_path = download_brdc(days_back) if mode else \
                   find_latest(DATA_DIR, prefixes=("brdc_",), suffixes=(".nav",))

    if not nav_path:
        print("nav not found")
        return

    ephemerides = parse_rinex_nav(nav_path)
    print(f"nav: {len(ephemerides)} ephemerides ({os.path.basename(nav_path)})")
    if not ephemerides:
        return

    ecef_path = ephemeris_solution(ephemerides)

    obs_path = find_latest(output_dir, suffixes=(".rnx", ".txt", ".obs"))
    if not obs_path and mode:
        obs_path = download_obs(stations, output_dir, days_back, t_listing, t_file)

    if obs_path:
        epochs  = parse_rinex_obs(obs_path)
        ref_xyz = get_approx_position(obs_path)
        print(f"obs: {len(epochs)} epochs ({os.path.basename(obs_path)})")
        if epochs:
            solutions = spp(ephemerides, epochs)
            save_pvt(solutions)
            report_pvt(solutions, ref=ref_xyz)

    plot_satellites(ecef_path, duration_hours=12)


if __name__ == "__main__":
    main()
