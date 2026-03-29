def _parse_float(s: str) -> float:
    return float(s.replace('D', 'E').replace('d', 'e'))


def parse_glonass_rinex(text: str) -> list[dict]:
    lines = text.splitlines()

    data_start = 0
    for i, line in enumerate(lines):
        if 'END OF HEADER' in line:
            data_start = i + 1
            break

    records = []
    i = data_start

    while i + 3 < len(lines):
        l0 = lines[i]
        try:
            prn        = int(l0[0:2])
            year       = int(l0[3:5])
            month      = int(l0[6:8])
            day        = int(l0[9:11])
            hour       = int(l0[12:14])
            minute     = int(l0[15:17])
            clock_bias = _parse_float(l0[22:41])
            freq_drift = _parse_float(l0[41:60])

            year = 2000 + year if year < 80 else 1900 + year

            def row(line):
                return [_parse_float(line[3 + j*19: 3 + (j+1)*19]) for j in range(4)]

            r2 = row(lines[i + 1])
            r3 = row(lines[i + 2])
            r4 = row(lines[i + 3])

            records.append({
                'prn'       : prn,
                'epoch'     : f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}",
                'clock_bias': clock_bias,
                'freq_drift': freq_drift,
                'x' : r2[0], 'vx': r2[1], 'ax': r2[2], 'health'  : int(r2[3]),
                'y' : r3[0], 'vy': r3[1], 'ay': r3[2], 'freq_num': int(r3[3]),
                'z' : r4[0], 'vz': r4[1], 'az': r4[2], 'age'     : r4[3],
            })
        except Exception:
            pass

        i += 4

    print(f"[OK] {len(records)} записей, {len(set(r['prn'] for r in records))} спутников")
    return records


def get_latest_positions(records: list[dict]) -> list[dict]:
    latest = {}
    for r in records:
        if r['health'] != 0:
            continue
        latest[r['prn']] = r
    return list(latest.values())
