# ONNX Integration Guide

This document explains how the exported ONNX model is integrated into this project, the expected input/output formats, preprocessing steps, usage examples, performance notes, and how to re-export the model from PyTorch.

## Model location

- Canonical model path in this repository: `models/onnx/best.onnx`
- Metadata and checksum: `models/onnx/README.md`

## Inspecting model inputs/outputs

Install `onnx` to inspect the model graph locally:

```bash
pip install onnx
python -c "import onnx; m=onnx.load('models/onnx/best.onnx'); print([ (i.name, [d.dim_value for d in i.type.tensor_type.shape.dim]) for i in m.graph.input ])"
```

Alternatively, `src/onnx_model.py` uses ONNX Runtime and `session.get_inputs()` to read input metadata at runtime.

## Expected input shape and preprocessing

- The project preprocessing pipeline (see `src/preprocess.py`) performs the following steps in order:
  1. `load_image(path)` — loads and converts the image to RGB (PIL Image).
  2. `resize_and_crop(image, (W, H))` — resizes preserving aspect ratio and center-crops to the model HxW. The integration code attempts to infer the model's expected H and W from input metadata; otherwise it defaults to 224x224.
  3. `normalize(array, mean=(0.485,0.456,0.406), std=(0.229,0.224,0.225))` — converts pixels to float32 in [0,1] and normalizes per-channel.
  4. `to_tensor(array)` — converts HWC to NCHW (shape: `1, C, H, W`) and dtype `float32` for ONNX Runtime.

Ensure that callers pass a tensor with shape matching the model input. The code in `src/api_inference.py` will attempt to detect model spatial dims automatically and use them when preprocessing.

## Running inference (examples)

CLI (from repository root):

```bash
python -m src.api_inference predict --image path/to/image.jpg
```

Or use the demo script which creates a sample image:

```bash
python examples/predict_demo.py
```

The CLI prints a JSON summary containing the output tensors' shapes, dtypes and min/max values.

## Re-exporting the model (PyTorch example)

If you need to re-export the model from PyTorch, here's an example command:

```python
# example: export PyTorch model to ONNX
# model: a torch.nn.Module already in eval() mode
import torch
dummy = torch.randn(1, 3, 1024, 1024)  # use proper H,W for your model
torch.onnx.export(model, dummy, 'best.onnx', opset_version=17,
                  input_names=['images'], output_names=['output'])
```

After exporting, place the file at `models/onnx/best.onnx` and update `models/onnx/README.md` with the new checksum.

## Performance notes

- ONNX Runtime supports CPU and GPU execution. Install `onnxruntime` for CPU and `onnxruntime-gpu` for GPU acceleration. See `requirements.txt`.
- When running on CPU, enable intra-op and inter-op thread tuning via `ort.SessionOptions()` if needed.
- For throughput-sensitive scenarios, use batching (provide N>1 in the input tensor) and warm up the session before measuring.
- If the model input HxW is very large (e.g., 1024x1024 in this repo's model), prefer resizing strategies or tiling to reduce memory usage.

## CI and model storage

- Small model binaries (<50MB) can be stored directly in the repo. For larger files, use Git LFS or an artifact store (GitHub Releases, S3).
- CI should install test dependencies and fetch the model from an artifact if not committed. See `.github/workflows/ci.yml` (not present by default) for examples.

## Troubleshooting

- If inference fails with dimension errors, inspect the model input shapes and ensure preprocessing produces tensors with matching shape and dtype.
- Use `session.get_inputs()` to inspect ONNX Runtime input metadata at runtime.

If you need a migration guide for a new model or opinionated production recommendations (quantization, dynamic shapes, FastAPI integration), open an issue or request a follow-up task.
