import io

from fastapi.testclient import TestClient
from PIL import Image

from src.api_fastapi import app


def test_identify_endpoint_returns_expected_schema():
    image = Image.new("RGB", (320, 240), color=(120, 100, 80))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    with TestClient(app) as client:
        response = client.post(
            "/identify",
            files={"file": ("sample.jpg", buffer.getvalue(), "image/jpeg")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_object"] == "smartphone"
    assert "model_id" in payload
    assert isinstance(payload["confidence_score"], float)
    assert payload["action"] in {"trigger_db_lookup", "prompt_user_retry"}
