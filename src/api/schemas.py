"""Pydantic request / response schemas for the decision-support API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Smartphones ──────────────────────────────────────────────────────────────

class SmartphoneSpecs(BaseModel):
    price: float
    battery_mah: float
    camera_score: float
    antutu_score: float
    storage_gb: float
    weight_g: float
    charging_watts: float
    screen_ratio: float


class SmartphoneResponse(BaseModel):
    id: str
    brand: str
    model_name: str
    image_url: str = ""
    supported_by_cv: bool = True
    specs: SmartphoneSpecs


class SmartphoneListResponse(BaseModel):
    smartphones: List[SmartphoneResponse]


# ── Criteria ─────────────────────────────────────────────────────────────────

class CriterionResponse(BaseModel):
    id: str
    name: str
    direction: str
    unit: str


class CriteriaListResponse(BaseModel):
    criteria: List[CriterionResponse]


# ── Preferences / AHP ────────────────────────────────────────────────────────

class PreferencesRequest(BaseModel):
    price: float = Field(0.5, ge=0.0, le=1.0)
    battery: float = Field(0.5, ge=0.0, le=1.0)
    camera: float = Field(0.5, ge=0.0, le=1.0)
    antutu: float = Field(0.5, ge=0.0, le=1.0)
    storage: float = Field(0.5, ge=0.0, le=1.0)
    weight: float = Field(0.5, ge=0.0, le=1.0)
    charging: float = Field(0.5, ge=0.0, le=1.0)
    screen_ratio: float = Field(0.5, ge=0.0, le=1.0)

    def to_raw_dict(self) -> Dict[str, float]:
        return {
            "price": self.price,
            "battery": self.battery,
            "camera_score": self.camera,
            "antutu": self.antutu,
            "storage": self.storage,
            "weight": self.weight,
            "charging": self.charging,
            "screen_ratio": self.screen_ratio,
        }


class PreferencesResponse(BaseModel):
    weights: Dict[str, float]


# ── Ranking ──────────────────────────────────────────────────────────────────

class RankingEntry(BaseModel):
    rank: int
    id: str
    model_name: str
    brand: str
    closeness_coefficient: float
    score: float
    s_plus: float
    s_minus: float
    weighted_normalized: Dict[str, float]


class TopMatchResponse(BaseModel):
    rank: int
    id: str
    model_name: str
    brand: str
    closeness_coefficient: float
    score: float


class RankingResponse(BaseModel):
    method: str = "AHP + TOPSIS"
    ranking_id: str
    top_match: TopMatchResponse
    rankings: List[RankingEntry]
    weights_used: Dict[str, float]
    ideal_best: Dict[str, float]
    ideal_worst: Dict[str, float]
    criteria_directions: Dict[str, str]


class RankRequest(BaseModel):
    """Request body for POST /api/rank.

    If weights are omitted, default balanced weights are used.
    """
    weights: Optional[Dict[str, float]] = None


# ── Explanation ──────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    ranking_id: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    model: Optional[str] = None


class ExplainResponse(BaseModel):
    answer: str
    model_used: str = "template"


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    ranking_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    model_used: str = "chatbot"


# ── Detection (matches existing /identify response) ─────────────────────────

class DetectionResponse(BaseModel):
    detected_object: str = "smartphone"
    model_id: str
    confidence_score: float
    action: str
