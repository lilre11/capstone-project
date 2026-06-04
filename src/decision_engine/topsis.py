"""TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution).

Ranks smartphone alternatives based on their closeness to the ideal solution
using AHP-derived criterion weights.

The full pipeline is:
  1. Build the decision matrix (m phones × n criteria).
  2. Normalise using vector normalisation.
  3. Apply AHP weights to obtain the weighted normalised matrix.
  4. Determine the ideal best (A⁺) and ideal worst (A⁻).
  5. Compute Euclidean separation distances S⁺ and S⁻.
  6. Compute the closeness coefficient C⁺ = S⁻ / (S⁺ + S⁻).
  7. Rank by descending C⁺.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from src.decision_engine.ahp import CRITERIA_ORDER

# Direction of each criterion:  "max" = benefit (higher is better),
#                                "min" = cost   (lower  is better).
CRITERIA_DIRECTION: Dict[str, str] = {
    "price": "min",
    "battery": "max",
    "camera_score": "max",
    "antutu": "max",
    "storage": "max",
    "weight": "min",
    "charging": "max",
    "screen_ratio": "max",
}


def build_decision_matrix(
    smartphones: List[Dict[str, Any]],
    criteria: Sequence[str] = CRITERIA_ORDER,
) -> np.ndarray:
    """Create the m × n decision matrix from phone spec dicts.

    Parameters
    ----------
    smartphones:
        List of dicts, each containing at least the keys in *criteria*.
    criteria:
        Ordered list of criterion names.

    Returns
    -------
    np.ndarray
        Shape (m, n) float64 matrix.
    """
    m = len(smartphones)
    n = len(criteria)
    matrix = np.zeros((m, n), dtype=np.float64)
    for i, phone in enumerate(smartphones):
        for j, crit in enumerate(criteria):
            matrix[i, j] = float(phone[crit])
    return matrix


def normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    """Vector-normalise each column: x_ij / sqrt(sum(x_ij²)).

    Returns
    -------
    np.ndarray
        Normalised matrix with the same shape.
    """
    col_norms = np.sqrt((matrix ** 2).sum(axis=0))
    # Avoid division by zero.
    col_norms = np.where(col_norms == 0, 1.0, col_norms)
    return matrix / col_norms


def apply_weights(
    normalized: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    """Multiply each column of the normalised matrix by its AHP weight.

    Parameters
    ----------
    normalized:
        Normalised decision matrix (m, n).
    weights:
        Weight vector of length n.

    Returns
    -------
    np.ndarray
        Weighted normalised matrix (m, n).
    """
    return normalized * weights


def find_ideal_solutions(
    weighted: np.ndarray,
    criteria: Sequence[str] = CRITERIA_ORDER,
    directions: Optional[Dict[str, str]] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Determine ideal best (A⁺) and ideal worst (A⁻) vectors.

    For *benefit* criteria the ideal best is the column maximum and the ideal
    worst is the column minimum; for *cost* criteria the logic is inverted.

    Returns
    -------
    tuple
        (ideal_best, ideal_worst) each of shape (n,).
    """
    if directions is None:
        directions = CRITERIA_DIRECTION

    n = weighted.shape[1]
    ideal_best = np.zeros(n, dtype=np.float64)
    ideal_worst = np.zeros(n, dtype=np.float64)

    for j, crit in enumerate(criteria):
        direction = directions.get(crit, "max")
        if direction == "max":
            ideal_best[j] = weighted[:, j].max()
            ideal_worst[j] = weighted[:, j].min()
        else:  # min / cost
            ideal_best[j] = weighted[:, j].min()
            ideal_worst[j] = weighted[:, j].max()

    return ideal_best, ideal_worst


def calculate_separation(
    weighted: np.ndarray,
    ideal_best: np.ndarray,
    ideal_worst: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate Euclidean separation distances S⁺ and S⁻ for each alternative.

    Returns
    -------
    tuple
        (s_plus, s_minus) each of shape (m,).
    """
    s_plus = np.sqrt(((weighted - ideal_best) ** 2).sum(axis=1))
    s_minus = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))
    return s_plus, s_minus


def calculate_closeness(
    s_plus: np.ndarray,
    s_minus: np.ndarray,
) -> np.ndarray:
    """Compute closeness coefficient C⁺ = S⁻ / (S⁺ + S⁻).

    Returns
    -------
    np.ndarray
        Closeness coefficients of shape (m,).  Range [0, 1].
    """
    denominator = s_plus + s_minus
    denominator = np.where(denominator == 0, 1.0, denominator)
    return s_minus / denominator


def rank_smartphones(
    smartphones: List[Dict[str, Any]],
    weights: Dict[str, float],
    criteria: Sequence[str] = CRITERIA_ORDER,
    directions: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Run the complete TOPSIS pipeline and return ranked results.

    Parameters
    ----------
    smartphones:
        List of phone-spec dicts (each must contain keys matching *criteria*
        plus an ``"id"`` and ``"model_name"`` key).
    weights:
        Criterion → weight mapping (should sum to ~1.0).
    criteria:
        Ordered criterion names.
    directions:
        Criterion → "max" or "min" direction.

    Returns
    -------
    dict
        ``method``, ``top_match``, ``rankings`` (list sorted by rank), and
        all intermediate matrices for transparency.
    """
    if directions is None:
        directions = CRITERIA_DIRECTION

    weight_arr = np.array([weights[c] for c in criteria], dtype=np.float64)

    # 1. Decision matrix
    decision_matrix = build_decision_matrix(smartphones, criteria)

    # 2. Normalise
    normalized = normalize_matrix(decision_matrix)

    # 3. Apply weights
    weighted = apply_weights(normalized, weight_arr)

    # 4. Ideal solutions
    ideal_best, ideal_worst = find_ideal_solutions(weighted, criteria, directions)

    # 5. Separation
    s_plus, s_minus = calculate_separation(weighted, ideal_best, ideal_worst)

    # 6. Closeness coefficient
    closeness = calculate_closeness(s_plus, s_minus)

    # 7. Rank (descending closeness → rank 1 is best)
    rank_order = np.argsort(-closeness)  # indices sorted by descending C⁺

    rankings: List[Dict[str, Any]] = []
    for rank_position, idx in enumerate(rank_order, start=1):
        phone = smartphones[idx]
        rankings.append({
            "rank": rank_position,
            "id": phone.get("id", f"phone_{idx}"),
            "model_name": phone.get("model_name", f"Phone {idx}"),
            "brand": phone.get("brand", ""),
            "closeness_coefficient": round(float(closeness[idx]), 4),
            "score": round(float(closeness[idx]) * 100, 2),
            "s_plus": round(float(s_plus[idx]), 5),
            "s_minus": round(float(s_minus[idx]), 5),
            "weighted_normalized": {
                c: round(float(weighted[idx, j]), 5)
                for j, c in enumerate(criteria)
            },
        })

    top_match = rankings[0] if rankings else None

    return {
        "method": "AHP + TOPSIS",
        "top_match": top_match,
        "rankings": rankings,
        "weights_used": {c: round(float(w), 6) for c, w in zip(criteria, weight_arr)},
        "ideal_best": {c: round(float(v), 5) for c, v in zip(criteria, ideal_best)},
        "ideal_worst": {c: round(float(v), 5) for c, v in zip(criteria, ideal_worst)},
        "criteria_directions": {c: directions.get(c, "max") for c in criteria},
    }


__all__ = [
    "CRITERIA_DIRECTION",
    "build_decision_matrix",
    "normalize_matrix",
    "apply_weights",
    "find_ideal_solutions",
    "calculate_separation",
    "calculate_closeness",
    "rank_smartphones",
]
