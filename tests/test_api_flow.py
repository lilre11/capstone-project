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
