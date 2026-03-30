import numpy as np
import csv

def matrix_of_direction_cos(psi=0, gamma=0, theta=0):
    matrix = np.eye(3) 

    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(psi), -np.sin(psi)],
        [0, np.sin(psi), np.cos(psi)]
    ])
    matrix = np.dot(matrix, Rx)

    Ry = np.array([
        [np.cos(gamma), 0, np.sin(gamma)],
        [0, 1, 0],
        [-np.sin(gamma), 0, np.cos(gamma)]
    ])
    matrix = np.dot(matrix, Ry)

    Rz = np.array([
        [np.cos(theta), -np.sin(theta), 0],
        [np.sin(theta), np.cos(theta), 0],
        [0, 0, 1]
    ])
    matrix = np.dot(matrix, Rz)
    
    return matrix


MU = 3.986005e14
OMEGA_E = 7.2921151467e-5
WEEK_SEC = 604800

def calculate_position_in_ECI_GPS(t, eph):
    tk = t - eph['toe']
    if tk > 302400:
        tk = tk - WEEK_SEC
    if tk < -302400:
        tk = tk + WEEK_SEC

    A = eph['sqrtA'] ** 2
    n0 = np.sqrt(MU / (A ** 3))

    n = n0 + eph['delta_n']

    Mk = eph['M0'] + n * tk

    Ek = Mk
    for _ in range(10):
        f = Ek - eph['e'] * np.sin(Ek) - Mk
        fp = 1 - eph['e'] * np.cos(Ek)
        Ek = Ek - f / fp
        if abs(f) < 1e-12:
            break

    sin_Ek_2 = np.sin(Ek / 2)
    cos_Ek_2 = np.cos(Ek / 2)
    sin_vk = (np.sqrt(1 - eph['e'] ** 2) * sin_Ek_2 * cos_Ek_2 * 2) / (1 - eph['e'] * np.cos(Ek))
    cos_vk = (np.cos(Ek) - eph['e']) / (1 - eph['e'] * np.cos(Ek))
    vk = np.arctan2(sin_vk, cos_vk)

    Phi = eph['omega'] + vk

    duk = eph['cuc'] * np.cos(2 * Phi) + eph['cus'] * np.sin(2 * Phi)
    drk = eph['crc'] * np.cos(2 * Phi) + eph['crs'] * np.sin(2 * Phi)
    dik = eph['cic'] * np.cos(2 * Phi) + eph['cis'] * np.sin(2 * Phi)

    uk = Phi + duk

    rk = A * (1 - eph['e'] * np.cos(Ek)) + drk

    ik = eph['i0'] + eph['i_dot'] * tk + dik
    Omegak = eph['Omega0'] + (eph['Omega_dot'] - OMEGA_E) * tk - OMEGA_E * eph['toe']

    xp = rk * np.cos(uk)
    yp = rk * np.sin(uk)

    X = xp * np.cos(Omegak) - yp * np.cos(ik) * np.sin(Omegak)
    Y = xp * np.sin(Omegak) + yp * np.cos(ik) * np.cos(Omegak)
    Z = yp * np.sin(ik)
    
    return {'X': X, 'Y': Y, 'Z': Z}

def make_csv_of_ECI_from_t_points(t_points, eph, output_dir='output'):
    import csv
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    
    toe = int(eph['toe'])
    filename = f"sat_pos_toe_{toe}.csv"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'X', 'Y', 'Z'])
        
        for t in t_points:
            pos = calculate_position_in_ECI_GPS(t, eph)
            writer.writerow([t, pos['X'], pos['Y'], pos['Z']])
    
    return filepath