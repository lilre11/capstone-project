# ONNX model: best.onnx

Source: Provided by user (original path: `C:\Users\EmreY\Downloads\best.onnx`)

Format: ONNX

SHA256: BFCBE8A56F86184E2FD84ED21E7B767F61E7850B699AD3B742E8B4CA8099245A

Suggested export command (example for PyTorch):

```python
# Example export command (PyTorch)
# torch.onnx.export(model, dummy_input, "best.onnx", opset_version=17, input_names=["input"], output_names=["output"]) 
```

Notes:
- File size: 10,873,690 bytes
- If the model is large (>50MB), consider using Git LFS or an external artifact store; current file is ~10.9MB and safe to commit.
- Input/output shapes not recorded here; run the following to inspect shapes locally if `onnx` or `onnxruntime` is installed:

```bash
python -c "import onnx; m=onnx.load('models/onnx/best.onnx'); print([i.name+':'+str([d.dim_value for d in i.type.tensor_type.shape.dim]) for i in m.graph.input])"
```
