import os
import requests
from datetime import datetime, timedelta, timezone


def get_glonass_rinex_url(dt: datetime = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc) - timedelta(days=1)
    doy  = dt.timetuple().tm_yday
    year = dt.year
    yy   = str(year)[2:]
    return (
        f"https://igs.bkg.bund.de/root_ftp/NTRIP/BRDC/"
        f"{year}/{doy:03d}/brdc{doy:03d}0.{yy}g"
    )


def fetch_or_cache(url: str, cache_dir: str = "data/cache") -> str | None:
    os.makedirs(cache_dir, exist_ok=True)

    filename   = url.split("/")[-1]
    cache_path = os.path.join(cache_dir, filename)

    if os.path.exists(cache_path):
        print(f"[CACHE] {filename}")
        with open(cache_path, "r") as f:
            return f.read()

    print(f"[HTTP] {url}")
    headers = {"User-Agent": "GNSSLab/1.0"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            with open(cache_path, "w") as f:
                f.write(r.text)
            print(f"[OK] {cache_path}")
            return r.text
        else:
            print(f"[ERR] HTTP {r.status_code}")
    except Exception as e:
        print(f"[ERR] {e}")

    cached = [f for f in os.listdir(cache_dir) if f.endswith(".g") or f.endswith(".20g")]
    if cached:
        fallback = os.path.join(cache_dir, cached[-1])
        print(f"[LOCAL] {fallback}")
        with open(fallback, "r") as f:
            return f.read()

    return None
