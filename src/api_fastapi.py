import base64
import io
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from PIL import Image

from src import preprocess
from src.onnx_model import ONNXModel
from src.yolo_postprocess import extract_detections

try:
    import cv2
except Exception:
    cv2 = None


DEFAULT_MODEL_PATH = "models/onnx/best.onnx"
DEFAULT_CLASS_NAMES = [
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
ONNX_MODEL_PATHS = {
    "model1": "computer_vision/models/onnx/model_1.onnx",
    "model2": "computer_vision/models/onnx/model_2.onnx",
    "model3": "computer_vision/models/onnx/model_3.onnx",
}
DEFAULT_ONNX_MODEL_KEY = next(reversed(ONNX_MODEL_PATHS))

logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


def _resolve_class_names() -> List[str]:
    raw = os.getenv("CLASS_NAMES", "")
    if not raw.strip():
        return DEFAULT_CLASS_NAMES
    names = [x.strip() for x in raw.split(",") if x.strip()]
    return names if names else DEFAULT_CLASS_NAMES


def _resolve_onnx_model_path(model_key: str | None) -> str:
    key = (model_key or DEFAULT_ONNX_MODEL_KEY).strip().lower()
    if key not in ONNX_MODEL_PATHS:
        raise HTTPException(status_code=400, detail="Invalid model specified.")
    return ONNX_MODEL_PATHS[key]


def _infer_hw_from_model(model: ONNXModel) -> Tuple[int, int]:
    input_meta = model.session.get_inputs()[0]
    shape = input_meta.shape
    if len(shape) >= 4 and isinstance(shape[2], int) and isinstance(shape[3], int):
        return int(shape[3]), int(shape[2])
    return 224, 224


def _get_or_load_onnx_model(app: FastAPI, model_path: str) -> ONNXModel | None:
    cache = getattr(app.state, "onnx_models", None)
    if cache is None or not isinstance(cache, dict):
        cache = {}
        app.state.onnx_models = cache

    model = cache.get(model_path)
    if model is not None and getattr(model, "session", None) is not None:
        input_sizes = getattr(app.state, "onnx_input_sizes", None)
        if input_sizes is None or not isinstance(input_sizes, dict):
            input_sizes = {}
            app.state.onnx_input_sizes = input_sizes
        if model_path not in input_sizes:
            input_sizes[model_path] = _infer_hw_from_model(model)
        return model

    try:
        model = ONNXModel.load(model_path)
    except Exception:
        logger.exception("Failed to load ONNX model.")
        return None

    cache[model_path] = model
    input_sizes = getattr(app.state, "onnx_input_sizes", None)
    if input_sizes is None or not isinstance(input_sizes, dict):
        input_sizes = {}
        app.state.onnx_input_sizes = input_sizes
    input_sizes[model_path] = _infer_hw_from_model(model)
    return model


def preprocess_image(
    image_bytes: bytes, target_size: Tuple[int, int]
) -> tuple[np.ndarray, tuple[int, int]] | None:
    target_w, target_h = target_size
    if cv2 is not None:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            orig_size = (img.shape[1], img.shape[0])
            img_filtered = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
            img_resized = cv2.resize(img_filtered, (target_w, target_h))
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            img_chw = img_rgb.transpose((2, 0, 1))
            img_normalized = img_chw.astype(np.float32) / 255.0
            return np.expand_dims(img_normalized, axis=0), orig_size

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        orig_size = img.size
        img = preprocess.resize_and_crop(img, (target_w, target_h))
        arr = preprocess.normalize(np.array(img))
        tensor = preprocess.to_tensor(arr)
        return tensor, orig_size
    except Exception:
        return None


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
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

        class_names = _resolve_class_names()
        app.state.class_names = class_names

        model_path = _resolve_onnx_model_path(None)
        model = _get_or_load_onnx_model(app, model_path)
        if model is None:
            raise RuntimeError("ONNX model failed to load during startup.")

        try:
            yield
        finally:
            models = getattr(app.state, "onnx_models", None) or {}
            for m in models.values():
                if m is not None:
                    m.close()
            app.state.onnx_models = None
            app.state.onnx_input_sizes = None

    app = FastAPI(
        title="AI Smartphone Decision Support System",
        description="CV detection, AHP weighting, TOPSIS ranking, and LLM explanation.",
        lifespan=lifespan,
    )

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

    artifacts_dir = Path(__file__).resolve().parents[1] / "computer_vision" / "training_artifacts"
    if artifacts_dir.is_dir():
        app.mount("/artifacts", StaticFiles(directory=str(artifacts_dir)), name="artifacts")

    from src.api.routes import router as api_router
    app.include_router(api_router)

    @app.post("/identify")
    async def identify_device(
        file: UploadFile = File(...),
        model: str | None = Query(
            default=None,
            description="ONNX model key: model1|model2|model3",
        ),
    ) -> Dict[str, Any]:
        try:
            image_bytes = await file.read()
        finally:
            await file.close()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Invalid image file provided.")

        model_path = _resolve_onnx_model_path(model)
        model_obj = _get_or_load_onnx_model(app, model_path)
        if model_obj is None:
            raise HTTPException(status_code=500, detail="ONNX Model Engine is offline.")

        input_sizes = getattr(app.state, "onnx_input_sizes", {})
        input_size = input_sizes.get(model_path)
        if input_size is None:
            input_size = _infer_hw_from_model(model_obj)
            input_sizes[model_path] = input_size
            app.state.onnx_input_sizes = input_sizes

        result = preprocess_image(image_bytes, input_size)
        if result is None:
            raise HTTPException(status_code=400, detail="Invalid image file provided.")

        input_tensor, orig_size = result

        outputs = model_obj.predict(input_tensor)
        if not outputs:
            raise HTTPException(status_code=500, detail="Model returned no outputs.")

        detected_model, confidence_score, detections = extract_detections(
            outputs[0],
            app.state.class_names,
            orig_size,
            input_size,
            conf_threshold=0.3,
        )

        if not orig_size or orig_size == (0, 0):
            orig_size = (640, 640)

        return {
            "detected_object": "smartphone",
            "model_id": detected_model,
            "confidence_score": round(float(confidence_score), 3),
            "action": "trigger_db_lookup" if confidence_score > 0.5 else "prompt_user_retry",
            "detections": detections[:1],
            "image_width": orig_size[0],
            "image_height": orig_size[1],
        }

    @app.websocket("/ws/detect")
    async def ws_detect(websocket: WebSocket, model: str | None = None):
        await websocket.accept()
        try:
            model_path = _resolve_onnx_model_path(model)
        except HTTPException:
            await websocket.send_json({"type": "error", "message": "Invalid model"})
            await websocket.close()
            return

        model_obj = _get_or_load_onnx_model(app, model_path)
        if model_obj is None:
            await websocket.send_json({"type": "error", "message": "Model engine offline"})
            await websocket.close()
            return

        input_sizes = getattr(app.state, "onnx_input_sizes", {})
        input_size = input_sizes.get(model_path)
        if input_size is None:
            input_size = _infer_hw_from_model(model_obj)
            input_sizes[model_path] = input_size
            app.state.onnx_input_sizes = input_sizes

        class_names = app.state.class_names

        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") != "frame":
                    continue

                image_bytes = base64.b64decode(msg["data"])
                result = preprocess_image(image_bytes, input_size)
                if result is None:
                    continue

                input_tensor, orig_size = result
                outputs = model_obj.predict(input_tensor)
                if not outputs:
                    continue

                detected_model, confidence_score, detections = extract_detections(
                    outputs[0],
                    class_names,
                    orig_size,
                    input_size,
                    conf_threshold=0.3,
                )

                await websocket.send_json({
                    "type": "detection",
                    "model_id": detected_model,
                    "confidence_score": round(float(confidence_score), 3),
                    "detections": detections[:1],
                    "image_width": orig_size[0],
                    "image_height": orig_size[1],
                })
        except WebSocketDisconnect:
            pass

    return app


app = create_app()
