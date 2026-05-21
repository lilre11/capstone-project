import argparse
import json
import tempfile
from typing import Any, Dict

import numpy as np

from src.onnx_model import ONNXModel
from src import preprocess
from PIL import Image


DEFAULT_MODEL_PATH = "models/onnx/best.onnx"


def predict_image(model_path: str, image_path: str, input_size=(224, 224)) -> Dict[str, Any]:
    """Run end-to-end inference for `image_path` using ONNX model at `model_path`.

    Returns a JSON-serializable dict with model outputs (shapes and values summary).
    """
    model = ONNXModel.load(model_path)
    try:
        # determine model expected spatial size from input metadata when possible
        try:
            input_meta = model.session.get_inputs()[0]
            meta_shape = input_meta.shape  # e.g. [N, C, H, W]
            if len(meta_shape) >= 4 and isinstance(meta_shape[2], int) and isinstance(meta_shape[3], int):
                input_size = (int(meta_shape[3]), int(meta_shape[2]))  # PIL expects (W, H)
        except Exception:
            # fallback to provided input_size
            pass

        img = preprocess.load_image(image_path)
        img = preprocess.resize_and_crop(img, input_size)
        arr = np.array(img)
        arr = preprocess.normalize(arr)
        tensor = preprocess.to_tensor(arr)

        outputs = model.predict(tensor)

        # Summarize outputs
        out_summary = []
        for out in outputs:
            out_summary.append({
                "shape": list(out.shape),
                "dtype": str(out.dtype),
                "min": float(np.min(out)),
                "max": float(np.max(out)),
            })

        return {"success": True, "outputs": out_summary}
    finally:
        model.close()


def _cli():
    parser = argparse.ArgumentParser(description="Run ONNX model prediction")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("predict", help="Run prediction on an image file")
    p.add_argument("--model", default=DEFAULT_MODEL_PATH)
    p.add_argument("--image", required=True)
    p.add_argument("--width", type=int, default=224)
    p.add_argument("--height", type=int, default=224)

    args = parser.parse_args()
    if args.cmd == "predict":
        res = predict_image(args.model, args.image, input_size=(args.width, args.height))
        print(json.dumps(res, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
