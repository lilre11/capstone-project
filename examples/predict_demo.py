import os
import tempfile
from PIL import Image

from src.api_inference import predict_image


def main():
    # Create a sample RGB image and save to temp file
    img = Image.new("RGB", (300, 200), color=(120, 150, 200))
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    try:
        img.save(path, format="JPEG")
        print("Running demo predict on sample image:", path)
        res = predict_image("models/onnx/best.onnx", path)
        print(res)
    finally:
        os.remove(path)


if __name__ == "__main__":
    main()
