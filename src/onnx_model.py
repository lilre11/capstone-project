from typing import List, Any

import numpy as np
import onnxruntime as ort


class ONNXModel:
    """Simple ONNX model wrapper using ONNX Runtime.

    Usage:
        m = ONNXModel.load('models/onnx/best.onnx')
        out = m.predict(np.zeros((1,3,224,224), dtype=np.float32))
        m.close()
    """

    def __init__(self, session: ort.InferenceSession, input_names: List[str], output_names: List[str]):
        self.session = session
        self.input_names = input_names
        self.output_names = output_names

    @classmethod
    def load(cls, path: str, use_cuda: bool | None = None) -> "ONNXModel":
        """Load ONNX model from `path` and return an `ONNXModel` instance.

        If `use_cuda` is None, automatically enable CUDA if available.
        """
        providers = ort.get_available_providers()
        if use_cuda is None:
            use_cuda = "CUDAExecutionProvider" in providers

        if use_cuda and "CUDAExecutionProvider" in providers:
            chosen = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            chosen = ["CPUExecutionProvider"]

        sess_options = ort.SessionOptions()
        session = ort.InferenceSession(path, sess_options, providers=chosen)
        input_names = [inp.name for inp in session.get_inputs()]
        output_names = [out.name for out in session.get_outputs()]
        return cls(session, input_names, output_names)

    def predict(self, batch: Any) -> List[np.ndarray]:
        """Run inference on `batch`.

        Accepts a numpy array with shape (N,C,H,W) or (C,H,W) or a dict mapping input names to arrays.
        Returns list of numpy outputs in the same order as the model outputs.
        """
        if isinstance(batch, dict):
            inputs = batch
        else:
            arr = np.asarray(batch)
            if arr.ndim == 3:
                arr = np.expand_dims(arr, 0)
            inputs = {self.input_names[0]: arr}

        outputs = self.session.run(self.output_names, inputs)
        return outputs

    def close(self) -> None:
        """Release session resources."""
        try:
            # best-effort cleanup
            del self.session
        except Exception:
            pass


__all__ = ["ONNXModel"]
