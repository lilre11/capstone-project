import io
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Tuple

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

from src import preprocess
from src.onnx_model import ONNXModel

try:
    import cv2  # optional: OpenCV preprocessing path
except Exception:  # pragma: no cover - optional dependency
    cv2 = None


DEFAULT_MODEL_PATH = "models/onnx/best.onnx"
DEFAULT_CLASS_NAMES = [
    "apple_iphone_17_pm",
    "samsung_s25_ultra",
    "oppo_find_x9_pro",
    "samsung_galaxy_z_fold_7",
    "asus_rog_phone_9_pro",
    "oneplus_13",
    "xiaomi_15t",
    "apple_iphone_16e",
    "samsung_galaxy_a56_5g",
    "nothing_cmf_phone_2_pro",
]


def _resolve_class_names() -> List[str]:
    raw = os.getenv("CLASS_NAMES", "")
    if not raw.strip():
        return DEFAULT_CLASS_NAMES
    names = [x.strip() for x in raw.split(",") if x.strip()]
    return names if names else DEFAULT_CLASS_NAMES


def _resolve_model_path() -> str:
    return os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)


def _infer_hw_from_model(model: ONNXModel) -> Tuple[int, int]:
    input_meta = model.session.get_inputs()[0]
    shape = input_meta.shape
    if len(shape) >= 4 and isinstance(shape[2], int) and isinstance(shape[3], int):
        return int(shape[3]), int(shape[2])  # (W, H)
    return 224, 224


def preprocess_image(image_bytes: bytes, target_size: Tuple[int, int]) -> np.ndarray | None:
    """Preprocess bytes into NCHW float32 tensor.

    Uses OpenCV path if installed; otherwise uses the Pillow-based project utilities.
    """
    target_w, target_h = target_size
    if cv2 is not None:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        img_filtered = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
        img_resized = cv2.resize(img_filtered, (target_w, target_h))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_chw = img_rgb.transpose((2, 0, 1))
        img_normalized = img_chw.astype(np.float32) / 255.0
        return np.expand_dims(img_normalized, axis=0)

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = preprocess.resize_and_crop(img, (target_w, target_h))
        arr = preprocess.normalize(np.array(img))
        return preprocess.to_tensor(arr)
    except Exception:
        return None


def _extract_best_class(predictions: np.ndarray, num_classes: int) -> Tuple[int, float]:
    """Extract the best class and confidence across known output layouts.

    Supported policies:
    - Classification-like: (N, C)
    - YOLO-like: (N, A, 4+C) or transposed (N, 4+C, A)
    - Fallback: flatten and search score-like slices
    """
    preds = np.asarray(predictions)

    # Policy 1: classification-like logits/probabilities (N, C)
    if preds.ndim == 2 and preds.shape[1] >= num_classes:
        scores = preds[:, :num_classes]
        row, col = np.unravel_index(np.argmax(scores), scores.shape)
        return int(col), float(scores[row, col])

    # Policy 2: YOLO-like (N, A, 4+C)
    if preds.ndim == 3:
        p = preds[0]
        if p.ndim == 2 and p.shape[-1] >= 4 + num_classes:
            scores = p[:, 4 : 4 + num_classes]
            row, col = np.unravel_index(np.argmax(scores), scores.shape)
            return int(col), float(scores[row, col])

        # YOLO-like transposed (N, 4+C, A)
        if p.ndim == 2 and p.shape[0] >= 4 + num_classes:
            pt = p.T
            if pt.shape[-1] >= 4 + num_classes:
                scores = pt[:, 4 : 4 + num_classes]
                row, col = np.unravel_index(np.argmax(scores), scores.shape)
                return int(col), float(scores[row, col])

    # Policy 3: fallback - search across score-like tail columns
    if preds.ndim >= 1:
        last_dim = preds.shape[-1] if preds.ndim > 0 else 1
        flat = preds.reshape(-1, last_dim)
        if last_dim >= num_classes:
            scores = flat[:, -num_classes:]
            row, col = np.unravel_index(np.argmax(scores), scores.shape)
            return int(col), float(scores[row, col])

        # last resort: max over whole tensor and map to class 0
        return 0, float(np.max(preds))

    return 0, 0.0


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        class_names = _resolve_class_names()
        model_path = _resolve_model_path()
        model = ONNXModel.load(model_path)
        input_size = _infer_hw_from_model(model)

        app.state.onnx_model = model
        app.state.class_names = class_names
        app.state.input_size = input_size

        try:
            yield
        finally:
            model = getattr(app.state, "onnx_model", None)
            if model is not None:
                model.close()

    app = FastAPI(
        title="AI Smartphone Decision Support System - CV Layer",
        lifespan=lifespan,
    )

    @app.post("/identify")
    async def identify_device(file: UploadFile = File(...)) -> Dict[str, Any]:
        model = getattr(app.state, "onnx_model", None)
        if model is None:
            raise HTTPException(status_code=500, detail="ONNX Model Engine is offline.")

        image_bytes = await file.read()
        input_tensor = preprocess_image(image_bytes, app.state.input_size)
        if input_tensor is None:
            raise HTTPException(status_code=400, detail="Invalid image file provided.")

        outputs = model.predict(input_tensor)
        if not outputs:
            raise HTTPException(status_code=500, detail="Model returned no outputs.")

        best_class_id, best_conf = _extract_best_class(outputs[0], len(app.state.class_names))
        confidence_score = float(best_conf)

        detected_model = (
            app.state.class_names[best_class_id]
            if confidence_score > 0.3 and 0 <= best_class_id < len(app.state.class_names)
            else "unknown_device"
        )

        return {
            "detected_object": "smartphone",
            "model_id": detected_model,
            "confidence_score": round(confidence_score, 3),
            "action": "trigger_db_lookup" if confidence_score > 0.5 else "prompt_user_retry",
        }

    return app


app = create_app()
