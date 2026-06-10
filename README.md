# AI-Powered Smartphone Decision Support System

An intelligent full-stack decision support system that helps users identify and rank smartphones using computer vision, multi-criteria decision analysis, and optional AI-generated explanations.

## Features
- Identify smartphone models from uploaded images.
- Rank devices with AHP and TOPSIS decision-making methods.
- Show transparent scoring inputs and comparison results.
- Generate natural-language explanations with SuperRouter when configured.
- Run a React frontend and FastAPI backend together from the project root.

## Tech Stack
- Backend: FastAPI, SQLite, SQLAlchemy, pytest, ONNX Runtime
- Frontend: React, Vite, TypeScript, Recharts, Framer Motion, Axios
- Vision: Roboflow API with local ONNX fallback support

## Project Structure
```text
src/
  api/                API endpoints and schemas
  database/           Database models, connection, and seed data
  decision_engine/    AHP and TOPSIS ranking logic
  explanation/        Explanation generation utilities
frontend/
  src/                React application source
tests/                Unit and integration tests
computer_vision/      Training artifacts and exported models
```

## Environment Setup
Create a `.env` file in the project root with any keys you plan to use:

```env
ROBOFLOW_API_KEY=your_roboflow_key
OPENROUTER_API_KEY=your_openrouter_key
DEFAULT_BACKEND=roboflow
```

If `OPENROUTER_API_KEY` is missing, the app falls back to local explanation templates.

## Install
From the project root:

```bash
npm run install:all
```

## Run
Start the backend and frontend together:

```bash
npm run dev
```

Expected local services:
- Backend: `http://127.0.0.1:8000`
- Frontend: `http://localhost:5173`

## Test
Run the full test suite:

```bash
npm run test
```

Or run Python tests directly:

```bash
pytest
```
