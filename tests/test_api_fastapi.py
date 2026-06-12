import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

import src.api_fastapi as api_fastapi
from src.api_fastapi import app
from src.yolo_postprocess import extract_detections


_FAKE_IMGSZ = 640


class _FakeInputMeta:
    shape = [1, 3, _FAKE_IMGSZ, _FAKE_IMGSZ]


class _FakeSession:
    def get_inputs(self):
        return [_FakeInputMeta()]


class _FakeONNXModel:
    def __init__(self):
        self.session = _FakeSession()

    def predict(self, tensor):
        num_classes = len(api_fastapi.DEFAULT_CLASS_NAMES)
        num_anchors = 8400
        out = np.full((1, 4 + num_classes, num_anchors), -3.0, dtype=np.float32)
        out[0, 4 + 0, 0] = 5.0
        out[0, 0, 0] = 320.0
        out[0, 1, 0] = 320.0
        out[0, 2, 0] = 100.0
        out[0, 3, 0] = 200.0
        return [out]

    def close(self):
        pass


def _make_test_image_bytes():
    image = Image.new("RGB", (320, 240), color=(120, 100, 80))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _force_onnx_reload(state):
    state.pop("onnx_model", None)
    state.pop("input_size", None)
    state.pop("onnx_models", None)
    state.pop("onnx_input_sizes", None)


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
    assert isinstance(payload["detections"], list)
    assert isinstance(payload["image_width"], int)
    assert isinstance(payload["image_height"], int)


def test_extract_detections_parses_yolo_output():
    predictions = np.full((1, 14, 20), -3.0, dtype=np.float32)
    predictions[0, 4 + 3, 6] = 2.0
    predictions[0, 0, 6] = 320.0
    predictions[0, 1, 6] = 320.0
    predictions[0, 2, 6] = 100.0
    predictions[0, 3, 6] = 200.0
    class_names = [
        "c0", "c1", "c2", "c3", "c4",
        "c5", "c6", "c7", "c8", "c9",
    ]

    model_id, confidence, detections = extract_detections(
        predictions, class_names, (640, 640), (640, 640), conf_threshold=0.3,
    )

    assert model_id == "c3"
    assert confidence > 0.8
    assert len(detections) == 1
    assert detections[0]["class"] == "c3"
    assert "bbox" in detections[0]


def test_default_class_names_match_onnx_training_order():
    assert api_fastapi.DEFAULT_CLASS_NAMES == [
        "asus_rog_phone_9_pro",
        "apple_iphone_16e",
        "apple_iphone_17_pm",
        "nothing_cmf_phone_2_pro",
        "oneplus_13",
        "oppo_find_x9_pro",
        "samsung_galaxy_a56_5g",
        "samsung_s25_ultra",
        "samsung_galaxy_z_fold_7",
        "xiaomi_15t",
    ]


def test_identify_endpoint_model1_uses_correct_onnx_path(monkeypatch):
    loaded_paths = []

    def fake_load(path, use_cuda=None):
        loaded_paths.append(path)
        return _FakeONNXModel()

    monkeypatch.setattr(api_fastapi.ONNXModel, "load", fake_load)

    image_bytes = _make_test_image_bytes()
    with TestClient(app) as client:
        state = getattr(app.state, "_state", {})
        _force_onnx_reload(state)
        response = client.post(
            "/identify?model=model1",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        )

    assert response.status_code == 200
    assert loaded_paths
    assert loaded_paths[-1].endswith("computer_vision/models/onnx/model_1.onnx")


def test_identify_endpoint_model2_uses_correct_onnx_path(monkeypatch):
    loaded_paths = []

    def fake_load(path, use_cuda=None):
        loaded_paths.append(path)
        return _FakeONNXModel()

    monkeypatch.setattr(api_fastapi.ONNXModel, "load", fake_load)

    image_bytes = _make_test_image_bytes()
    with TestClient(app) as client:
        state = getattr(app.state, "_state", {})
        _force_onnx_reload(state)
        response = client.post(
            "/identify?model=model2",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        )

    assert response.status_code == 200
    assert loaded_paths
    assert loaded_paths[-1].endswith("computer_vision/models/onnx/model_2.onnx")


def test_identify_endpoint_model3_uses_correct_onnx_path(monkeypatch):
    loaded_paths = []

    def fake_load(path, use_cuda=None):
        loaded_paths.append(path)
        return _FakeONNXModel()

    monkeypatch.setattr(api_fastapi.ONNXModel, "load", fake_load)

    image_bytes = _make_test_image_bytes()
    with TestClient(app) as client:
        state = getattr(app.state, "_state", {})
        _force_onnx_reload(state)
        response = client.post(
            "/identify?model=model3",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        )

    assert response.status_code == 200
    assert loaded_paths
    assert loaded_paths[-1].endswith("computer_vision/models/onnx/model_3.onnx")


def test_identify_endpoint_invalid_model_returns_400():
    image_bytes = _make_test_image_bytes()

    with TestClient(app) as client:
        response = client.post(
            "/identify?model=bad",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        )

    assert response.status_code == 400


def test_identify_endpoint_defaults_to_model3(monkeypatch):
    loaded_paths = []

    def fake_load(path, use_cuda=None):
        loaded_paths.append(path)
        return _FakeONNXModel()

    monkeypatch.setattr(api_fastapi.ONNXModel, "load", fake_load)

    image_bytes = _make_test_image_bytes()

    with TestClient(app) as client:
        state = getattr(app.state, "_state", {})
        _force_onnx_reload(state)
        response = client.post(
            "/identify",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        )

    assert response.status_code == 200
    assert loaded_paths
    assert loaded_paths[-1].endswith("computer_vision/models/onnx/model_3.onnx")
    payload = response.json()
    assert payload["detected_object"] == "smartphone"
    assert "model_id" in payload
    assert isinstance(payload["confidence_score"], float)
    assert payload["action"] in {"trigger_db_lookup", "prompt_user_retry"}
    assert isinstance(payload["detections"], list)
    assert isinstance(payload["image_width"], int)
    assert isinstance(payload["image_height"], int)
