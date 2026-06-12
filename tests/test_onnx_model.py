import os
import numpy as np

from src.onnx_model import ONNXModel


def test_onnx_model_predict_small():
    model_path = os.path.join("computer_vision", "models", "onnx", "model_3.onnx")
    assert os.path.exists(model_path), f"Model not found at {model_path}"

    model = ONNXModel.load(model_path)
    sess = model.session
    input_meta = sess.get_inputs()[0]
    shape = input_meta.shape

    # Build a sample input by replacing dynamic dims with 1 and defaulting H/W to 224
    sample_shape = []
    for i, d in enumerate(shape):
        if isinstance(d, str) or d is None:
            # batch or dynamic dimension -> set to 1
            sample_shape.append(1)
        else:
            sample_shape.append(d)

    # Ensure 4 dims (N,C,H,W) if model expects images; otherwise keep as-is
    if len(sample_shape) == 4:
        if sample_shape[2] in (None, 0):
            sample_shape[2] = 224
        if sample_shape[3] in (None, 0):
            sample_shape[3] = 224

    sample = np.random.rand(*sample_shape).astype(np.float32)

    outputs = model.predict(sample)
    assert isinstance(outputs, list)
    assert len(outputs) >= 1
    for out in outputs:
        assert isinstance(out, np.ndarray)

    model.close()
