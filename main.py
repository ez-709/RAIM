import sys
import os
import gzip
from datetime import datetime, timedelta
import requests
import numpy as np
from parsers.rinex_parser import parse_rinex_nav
from math_model import GPSSatellite
from utils import write_csv, log, DATA_DIR


def download_brdc(days_back=1):
    date = datetime.utcnow() - timedelta(days=days_back)
    year = date.year
    yy = year % 100
    doy = date.timetuple().tm_yday

    urls = [
        f"https://igs.bkg.bund.de/root_ftp/IGS/BRDC/{year}/{doy:03d}/BRDC00IGS_R_{year}{doy:03d}0000_01D_MN.rnx.gz",
        f"https://igs.bkg.bund.de/root_ftp/EUREF/BRDC/{year}/{doy:03d}/BRDC00WRD_S_{year}{doy:03d}0000_01D_MN.rnx.gz",
        f"https://igs.bkg.bund.de/root_ftp/IGS/BRDC/{year}/{doy:03d}/brdc{doy:03d}0.{yy:02d}n.gz",
    ]

    log(f"download brdc: {date:%Y-%m-%d} (doy {doy})")

    for url in urls:
        log(f"  trying: {url}")
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 500:
                data = gzip.decompress(r.content)
                out_path = os.path.join(DATA_DIR, f"brdc_{year}_{doy:03d}.nav")
                with open(out_path, "wb") as f:
                    f.write(data)
                log(f"  ok: {out_path} ({len(data)} bytes)")
                return out_path
            log(f"  http {r.status_code}")
        except Exception as e:
            log(f"  fail: {e}")

    if days_back < 5:
        log(f"  trying {days_back + 1} days back...")
        return download_brdc(days_back + 1)

    return None


def compute(ephemerides):
    prns = sorted(set(e.prn for e in ephemerides))
    toes = [e.toe for e in ephemerides]
    t0, t1 = min(toes), max(toes)
    times = np.arange(t0, t1 + 600, 600)
    log(f"satellites: {len(prns)} PRNs — {prns}")
    log(f"time grid: {t0:.0f} — {t1:.0f} s, step 600 s, {len(times)} epochs")

    header = ["t", "prn", "x", "y", "z", "vx", "vy", "vz", "clock"]
    eci_rows = []
    ecef_rows = []

    for prn in prns:
        eph_list = [e for e in ephemerides if e.prn == prn]
        for t in times:
            eph = min(eph_list, key=lambda e: abs(t - e.toe))
            sat = GPSSatellite(eph)

            pos_eci, vel_eci, clk = sat.eci(t)
            pos_ecef, vel_ecef, _ = sat.ecef(t)

            eci_rows.append([t, prn, *pos_eci, *vel_eci, clk])
            ecef_rows.append([t, prn, *pos_ecef, *vel_ecef, clk])

    eci_path = os.path.join(DATA_DIR, "eci.csv")
    ecef_path = os.path.join(DATA_DIR, "ecef.csv")
    write_csv(eci_path, header, eci_rows)
    write_csv(ecef_path, header, ecef_rows)
    log(f"saved: {eci_path} ({len(eci_rows)} rows)")
    log(f"saved: {ecef_path} ({len(ecef_rows)} rows)")

    return ecef_path


def main():
    log("RAIM — start", reset=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    if len(sys.argv) >= 2:
        nav_path = sys.argv[1]
    else:
        nav_path = download_brdc()
        if nav_path is None:
            log("ERROR: не удалось скачать brdc")
            return

    log(f"nav file: {nav_path}")

    ephemerides = parse_rinex_nav(nav_path)
    log(f"parsed: {len(ephemerides)} GPS ephemeris records")

    if not ephemerides:
        log("ERROR: no valid ephemeris found")
        return

    ecef_path = compute(ephemerides)

    from plots import plot_satellites
    plot_satellites(ecef_path)


if __name__ == "__main__":
    main()