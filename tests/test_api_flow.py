import pytest
from fastapi.testclient import TestClient
from src.api_fastapi import app

def test_full_rest_api_flow():
    with TestClient(app) as client:
        # 1. GET /api/smartphones - fetch smartphones list
        response = client.get("/api/smartphones")
        assert response.status_code == 200
        smartphones_data = response.json()
        assert "smartphones" in smartphones_data
        smartphones = smartphones_data["smartphones"]
        assert isinstance(smartphones, list)
        assert len(smartphones) == 10
        assert smartphones[0]["brand"] in ["Apple", "Samsung", "Oppo", "Asus", "OnePlus", "Xiaomi", "Nothing"]

        # 2. GET /api/criteria - fetch criteria list
        response = client.get("/api/criteria")
        assert response.status_code == 200
        criteria_data = response.json()
        assert "criteria" in criteria_data
        criteria = criteria_data["criteria"]
        assert isinstance(criteria, list)
        assert len(criteria) == 8
        criterion_ids = [c["id"] for c in criteria]
        assert "price" in criterion_ids
        assert "battery" in criterion_ids

        # 3. POST /api/preferences - calculate AHP weights from preferences
        # Body is flat PreferencesRequest (values 0.0 to 1.0)
        prefs_payload = {
            "price": 0.8,
            "battery": 0.5,
            "camera": 0.9,
            "antutu": 0.7,
            "storage": 0.4,
            "weight": 0.3,
            "charging": 0.6,
            "screen_ratio": 0.5
        }
        response = client.post("/api/preferences", json=prefs_payload)
        assert response.status_code == 200
        weights_data = response.json()
        assert "weights" in weights_data
        assert isinstance(weights_data["weights"], dict)
        assert abs(sum(weights_data["weights"].values()) - 1.0) < 1e-4

        # 4. POST /api/rank - run TOPSIS ranking based on AHP weights
        rank_payload = {
            "weights": weights_data["weights"]
        }
        response = client.post("/api/rank", json=rank_payload)
        assert response.status_code == 200
        ranking_data = response.json()
        assert "ranking_id" in ranking_data
        assert "rankings" in ranking_data
        assert len(ranking_data["rankings"]) == 10
        
        # Verify ranking structure
        best_match = ranking_data["rankings"][0]
        assert "rank" in best_match
        assert "score" in best_match
        assert best_match["rank"] == 1
        
        # 5. GET /api/rank/{id} - retrieve previous ranking
        ranking_id = ranking_data["ranking_id"]
        response = client.get(f"/api/rank/{ranking_id}")
        assert response.status_code == 200
        retrieved_data = response.json()
        assert retrieved_data["ranking_id"] == ranking_id
        assert len(retrieved_data["rankings"]) == 10

        # 6. POST /api/explain - retrieve AI explanation
        explain_payload = {
            "ranking_id": ranking_id,
            "question": "Why was the top phone selected as number 1?",
            "conversation_history": []
        }
        response = client.post("/api/explain", json=explain_payload)
        assert response.status_code == 200
        explanation_data = response.json()
        assert "answer" in explanation_data
        assert "model_used" in explanation_data
        assert len(explanation_data["answer"]) > 0


def test_chat_endpoint_with_ranking_context(monkeypatch):
    from src.explanation import chatbot

    async def fake_answer_chat(**kwargs):
        ranking_data = kwargs.get("ranking_data")
        model_id = kwargs.get("model_id")
        assert ranking_data is not None
        assert ranking_data["rankings"][0]["rank"] == 1
        assert model_id == "openrouter/free"
        return "Ranking-aware answer"

    monkeypatch.setattr(chatbot, "answer_chat", fake_answer_chat)

    with TestClient(app) as client:
        rank_response = client.post("/api/rank", json={})
        assert rank_response.status_code == 200
        ranking_id = rank_response.json()["ranking_id"]

        response = client.post(
            "/api/chat",
            json={
                "question": "Why did the top phone win?",
                "ranking_id": ranking_id,
                "conversation_history": [],
                "model": "openrouter/free",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Ranking-aware answer"
    assert payload["model_used"] == "openrouter/free"


def test_chat_endpoint_without_ranking_context(monkeypatch):
    from src.explanation import chatbot

    async def fake_answer_chat(**kwargs):
        ranking_data = kwargs.get("ranking_data")
        phone_specs = kwargs.get("phone_specs")
        model_id = kwargs.get("model_id")
        assert ranking_data is None
        assert isinstance(phone_specs, list)
        assert len(phone_specs) == 10
        assert model_id == "meta-llama/llama-3.3-70b-instruct:free"
        return "General answer"

    monkeypatch.setattr(chatbot, "answer_chat", fake_answer_chat)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "question": "What kind of phone should I buy for battery life?",
                "conversation_history": [],
                "model": "meta-llama/llama-3.3-70b-instruct:free",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "General answer"
    assert payload["model_used"] == "meta-llama/llama-3.3-70b-instruct:free"


def test_chat_endpoint_unknown_ranking_id_returns_404():
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "question": "Explain this result",
                "ranking_id": "missing-id",
                "conversation_history": [],
            },
        )

    assert response.status_code == 404


def test_chat_endpoint_invalid_model_returns_400():
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "question": "Explain this result",
                "model": "not-a-real-model",
                "conversation_history": [],
            },
        )

    assert response.status_code == 400


def test_chat_endpoint_returns_fallback_when_chatbot_service_fails(monkeypatch):
    from src.explanation import chatbot

    async def fake_answer_chat(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(chatbot, "answer_chat", fake_answer_chat)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "question": "Compare the top phones",
                "conversation_history": [],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_used"] == "template_fallback"
    assert "smartphone" in payload["answer"].lower() or "analysis" in payload["answer"].lower()
