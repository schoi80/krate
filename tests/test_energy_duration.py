import pytest

from djkr8.models import Track
from djkr8.optimizer import PlaylistOptimizer


class TestEnergyAndDuration:
    def test_energy_level_objective(self):
        tracks = [
            Track(id="start", key="8A", bpm=120, energy=3),
            Track(id="high", key="8A", bpm=120, energy=4),
            Track(id="low", key="8A", bpm=150, energy=5),
        ]

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

    def test_max_energy_increase_constraint(self):
        tracks = [
            Track(id="t1", key="8A", bpm=120, energy=1),
            Track(id="t2", key="8A", bpm=120, energy=2),
            Track(id="t3", key="8A", bpm=120, energy=4),
        ]

        optimizer = PlaylistOptimizer(bpm_tolerance=10, enforce_energy_flow=True)
        result = optimizer.optimize(tracks)

        assert len(result.playlist) == 2
        assert result.playlist[0].id == "t1"
        assert result.playlist[1].id == "t2"

    def test_energy_increase_when_flow_disabled(self):
        tracks = [
            Track(id="t1", key="8A", bpm=120, energy=1),
            Track(id="t2", key="8A", bpm=120, energy=5),
        ]

        optimizer = PlaylistOptimizer(bpm_tolerance=10, enforce_energy_flow=False)
        result = optimizer.optimize(tracks)

        assert len(result.playlist) == 2
