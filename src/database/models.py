"""SQLAlchemy ORM models for the smartphone decision-support system."""

from __future__ import annotations

import datetime
import json
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Smartphone(Base):
    """A smartphone alternative in the decision matrix."""

    __tablename__ = "smartphones"

    id = Column(String, primary_key=True)
    brand = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    image_url = Column(String, default="")
    supported_by_cv = Column(Boolean, default=True)

    # Retail tech specs (JSON string — display-only, not used in TOPSIS)
    tech_specs = Column(Text, default="{}")

    # Raw specification values (denormalised for easy access)
    price = Column(Float, nullable=False, doc="Price in TRY")
    battery_mah = Column(Float, nullable=False, doc="Battery capacity in mAh")
    camera_score = Column(Float, nullable=False, doc="Camera score (DxOMark-style)")
    antutu_score = Column(Float, nullable=False, doc="AnTuTu benchmark score")
    storage_gb = Column(Float, nullable=False, doc="Base storage in GB")
    weight_g = Column(Float, nullable=False, doc="Weight in grams")
    charging_watts = Column(Float, nullable=False, doc="Max charging speed in watts")
    screen_ratio = Column(Float, nullable=False, doc="Screen-to-body ratio (0-1)")

    specs = relationship("SmartphoneSpec", back_populates="smartphone", cascade="all, delete-orphan")

    def to_criteria_dict(self) -> dict:
        """Return a dict mapping TOPSIS criterion names → raw values."""
        return {
            "id": self.id,
            "brand": self.brand,
            "model_name": self.model_name,
            "price": self.price,
            "battery": self.battery_mah,
            "camera_score": self.camera_score,
            "antutu": self.antutu_score,
            "storage": self.storage_gb,
            "weight": self.weight_g,
            "charging": self.charging_watts,
            "screen_ratio": self.screen_ratio,
        }

    def to_display_dict(self) -> dict:
        """Return a dict suitable for API responses / frontend display."""
        return {
            "id": self.id,
            "brand": self.brand,
            "model_name": self.model_name,
            "image_url": self.image_url or "",
            "supported_by_cv": self.supported_by_cv,
            "tech_specs": json.loads(self.tech_specs) if self.tech_specs else {},
            "specs": {
                "price": self.price,
                "battery_mah": self.battery_mah,
                "camera_score": self.camera_score,
                "antutu_score": self.antutu_score,
                "storage_gb": self.storage_gb,
                "weight_g": self.weight_g,
                "charging_watts": self.charging_watts,
                "screen_ratio": self.screen_ratio,
            },
        }


class Criterion(Base):
    """A decision criterion (e.g. price, battery)."""

    __tablename__ = "criteria"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    direction = Column(String, nullable=False, doc="'min' (cost) or 'max' (benefit)")
    unit = Column(String, default="")

    specs = relationship("SmartphoneSpec", back_populates="criterion")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "direction": self.direction,
            "unit": self.unit,
        }


class SmartphoneSpec(Base):
    """Junction table: one spec value per phone × criterion pair."""

    __tablename__ = "smartphone_specs"

    phone_id = Column(String, ForeignKey("smartphones.id"), primary_key=True)
    criterion_id = Column(String, ForeignKey("criteria.id"), primary_key=True)
    value = Column(Float, nullable=False)
    source = Column(String, default="seed")

    smartphone = relationship("Smartphone", back_populates="specs")
    criterion = relationship("Criterion", back_populates="specs")


class RankingResult(Base):
    """Persisted TOPSIS ranking result."""

    __tablename__ = "rankings"

    id = Column(String, primary_key=True)
    method = Column(String, default="AHP + TOPSIS")
    weights_json = Column(Text, nullable=False)
    results_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    def set_weights(self, weights: dict) -> None:
        self.weights_json = json.dumps(weights)

    def get_weights(self) -> dict:
        return json.loads(self.weights_json) if self.weights_json else {}

    def set_results(self, results: dict) -> None:
        self.results_json = json.dumps(results, default=str)

    def get_results(self) -> dict:
        return json.loads(self.results_json) if self.results_json else {}


__all__ = ["Base", "Smartphone", "Criterion", "SmartphoneSpec", "RankingResult"]
