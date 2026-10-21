"""Small download helper: saves a URL into data/raw/ and logs it in data/raw/manifest.csv."""
import csv
import datetime as dt
import pathlib
import sys

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.csv"


def fetch(url, name=None, force=False, **kwargs):
    """Download url to data/raw/<name> unless it is already there. Returns the path."""
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / (name or url.rstrip("/").split("/")[-1].split("?")[0])
    if path.exists() and not force:
        return path
    print(f"downloading {url}", file=sys.stderr)
    with requests.get(url, stream=True, timeout=300, **kwargs) as r:
        r.raise_for_status()
        tmp = path.with_suffix(path.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(path)
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["file", "url", "pulled_utc"])
        w.writerow([path.name, url, dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")])
    return path


if __name__ == "__main__":
    for u in sys.argv[1:]:
        print(fetch(u))
