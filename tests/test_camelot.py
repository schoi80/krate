"""Tests for Camelot wheel harmonic compatibility logic."""

import pytest

from djkr8.camelot import (
    get_compatible_keys,
    get_hour_distance,
    is_harmonic_compatible,
    parse_camelot_key,
)
from djkr8.models import HarmonicLevel


class TestParseCamelotKey:
    def test_valid_keys(self):
        assert parse_camelot_key("8A") == (8, "A")
        assert parse_camelot_key("12B") == (12, "B")
        assert parse_camelot_key("1A") == (1, "A")
        assert parse_camelot_key("1B") == (1, "B")

    def test_lowercase_normalized(self):
        assert parse_camelot_key("8a") == (8, "A")
        assert parse_camelot_key("12b") == (12, "B")

    def test_whitespace_stripped(self):
        assert parse_camelot_key(" 8A ") == (8, "A")
        assert parse_camelot_key("  12B  ") == (12, "B")

    def test_invalid_letter(self):
        with pytest.raises(ValueError, match="Invalid Camelot key letter"):
            parse_camelot_key("8C")
        with pytest.raises(ValueError, match="Invalid Camelot key letter"):
            parse_camelot_key("8X")

    def test_invalid_hour(self):
        with pytest.raises(ValueError, match="Camelot hour must be 1-12"):
            parse_camelot_key("0A")
        with pytest.raises(ValueError, match="Camelot hour must be 1-12"):
            parse_camelot_key("13A")
        with pytest.raises(ValueError, match="Camelot hour must be 1-12"):
            parse_camelot_key("-1A")

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid Camelot key"):
            parse_camelot_key("A")
        with pytest.raises(ValueError, match="Invalid Camelot key"):
            parse_camelot_key("")


class TestGetHourDistance:
    def test_adjacent_hours(self):
        assert get_hour_distance(1, 2) == 1
        assert get_hour_distance(8, 9) == 1
        assert get_hour_distance(11, 12) == 1

    def test_circular_distance(self):
        assert get_hour_distance(1, 12) == 1
        assert get_hour_distance(12, 1) == 1

    def test_opposite_hours(self):
        assert get_hour_distance(1, 7) == 6
        assert get_hour_distance(6, 12) == 6

    def test_same_hour(self):
        assert get_hour_distance(8, 8) == 0
        assert get_hour_distance(1, 1) == 0


class TestIsHarmonicCompatible:
    def test_perfect_match(self):
        assert is_harmonic_compatible("8A", "8A") is True
        assert is_harmonic_compatible("12B", "12B") is True

    def test_energy_boost_drop_strict(self):
        assert is_harmonic_compatible("8A", "7A", HarmonicLevel.STRICT) is True
        assert is_harmonic_compatible("8A", "9A", HarmonicLevel.STRICT) is True
        assert is_harmonic_compatible("1A", "12A", HarmonicLevel.STRICT) is True
        assert is_harmonic_compatible("12A", "1A", HarmonicLevel.STRICT) is True

    def test_relative_major_minor_strict(self):
        assert is_harmonic_compatible("8A", "8B", HarmonicLevel.STRICT) is True
        assert is_harmonic_compatible("8B", "8A", HarmonicLevel.STRICT) is True

    def test_dominant_subdominant_not_strict(self):
        assert is_harmonic_compatible("8A", "9B", HarmonicLevel.STRICT) is False
        assert is_harmonic_compatible("8A", "7B", HarmonicLevel.STRICT) is False

    def test_dominant_subdominant_moderate(self):
        assert is_harmonic_compatible("8A", "9B", HarmonicLevel.MODERATE) is True
        assert is_harmonic_compatible("8A", "7B", HarmonicLevel.MODERATE) is True
        assert is_harmonic_compatible("8B", "9A", HarmonicLevel.MODERATE) is True

    def test_mood_changes_relaxed(self):
        assert is_harmonic_compatible("8A", "5A", HarmonicLevel.RELAXED) is True
        assert is_harmonic_compatible("8A", "11A", HarmonicLevel.RELAXED) is True
        assert is_harmonic_compatible("1A", "4A", HarmonicLevel.RELAXED) is True

    def test_mood_changes_not_moderate(self):
        assert is_harmonic_compatible("8A", "5A", HarmonicLevel.MODERATE) is False
        assert is_harmonic_compatible("8A", "11A", HarmonicLevel.STRICT) is False

    def test_too_far_apart(self):
        assert is_harmonic_compatible("8A", "10A", HarmonicLevel.STRICT) is False
        assert is_harmonic_compatible("8A", "6A", HarmonicLevel.MODERATE) is False

    def test_invalid_keys(self):
        assert is_harmonic_compatible("invalid", "8A") is False
        assert is_harmonic_compatible("8A", "invalid") is False


class TestGetCompatibleKeys:
    def test_strict_compatibility_count(self):
        compatible = get_compatible_keys("8A", HarmonicLevel.STRICT)
        assert len(compatible) == 4
        assert "8A" in compatible
        assert "7A" in compatible
        assert "9A" in compatible
        assert "8B" in compatible

    def test_moderate_compatibility_count(self):
        compatible = get_compatible_keys("8A", HarmonicLevel.MODERATE)
        assert len(compatible) == 6
        assert "8A" in compatible
        assert "7A" in compatible
        assert "9A" in compatible
        assert "8B" in compatible
        assert "7B" in compatible
        assert "9B" in compatible

    def test_relaxed_compatibility_count(self):
        compatible = get_compatible_keys("8A", HarmonicLevel.RELAXED)
        assert len(compatible) >= 8
        assert "5A" in compatible
        assert "11A" in compatible

    def test_edge_case_1a(self):
        compatible = get_compatible_keys("1A", HarmonicLevel.STRICT)
        assert "12A" in compatible
        assert "2A" in compatible
        assert "1B" in compatible

    def test_edge_case_12b(self):
        compatible = get_compatible_keys("12B", HarmonicLevel.STRICT)
        assert "11B" in compatible
        assert "1B" in compatible
        assert "12A" in compatible
