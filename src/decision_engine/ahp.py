"""AHP (Analytic Hierarchy Process) weighting module.

Converts user preference slider values into normalised criterion weight
vectors suitable for TOPSIS ranking.

Two modes are supported:
  1. **Slider normalisation** (MVP) – raw 0-1 slider values are divided by
     their sum so the weights add up to 1.
  2. **Pairwise comparison matrix** (academic) – a full n×n reciprocal matrix
     is eigen-decomposed to extract the principal eigenvector, and a
     consistency ratio is computed.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np

# Criteria in the canonical order used throughout the system.
CRITERIA_ORDER: List[str] = [
    "price",
    "battery",
    "camera_score",
    "antutu",
    "storage",
    "weight",
    "charging",
    "screen_ratio",
]

# Saaty's Random Index table (for n = 1 … 10).
_RI: Dict[int, float] = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}


# ---------------------------------------------------------------------------
# Slider-based weight calculation (MVP)
# ---------------------------------------------------------------------------

def normalize_slider_weights(preferences: Dict[str, float]) -> Dict[str, float]:
    """Convert raw slider values (each 0.0–1.0) to a weight vector summing to 1.

    Missing criteria receive a default value of 0.5 (moderate importance).
    If every slider is 0 the result is equal weights.

    Parameters
    ----------
    preferences:
        Mapping of criterion name → slider value (0.0 – 1.0).

    Returns
    -------
    dict
        Mapping of criterion name → normalised weight.
    """
    values = np.array(
        [max(0.0, float(preferences.get(c, 0.5))) for c in CRITERIA_ORDER],
        dtype=np.float64,
    )
    total = values.sum()
    if total == 0:
        weights = np.ones_like(values) / len(values)
    else:
        weights = values / total
    return {c: round(float(w), 6) for c, w in zip(CRITERIA_ORDER, weights)}


# ---------------------------------------------------------------------------
# Pairwise-matrix based AHP (full academic version)
# ---------------------------------------------------------------------------

def build_pairwise_matrix(preferences: Dict[str, float]) -> np.ndarray:
    """Build an n×n reciprocal pairwise comparison matrix from slider values.

    The ratio ``preferences[i] / preferences[j]`` is used as the (i, j)
    entry.  Diagonal entries are 1 and the matrix is reciprocal (a_ji = 1/a_ij).
    """
    n = len(CRITERIA_ORDER)
    vals = np.array(
        [max(0.01, float(preferences.get(c, 0.5))) for c in CRITERIA_ORDER],
        dtype=np.float64,
    )
    matrix = np.ones((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i, j] = vals[i] / vals[j]
    return matrix


def eigenvector_weights(matrix: np.ndarray) -> np.ndarray:
    """Extract the principal eigenvector of *matrix* and normalise it."""
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    # The principal eigenvalue is the largest real eigenvalue.
    max_idx = int(np.argmax(np.real(eigenvalues)))
    principal = np.real(eigenvectors[:, max_idx])
    principal = np.abs(principal)
    return principal / principal.sum()


def consistency_ratio(matrix: np.ndarray) -> float:
    """Compute the Consistency Ratio (CR) for the pairwise matrix.

    CR < 0.10 is generally considered acceptable.
    """
    n = matrix.shape[0]
    eigenvalues = np.real(np.linalg.eigvals(matrix))
    lambda_max = float(np.max(eigenvalues))
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = _RI.get(n, 1.49)
    if ri == 0:
        return 0.0
    return ci / ri


# ---------------------------------------------------------------------------
# Unified entry-point
# ---------------------------------------------------------------------------

def get_weights(
    preferences: Dict[str, float],
    method: str = "slider",
) -> Dict[str, float]:
    """Return normalised criterion weights from user preferences.

    Parameters
    ----------
    preferences:
        Mapping of criterion name → importance value (0.0–1.0).
    method:
        ``"slider"`` for simple normalisation, ``"ahp"`` for full pairwise
        eigenvector decomposition.

    Returns
    -------
    dict
        Mapping of criterion name → normalised weight (sums to ~1.0).
    """
    if method == "ahp":
        matrix = build_pairwise_matrix(preferences)
        weights = eigenvector_weights(matrix)
        return {c: round(float(w), 6) for c, w in zip(CRITERIA_ORDER, weights)}
    return normalize_slider_weights(preferences)


__all__ = [
    "CRITERIA_ORDER",
    "normalize_slider_weights",
    "build_pairwise_matrix",
    "eigenvector_weights",
    "consistency_ratio",
    "get_weights",
]
