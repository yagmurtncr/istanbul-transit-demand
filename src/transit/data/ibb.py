"""Download hourly public transport CSVs from the İBB open data portal (CKAN API)."""
from __future__ import annotations

import time
from pathlib import Path

import requests

from transit.config import CKAN_BASE, DATASET_ID, RAW

HEADERS = {"User-Agent": "istanbul-transit-demand/0.1 (research project)"}


def _get(url: str, retries: int = 4, **kw) -> requests.Response:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def list_resources(dataset_id: str = DATASET_ID) -> list[dict]:
    """Return the dataset's CSV resources (one per month) as name/url/format dicts."""
    r = _get(f"{CKAN_BASE}/package_show", params={"id": dataset_id})
    res = r.json()["result"]["resources"]
    return [
        {"name": x.get("name", ""), "url": x["url"], "format": (x.get("format") or "").lower(), "size": x.get("size") or 0}
        for x in res
        if ((x.get("format") or "").lower() == "csv" or x["url"].lower().endswith(".csv"))
        # Kasım-Aralık 2024 dosyaları boş (187 bayt) yayımlanmış: 1 MB altını atla
        and (x.get("size") or 0) > 1_000_000
    ]


def download(resources: list[dict], out_dir: Path = RAW, overwrite: bool = False) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for res in resources:
        path = out_dir / Path(res["url"]).name
        if path.exists() and not overwrite:
            paths.append(path)
            continue
        with _get(res["url"], stream=True) as r, open(path, "wb") as f:
            f.writelines(r.iter_content(1 << 20))
        paths.append(path)
        print(f"downloaded {path.name}")
    return paths
