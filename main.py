import sys
import os
import gzip
from datetime import datetime, timedelta
import requests
import numpy as np

from parsers.rinex_parser import parse_rinex_nav
from math_model import GPSSatellite
from utils import write_csv, log, json_to_py, DATA_DIR
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

    date = datetime.utcnow() - timedelta(days=days_back)
    year, doy, yy = date.year, date.timetuple().tm_yday, date.year % 100
    log(f"download brdc: {date:%Y-%m-%d} (doy {doy})")

    for tmpl in BRDC_URLS:
        url = tmpl.format(year=year, doy=doy, yy=yy)
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 500:
                data = gzip.decompress(r.content)
                out_path = os.path.join(DATA_DIR, f"brdc_{year}_{doy:03d}.nav")
                with open(out_path, "wb") as f:
                    f.write(data)
                log(f"  ok: {out_path} ({len(data)} bytes)")
                return out_path
        except Exception as e:
            log(f"  fail {url}: {e}")

    return download_brdc(days_back + 1)


def find_existing_brdc():
    if not os.path.isdir(DATA_DIR):
        return None
    files = sorted(f for f in os.listdir(DATA_DIR)
                   if f.startswith("brdc_") and f.endswith(".nav"))
    return os.path.join(DATA_DIR, files[-1]) if files else None


def compute(ephemerides):
    prns  = sorted(set(e.prn for e in ephemerides))
    toes  = [e.toe for e in ephemerides]
    times = np.arange(min(toes), max(toes) + 600, 600)
    log(f"satellites: {len(prns)} PRNs, {len(times)} epochs")

    header    = ["t", "prn", "x", "y", "z", "vx", "vy", "vz", "clock"]
    eci_rows  = []
    ecef_rows = []

    for prn in prns:
        eph_list = [e for e in ephemerides if e.prn == prn]
        for t in times:
            eph = min(eph_list, key=lambda e: abs(t - e.toe))
            sat = GPSSatellite(**vars(eph))
            pos_eci,  vel_eci,  clk = sat.eci(t)
            pos_ecef, vel_ecef, _   = sat.ecef(t)
            eci_rows.append([t, prn, *pos_eci, *vel_eci, clk])
            ecef_rows.append([t, prn, *pos_ecef, *vel_ecef, clk])

    eci_path  = os.path.join(DATA_DIR, "eci.csv")
    ecef_path = os.path.join(DATA_DIR, "ecef.csv")
    write_csv(eci_path,  header, eci_rows)
    write_csv(ecef_path, header, ecef_rows)
    log(f"saved: {eci_path}, {ecef_path}")
    return ecef_path


def main():
    log("RAIM — start", reset=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    if len(sys.argv) >= 2:
        nav_path = sys.argv[1]
    else:
        cfg = json_to_py(CONFIG_PATH)["download"]
        nav_path = download_brdc(cfg["days_back"]) if cfg["mode"] else find_existing_brdc()

    if not nav_path:
        log("ERROR: nav file not found")
        return

    log(f"nav file: {nav_path}")
    ephemerides = parse_rinex_nav(nav_path)
    log(f"parsed: {len(ephemerides)} ephemeris records")

    if not ephemerides:
        log("ERROR: no valid ephemeris")
        return

    ecef_path = compute(ephemerides)
    plot_satellites(ecef_path, duration_hours=2)


if __name__ == "__main__":
    main()