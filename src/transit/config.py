from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW, INTERIM, PROCESSED = DATA / "raw", DATA / "interim", DATA / "processed"

# İBB Açık Veri Portalı (CKAN). Dataset: "Saatlik Toplu Ulaşım Veri Seti"
CKAN_BASE = "https://data.ibb.gov.tr/api/3/action"
DATASET_ID = "hourly-public-transport-data-set"

# Istanbul city centre, used for hourly weather (Open-Meteo, no API key needed)
LAT, LON = 41.01, 28.97
TIMEZONE = "Europe/Istanbul"

TRANSPORT_TYPES = {1: "road", 2: "rail", 3: "sea"}
