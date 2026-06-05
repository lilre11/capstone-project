# Identify Model Selection (model1/model2)

## Summary
Add a model selector on the Identify page and route the selection to the backend so the user can switch between model1 and model2 for inference.

## Goals
- Let users choose model1 or model2 in the Identify flow.
- Use the selected ONNX file for inference on `/identify`.
- Preserve existing Identify UX and error handling.

## Non-Goals
- Automatic model selection or ensemble logic.
- Changing ranking, preferences, or explanation behavior.

## Proposed Approach
### Frontend
- Add a selector on the Identify page with options: `Model 1`, `Model 2`.
- Keep selection state local to Identify page.
- Send the selection as a query param: `/identify?model=model1` or `/identify?model=model2`.

### Backend
- Extend `/identify` to accept a `model` query param.
- Map:
  - `model1` -> `computer_vision/models/onnx/model_1.onnx`
  - `model2` -> `computer_vision/models/onnx/model_2.onnx`
- Load the selected ONNX model at request time using the existing ONNX loader.

## Data Flow
1. User selects model in Identify page.
2. User uploads image.
3. Frontend posts multipart file to `/identify?model=modelX`.
4. Backend resolves ONNX path and runs inference.
5. Backend returns detection response.

## Error Handling
- Invalid `model` -> 400.
- Model load failure -> 500.
- Missing image -> 400 (existing behavior).
- If `model` is omitted -> default to `model1`.

## Testing
- API: request `/identify?model=model1` and `/identify?model=model2` returns 200 with expected schema.
- API: `/identify?model=bad` returns 400.
- Frontend: verify dropdown affects the request URL and existing flow works.
