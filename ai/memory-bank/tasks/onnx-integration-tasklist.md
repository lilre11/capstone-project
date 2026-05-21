# ONNX Model Integration Tasklist

## Specification Summary
**Original Requirements**: Add an exported ONNX model to the project and fully integrate it so developers can run inference locally and in CI.
**Technical Stack**: Python (project codebase), ONNX model, ONNX Runtime (`onnxruntime`), unit tests (pytest), CI (GitHub Actions / existing pipeline).

## Development Tasks

### [ ] Task 1: Add ONNX model files
Description: Place exported ONNX file(s) into a repo path and add lightweight metadata (checksum, format, input shape).
Acceptance Criteria:
- Model file exists at `models/onnx/<model-name>.onnx`
- A `models/onnx/README.md` lists source, export command, and SHA256 checksum
Files to Create/Edit:
- models/onnx/<model-name>.onnx (binary)
- models/onnx/README.md
Assigned Agent: AI Engineer

### [ ] Task 2: Add ONNX runtime dependency
Description: Add `onnxruntime` to the project's dependency manifest and provide install instructions.
Acceptance Criteria:
- `requirements.txt` (or `pyproject.toml`) contains `onnxruntime` with a pinned or minimum version
- Local install command in README works
Files to Create/Edit:
- requirements.txt (or pyproject.toml)
- README.md (install snippet)
Assigned Agent: DevOps Automator

### [ ] Task 3: Implement preprocessing utilities
Description: Implement deterministic preprocessing pipeline to convert raw inputs to model-ready tensors.
Acceptance Criteria:
- `preprocess.py` exposes functions: `load_image()`, `resize_and_crop()`, `normalize()`, `to_tensor()`
- Each function has docstrings and simple unit tests
Files to Create/Edit:
- src/preprocess.py
- tests/test_preprocess.py
Assigned Agent: AI Engineer

### [ ] Task 4: Implement model loader & wrapper
Description: Create a module to load the ONNX model with ONNX Runtime and run inference with batched inputs.
Acceptance Criteria:
- `onnx_model.py` exposes `ONNXModel` class with `load(path)`, `predict(batch)`, `close()`
- Proper device selection (CPU / CUDA) based on availability
- Resource cleanup works and has unit tests (mocked or small input)
Files to Create/Edit:
- src/onnx_model.py
- tests/test_onnx_model.py
Assigned Agent: AI Engineer

### [ ] Task 5: Integrate inference into API
Description: Wire the model inference into the existing inference API/CLI so downstream code can call it.
Acceptance Criteria:
- Endpoint or CLI command `predict` uses `ONNXModel` and returns expected JSON/results
- Integration example present in `examples/` demonstrating end-to-end inference
Files to Create/Edit:
- src/api_inference.py (or existing API handler)
- examples/predict_demo.py
Assigned Agent: Backend Architect

### [ ] Task 6: Write unit & integration tests
Description: Add tests that validate preprocessing, model loading, and a small end-to-end prediction using a lightweight sample (or mocked outputs).
Acceptance Criteria:
- `pytest` runs and covers preprocessing and model wrapper
- CI will run tests and report pass/fail
Files to Create/Edit:
- tests/test_integration.py
- tests/test_preprocess.py
Assigned Agent: Test Results Analyzer

### [ ] Task 7: Add demo script / notebook
Description: Provide a simple script and optional notebook showing how to run inference locally with the model and sample inputs.
Acceptance Criteria:
- `examples/demo.py` runs and prints inference results for a provided sample image
- Notebook `examples/demo.ipynb` documents steps and includes sample output
Files to Create/Edit:
- examples/demo.py
- examples/demo.ipynb
Assigned Agent: Rapid Prototyper

### [ ] Task 8: Update documentation
Description: Update `README.md` and add a `docs/onnx-integration.md` describing usage, shape expectations, performance notes, and export provenance.
Acceptance Criteria:
- Docs describe input shapes, preprocess steps, how to run demo, and how to re-export the model
Files to Create/Edit:
- docs/onnx-integration.md
- README.md
Assigned Agent: Technical Writer

### [ ] Task 9: CI updates for model & tests
Description: Modify CI to install `onnxruntime`, run tests, and optionally cache the model or fetch it from an artifact store.
Acceptance Criteria:
- CI installs dependencies and runs `pytest` successfully
- If model is large, CI fetches it from a release or artifact rather than committing large binaries
Files to Create/Edit:
- .github/workflows/ci.yml (or existing pipeline file)
Assigned Agent: DevOps Automator

## Quality Requirements
- Keep model binary out of history when large; use Git LFS or external storage for >50MB
- Tests must be deterministic and fast (< 30s for unit tests)
- Document CPU/GPU behavior and fallback

## Quick Try Commands
- Install deps:
```bash
pip install -r requirements.txt
```
- Run demo:
```bash
python examples/demo.py --image tests/data/sample.jpg
```

## Timeline Expectations
Each task is scoped for a 30–60 minute developer ticket; whole integration should fit into a 1–2 day focused effort including tests and docs.
