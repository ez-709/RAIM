from datetime import datetime
from types import SimpleNamespace

GPS_EPOCH = datetime(1980, 1, 6)
RECORD_LINES = {
    'G': 8, 'J': 8, 'C': 8, 'E': 8, 'I': 8,
    'R': 4, 'S': 4,
}


def parse_float(s):
    s = s.strip()
    return float(s.replace('D', 'E').replace('d', 'e')) if s else 0.0


def tow(year, month, day, hour, minute, second):
    if year < 80:
        year += 2000
    elif year < 100:
        year += 1900
    dt  = datetime(year, month, day, hour, minute, int(second))
    dow = (dt - GPS_EPOCH).days % 7
    return dow * 86400 + hour * 3600 + minute * 60 + second


def values(line, offset, n=4, width=19):
    return [parse_float(line[offset + k * width: offset + (k + 1) * width])
            for k in range(n)]


def find_header_end(lines):
    for k, line in enumerate(lines):
        if 'END OF HEADER' in line:
            return k + 1
    return 0


def get_approx_position(path):
    """Эталонные координаты станции из шапки .obs (APPROX POSITION XYZ)."""
    with open(path, 'r') as f:
        for line in f:
            if 'APPROX POSITION XYZ' in line:
                return [parse_float(line[k * 14:(k + 1) * 14]) for k in range(3)]
            if 'END OF HEADER' in line:
                break
    return None


def parse_rinex_nav(path):
    with open(path, 'r') as f:
        lines = f.readlines()

    version = 2
    for line in lines:
        if 'RINEX VERSION' in line:
            version = int(float(line[:9].strip()))
            break

    rec = lines[find_header_end(lines):]
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


def parse_rinex_obs(path):
    with open(path, 'r') as f:
        lines = f.readlines()

    gps_types = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line[60:].strip() == 'SYS / # / OBS TYPES' and line[0] == 'G':
            n     = int(line[3:6])
            gps_types = line[7:60].split()
            for k in range((n - 1) // 13):
                gps_types += lines[i + 1 + k][7:60].split()
            break
        if 'END OF HEADER' in line:
            break
        i += 1

    if 'C1C' not in gps_types:
        return []

    c1_idx     = gps_types.index('C1C')
    header_end = find_header_end(lines)

    out = []
    i = header_end
    while i < len(lines):
        line = lines[i]
        if not line.startswith('>'):
            i += 1
            continue

        try:
            year   = int(line[2:6])
            month  = int(line[7:9])
            day    = int(line[10:12])
            hour   = int(line[13:15])
            minute = int(line[16:18])
            second = float(line[19:29])
            n_sat  = int(line[32:35])
        except (ValueError, IndexError):
            i += 1
            continue

        sats = {}
        for k in range(n_sat):
            row = lines[i + 1 + k]
            if row[0] != 'G':
                continue
            try:
                prn = int(row[1:3])
                off = 3 + c1_idx * 16
                c1  = parse_float(row[off:off + 14])
                if c1 > 0:
                    sats[prn] = c1
            except (ValueError, IndexError):
                continue

        out.append(SimpleNamespace(
            time = datetime(year, month, day, hour, minute, int(second)),
            tow  = tow(year, month, day, hour, minute, second),
            sats = sats,
        ))
        i += 1 + n_sat

    return out
