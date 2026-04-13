import os
import re
import gzip
from datetime import datetime, timedelta
import requests
import hatanaka
from utils import write_logs, read_config

CD_CONFIG = "config.json"

(
    OBS_LON,
    OBS_LAT,
    OBS_ALT,
    TIMEZONE_UTC,
    DAYS_BACK,
    OUTPUT_DIR,
    TIMEOUT_LISTING,
    TIMEOUT_FILE,
    LOG_FILE,
    STATIONS
) = read_config(CD_CONFIG)


def try_download(station, date, doy, year):
    base_url = f"https://igs.bkg.bund.de/root_ftp/IGS/obs/{year}/{doy:03d}/"
    write_logs(LOG_FILE, f"  listing url: {base_url}\n")

    try:
        r = requests.get(base_url, timeout=TIMEOUT_LISTING)
        r.raise_for_status()
        write_logs(LOG_FILE, f"  listing response: {r.status_code} ok\n")
    except requests.RequestException as e:
        write_logs(LOG_FILE, f"  listing failed: {e}\n")
        return False

    pattern = rf'href="({station.upper()[:4]}\w+\.(?:crx|rnx)\.gz)"'
    match   = re.search(pattern, r.text, re.IGNORECASE)

    if not match:
        write_logs(LOG_FILE, f"  no files found for {station}\n")
        return False

    filename = match.group(1)
    file_url = base_url + filename
    write_logs(LOG_FILE, f"  file found: {filename}\n")
    write_logs(LOG_FILE, f"  download url: {file_url}\n")

    try:
        r = requests.get(file_url, timeout=TIMEOUT_FILE)
        r.raise_for_status()
        write_logs(LOG_FILE, f"  download: {r.status_code} ok | size: {len(r.content):,} bytes\n")
    except requests.RequestException as e:
        write_logs(LOG_FILE, f"  download failed: {e}\n")
        return False

    try:
        data = gzip.decompress(r.content)
        write_logs(LOG_FILE, f"  gzip decompressed: {len(data):,} bytes\n")
    except OSError as e:
        write_logs(LOG_FILE, f"  gzip failed: {e}\n")
        return False

    if filename.endswith(".crx.gz"):
        try:
            data = hatanaka.decompress(data)
            write_logs(LOG_FILE, f"  hatanaka decoded: {len(data):,} bytes\n")
        except Exception as e:
            write_logs(LOG_FILE, f"  hatanaka failed: {e}\n")
            return False

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_name = re.sub(r"\.(crx|rnx)\.gz$", ".txt", filename)
    out_path = os.path.join(OUTPUT_DIR, out_name)

    with open(out_path, "wb") as f:
        f.write(data)

    write_logs(LOG_FILE, f"  saved: {out_path}\n")
    return True


def main():
    os.makedirs("logs", exist_ok=True)

    date = datetime.utcnow() - timedelta(days=DAYS_BACK)
    doy  = date.timetuple().tm_yday
    year = date.year

    write_logs(LOG_FILE, f"date: {date:%Y-%m-%d} | doy: {doy}\n", update=False)
    write_logs(LOG_FILE, f"stations to try: {', '.join(STATIONS)}\n")
    write_logs(LOG_FILE, "-" * 40 + "\n")

    for station in STATIONS:
        write_logs(LOG_FILE, f"trying station: {station}\n")

        success = try_download(station, date, doy, year)

        if success:
            write_logs(LOG_FILE, f"result: ok | station used: {station}\n")
            return

        write_logs(LOG_FILE, f"station {station} failed, trying next\n")
        write_logs(LOG_FILE, "-" * 40 + "\n")

    write_logs(LOG_FILE, "result: all stations failed\n")


if __name__ == "__main__":
    main()