"""API routes for the decision-support system.

Endpoints
---------
GET  /api/smartphones       – List all smartphones
GET  /api/smartphones/{id}  – Get single phone details
GET  /api/criteria          – List all criteria with directions
POST /api/preferences       – Submit preference sliders → AHP weights
POST /api/rank              – Run TOPSIS ranking
GET  /api/rank/{id}         – Retrieve a saved ranking
POST /api/explain           – Ask AI to explain a ranking
"""

from __future__ import annotations

import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    CriteriaListResponse,
    CriterionResponse,
    ExplainRequest,
    ExplainResponse,
    PreferencesRequest,
    PreferencesResponse,
    RankingEntry,
    RankingResponse,
    RankRequest,
    SmartphoneListResponse,
    SmartphoneResponse,
    SmartphoneSpecs,
    TopMatchResponse,
)
from src.database.database import get_db
from src.database.models import Criterion, RankingResult, Smartphone
from src.decision_engine.ahp import get_weights, CRITERIA_ORDER
from src.decision_engine.topsis import rank_smartphones
from src.explanation import chatbot
from src.explanation.llm_explainer import explain as llm_explain, explain_fallback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Decision Support"])


# ── Smartphones ──────────────────────────────────────────────────────────────

@router.get("/smartphones", response_model=SmartphoneListResponse)
def list_smartphones(db: Session = Depends(get_db)):
    """Return all smartphones in the database."""
    phones = db.query(Smartphone).all()
    return SmartphoneListResponse(
        smartphones=[
            SmartphoneResponse(
                id=p.id,
                brand=p.brand,
                model_name=p.model_name,
                image_url=p.image_url or "",
                supported_by_cv=p.supported_by_cv,
                specs=SmartphoneSpecs(
                    price=p.price,
                    battery_mah=p.battery_mah,
                    camera_score=p.camera_score,
                    antutu_score=p.antutu_score,
                    storage_gb=p.storage_gb,
                    weight_g=p.weight_g,
                    charging_watts=p.charging_watts,
                    screen_ratio=p.screen_ratio,
                ),
            )
            for p in phones
        ]
    )


@router.get("/smartphones/{phone_id}", response_model=SmartphoneResponse)
def get_smartphone(phone_id: str, db: Session = Depends(get_db)):
    """Return a single smartphone by ID."""
    phone = db.query(Smartphone).filter_by(id=phone_id).first()
    if phone is None:
        raise HTTPException(status_code=404, detail=f"Smartphone '{phone_id}' not found.")
    return SmartphoneResponse(
        id=phone.id,
        brand=phone.brand,
        model_name=phone.model_name,
        image_url=phone.image_url or "",
        supported_by_cv=phone.supported_by_cv,
        specs=SmartphoneSpecs(
            price=phone.price,
            battery_mah=phone.battery_mah,
            camera_score=phone.camera_score,
            antutu_score=phone.antutu_score,
            storage_gb=phone.storage_gb,
            weight_g=phone.weight_g,
            charging_watts=phone.charging_watts,
            screen_ratio=phone.screen_ratio,
        ),
    )


# ── Criteria ─────────────────────────────────────────────────────────────────

@router.get("/criteria", response_model=CriteriaListResponse)
def list_criteria(db: Session = Depends(get_db)):
    """Return all criteria with directions."""
    criteria = db.query(Criterion).all()
    return CriteriaListResponse(
        criteria=[
            CriterionResponse(id=c.id, name=c.name, direction=c.direction, unit=c.unit)
            for c in criteria
        ]
    )


# ── Preferences ──────────────────────────────────────────────────────────────

@router.post("/preferences", response_model=PreferencesResponse)
def submit_preferences(prefs: PreferencesRequest):
    """Submit slider preferences and receive normalised AHP weights."""
    raw = prefs.to_raw_dict()
    weights = get_weights(raw, method="slider")
    return PreferencesResponse(weights=weights)


# ── Ranking ──────────────────────────────────────────────────────────────────

@router.post("/rank", response_model=RankingResponse)
def run_ranking(
    body: RankRequest | None = None,
    db: Session = Depends(get_db),
):
    """Run TOPSIS ranking with the given (or default) weights."""
    # Default balanced weights if none provided
    if body is None or body.weights is None:
        default_prefs = {c: 0.5 for c in CRITERIA_ORDER}
        weights = get_weights(default_prefs, method="slider")
    else:
        weights = body.weights
        # Ensure all criteria are present
        for c in CRITERIA_ORDER:
            if c not in weights:
                weights[c] = 0.0

    # Fetch all phones from DB
    phones = db.query(Smartphone).all()
    if not phones:
        raise HTTPException(status_code=404, detail="No smartphones in database.")

    phone_dicts = [p.to_criteria_dict() for p in phones]

    # Run TOPSIS
    result = rank_smartphones(phone_dicts, weights)

    # Persist the result
    ranking_id = str(uuid.uuid4())[:8]
    ranking_record = RankingResult(id=ranking_id)
    ranking_record.set_weights(weights)
    ranking_record.set_results(result)
    db.add(ranking_record)
    db.commit()

    top = result["top_match"]

    return RankingResponse(
        method=result["method"],
        ranking_id=ranking_id,
        top_match=TopMatchResponse(
            rank=top["rank"],
            id=top["id"],
            model_name=top["model_name"],
            brand=top["brand"],
            closeness_coefficient=top["closeness_coefficient"],
            score=top["score"],
        ),
        rankings=[
            RankingEntry(**r) for r in result["rankings"]
        ],
        weights_used=result["weights_used"],
        ideal_best=result["ideal_best"],
        ideal_worst=result["ideal_worst"],
        criteria_directions=result["criteria_directions"],
    )


@router.get("/rank/{ranking_id}", response_model=RankingResponse)
def get_ranking(ranking_id: str, db: Session = Depends(get_db)):
    """Retrieve a previously saved ranking result."""
    record = db.query(RankingResult).filter_by(id=ranking_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Ranking '{ranking_id}' not found.")

    result = record.get_results()
    top = result.get("top_match", {})

    return RankingResponse(
        method=result.get("method", "AHP + TOPSIS"),
        ranking_id=ranking_id,
        top_match=TopMatchResponse(**top) if top else TopMatchResponse(
            rank=0, id="", model_name="", brand="", closeness_coefficient=0, score=0
        ),
        rankings=[RankingEntry(**r) for r in result.get("rankings", [])],
        weights_used=result.get("weights_used", {}),
        ideal_best=result.get("ideal_best", {}),
        ideal_worst=result.get("ideal_worst", {}),
        criteria_directions=result.get("criteria_directions", {}),
    )


# ── Explanation ──────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(body: ChatRequest, db: Session = Depends(get_db)):
    """Ask the in-app chatbot for general or ranking-aware smartphone guidance."""
    ranking_data = None
    selected_model = body.model or chatbot.DEFAULT_CHAT_MODEL
    if selected_model not in chatbot.CURATED_FREE_CHAT_MODELS:
        raise HTTPException(status_code=400, detail="Invalid chat model specified.")

    if body.ranking_id:
        record = db.query(RankingResult).filter_by(id=body.ranking_id).first()
        if record is None:
            raise HTTPException(status_code=404, detail=f"Ranking '{body.ranking_id}' not found.")
        ranking_data = record.get_results()

    phones = db.query(Smartphone).all()
    phone_specs = [p.to_display_dict() for p in phones]

    try:
        answer = await chatbot.answer_chat(
            question=body.question,
            ranking_data=ranking_data,
            phone_specs=phone_specs,
            conversation_history=body.conversation_history,
            model_id=selected_model,
        )
        model_used = selected_model
    except Exception:
        logger.exception("Chatbot failed, using fallback.")
        answer = chatbot.fallback_chat_answer(body.question, ranking_data)
        model_used = "template_fallback"

    return ChatResponse(answer=answer, model_used=model_used)


@router.post("/explain", response_model=ExplainResponse)
async def explain_ranking(body: ExplainRequest, db: Session = Depends(get_db)):
    """Ask the AI to explain a ranking result."""
    selected_model = body.model or chatbot.DEFAULT_CHAT_MODEL
    if selected_model not in chatbot.CURATED_FREE_CHAT_MODELS:
        raise HTTPException(status_code=400, detail="Invalid explain model specified.")

    record = db.query(RankingResult).filter_by(id=body.ranking_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Ranking '{body.ranking_id}' not found.")

    ranking_data = record.get_results()

    # Get phone specs for context
    phones = db.query(Smartphone).all()
    phone_specs = [p.to_display_dict() for p in phones]

    try:
        answer = await llm_explain(
            question=body.question,
            ranking_data=ranking_data,
            phone_specs=phone_specs,
            conversation_history=body.conversation_history,
            model_id=selected_model,
        )
        model_used = selected_model
    except Exception as e:
        logger.exception("LLM explanation failed, using fallback.")
        answer = explain_fallback(body.question, ranking_data)
        model_used = "template_fallback"

    return ExplainResponse(answer=answer, model_used=model_used)
