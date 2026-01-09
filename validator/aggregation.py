"""
Deterministic aggregation of validator results into a hygiene score and rating.

This module is intentionally independent from validator internals and relies
only on the presence of a severity value for each result item. It exposes a
single pure function, ``aggregate_validator_results``, which accepts an
iterable of validator outputs and returns an explainable score, rating, and
severity counts.
"""
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, MutableMapping, Optional

# Default weights used to penalize findings by severity.
DEFAULT_SEVERITY_WEIGHTS: Mapping[str, int] = {
    "critical": 50,
    "high": 25,
    "medium": 10,
    "low": 5,
    "info": 0,
}

CRITICAL_SEVERITY = "critical"

# Fallback penalty applied when a result has an unrecognized severity label.
UNKNOWN_SEVERITY_WEIGHT = 10

# Rating thresholds, expressed as minimum hygiene score required for each tier.
RATING_THRESHOLDS: Mapping[str, int] = {
    "clean": 90,
    "needs_attention": 60,
}

MAX_SCORE = 100


def _extract_severity(result: Any) -> str:
    """
    Pull a severity label from a validator result without depending on
    validator-specific shapes.

    Accepted patterns:
    - Mapping with a "severity" key
    - Object with a ``severity`` attribute
    - A bare string interpreted directly as the severity label
    """
    if isinstance(result, Mapping) and "severity" in result:
        return str(result["severity"])

    if hasattr(result, "severity"):
        return str(getattr(result, "severity"))

    if isinstance(result, str):
        return result

    return "unknown"


def _rating_from_score(score: int, counts: MutableMapping[str, int]) -> str:
    """
    Convert a hygiene score into a qualitative rating.
    """
    if score >= RATING_THRESHOLDS["clean"] and counts.get(CRITICAL_SEVERITY, 0) == 0:
        return "clean"

    if score >= RATING_THRESHOLDS["needs_attention"]:
        return "needs_attention"

    return "unsafe"


def aggregate_validator_results(
    results: Iterable[Any],
    severity_weights: Optional[Mapping[str, int]] = None,
) -> Mapping[str, Any]:
    """
    Aggregate validator results into a deterministic hygiene score and rating.

    Parameters
    ----------
    results:
        Iterable of validator outputs. Each item should expose a severity label
        via a ``severity`` attribute, ``severity`` mapping key, or be a string
        representing the severity directly.
    severity_weights:
        Optional overrides for the default severity weighting table.

    Returns
    -------
    dict with keys:
        - hygiene_score: int in [0, 100]
        - rating: str, one of {"clean", "needs_attention", "unsafe"}
        - severity_counts: dict of severities observed
        - penalties: explainable penalty breakdown
    """
    weights = {**DEFAULT_SEVERITY_WEIGHTS, **(severity_weights or {})}

    severity_counts: Counter[str] = Counter()
    penalty_by_severity: MutableMapping[str, int] = defaultdict(
        int, {severity: 0 for severity in weights}
    )

    total_penalty = 0

    for result in results:
        severity = _extract_severity(result)
        weight = weights.get(severity, UNKNOWN_SEVERITY_WEIGHT)

        severity_counts[severity] += 1
        penalty_by_severity[severity] += weight
        total_penalty += weight

    hygiene_score = max(0, MAX_SCORE - total_penalty)
    rating = _rating_from_score(hygiene_score, severity_counts)

    severity_counts_output = dict(severity_counts)
    for severity in weights:
        severity_counts_output.setdefault(severity, 0)

    return {
        "hygiene_score": hygiene_score,
        "rating": rating,
        "severity_counts": severity_counts_output,
        "penalties": {
            "total_penalty": total_penalty,
            "by_severity": dict(penalty_by_severity),
            "weights": dict(weights),
            "unknown_weight": UNKNOWN_SEVERITY_WEIGHT,
        },
        "max_score": MAX_SCORE,
    }
