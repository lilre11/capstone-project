"""Fetch phone images for the seed JSON.

Strategy (tiered):
  1. Try GSMArena bigpic CDN (direct URL construction, verified endpoints)
  2. Fallback to Wikipedia REST API with high-res upgrade
  3. Leave empty if both fail (frontend shows gradient fallback)

Usage:
    python tools/fetch_phone_images.py          # skip existing
    python tools/fetch_phone_images.py --force   # re-fetch all
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_SEED_FILE = Path(__file__).resolve().parents[1] / "src" / "data" / "smartphones_seed.json"
_UA = "SmartPickAI/1.0 (capstone project; academic use)"


# -- GSMArena bigpic CDN -- explicit verified slugs ----------------------------

_GSM_BASE = "https://fdn2.gsmarena.com/vv/bigpic"

_GSMARENA_SLUGS: dict[str, str | None] = {
    "apple_iphone_17_pm": "apple-iphone-17-pro-max",
    "samsung_s25_ultra": None,
    "oppo_find_x9_pro": "oppo-find-x9-pro",
    "samsung_galaxy_z_fold_7": "samsung-galaxy-z-fold7",
    "asus_rog_phone_9_pro": "asus-rog-phone-9-pro",
    "oneplus_13": "oneplus-13",
    "xiaomi_15t": "xiaomi-15t",
    "apple_iphone_16e": "apple-iphone-16e",
    "samsung_galaxy_a56_5g": None,
    "nothing_cmf_phone_2_pro": "nothing-cmf-phone-2-pro",
}


def _try_gsmarena(phone_id: str) -> str | None:
    slug = _GSMARENA_SLUGS.get(phone_id)
    if slug is None:
        return None
    url = f"{_GSM_BASE}/{slug}.jpg"
    try:
        resp = requests.head(url, timeout=8)
        if resp.status_code == 200:
            return url
    except requests.RequestException:
        pass
    return None


# -- Wikipedia REST API --------------------------------------------------------


def _upgrade_wikipedia_resolution(url: str, target_px: int = 500) -> str:
    return re.sub(r"/\d+px-", f"/{target_px}px-", url)


def _search_wikipedia(query: str) -> str | None:
    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(query)}",
            headers={"User-Agent": _UA},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            thumb = data.get("thumbnail")
            if thumb and thumb.get("source"):
                return _upgrade_wikipedia_resolution(thumb["source"], 500)
    except requests.RequestException:
        pass
    return None


def _try_wikipedia(brand: str, model: str) -> str | None:
    queries = [
        f"{brand} {model}",
        model,
        f"{brand} {model} (smartphone)",
    ]
    for query in queries:
        url = _search_wikipedia(query)
        if url:
            return url
        time.sleep(0.3)
    return None


# -- Main ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch phone images for seed JSON")
    parser.add_argument("--force", action="store_true", help="Re-fetch all, even existing")
    args = parser.parse_args()

    if not _SEED_FILE.exists():
        logger.error("Seed file not found: %s", _SEED_FILE)
        sys.exit(1)

    data = json.loads(_SEED_FILE.read_text(encoding="utf-8"))
    updated = 0
    skipped = 0
    failed = 0

    for phone in data:
        phone_id = phone["id"]
        brand = phone["brand"]
        model = phone["model_name"]

        if phone.get("image_url") and not args.force:
            logger.info("SKIP  %s - already has image_url", phone_id)
            skipped += 1
            continue

        image_url = None

        # Tier 1: GSMArena CDN
        image_url = _try_gsmarena(phone_id)
        if image_url:
            logger.info("GSM   %s OK", phone_id)

        # Tier 2: Wikipedia
        if not image_url:
            logger.info("WIKI  %s - trying Wikipedia...", phone_id)
            image_url = _try_wikipedia(brand, model)
            if image_url:
                logger.info("WIKI  %s OK (500px)", phone_id)

        if image_url:
            phone["image_url"] = image_url
            updated += 1
        else:
            logger.warning("MISS  %s - no image found anywhere", phone_id)
            failed += 1

        time.sleep(0.5)

    _SEED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Done. Updated: %d, Skipped: %d, Failed: %d", updated, skipped, failed)


if __name__ == "__main__":
    main()
