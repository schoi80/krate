"""Tests for BPM compatibility with halftime/doubletime support."""

from djkr8.bpm import bpm_compatible, get_bpm_difference


class TestBpmCompatible:
    def test_direct_match_within_tolerance(self):
        assert bpm_compatible(128, 130, tolerance=10) is True
        assert bpm_compatible(128, 132, tolerance=10) is True
        assert bpm_compatible(128, 138, tolerance=10) is True
        assert bpm_compatible(128, 118, tolerance=10) is True

    def test_direct_match_exact(self):
        assert bpm_compatible(128, 128, tolerance=10) is True
        assert bpm_compatible(75, 75, tolerance=5) is True

    def test_direct_match_outside_tolerance(self):
        assert bpm_compatible(128, 100, tolerance=10) is False
        assert bpm_compatible(128, 150, tolerance=10) is False

    def test_halftime_perfect_match(self):
        assert bpm_compatible(128, 64, tolerance=10) is True
        assert bpm_compatible(64, 128, tolerance=10) is True
        assert bpm_compatible(150, 75, tolerance=10) is True

    def test_halftime_with_tolerance(self):
        assert bpm_compatible(140, 68, tolerance=10) is True
        assert bpm_compatible(132, 64, tolerance=10) is True

    def test_doubletime_perfect_match(self):
        assert bpm_compatible(75, 150, tolerance=10) is True
        assert bpm_compatible(64, 128, tolerance=10) is True

    def test_doubletime_with_tolerance(self):
        assert bpm_compatible(68, 140, tolerance=10) is True
        assert bpm_compatible(72, 150, tolerance=10) is True

    def test_halftime_disabled(self):
        assert bpm_compatible(128, 64, tolerance=10, allow_halftime=False) is False
        assert bpm_compatible(75, 150, tolerance=10, allow_halftime=False) is False
        assert bpm_compatible(128, 130, tolerance=10, allow_halftime=False) is True

    def test_edge_cases(self):
        assert bpm_compatible(0, 0, tolerance=10) is True
        assert bpm_compatible(300, 150, tolerance=10) is True

    def test_realistic_dnb_halftime(self):
        assert bpm_compatible(175, 87.5, tolerance=5) is True
        assert bpm_compatible(174, 87, tolerance=5) is True

    def test_realistic_dubstep_house(self):
        assert bpm_compatible(140, 70, tolerance=5) is True
        assert bpm_compatible(128, 64, tolerance=5) is True


class TestGetBpmDifference:
    def test_direct_difference(self):
        assert get_bpm_difference(128, 130) == 2.0
        assert get_bpm_difference(130, 128) == 2.0
        assert get_bpm_difference(100, 150) == 25.0

    def test_halftime_difference(self):
        assert get_bpm_difference(128, 64) == 0.0
        assert get_bpm_difference(64, 128) == 0.0

    def test_halftime_with_offset(self):
        assert get_bpm_difference(140, 68) == 4.0
        assert get_bpm_difference(132, 64) == 4.0

    def test_doubletime_difference(self):
        assert get_bpm_difference(75, 150) == 0.0
        assert get_bpm_difference(150, 75) == 0.0

    def test_minimum_difference_chosen(self):
        diff = get_bpm_difference(130, 128)
        assert diff == 2.0

        diff = get_bpm_difference(65, 128)
        assert diff == 1.0

    def test_halftime_disabled(self):
        assert get_bpm_difference(128, 64, allow_halftime=False) == 64.0
        assert get_bpm_difference(75, 150, allow_halftime=False) == 75.0
        assert get_bpm_difference(128, 130, allow_halftime=False) == 2.0

    def test_exact_match(self):
        assert get_bpm_difference(128, 128) == 0.0
        assert get_bpm_difference(75, 75) == 0.0
