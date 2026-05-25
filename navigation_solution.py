import os
import numpy as np

from math_model import (GPSSatellite, C,
                         ecef_to_geodetic, sat_el_az,
                         klobuchar, saastamoinen)
from utils import write_csv, DATA_DIR


def ned_rotation(r_u):
    lat, lon, _ = ecef_to_geodetic(*r_u)
    sla, cla = np.sin(lat), np.cos(lat)
    slo, clo = np.sin(lon), np.cos(lon)
    return np.array([[-sla*clo, -sla*slo,  cla],
                     [-slo,      clo,      0.0],
                     [-cla*clo, -cla*slo, -sla]])


def lse_epoch(eph_by_prn, pseudoranges, t_rx, x0=None,
              max_iter=10, tol=1e-3, iono_params=None, el_mask_deg=10.0):
    prns_all = [p for p in pseudoranges if p in eph_by_prn]
    if len(prns_all) < 4:
        return None

    rho_all  = np.array([pseudoranges[p] for p in prns_all])
    sats_all = [GPSSatellite(**vars(eph_by_prn[p])) for p in prns_all]
    x        = np.zeros(4) if x0 is None else np.array(x0, dtype=float)
    el_mask  = np.radians(el_mask_deg)

    r_sat = np.zeros((len(prns_all), 3))
    dt_s  = np.zeros(len(prns_all))
    for k, sat in enumerate(sats_all):
        t_tx = t_rx - rho_all[k] / C
        pos, vel, clk = sat.ecef(t_tx)
        pos, _    = GPSSatellite.sagnac(pos, vel, rho_all[k] / C)
        r_sat[k]  = pos
        dt_s[k]   = clk

    for it in range(max_iter):
        has_pos = np.linalg.norm(x[:3]) > 1_000_000

        if not has_pos:
            mask = np.ones(len(prns_all), dtype=bool)
        else:
            el_arr = np.array([sat_el_az(x[:3], r_sat[k])[0]
                                for k in range(len(prns_all))])
            mask = el_arr >= el_mask
            if mask.sum() < 4:
                mask = np.ones(len(prns_all), dtype=bool)

        r_s   = r_sat[mask]
        rho_m = rho_all[mask].copy()
        dt_m  = dt_s[mask]

        if has_pos:
            lat_r, lon_r, h_r = ecef_to_geodetic(*x[:3])
            for j in range(len(r_s)):
                el_j, az_j = sat_el_az(x[:3], r_s[j])
                if el_j > np.radians(5.0):
                    rho_m[j] -= saastamoinen(el_j, h_r)
                    if iono_params is not None:
                        rho_m[j] -= klobuchar(lat_r, lon_r, az_j, el_j, t_rx,
                                               iono_params['alpha'], iono_params['beta'])

        diff      = r_s - x[:3]
        rng       = np.linalg.norm(diff, axis=1)
        rho_calc  = rng + x[3] - C * dt_m
        residuals = rho_m - rho_calc
        los       = diff / rng[:, None]
        G         = np.column_stack([-los, np.ones(len(rng))])
        dx        = np.linalg.lstsq(G, residuals, rcond=None)[0]
        x        += dx
        if np.linalg.norm(dx[:3]) < tol:
            break

    n_sat    = G.shape[0]
    sigma_pr = float(np.sqrt(np.sum(residuals**2) / max(n_sat - 4, 1)))

    return dict(r_u=x[:3], dt_u=x[3]/C, residuals=residuals,
                G=G, prns=[prns_all[k] for k in np.where(mask)[0]],
                iter=it+1, sigma_pr=sigma_pr, n_sat=n_sat)


def spp(ephemerides, epochs, max_iter=10,
        iono_params=None, el_mask_deg=10.0, run_raim=True):
    from raim import raim_epoch

    eph_by_prn = {}
    for eph in ephemerides:
        eph_by_prn.setdefault(eph.prn, []).append(eph)

    out, x_prev = [], None
    for ep in epochs:
        nearest = {p: min(eph_by_prn[p], key=lambda e: abs(ep.tow - e.toe))
                   for p in ep.sats if p in eph_by_prn}
        sol = lse_epoch(nearest, ep.sats, ep.tow, x0=x_prev,
                        max_iter=max_iter, iono_params=iono_params,
                        el_mask_deg=el_mask_deg)
        if sol is None:
            continue
        sol['raim'] = raim_epoch(sol) if run_raim else None
        out.append({'time': ep.time, **sol})
        x_prev = np.concatenate([sol['r_u'], [sol['dt_u'] * C]])
    return out


def ephemeris_solution(ephemerides):
    prns  = sorted(set(e.prn for e in ephemerides))
    toes  = [e.toe for e in ephemerides]
    times = np.arange(min(toes), max(toes) + 600, 600)
    header = ["t", "prn", "x", "y", "z", "vx", "vy", "vz", "clock"]
    eci_rows, ecef_rows = [], []
    for prn in prns:
        eph_list = [e for e in ephemerides if e.prn == prn]
        for t in times:
            eph = min(eph_list, key=lambda e: abs(t - e.toe))
            sat = GPSSatellite(**vars(eph))
            p_eci,  v_eci,  clk = sat.eci(t)
            p_ecef, v_ecef, _   = sat.ecef(t)
            eci_rows.append([t, prn, *p_eci,  *v_eci,  clk])
            ecef_rows.append([t, prn, *p_ecef, *v_ecef, clk])
    eci_path  = os.path.join(DATA_DIR, "eci.csv")
    ecef_path = os.path.join(DATA_DIR, "ecef.csv")
    write_csv(eci_path,  header, eci_rows)
    write_csv(ecef_path, header, ecef_rows)
    return ecef_path


def save_pvt(solutions):
    header = ["time", "n_sat", "x", "y", "z", "dt_u",
              "rms", "sigma_pr", "HPL", "HAL", "raim_ok", "fault"]
    rows = []
    for s in solutions:
        rms = float(np.sqrt(np.mean(s['residuals']**2)))
        r   = s.get('raim') or {}
        rows.append([s['time'].isoformat(), len(s['prns']),
                     *s['r_u'], s['dt_u'], rms, s.get('sigma_pr', ''),
                     r.get('HPL', ''), r.get('HAL', ''),
                     int(r.get('available', -1)) if r else '',
                     r.get('fault_prn', '') if r else ''])
    write_csv(os.path.join(DATA_DIR, "pvt.csv"), header, rows)

def report_pvt(solutions, ref=None):
    if not solutions:
        return
    r      = np.array([s['r_u'] for s in solutions])
    r_mean = r.mean(axis=0)
    r_std  = r.std(axis=0)
    
    print(f"Mean ECEF coordinates: X={r_mean[0]:.2f} Y={r_mean[1]:.2f} Z={r_mean[2]:.2f} m")
    print(f"ECEF coordinate STD:     {r_std[0]:.2f} {r_std[1]:.2f} {r_std[2]:.2f} m")
    
    if ref is not None:
        ref = np.array(ref)
        e   = r_mean - ref
        e3d = np.linalg.norm(r - ref, axis=1)
        print(f"Error:       dX={e[0]:+.2f} dY={e[1]:+.2f} dZ={e[2]:+.2f} m")
        print(f"3D error: mean={e3d.mean():.2f}  95th percentile={np.percentile(e3d, 95):.2f} m")
        
    rs = [s['raim'] for s in solutions if s.get('raim') is not None]
    if rs:
        hpls  = np.array([r['HPL'] for r in rs])
        avail = np.array([r['available'] for r in rs])
        print(f"HPL: mean={hpls.mean():.1f} max={hpls.max():.1f} m  availability={100.0 * avail.mean():.2f}%")