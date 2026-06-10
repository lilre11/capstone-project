import os
import tempfile
from typing import Any, Dict

from inference_sdk import InferenceHTTPClient


class RoboflowClient:
    def __init__(self, api_url: str, api_key: str, model_id: str):
        if not api_key:
            raise ValueError("ROBOFLOW_API_KEY is required for Roboflow backend")
        self.client = InferenceHTTPClient(api_url=api_url, api_key=api_key)
        self.model_id = model_id

    def infer_image(self, image_bytes: bytes) -> Dict[str, Any]:
        suffix = ".jpg"
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(image_bytes)
            return self.client.infer(path, model_id=self.model_id)
        finally:
            try:
                os.remove(path)
            except Exception:
                pass
