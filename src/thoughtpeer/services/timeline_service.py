"""Mood timeline aggregation with moving average and trend detection."""

from __future__ import annotations

from typing import Literal

import aiosqlite

_MOOD_SCORE = {
    "terrible": 1.0,
    "bad": 2.0,
    "neutral": 3.0,
    "good": 4.0,
    "great": 5.0,
}

_WINDOW = 7


def _linreg_slope(ys: list[float]) -> float:
    """Slope of simple linear regression y ~ x where x = 0..n-1."""
    n = len(ys)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2
    mean_y = sum(ys) / n
    num = sum((i - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den if den else 0.0


def _moving_average(values: list[float], window: int = _WINDOW) -> list[float | None]:
    """Trailing moving average — None until we have `window` samples."""
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(sum(values[i + 1 - window : i + 1]) / window)
    return out


def classify_trend(scores: list[float]) -> Literal["improving", "stable", "declining"]:
    """Classify mood trend from most recent `_WINDOW` scores."""
    sample = scores[-_WINDOW:]
    if len(sample) < 2:
        return "stable"
    slope = _linreg_slope(sample)
    if slope > 0.15:
        return "improving"
    if slope < -0.15:
        return "declining"
    return "stable"


async def build_timeline(db: aiosqlite.Connection, *, user_id: int) -> dict:
    """Return list of points {date, mood, score, moving_avg} + mood_trend."""
    cursor = await db.execute(
        """SELECT date(created_at) AS d, mood FROM entries
           WHERE user_id = ? AND mood IS NOT NULL
           ORDER BY created_at ASC""",
        (user_id,),
    )
    rows = await cursor.fetchall()

    # Collapse per day — take the daily average if multiple entries that day.
    per_day: dict[str, list[float]] = {}
    for r in rows:
        score = _MOOD_SCORE.get(r["mood"])
        if score is None:
            continue
        per_day.setdefault(r["d"], []).append(score)

    dates = sorted(per_day.keys())
    scores = [sum(per_day[d]) / len(per_day[d]) for d in dates]
    mavg = _moving_average(scores)

    points = [
        {"date": d, "score": round(s, 2), "moving_avg": round(m, 2) if m is not None else None}
        for d, s, m in zip(dates, scores, mavg)
    ]

    return {
        "points": points,
        "mood_trend": classify_trend(scores),
        "window": _WINDOW,
        "sample_size": len(scores),
    }
