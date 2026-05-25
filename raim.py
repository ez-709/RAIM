import numpy as np
from scipy.stats import norm as sp_norm
from navigation_solution import ned_rotation


def raim_epoch(sol, p_fd=0.002/3600.0, p_md=0.001, HAL=550):
    G, res, r_u, sigma_pr = sol['G'], sol['residuals'], sol['r_u'], sol['sigma_pr']
    N = G.shape[0]
    if N < 5:
        return None

    R3 = ned_rotation(r_u)
    R4 = np.eye(4)
    R4[:3, :3] = R3
    S0 = np.linalg.pinv(G)

    Sigma_pr = sigma_pr**2 * np.eye(N)

    dn_list, Dn_list, an_list = [], [], []
    for n in range(N):
        mask_n = np.ones(N, dtype=bool)
        mask_n[n] = False
        Sn_sub = np.linalg.pinv(G[mask_n])
        Sn = np.zeros((4, N))
        Sn[:, mask_n] = Sn_sub

        sep = R3 @ ((S0 - Sn)[:3] @ res)
        dn_list.append(float(np.linalg.norm(sep[:2])))

        dS = S0 - Sn
        dPn_h = (R4 @ dS @ Sigma_pr @ dS.T @ R4.T)[:2, :2]
        Pn_h = (R4 @ Sn @ Sigma_pr @ Sn.T @ R4.T)[:2, :2]

        lam_dP = float(np.max(np.linalg.eigvalsh(dPn_h)))
        lam_P = float(np.max(np.linalg.eigvalsh(Pn_h)))

        Dn_list.append(float(np.sqrt(max(lam_dP, 0.0)) * sp_norm.isf(p_fd / (2.0 * N))))
        an_list.append(float(np.sqrt(max(lam_P, 0.0)) * sp_norm.isf(p_md)))

    dn, Dn, an = map(np.array, (dn_list, Dn_list, an_list))
    HPL = float(np.max(Dn + an))
    fault_detected = bool(np.any(dn > Dn))
    worst = int(np.argmax(dn - Dn))

    return dict(HPL=HPL, HAL=HAL, available=HPL <= HAL,
                fault_detected=fault_detected,
                fault_prn=sol['prns'][worst] if fault_detected else None,
                dn=dn, Dn=Dn, an=an)