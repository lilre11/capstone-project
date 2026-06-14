import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def disable_external_ai_keys(monkeypatch):
    """Keep tests offline unless a test explicitly supplies a mocked client."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
