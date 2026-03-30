import csv
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class GPSEphemeris:
    prn: Optional[int] = None
    
    toc: float = 0.0
    af0: float = 0.0
    af1: float = 0.0
    af2: float = 0.0
    
    toe: float = 0.0
    sqrtA: float = 0.0
    e: float = 0.0
    M0: float = 0.0
    delta_n: float = 0.0
    Omega0: float = 0.0
    i0: float = 0.0
    omega: float = 0.0
    Omega_dot: float = 0.0
    i_dot: float = 0.0
    
    cuc: float = 0.0
    cus: float = 0.0
    crc: float = 0.0
    crs: float = 0.0
    cic: float = 0.0
    cis: float = 0.0

    def calculate_position(self, t: float) -> Dict[str, float]:
        """
        Заглушка для расчета координат.
        Реализуйте алгоритм IS-GPS-200 / ESA Navipedia здесь.
        """
        raise NotImplementedError("Алгоритм расчета не реализован")

def parse_ephemeris_csv(filename: str) -> GPSEphemeris:
    eph = GPSEphemeris()
    found_params = set()
    required_params = {
        'toc_af0_af1_af2', 'toe_sqra_deln_m0', 'e_omega_cus_cuc',
        'crc_crs_cic_cis', 'i0_idot_omg0_omgdot'
    }

    with open(filename, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Пропуск заголовка
        
        for row in reader:
            if len(row) < 5:
                continue
                
            section, param = row[0], row[1]
            values = [float(v) for v in row[2:6]]

            if section != 'floating_point_clock_ephemeris':
                continue

            if param == 'toc_af0_af1_af2':
                eph.toc, eph.af0, eph.af1, eph.af2 = values
                found_params.add(param)
                
            elif param == 'toe_sqra_deln_m0':
                eph.toe, eph.sqrtA, eph.delta_n, eph.M0 = values
                found_params.add(param)
                
            elif param == 'e_omega_cus_cuc':
                eph.e, eph.omega, eph.cus, eph.cuc = values
                found_params.add(param)
                
            elif param == 'crc_crs_cic_cis':
                eph.crc, eph.crs, eph.cic, eph.cis = values
                found_params.add(param)
                
            elif param == 'i0_idot_omg0_omgdot':
                eph.i0, eph.i_dot, eph.Omega0, eph.Omega_dot = values
                found_params.add(param)

    missing = required_params - found_params
    if missing:
        raise ValueError(f"Отсутствуют параметры в CSV: {missing}")


    eph.prn = None 

    return eph

if __name__ == "__main__":
    try:
        eph = parse_ephemeris_csv('ephemeris.csv')
        print(f"Данные загружены для PRN: {eph.prn}")
        print(f"TOE: {eph.toe}, SQRT_A: {eph.sqrtA}")
        # coords = eph.calculate_position(t=496800)
    except Exception as e:
        print(f"Ошибка: {e}")