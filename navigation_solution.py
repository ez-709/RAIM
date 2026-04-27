import os
import numpy as np

from math_model import GPSSatellite, C
from utils import write_csv, DATA_DIR

def lse_epoch(eph_by_prn, pseudoranges, t_rx, x0=None, max_iter=10, tol=1e-3):
    prns = [prn for prn in pseudoranges if prn in eph_by_prn]
    if len(prns) < 4:
        return None

    rho  = np.array([pseudoranges[prn] for prn in prns])
    sats = [GPSSatellite(**vars(eph_by_prn[prn])) for prn in prns]

    x = np.zeros(4) if x0 is None else np.array(x0, dtype=float)

    for it in range(max_iter):
        r_sat = np.zeros((len(prns), 3))
        dt_s  = np.zeros(len(prns))

        for k, sat in enumerate(sats):
            t_tx        = t_rx - rho[k] / C
            pos, vel, c = sat.ecef(t_tx)
            pos, _      = GPSSatellite.sagnac(pos, vel, rho[k] / C)
            r_sat[k]    = pos
            dt_s[k]     = c

        diff      = r_sat - x[:3]
        rng       = np.linalg.norm(diff, axis=1)
        rho_calc  = rng + x[3] - C * dt_s
        residuals = rho - rho_calc

        los = diff / rng[:, None]
        G   = np.column_stack([-los, np.ones(len(prns))])

        dx = np.linalg.lstsq(G, residuals, rcond=None)[0]
        x += dx

        if np.linalg.norm(dx[:3]) < tol:
            break

    return {
        'r_u':       x[:3],
        'dt_u':      x[3] / C,
        'residuals': residuals,
        'G':         G,
        'prns':      prns,
        'iter':      it + 1,
    }


def spp(ephemerides, epochs, max_iter=10):
    eph_by_prn = {}
    for eph in ephemerides:
        eph_by_prn.setdefault(eph.prn, []).append(eph)

    out    = []
    x_prev = None

    for ep in epochs:
        nearest = {prn: min(eph_by_prn[prn], key=lambda e: abs(ep.tow - e.toe))
                   for prn in ep.sats if prn in eph_by_prn}
        sol = lse_epoch(nearest, ep.sats, ep.tow, x0=x_prev, max_iter=max_iter)
        if sol is not None:
            out.append({'time': ep.time, **sol})
            x_prev = np.concatenate([sol['r_u'], [sol['dt_u'] * C]])

    return out


def ephemeris_solution(ephemerides):
    prns  = sorted(set(e.prn for e in ephemerides))
    toes  = [e.toe for e in ephemerides]
    times = np.arange(min(toes), max(toes) + 600, 600)

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
    return ecef_path


def save_pvt(solutions):
    header = ["time", "n_sat", "x", "y", "z", "dt_u", "rms"]
    rows = []
    for s in solutions:
        rms = float(np.sqrt(np.mean(s['residuals'] ** 2)))
        rows.append([s['time'].isoformat(), len(s['prns']),
                     *s['r_u'], s['dt_u'], rms])
    path = os.path.join(DATA_DIR, "pvt.csv")
    write_csv(path, header, rows)
    return path

def report_pvt(solutions, ref=None):
    if not solutions:
        print("PVT: решения отсутствуют")
        return

    r   = np.array([s['r_u'] for s in solutions])
    rms = np.array([np.sqrt(np.mean(s['residuals'] ** 2)) for s in solutions])

    r_mean = r.mean(axis=0)
    r_std  = r.std(axis=0)

    print(f"PVT: {len(solutions)} эпох")
    print(f"  Среднее ECEF : X={r_mean[0]:>12.2f}  Y={r_mean[1]:>12.2f}  Z={r_mean[2]:>12.2f} м")
    print(f"  СКО ECEF     :  {r_std[0]:>11.2f}   {r_std[1]:>11.2f}   {r_std[2]:>11.2f} м")
    print(f"  СКЗ невязок  : средн={rms.mean():.2f} м, макс={rms.max():.2f} м")

    if ref is not None:
        ref      = np.array(ref)
        err_mean = r_mean - ref
        err_3d   = np.linalg.norm(r - ref, axis=1)

        print(f"  Референс: X={ref[0]:>12.2f}  Y={ref[1]:>12.2f}  Z={ref[2]:>12.2f} м")
        print(f"  Ср. ошибка: dX={err_mean[0]:>+9.2f}  dY={err_mean[1]:>+9.2f}  dZ={err_mean[2]:>+9.2f} м")
        print(f"  3D ошибка: средн={err_3d.mean():.2f} м, макс={err_3d.max():.2f} м, "
              f"95%={np.percentile(err_3d, 95):.2f} м")