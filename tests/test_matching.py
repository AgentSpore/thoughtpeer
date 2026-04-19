"""Pure-function tests for peer matching math."""

from __future__ import annotations

import math

import pytest

from thoughtpeer.services.matching_service import (
    cosine_similarity,
    tokenize,
)
from thoughtpeer.services.timeline_service import (
    _linreg_slope,
    _moving_average,
    classify_trend,
)


class TestCosineSimilarity:
    def test_identical_bags_are_one(self):
        a = ["stress", "work", "deadline"]
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_disjoint_bags_are_zero(self):
        assert cosine_similarity(["a", "b"], ["c", "d"]) == 0.0

    def test_empty_is_zero(self):
        assert cosine_similarity([], ["a"]) == 0.0
        assert cosine_similarity(["a"], []) == 0.0
        assert cosine_similarity([], []) == 0.0

    def test_partial_overlap_in_unit_interval(self):
        s = cosine_similarity(["a", "b", "c"], ["b", "c", "d"])
        assert 0.0 < s < 1.0

    def test_order_insensitive(self):
        x = cosine_similarity(["a", "b", "c"], ["c", "b", "a"])
        y = cosine_similarity(["a", "b", "c"], ["a", "b", "c"])
        assert x == pytest.approx(y)

    def test_duplicates_count(self):
        # Duplicates increase magnitude but keep similarity bounded.
        s = cosine_similarity(["a", "a", "b"], ["a", "b", "b"])
        # Not identical, not zero.
        assert 0.0 < s < 1.0

    def test_known_value(self):
        # Two 3-word bags sharing 1 token → 1 / sqrt(3)*sqrt(3) = 1/3
        s = cosine_similarity(["a", "b", "c"], ["a", "x", "y"])
        assert s == pytest.approx(1 / 3, abs=1e-6)


class TestTokenize:
    def test_filters_short_and_stopwords(self):
        tokens = tokenize("I am stressed about the deadline at work")
        assert "stressed" in tokens
        assert "deadline" in tokens
        assert "work" in tokens
        assert "the" not in tokens
        assert "i" not in tokens

    def test_empty_input(self):
        assert tokenize("") == []
        assert tokenize(None) == []  # type: ignore[arg-type]


class TestTimelineMath:
    def test_linreg_slope_positive(self):
        assert _linreg_slope([1.0, 2.0, 3.0, 4.0]) == pytest.approx(1.0)

    def test_linreg_slope_flat(self):
        assert _linreg_slope([3.0, 3.0, 3.0]) == pytest.approx(0.0)

    def test_linreg_slope_negative(self):
        assert _linreg_slope([5.0, 4.0, 3.0, 2.0]) == pytest.approx(-1.0)

    def test_moving_average_window(self):
        out = _moving_average([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], window=3)
        # first two are None, then means
        assert out[0] is None and out[1] is None
        assert out[2] == pytest.approx(2.0)
        assert out[7] == pytest.approx(7.0)

    def test_classify_trend_improving(self):
        assert classify_trend([1, 2, 3, 4, 5]) == "improving"

    def test_classify_trend_declining(self):
        assert classify_trend([5, 4, 3, 2, 1]) == "declining"

    def test_classify_trend_stable(self):
        assert classify_trend([3, 3, 3, 3, 3]) == "stable"

    def test_classify_trend_too_few_is_stable(self):
        assert classify_trend([3.0]) == "stable"
        assert classify_trend([]) == "stable"
