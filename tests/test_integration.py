import os
import tempfile

from PIL import Image

from src.api_inference import predict_image


def test_end_to_end_predict():
    # create a temporary image
    img = Image.new("RGB", (640, 480), color=(10, 120, 200))
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    try:
        img.save(path, format="JPEG")
        res = predict_image("computer_vision/models/onnx/model_3.onnx", path)
        assert isinstance(res, dict)
        assert res.get("success") is True
        outputs = res.get("outputs")
        assert isinstance(outputs, list)
        assert len(outputs) >= 1
        for o in outputs:
            assert "shape" in o and "dtype" in o
    finally:
        os.remove(path)
