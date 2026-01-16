import pytest

from djkr8.models import PlaylistStatistics, Track


class TestModels:
    def test_track_validation(self):
        # Test empty ID
        with pytest.raises(ValueError, match="Track id cannot be empty"):
            Track(id="", key="1A", bpm=120)

        # Test invalid BPM
        with pytest.raises(ValueError, match="Invalid BPM"):
            Track(id="t1", key="1A", bpm=0)

        # Test invalid Key
        with pytest.raises(ValueError, match="Invalid Camelot key"):
            Track(id="t1", key="X", bpm=120)

        # Test invalid Energy
        with pytest.raises(ValueError, match="Energy must be between"):
            Track(id="t1", key="1A", bpm=120, energy=11)

        # Test negative Duration
        with pytest.raises(ValueError, match="Duration cannot be negative"):
            Track(id="t1", key="1A", bpm=120, duration=-1.0)

    def test_statistics_edge_cases(self):
        # Zero tracks -> coverage
        stats = PlaylistStatistics(
            total_input_tracks=0,
            playlist_length=0,
            harmonic_transitions=0,
            non_harmonic_transitions=0,
            avg_bpm=0,
            bpm_range=(0, 0),
        )
        assert stats.coverage_pct == 0.0

        # Zero transitions -> harmonic pct
        stats.total_input_tracks = 1
        stats.playlist_length = 1
        # No transitions if length 1
        assert stats.harmonic_pct == 100.0
