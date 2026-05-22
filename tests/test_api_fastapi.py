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
            "/identify?backend=onnx",
            files={"file": ("sample.jpg", buffer.getvalue(), "image/jpeg")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_object"] == "smartphone"
    assert "model_id" in payload
    assert isinstance(payload["confidence_score"], float)
    assert payload["action"] in {"trigger_db_lookup", "prompt_user_retry"}


class _FakeRoboflowClient:
    def __init__(self, payload):
        self._payload = payload

    def infer_image(self, image_bytes: bytes):
        return self._payload


def _make_test_image_bytes():
    image = Image.new("RGB", (320, 240), color=(120, 100, 80))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_identify_endpoint_accepts_backend_onnx_query_param():
    image_bytes = _make_test_image_bytes()

    with TestClient(app) as client:
        response = client.post(
            "/identify?backend=onnx",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_object"] == "smartphone"
    assert "model_id" in payload
    assert isinstance(payload["confidence_score"], float)
    assert payload["action"] in {"trigger_db_lookup", "prompt_user_retry"}


def test_identify_endpoint_uses_roboflow_when_selected(monkeypatch):
    image_bytes = _make_test_image_bytes()
    rf_payload = {
        "predictions": [
            {"class": "apple_iphone_17_pm", "confidence": 0.91},
            {"class": "samsung_s25_ultra", "confidence": 0.12},
        ]
    }

    with TestClient(app) as client:
        state = getattr(app.state, "_state", {})
        had_roboflow_client = "roboflow_client" in state
        had_roboflow_model_id = "roboflow_model_id" in state
        original_roboflow_client = state.get("roboflow_client")
        original_roboflow_model_id = state.get("roboflow_model_id")
        try:
            state["roboflow_client"] = _FakeRoboflowClient(rf_payload)
            state["roboflow_model_id"] = "smartphones_capstone/4"

            response = client.post(
                "/identify?backend=roboflow",
                files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
            )
        finally:
            if had_roboflow_client:
                state["roboflow_client"] = original_roboflow_client
            else:
                state.pop("roboflow_client", None)

            if had_roboflow_model_id:
                state["roboflow_model_id"] = original_roboflow_model_id
            else:
                state.pop("roboflow_model_id", None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_id"] == "apple_iphone_17_pm"
    assert payload["confidence_score"] == 0.91


def test_identify_endpoint_defaults_to_roboflow_backend(monkeypatch):
    image_bytes = _make_test_image_bytes()
    rf_payload = {
        "predictions": [
            {"class": "apple_iphone_17_pm", "confidence": 0.91},
        ]
    }
    monkeypatch.setenv("DEFAULT_BACKEND", "roboflow")

    with TestClient(app) as client:
        state = getattr(app.state, "_state", {})
        had_onnx_model = "onnx_model" in state
        had_roboflow_client = "roboflow_client" in state
        had_roboflow_model_id = "roboflow_model_id" in state
        original_onnx_model = state.get("onnx_model")
        original_roboflow_client = state.get("roboflow_client")
        original_roboflow_model_id = state.get("roboflow_model_id")

        try:
            state["roboflow_client"] = _FakeRoboflowClient(rf_payload)
            state["roboflow_model_id"] = "smartphones_capstone/4"

            # Ensure we would fail if the ONNX backend were selected by default.
            state["onnx_model"] = None

            response = client.post(
                "/identify",
                files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
            )
        finally:
            if had_onnx_model:
                state["onnx_model"] = original_onnx_model
            else:
                state.pop("onnx_model", None)

            if had_roboflow_client:
                state["roboflow_client"] = original_roboflow_client
            else:
                state.pop("roboflow_client", None)

            if had_roboflow_model_id:
                state["roboflow_model_id"] = original_roboflow_model_id
            else:
                state.pop("roboflow_model_id", None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_id"] == "apple_iphone_17_pm"
    assert payload["confidence_score"] == 0.91


def test_identify_endpoint_invalid_backend_returns_400():
    image_bytes = _make_test_image_bytes()

    with TestClient(app) as client:
        response = client.post(
            "/identify?backend=invalid_backend",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        )

    assert response.status_code == 400


def test_identify_endpoint_roboflow_missing_key_returns_500(monkeypatch):
    image_bytes = _make_test_image_bytes()

    # Ensure env is cleared for Roboflow config
    monkeypatch.delenv("ROBOFLOW_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/identify?backend=roboflow",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        )

    assert response.status_code == 500
