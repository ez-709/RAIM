import numpy as np
from dataclasses import dataclass

MU = 3.986005e14
OMEGA_E = 7.2921151467e-5
C = 299792458.0
WEEK = 604800.0
HALF_WEEK = 302400.0


@dataclass
class Ephemeris:
    prn: int
    toe: float
    toc: float
    sqrt_a: float
    eccentricity: float
    inclination: float
    ascending_node: float
    perigee: float
    mean_anomaly: float
    mean_motion_corr: float
    ascending_node_rate: float
    inclination_rate: float
    cuc: float
    cus: float
    crc: float
    crs: float
    cic: float
    cis: float
    clock_bias: float
    clock_drift: float
    clock_drift_rate: float
    group_delay: float = 0.0
    week: int = 0


class GPSSatellite:
    def __init__(self, eph: Ephemeris):
        self.eph = eph
        self.a = eph.sqrt_a ** 2
        self.n = np.sqrt(MU / self.a ** 3) + eph.mean_motion_corr
        self.p = self.a * (1.0 - eph.eccentricity ** 2)

    def _wrap(self, dt):
        while dt > HALF_WEEK:
            dt -= WEEK
        while dt < -HALF_WEEK:
            dt += WEEK
        return dt

    def _kepler(self, M):
        e = self.eph.eccentricity
        E = M
        for _ in range(30):
            E_new = M + e * np.sin(E)
            if abs(E_new - E) < 1e-12:
                break
            E = E_new
        return E

    def _orbital(self, t_em):
        eph = self.eph
        e = eph.eccentricity

        tk = self._wrap(t_em - eph.toe)
        M = eph.mean_anomaly + self.n * tk
        E = self._kepler(M)

        sin_E = np.sin(E)
        cos_E = np.cos(E)
        d = 1.0 - e * cos_E

        sin_f = np.sqrt(1.0 - e * e) * sin_E / d
        cos_f = (cos_E - e) / d
        f = np.arctan2(sin_f, cos_f)

        phi = f + eph.perigee
        s2 = np.sin(2.0 * phi)
        c2 = np.cos(2.0 * phi)

        u = phi + eph.cus * s2 + eph.cuc * c2
        r = self.a * d + eph.crs * s2 + eph.crc * c2
        inc = eph.inclination + eph.cis * s2 + eph.cic * c2 + eph.inclination_rate * tk

        cos_u = np.cos(u)
        sin_u = np.sin(u)
        x_orb = r * cos_u
        y_orb = r * sin_u

        sq = np.sqrt(MU / self.p)
        vr = sq * e * sin_f
        vt = sq * (1.0 + e * cos_f)
        vx_orb = vr * cos_u - vt * sin_u
        vy_orb = vr * sin_u + vt * cos_u

        return tk, sin_E, x_orb, y_orb, vx_orb, vy_orb, inc

    def _clock(self, t_em, e_sin_E):
        eph = self.eph
        dt = self._wrap(t_em - eph.toc)
        trend = eph.clock_bias + eph.clock_drift * dt + eph.clock_drift_rate * dt * dt
        rel = -2.0 * np.sqrt(MU * self.a) / (C * C) * e_sin_E
        return trend + rel - eph.group_delay

    def eci(self, t_em):
        tk, sin_E, x, y, vx, vy, inc = self._orbital(t_em)
        eph = self.eph

        omega = eph.ascending_node + eph.ascending_node_rate * tk

        co = np.cos(omega)
        so = np.sin(omega)
        ci = np.cos(inc)
        si = np.sin(inc)

        pos = np.array([
            x * co - y * ci * so,
            x * so + y * ci * co,
            y * si
        ])
        vel = np.array([
            vx * co - vy * ci * so,
            vx * so + vy * ci * co,
            vy * si
        ])

        clk = self._clock(t_em, eph.eccentricity * sin_E)
        return pos, vel, clk

    def ecef(self, t_em):
        tk, sin_E, x, y, vx, vy, inc = self._orbital(t_em)
        eph = self.eph

        omega = (eph.ascending_node
                 + (eph.ascending_node_rate - OMEGA_E) * tk
                 - OMEGA_E * eph.toe)

        co = np.cos(omega)
        so = np.sin(omega)
        ci = np.cos(inc)
        si = np.sin(inc)

        pos = np.array([
            x * co - y * ci * so,
            x * so + y * ci * co,
            y * si
        ])
        vel = np.array([
            vx * co - vy * ci * so,
            vx * so + vy * ci * co,
            vy * si
        ])
        vel[0] += OMEGA_E * pos[1]
        vel[1] -= OMEGA_E * pos[0]

        clk = self._clock(t_em, eph.eccentricity * sin_E)
        return pos, vel, clk

    @staticmethod
    def sagnac(pos, vel, t_tr):
        a = OMEGA_E * t_tr
        ca = np.cos(a)
        sa = np.sin(a)
        R = np.array([[ca, sa, 0.0], [-sa, ca, 0.0], [0.0, 0.0, 1.0]])
        pos_out = R @ pos
        vel_out = R @ vel if vel is not None else None
        return pos_out, vel_out