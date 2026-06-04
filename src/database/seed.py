"""Seed the database with smartphone specifications and criteria definitions.

Run directly:  ``python -m src.database.seed``
Or call ``seed_database(session)`` programmatically.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.database.models import Criterion, Smartphone, SmartphoneSpec

logger = logging.getLogger(__name__)

_SEED_FILE = Path(__file__).resolve().parents[2] / "src" / "data" / "smartphones_seed.json"

# Criteria definitions
CRITERIA_DEFINITIONS: List[Dict[str, str]] = [
    {"id": "price", "name": "Price", "direction": "min", "unit": "TRY"},
    {"id": "battery", "name": "Battery", "direction": "max", "unit": "mAh"},
    {"id": "camera_score", "name": "Camera Score", "direction": "max", "unit": "points"},
    {"id": "antutu", "name": "AnTuTu Score", "direction": "max", "unit": "points"},
    {"id": "storage", "name": "Storage", "direction": "max", "unit": "GB"},
    {"id": "weight", "name": "Weight", "direction": "min", "unit": "g"},
    {"id": "charging", "name": "Charging Speed", "direction": "max", "unit": "W"},
    {"id": "screen_ratio", "name": "Screen-to-Body Ratio", "direction": "max", "unit": "ratio"},
]

# Mapping from seed JSON keys → criterion IDs
_SPEC_KEY_TO_CRITERION: Dict[str, str] = {
    "price": "price",
    "battery_mah": "battery",
    "camera_score": "camera_score",
    "antutu_score": "antutu",
    "storage_gb": "storage",
    "weight_g": "weight",
    "charging_watts": "charging",
    "screen_ratio": "screen_ratio",
}


def _load_seed_data(path: Path | None = None) -> List[Dict[str, Any]]:
    """Load smartphone seed data from JSON file."""
    file_path = path or _SEED_FILE
    if not file_path.exists():
        raise FileNotFoundError(f"Seed file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_criteria(db: Session) -> None:
    """Insert criteria definitions (idempotent)."""
    for crit_def in CRITERIA_DEFINITIONS:
        existing = db.query(Criterion).filter_by(id=crit_def["id"]).first()
        if existing is None:
            db.add(Criterion(**crit_def))
    db.commit()
    logger.info("Criteria seeded: %d definitions", len(CRITERIA_DEFINITIONS))


def seed_smartphones(db: Session, data: List[Dict[str, Any]] | None = None) -> None:
    """Insert smartphone records and their spec values (idempotent)."""
    phones = data or _load_seed_data()

    for phone_data in phones:
        phone_id = phone_data["id"]
        existing = db.query(Smartphone).filter_by(id=phone_id).first()
        if existing is not None:
            continue

        phone = Smartphone(
            id=phone_id,
            brand=phone_data["brand"],
            model_name=phone_data["model_name"],
            image_url=phone_data.get("image_url", ""),
            supported_by_cv=phone_data.get("supported_by_cv", True),
            price=phone_data["price"],
            battery_mah=phone_data["battery_mah"],
            camera_score=phone_data["camera_score"],
            antutu_score=phone_data["antutu_score"],
            storage_gb=phone_data["storage_gb"],
            weight_g=phone_data["weight_g"],
            charging_watts=phone_data["charging_watts"],
            screen_ratio=phone_data["screen_ratio"],
        )
        db.add(phone)
        db.flush()

        # Also populate the junction table
        for json_key, criterion_id in _SPEC_KEY_TO_CRITERION.items():
            spec = SmartphoneSpec(
                phone_id=phone_id,
                criterion_id=criterion_id,
                value=float(phone_data[json_key]),
                source="seed",
            )
            db.add(spec)

    db.commit()
    logger.info("Smartphones seeded: %d records", len(phones))


def seed_database(db: Session, seed_path: Path | None = None) -> None:
    """Run full seed: criteria + smartphones."""
    seed_criteria(db)
    data = _load_seed_data(seed_path) if seed_path else None
    seed_smartphones(db, data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.database.database import init_db, get_db

    init_db()
    db_gen = get_db()
    db = next(db_gen)
    try:
        seed_database(db)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
