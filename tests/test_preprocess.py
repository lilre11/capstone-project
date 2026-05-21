import os
import tempfile

import numpy as np
from PIL import Image

from src import preprocess


def test_load_image_and_resize_and_crop():
    # create a temporary image file
    img = Image.new("RGB", (300, 200), color=(123, 222, 64))
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    try:
        img.save(path, format="JPEG")
        loaded = preprocess.load_image(path)
        assert loaded.mode == "RGB"

        cropped = preprocess.resize_and_crop(loaded, (224, 224))
        assert cropped.size == (224, 224)
    finally:
        os.remove(path)


def test_normalize_and_to_tensor():
    # Create a sample HWC image with values in 0-255
    arr = np.ones((224, 224, 3), dtype=np.uint8) * 128
    norm = preprocess.normalize(arr)
    assert norm.dtype == np.float32
    # After normalization, values should not equal the original 0.5 exactly
    assert np.all(np.isfinite(norm))

    tensor = preprocess.to_tensor(norm)
    assert tensor.shape == (1, 3, 224, 224)
    assert tensor.dtype == np.float32
