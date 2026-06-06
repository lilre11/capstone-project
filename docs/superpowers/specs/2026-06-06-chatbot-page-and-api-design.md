# Chatbot Page and API

## Summary
Add a dedicated chatbot page and a new `POST /api/chat` endpoint so the app can answer general smartphone questions while staying grounded in saved ranking results, scores, and comparisons when that context is available.

## Goals
- Add a top navigation link for a dedicated `Chatbot` page.
- Create a real chat API instead of overloading the existing explanation route.
- Support two chat modes through one endpoint:
  - general smartphone guidance using in-app catalog data plus LLM knowledge
  - ranking-aware chat using saved ranking results, scores, and comparisons
- Preserve a safe fallback when the LLM is unavailable or the API key is missing.

## Non-Goals
- Live web browsing or current market data retrieval.
- Streaming responses in v1.
- User accounts or persistent chat storage beyond the in-memory page session.
- Retiring the existing `/api/explain` route during this change.

## Proposed Approach
### Backend
- Add `POST /api/chat`.
- Request body:
  - `question: string`
  - `ranking_id?: string`
  - `conversation_history?: ChatMessage[]`
- Response body:
  - `answer: string`
  - `model_used: string`
- If `ranking_id` is provided:
  - load the saved ranking from `RankingResult`
  - load smartphone catalog/spec context from the database
  - build a ranking-aware prompt that can explain winners, losers, trade-offs, and comparisons
- If `ranking_id` is omitted:
  - load the smartphone catalog/spec context from the database
  - build a general smartphone assistant prompt that still knows app data but does not fabricate live information
- Reuse the existing OpenRouter integration pattern from `src/explanation/llm_explainer.py`, but move chatbot-specific prompt/context construction into a separate module so the new route is not coupled to "explain ranking" behavior.
- Keep the existing `/api/explain` route working.

### Frontend
- Add a new `Chatbot` entry to the top navbar.
- Add a new route at `/chat`.
- Create `frontend/src/pages/ChatbotPage.tsx`.
- Reuse the existing app-level `rankingData` state from `App.tsx` so the chat page can automatically become ranking-aware after the user runs an analysis.
- Add a new API client method for `/api/chat`.
- Keep the v1 interface simple:
  - assistant/user message list
  - starter prompts
  - text input
  - send button
  - loading/disabled states
- Initial assistant message behavior:
  - with ranking data: explain that it can discuss scores, rankings, trade-offs, and comparisons
  - without ranking data: explain that it can provide general smartphone guidance and will become more specific after analysis

## Data Flow
1. User opens `/chat`.
2. Frontend checks whether `rankingData` exists in app state.
3. User submits a question.
4. Frontend posts to `/api/chat` with:
   - the question
   - optional `ranking_id`
   - accumulated conversation history
5. Backend loads context:
   - smartphone catalog for all requests
   - saved ranking data when `ranking_id` is present
6. Backend sends prompt + context to the LLM or fallback path.
7. Backend returns the answer and model identifier.
8. Frontend appends the assistant response to the conversation.

## Guardrails
- The assistant must explicitly behave as an in-app chatbot without live web access.
- It must not claim current prices, recent release dates, news, availability, or market changes unless that information is already present in app data.
- Ranking-aware answers must not contradict saved ranking results.
- The assistant may use general, non-time-sensitive smartphone knowledge, but app data wins if there is any tension between generic knowledge and the stored ranking/spec context.
- Unknown or unsupported questions should be answered honestly instead of with fabricated certainty.

## Error Handling
- Unknown `ranking_id` -> `404`.
- LLM/API failure -> template fallback response.
- Missing API key -> template fallback response.
- Empty or invalid questions -> validation error from request schema.
- Frontend request failure -> show a friendly assistant-style error message and keep prior conversation intact.

## Testing
- Backend:
  - `/api/chat` returns `200` with expected schema when `ranking_id` is present
  - `/api/chat` returns `200` with expected schema when `ranking_id` is omitted
  - `/api/chat` returns `404` for unknown `ranking_id`
  - chatbot fallback is returned when LLM invocation fails
- Frontend:
  - route and navbar wiring for `/chat`
  - chat request includes `ranking_id` when ranking data exists
  - initial empty-state copy is correct with and without ranking context
- If the repo does not already have frontend test infrastructure for these cases, verify frontend behavior through lint/build/manual flow in this pass.

## Implementation Notes
- Prefer introducing new `ChatRequest` and `ChatResponse` schemas instead of overloading `ExplainRequest` and `ExplainResponse`.
- Prefer a new chat module under `src/explanation/` or `src/api/` that shares low-level LLM utilities with the current explainer.
- Keep the first version synchronous request/response to reduce moving parts.
- Keep the existing explain page untouched unless small shared UI refactors make the new chat page simpler.
