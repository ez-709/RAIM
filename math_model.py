import numpy as np

MU        = 3.986005e14
OMEGA_E   = 7.2921151467e-5
C         = 299792458.0
WEEK      = 604800.0
HALF_WEEK = 302400.0


def ecef_to_geodetic(x, y, z):
    a, f = 6_378_137.0, 1.0 / 298.257_223_563
    e2   = 2*f - f*f
    lon  = np.arctan2(y, x)
    p    = np.sqrt(x**2 + y**2)
    lat  = np.arctan2(z, p * (1.0 - e2))
    for _ in range(10):
        N   = a / np.sqrt(1.0 - e2 * np.sin(lat)**2)
        lat_n = np.arctan2(z + e2 * N * np.sin(lat), p)
        if abs(lat_n - lat) < 1e-12:
            break
        lat = lat_n
    N = a / np.sqrt(1.0 - e2 * np.sin(lat)**2)
    h = p / np.cos(lat) - N if abs(np.cos(lat)) > 1e-9 else abs(z) / np.sin(lat) - N * (1.0 - e2)
    return lat, lon, h


def sat_el_az(r_u, r_sat):
    lat, lon, _ = ecef_to_geodetic(*r_u)
    sla, cla = np.sin(lat), np.cos(lat)
    slo, clo = np.sin(lon), np.cos(lon)
    R = np.array([[-sla*clo, -sla*slo,  cla],
                  [-slo,      clo,      0.0],
                  [-cla*clo, -cla*slo, -sla]])
    ned = R @ (np.asarray(r_sat) - np.asarray(r_u))
    return np.arctan2(ned[2], np.sqrt(ned[0]**2 + ned[1]**2)), np.arctan2(ned[1], ned[0])


def klobuchar(lat_r, lon_r, az, el, tow, alpha, beta):
    el_sc = el / np.pi
    psi   = 0.0137 / (el_sc + 0.11) - 0.022
    phi_i = np.clip(lat_r / np.pi + psi * np.cos(az), -0.416, 0.416)
    lam_i = lon_r / np.pi + psi * np.sin(az) / np.cos(phi_i * np.pi)
    phi_m = phi_i + 0.064 * np.cos((lam_i - 1.617) * np.pi)
    t     = (43200.0 * lam_i + tow) % 86400.0
    PER   = max(sum(beta[n]  * phi_m**n for n in range(4)), 72000.0)
    AMP   = max(sum(alpha[n] * phi_m**n for n in range(4)), 0.0)
    F     = 1.0 + 16.0 * (0.53 - el_sc)**3
    x     = 2.0 * np.pi * (t - 50400.0) / PER
    T     = F * (5e-9 + AMP * (1 - x**2/2 + x**4/24)) if abs(x) < 1.57 else F * 5e-9
    return T * C


def saastamoinen(el_rad, h_m):
    P  = 1013.25 * (1.0 - 2.2557e-5 * h_m) ** 5.2568
    mf = 1.0 / np.sqrt(np.sin(el_rad)**2 + 1.904e-3)
    return 2.312 * mf * (P / 1013.25)


class GPSSatellite:
    def __init__(self, prn, toe, toc,
                 sqrt_a, e, i_0, Omega_0, omega, M_0,
                 dn, Omega_dot, i_dot,
                 C_uc, C_us, C_rc, C_rs, C_ic, C_is,
                 alpha_0, alpha_1, alpha_2,
                 T_gd=0.0, week=0):
        self.prn = prn
        self.toe = toe; self.toc = toc
        self.e = e; self.i_0 = i_0; self.Omega_0 = Omega_0
        self.omega = omega; self.M_0 = M_0; self.dn = dn
        self.Omega_dot = Omega_dot; self.i_dot = i_dot
        self.C_uc = C_uc; self.C_us = C_us
        self.C_rc = C_rc; self.C_rs = C_rs
        self.C_ic = C_ic; self.C_is = C_is
        self.alpha_0 = alpha_0; self.alpha_1 = alpha_1; self.alpha_2 = alpha_2
        self.T_gd = T_gd; self.week = week
        self.a = sqrt_a ** 2
        self.n = np.sqrt(MU / self.a ** 3) + dn
        self.p = self.a * (1.0 - e ** 2)

    def wrap(self, dt):
        if dt >  HALF_WEEK: dt -= WEEK
        if dt < -HALF_WEEK: dt += WEEK
        return dt

    def kepler(self, M):
        E = M
        for _ in range(50):
            E_new = M + self.e * np.sin(E)
            if abs(E_new - E) < 1e-12: break
            E = E_new
        return E_new

    def orbital(self, t_em):
        e      = self.e
        t_star = self.wrap(t_em - self.toe)
        E      = self.kepler(self.M_0 + self.n * t_star)
        sin_E, cos_E = np.sin(E), np.cos(E)
        d      = 1.0 - e * cos_E
        f      = np.arctan2(np.sqrt(1 - e**2) * sin_E / d, (cos_E - e) / d)
        phi    = f + self.omega
        s2, c2 = np.sin(2*phi), np.cos(2*phi)
        u      = phi + self.C_us*s2 + self.C_uc*c2
        r      = self.a*d + self.C_rs*s2 + self.C_rc*c2
        i_k    = self.i_0 + self.C_is*s2 + self.C_ic*c2 + self.i_dot*t_star
        cu, su = np.cos(u), np.sin(u)
        x, y   = r*cu, r*su
        sq     = np.sqrt(MU / self.p)
        vx = sq*e*np.sin(f)*cu - sq*(1+e*np.cos(f))*su
        vy = sq*e*np.sin(f)*su + sq*(1+e*np.cos(f))*cu
        return t_star, sin_E, x, y, vx, vy, i_k

    def clock(self, t_em, e_sin_E):
        dt = self.wrap(t_em - self.toc)
        return (self.alpha_0 + self.alpha_1*dt + self.alpha_2*dt**2
                - 2*np.sqrt(MU*self.a)/C**2 * e_sin_E - self.T_gd)

    def _to_frame(self, t_em, inertial=False):
        t_star, sin_E, x, y, vx, vy, i_k = self.orbital(t_em)
        Ok = (self.Omega_0 + self.Omega_dot*t_star if inertial
              else self.Omega_0 + (self.Omega_dot - OMEGA_E)*t_star - OMEGA_E*self.toe)
        cO, sO, ci, si = np.cos(Ok), np.sin(Ok), np.cos(i_k), np.sin(i_k)
        pos = np.array([x*cO - y*ci*sO, x*sO + y*ci*cO, y*si])
        vel = np.array([vx*cO - vy*ci*sO, vx*sO + vy*ci*cO, vy*si])
        if not inertial:
            vel[0] += OMEGA_E*pos[1]; vel[1] -= OMEGA_E*pos[0]
        return pos, vel, self.clock(t_em, self.e*sin_E)

    def ecef(self, t_em): return self._to_frame(t_em, inertial=False)
    def eci(self,  t_em): return self._to_frame(t_em, inertial=True)

    @staticmethod
    def sagnac(pos, vel, t_tr):
        a  = OMEGA_E * t_tr
        ca, sa = np.cos(a), np.sin(a)
        A  = np.array([[ca, sa, 0], [-sa, ca, 0], [0, 0, 1]])
        return A @ pos, (A @ vel if vel is not None else None)