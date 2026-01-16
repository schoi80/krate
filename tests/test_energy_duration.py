import pytest

from dj_playlist_optimizer.models import Track
from dj_playlist_optimizer.optimizer import PlaylistOptimizer


class TestEnergyAndDuration:
    def test_energy_level_objective(self):
        # track_high has higher energy, track_low has lower energy
        # both are compatible with track_start, but track_high and track_low
        # are NOT compatible with each other (different keys)
        tracks = [
            Track(id="start", key="8A", bpm=120, energy=3),
            Track(id="high", key="8A", bpm=120, energy=5),
            Track(id="low", key="10A", bpm=120, energy=1),
        ]

        # Now track_low is not compatible with start (8A vs 10A strict)
        # Wait, 8A and 10A are not compatible in STRICT level.
        # Let's make them incompatible by BPM to be sure.
        tracks = [
            Track(id="start", key="8A", bpm=120, energy=3),
            Track(id="high", key="8A", bpm=120, energy=5),
            Track(id="low", key="8A", bpm=150, energy=5),  # Incompatible BPM
        ]

        # Now it should pick start -> high (or high -> start)
        optimizer = PlaylistOptimizer(energy_weight=10.0, bpm_tolerance=5)
        result = optimizer.optimize(tracks)

        assert len(result.playlist) == 2
        assert {t.id for t in result.playlist} == {"start", "high"}

    def test_max_duration_constraint(self):
        tracks = [
            Track(id="t1", key="8A", bpm=120, duration=180),  # 3 min
            Track(id="t2", key="8A", bpm=120, duration=180),  # 3 min
            Track(id="t3", key="8A", bpm=120, duration=180),  # 3 min
        ]

        # Max duration 400s should only allow 2 tracks (360s)
        optimizer = PlaylistOptimizer(max_playlist_duration=400.0)
        result = optimizer.optimize(tracks)

        assert len(result.playlist) == 2
        assert sum(t.duration for t in result.playlist) <= 400.0

    def test_track_validation(self):
        with pytest.raises(ValueError, match="Energy must be between 1 and 5"):
            Track(id="bad", key="8A", bpm=120, energy=6)

        with pytest.raises(ValueError, match="Duration cannot be negative"):
            Track(id="bad", key="8A", bpm=120, duration=-1.0)
