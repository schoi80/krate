"""Integration tests for the playlist optimizer."""

from djkr8 import (
    HarmonicLevel,
    PlaylistOptimizer,
    Track,
)


class TestPlaylistOptimizerIntegration:
    def test_empty_tracks(self):
        optimizer = PlaylistOptimizer()
        result = optimizer.optimize([])

        assert result.playlist == []
        assert result.solver_status == "empty_input"

    def test_single_track(self):
        optimizer = PlaylistOptimizer()
        tracks = [Track(id="track_1", key="8A", bpm=128)]

        result = optimizer.optimize(tracks)

        assert len(result.playlist) == 1
        assert result.playlist[0].id == "track_1"
        assert result.solver_status == "single_track"
        assert result.statistics.playlist_length == 1

    def test_two_compatible_tracks(self):
        optimizer = PlaylistOptimizer()
        tracks = [
            Track(id="track_1", key="8A", bpm=128),
            Track(id="track_2", key="8B", bpm=130),
        ]

        result = optimizer.optimize(tracks)

        assert len(result.playlist) == 2
        assert result.statistics.harmonic_transitions >= 1
        assert result.statistics.non_harmonic_transitions == 0

    def test_halftime_matching(self):
        optimizer = PlaylistOptimizer(allow_halftime_bpm=True)
        tracks = [
            Track(id="track_1", key="8A", bpm=128),
            Track(id="track_2", key="8A", bpm=64),
        ]

        result = optimizer.optimize(tracks)

        assert len(result.playlist) == 2
        if len(result.transitions) > 0:
            assert result.transitions[0].bpm_difference == 0.0

    def test_halftime_disabled(self):
        optimizer = PlaylistOptimizer(allow_halftime_bpm=False)
        tracks = [
            Track(id="track_1", key="8A", bpm=128),
            Track(id="track_2", key="8A", bpm=64),
        ]

        result = optimizer.optimize(tracks)

        assert len(result.playlist) <= 1

    def test_harmonic_strict_vs_moderate(self):
        tracks = [
            Track(id="track_1", key="8A", bpm=128),
            Track(id="track_2", key="9B", bpm=130),
        ]

        strict_optimizer = PlaylistOptimizer(harmonic_level=HarmonicLevel.STRICT)
        _strict_result = strict_optimizer.optimize(tracks)

        moderate_optimizer = PlaylistOptimizer(harmonic_level=HarmonicLevel.MODERATE)
        moderate_result = moderate_optimizer.optimize(tracks)

        if len(moderate_result.playlist) == 2:
            assert moderate_result.statistics.harmonic_transitions >= 1

    def test_complex_playlist(self):
        optimizer = PlaylistOptimizer(
            bpm_tolerance=10,
            allow_halftime_bpm=True,
            max_violation_pct=0.20,
            harmonic_level=HarmonicLevel.STRICT,
        )

        tracks = [
            Track(id="track_1", key="8A", bpm=128),
            Track(id="track_2", key="8B", bpm=130),
            Track(id="track_3", key="9A", bpm=125),
            Track(id="track_4", key="7A", bpm=132),
            Track(id="track_5", key="8A", bpm=64),
        ]

        result = optimizer.optimize(tracks)

        assert len(result.playlist) >= 3
        assert result.statistics.coverage_pct > 0
        assert result.solver_status in ["optimal", "feasible"]

    def test_bpm_incompatible_tracks(self):
        optimizer = PlaylistOptimizer(bpm_tolerance=5, allow_halftime_bpm=False)
        tracks = [
            Track(id="track_1", key="8A", bpm=128),
            Track(id="track_2", key="8A", bpm=100),
            Track(id="track_3", key="8A", bpm=150),
        ]

        result = optimizer.optimize(tracks)

        assert len(result.playlist) <= 1

    def test_all_same_key_different_bpm(self):
        optimizer = PlaylistOptimizer(bpm_tolerance=10)
        tracks = [
            Track(id="track_1", key="8A", bpm=128),
            Track(id="track_2", key="8A", bpm=130),
            Track(id="track_3", key="8A", bpm=125),
            Track(id="track_4", key="8A", bpm=132),
        ]

        result = optimizer.optimize(tracks)

        assert len(result.playlist) >= 3
        assert result.statistics.harmonic_pct == 100.0

    def test_violation_threshold(self):
        optimizer = PlaylistOptimizer(max_violation_pct=0.0, harmonic_level=HarmonicLevel.STRICT)

        tracks = [
            Track(id="track_1", key="8A", bpm=128),
            Track(id="track_2", key="10A", bpm=130),
        ]

        result = optimizer.optimize(tracks)

        if len(result.playlist) == 2:
            assert result.statistics.non_harmonic_transitions == 0

    def test_statistics_calculations(self):
        optimizer = PlaylistOptimizer()
        tracks = [
            Track(id="track_1", key="8A", bpm=120),
            Track(id="track_2", key="8B", bpm=130),
            Track(id="track_3", key="9A", bpm=140),
        ]

        result = optimizer.optimize(tracks)

        assert result.statistics is not None
        assert result.statistics.total_input_tracks == 3
        assert result.statistics.avg_bpm > 0
        assert result.statistics.bpm_range[0] <= result.statistics.bpm_range[1]
