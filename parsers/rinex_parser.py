from datetime import datetime
from types import SimpleNamespace

GPS_EPOCH = datetime(1980, 1, 6)

RECORD_LINES = {
    'G': 8, 'J': 8, 'C': 8, 'E': 8, 'I': 8,
    'R': 4, 'S': 4,
}


def parse_float(s):
    return float(s.replace('D', 'E').replace('d', 'e'))


def tow(year, month, day, hour, minute, second):
    if year < 80:
        year += 2000
    elif year < 100:
        year += 1900
    dt  = datetime(year, month, day, hour, minute, int(second))
    dow = (dt - GPS_EPOCH).days % 7
    return dow * 86400 + hour * 3600 + minute * 60 + second


def values(line, offset, n=4, width=19):
    out = []
    for k in range(n):
        s = line[offset + k * width: offset + (k + 1) * width].strip()
        out.append(parse_float(s) if s else 0.0)
    return out


def parse_rinex_nav(path):
    with open(path, 'r') as f:
        lines = f.readlines()

    version    = 2
    header_end = 0
    for k, line in enumerate(lines):
        if 'RINEX VERSION' in line:
            version = int(float(line[:9].strip()))
        if 'END OF HEADER' in line:
            header_end = k + 1
            break

    rec = lines[header_end:]
    out = []
    i   = 0

    while i < len(rec):
        line = rec[i]
        if not line.strip():
            i += 1
            continue

        try:
            if version >= 3:
                sys_id  = line[0]
                n_lines = RECORD_LINES.get(sys_id, 8)
                if sys_id != 'G':
                    i += n_lines
                    continue
                prn    = int(line[1:3])
                year   = int(line[4:8])
                month  = int(line[9:11])
                day    = int(line[12:14])
                hour   = int(line[15:17])
                minute = int(line[18:20])
                second = float(line[21:23])
                clk    = values(line, 23, n=3)
                offset = 4
            else:
                prn    = int(line[0:2])
                year   = int(line[2:5])
                month  = int(line[5:8])
                day    = int(line[8:11])
                hour   = int(line[11:14])
                minute = int(line[14:17])
                second = float(line[17:22])
                clk    = values(line, 22, n=3)
                offset = 3
        except (ValueError, IndexError):
            i += 1
            continue

        rows = [values(rec[i + k], offset) for k in range(1, 8)]

        _, Crs, dn, M0            = rows[0]
        Cuc, e, Cus, sqrt_a       = rows[1]
        toe, Cic, Omega0, Cis     = rows[2]
        i0, Crc, omega, Omega_dot = rows[3]
        i_dot                     = rows[4][0]
        gps_week                  = int(rows[4][2]) if rows[4][2] else 0
        sv_health                 = int(rows[5][1])
        T_gd                      = rows[5][2]

        if sv_health == 0:
            out.append(SimpleNamespace(
                prn       = prn,
                toe       = toe,
                toc       = tow(year, month, day, hour, minute, second),
                sqrt_a    = sqrt_a,
                e         = e,
                i_0       = i0,
                Omega_0   = Omega0,
                omega     = omega,
                M_0       = M0,
                dn        = dn,
                Omega_dot = Omega_dot,
                i_dot     = i_dot,
                C_uc      = Cuc, C_us = Cus,
                C_rc      = Crc, C_rs = Crs,
                C_ic      = Cic, C_is = Cis,
                alpha_0   = clk[0],
                alpha_1   = clk[1],
                alpha_2   = clk[2],
                T_gd      = T_gd,
                week      = gps_week,
            ))

        i += 8

    return out