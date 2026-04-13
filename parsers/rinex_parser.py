from datetime import datetime
from math_model import Ephemeris

GPS_EPOCH = datetime(1980, 1, 6)


def _float(s):
    return float(s.replace('D', 'E').replace('d', 'e'))


def _tow(year, month, day, hour, minute, second):
    if year < 80:
        year += 2000
    elif year < 100:
        year += 1900
    dt = datetime(year, month, day, hour, minute, int(second))
    delta = (dt - GPS_EPOCH).days
    dow = delta % 7
    return dow * 86400 + hour * 3600 + minute * 60 + second


def _values(line, offset, width=19):
    vals = []
    i = offset
    while i + width <= len(line):
        s = line[i:i + width].strip()
        if s:
            vals.append(_float(s))
        i += width
    return vals


def parse_rinex_nav(path):
    with open(path, 'r') as f:
        lines = f.readlines()

    version = 2
    header_end = 0
    for i, line in enumerate(lines):
        if 'RINEX VERSION' in line:
            version = int(float(line[:9].strip()))
        if 'END OF HEADER' in line:
            header_end = i + 1
            break

    records = lines[header_end:]
    ephemerides = []

    i = 0
    while i < len(records):
        line = records[i]
        if not line.strip():
            i += 1
            continue

        if version >= 3:
            sys_id = line[0]
            if sys_id not in ('G', ' '):
                i += 8
                continue
            prn = int(line[1:3])
            year = int(line[4:8])
            month = int(line[9:11])
            day = int(line[12:14])
            hour = int(line[15:17])
            minute = int(line[18:20])
            second = float(line[21:23])
            clk_vals = _values(line, 23)
            data_offset = 4
        else:
            prn = int(line[0:2])
            year = int(line[2:5])
            month = int(line[5:8])
            day = int(line[8:11])
            hour = int(line[11:14])
            minute = int(line[14:17])
            second = float(line[17:22])
            clk_vals = _values(line, 22)
            data_offset = 3

        while len(clk_vals) < 3:
            clk_vals.append(0.0)
        af0, af1, af2 = clk_vals[0], clk_vals[1], clk_vals[2]

        toc = _tow(year, month, day, hour, minute, second)

        data = []
        for j in range(1, 8):
            if i + j < len(records):
                data.extend(_values(records[i + j], data_offset))
        while len(data) < 28:
            data.append(0.0)

        week = int(data[18]) if data[18] != 0 else 0
        health = int(data[21])

        if health == 0:
            ephemerides.append(Ephemeris(
                prn=prn,
                toe=data[8],
                toc=toc,
                sqrt_a=data[7],
                eccentricity=data[5],
                inclination=data[12],
                ascending_node=data[10],
                perigee=data[14],
                mean_anomaly=data[3],
                mean_motion_corr=data[2],
                ascending_node_rate=data[15],
                inclination_rate=data[16],
                cuc=data[4],
                cus=data[6],
                crc=data[13],
                crs=data[1],
                cic=data[9],
                cis=data[11],
                clock_bias=af0,
                clock_drift=af1,
                clock_drift_rate=af2,
                group_delay=data[22],
                week=week,
            ))

        i += 8

    return ephemerides