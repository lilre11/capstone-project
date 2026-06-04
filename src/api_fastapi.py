import io
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PIL import Image

from src import preprocess
from src.onnx_model import ONNXModel
from src.roboflow_client import RoboflowClient

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
DEFAULT_BACKEND = "roboflow"
DEFAULT_ROBOFLOW_API_URL = "https://serverless.roboflow.com"
DEFAULT_ROBOFLOW_MODEL_ID = "smartphones_capstone/4"

logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


def _resolve_class_names() -> List[str]:
    raw = os.getenv("CLASS_NAMES", "")
    if not raw.strip():
        return DEFAULT_CLASS_NAMES
    names = [x.strip() for x in raw.split(",") if x.strip()]
    return names if names else DEFAULT_CLASS_NAMES


def _resolve_model_path() -> str:
    return os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)


def _resolve_default_backend() -> str:
    raw = os.getenv("DEFAULT_BACKEND", DEFAULT_BACKEND)
    if not raw or not raw.strip():
        return DEFAULT_BACKEND
    return raw.strip().lower()


def _resolve_roboflow_config() -> tuple[str, str | None, str]:
    api_url = os.getenv("ROBOFLOW_API_URL", DEFAULT_ROBOFLOW_API_URL)
    api_key = os.getenv("ROBOFLOW_API_KEY")
    model_id = os.getenv("ROBOFLOW_MODEL_ID", DEFAULT_ROBOFLOW_MODEL_ID)
    return api_url, api_key, model_id


def _get_roboflow_client(app: FastAPI) -> RoboflowClient:
    client = getattr(app.state, "roboflow_client", None)
    if client is not None:
        return client

    api_url, api_key, model_id = _resolve_roboflow_config()
    if not api_key:
        raise HTTPException(status_code=500, detail="Roboflow API key is missing.")

    client = RoboflowClient(api_url=api_url, api_key=api_key, model_id=model_id)
    app.state.roboflow_client = client
    app.state.roboflow_model_id = model_id
    return client


def _extract_roboflow_best(prediction_payload: dict, class_names: list[str]) -> tuple[str, float]:
    predictions = prediction_payload.get("predictions") or []
    if not isinstance(predictions, list) or not predictions:
        return "unknown_device", 0.0

    valid_predictions: list[tuple[dict, float]] = []
    for prediction in predictions:
        if not isinstance(prediction, dict):
            continue
        try:
            confidence = float(prediction.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        valid_predictions.append((prediction, confidence))

    if not valid_predictions:
        return "unknown_device", 0.0

    best_prediction, conf = max(valid_predictions, key=lambda item: item[1])
    label = str(best_prediction.get("class", "unknown_device"))

    if class_names and label not in class_names:
        return "unknown_device", conf

    return label, conf


def _infer_hw_from_model(model: ONNXModel) -> Tuple[int, int]:
    input_meta = model.session.get_inputs()[0]
    shape = input_meta.shape
    if len(shape) >= 4 and isinstance(shape[2], int) and isinstance(shape[3], int):
        return int(shape[3]), int(shape[2])  # (W, H)
    return 224, 224


def _set_onnx_model(app: FastAPI, model: ONNXModel) -> None:
    app.state.onnx_model = model
    app.state.input_size = _infer_hw_from_model(model)


def _get_or_load_onnx_model(app: FastAPI) -> ONNXModel | None:
    model = getattr(app.state, "onnx_model", None)
    if model is not None:
        if getattr(model, "session", None) is None:
            model = None
        else:
            if getattr(app.state, "input_size", None) is None:
                app.state.input_size = _infer_hw_from_model(model)
            return model

    model_path = _resolve_model_path()
    try:
        model = ONNXModel.load(model_path)
    except Exception:
        logger.exception("Failed to load ONNX model.")
        return None

    _set_onnx_model(app, model)
    return model


def preprocess_image(image_bytes: bytes, target_size: Tuple[int, int]) -> np.ndarray | None:
    """Preprocess bytes into NCHW float32 tensor.

    Uses OpenCV path if installed; otherwise uses the Pillow-based project utilities.
    """
    target_w, target_h = target_size
    if cv2 is not None:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
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
        # ── Initialise database ──
        from src.database.database import init_db, get_db
        from src.database.seed import seed_database

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

        # ── Load CV model ──
        class_names = _resolve_class_names()
        app.state.class_names = class_names

        if _resolve_default_backend() == "onnx":
            model = _get_or_load_onnx_model(app)
            if model is None:
                raise RuntimeError("ONNX model failed to load during startup.")
        else:
            if _get_or_load_onnx_model(app) is None:
                logger.warning("Skipping ONNX model startup load.")

        try:
            yield
        finally:
            model = getattr(app.state, "onnx_model", None)
            if model is not None:
                model.close()
            app.state.onnx_model = None
            app.state.input_size = None

    app = FastAPI(
        title="AI Smartphone Decision Support System",
        description="CV detection, AHP weighting, TOPSIS ranking, and LLM explanation.",
        lifespan=lifespan,
    )

    # ── CORS middleware ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Mount decision-support API routes ──
    from src.api.routes import router as api_router
    app.include_router(api_router)

    # ── CV identification endpoint (existing) ──
    @app.post("/identify")
    async def identify_device(
        file: UploadFile = File(...),
        backend: str = Query(default=None, description="Inference backend: roboflow|onnx"),
    ) -> Dict[str, Any]:
        selected = (backend or _resolve_default_backend()).lower()
        if selected not in {"roboflow", "onnx"}:
            raise HTTPException(status_code=400, detail="Invalid backend specified.")

        try:
            image_bytes = await file.read()
        finally:
            await file.close()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Invalid image file provided.")

        if selected == "roboflow":
            try:
                rf_client = _get_roboflow_client(app)
                rf_result = rf_client.infer_image(image_bytes)
                detected_model, confidence_score = _extract_roboflow_best(
                    rf_result, app.state.class_names
                )
            except HTTPException:
                raise
            except Exception:
                logger.exception("Roboflow inference failed.")
                raise HTTPException(status_code=502, detail="Roboflow inference failed.")
        else:
            model = _get_or_load_onnx_model(app)
            if model is None:
                raise HTTPException(status_code=500, detail="ONNX Model Engine is offline.")

            input_tensor = preprocess_image(image_bytes, app.state.input_size)
            if input_tensor is None:
                raise HTTPException(status_code=400, detail="Invalid image file provided.")

            outputs = model.predict(input_tensor)
            if not outputs:
                raise HTTPException(status_code=500, detail="Model returned no outputs.")

            best_class_id, best_conf = _extract_best_class(
                outputs[0], len(app.state.class_names)
            )
            confidence_score = float(best_conf)
            detected_model = (
                app.state.class_names[best_class_id]
                if confidence_score > 0.3 and 0 <= best_class_id < len(app.state.class_names)
                else "unknown_device"
            )

        return {
            "detected_object": "smartphone",
            "model_id": detected_model,
            "confidence_score": round(float(confidence_score), 3),
            "action": "trigger_db_lookup" if confidence_score > 0.5 else "prompt_user_retry",
        }

    return app


app = create_app()
