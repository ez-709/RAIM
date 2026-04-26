import numpy as np

MU        = 3.986005e14
OMEGA_E   = 7.2921151467e-5
C         = 299792458.0
WEEK      = 604800.0
HALF_WEEK = 302400.0


class GPSSatellite:
    def __init__(self, prn, toe, toc,
                 sqrt_a, e, i_0, Omega_0, omega, M_0,
                 dn, Omega_dot, i_dot,
                 C_uc, C_us, C_rc, C_rs, C_ic, C_is,
                 alpha_0, alpha_1, alpha_2,
                 T_gd=0.0, week=0):

        self.prn = prn
        self.toe = toe
        self.toc = toc
        self.e         = e
        self.i_0       = i_0
        self.Omega_0   = Omega_0
        self.omega     = omega
        self.M_0       = M_0
        self.dn        = dn
        self.Omega_dot = Omega_dot
        self.i_dot     = i_dot
        self.C_uc = C_uc; self.C_us = C_us
        self.C_rc = C_rc; self.C_rs = C_rs
        self.C_ic = C_ic; self.C_is = C_is
        self.alpha_0 = alpha_0
        self.alpha_1 = alpha_1
        self.alpha_2 = alpha_2
        self.T_gd = T_gd
        self.week = week

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
            if abs(E_new - E) < 1e-12:
                break
            E = E_new
        return E_new

    def orbital(self, t_em):
        e = self.e

        t_star = self.wrap(t_em - self.toe)

        M = self.M_0 + self.n * t_star

        E      = self.kepler(M)
        sin_E  = np.sin(E)
        cos_E  = np.cos(E)
        d      = 1.0 - e * cos_E

        sin_f  = np.sqrt(1.0 - e ** 2) * sin_E / d
        cos_f  = (cos_E - e) / d
        f      = np.arctan2(sin_f, cos_f)

        phi      = f + self.omega
        sin_2phi = np.sin(2.0 * phi)
        cos_2phi = np.cos(2.0 * phi)

        u   = phi + self.C_us * sin_2phi + self.C_uc * cos_2phi
        r   = self.a * d + self.C_rs * sin_2phi + self.C_rc * cos_2phi
        i_k = self.i_0 + self.C_is * sin_2phi + self.C_ic * cos_2phi + self.i_dot * t_star

        cos_u = np.cos(u); sin_u = np.sin(u)
        x = r * cos_u
        y = r * sin_u

        sq  = np.sqrt(MU / self.p)
        v_r = sq * e * sin_f
        v_u = sq * (1.0 + e * cos_f)

        vx = v_r * cos_u - v_u * sin_u
        vy = v_r * sin_u + v_u * cos_u

        return t_star, sin_E, x, y, vx, vy, i_k

    def clock(self, t_em, e_sin_E):
        dt    = self.wrap(t_em - self.toc)
        trend = self.alpha_0 + self.alpha_1 * dt + self.alpha_2 * dt ** 2
        T_rel = -2.0 * np.sqrt(MU * self.a) / C ** 2 * e_sin_E
        return trend + T_rel - self.T_gd

    def ecef(self, t_em):
        t_star, sin_E, x, y, vx, vy, i_k = self.orbital(t_em)

        Omega_k = self.Omega_0 + (self.Omega_dot - OMEGA_E) * t_star - OMEGA_E * self.toe

        cos_O = np.cos(Omega_k); sin_O = np.sin(Omega_k)
        cos_i = np.cos(i_k);     sin_i = np.sin(i_k)

        pos = np.array([
            x * cos_O - y * cos_i * sin_O,
            x * sin_O + y * cos_i * cos_O,
            y * sin_i,
        ])
        vel = np.array([
            vx * cos_O - vy * cos_i * sin_O,
            vx * sin_O + vy * cos_i * cos_O,
            vy * sin_i,
        ])
        vel[0] += OMEGA_E * pos[1]
        vel[1] -= OMEGA_E * pos[0]

        return pos, vel, self.clock(t_em, self.e * sin_E)

    def eci(self, t_em):
        t_star, sin_E, x, y, vx, vy, i_k = self.orbital(t_em)

        Omega_k = self.Omega_0 + self.Omega_dot * t_star

        cos_O = np.cos(Omega_k); sin_O = np.sin(Omega_k)
        cos_i = np.cos(i_k);     sin_i = np.sin(i_k)

        pos = np.array([
            x * cos_O - y * cos_i * sin_O,
            x * sin_O + y * cos_i * cos_O,
            y * sin_i,
        ])
        vel = np.array([
            vx * cos_O - vy * cos_i * sin_O,
            vx * sin_O + vy * cos_i * cos_O,
            vy * sin_i,
        ])

        return pos, vel, self.clock(t_em, self.e * sin_E)

    def sagnac(pos, vel, t_tr):
        a  = OMEGA_E * t_tr
        ca = np.cos(a); sa = np.sin(a)
        A  = np.array([[ca, sa, 0.0], [-sa, ca, 0.0], [0.0, 0.0, 1.0]])
        return A @ pos, (A @ vel if vel is not None else None)