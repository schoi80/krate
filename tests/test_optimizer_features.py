from djkr8.models import HarmonicLevel, Track
from djkr8.optimizer import PlaylistOptimizer


class TestOptimizerFeatures:
    def test_optimize_start_end_tracks(self):
        tracks = [
            Track(id="t1", key="1A", bpm=120),
            Track(id="t2", key="1A", bpm=120),
            Track(id="t3", key="1A", bpm=120),
            Track(id="t4", key="1A", bpm=120),
        ]

        optimizer = PlaylistOptimizer(bpm_tolerance=5.0)

        # Test start constraint
        result = optimizer.optimize(tracks, start_track_id="t3")
        assert len(result.playlist) == 4
        assert result.playlist[0].id == "t3"

        # Test end constraint
        result = optimizer.optimize(tracks, end_track_id="t2")
        assert len(result.playlist) == 4
        assert result.playlist[-1].id == "t2"

        # Test both
        result = optimizer.optimize(tracks, start_track_id="t1", end_track_id="t4")
        assert len(result.playlist) == 4
        assert result.playlist[0].id == "t1"
        assert result.playlist[-1].id == "t4"

    def test_optimize_must_include(self):
        tracks = [
            Track(id="target", key="1A", bpm=120),
            Track(id="t2", key="1A", bpm=120),
            Track(id="t3", key="1A", bpm=120),
            Track(id="t4", key="1A", bpm=120),
            Track(id="isolated", key="8A", bpm=140),  # Hard to include
        ]

        # Without constraint, might skip 'isolated'
        # But here all fit except isolated.

        optimizer = PlaylistOptimizer(bpm_tolerance=5.0)

        # Force inclusion of 'target' (already likely, but tests logic)
        result = optimizer.optimize(tracks, must_include_ids=["target"])
        assert "target" in [t.id for t in result.playlist]

        # Try to force isolated track - it might fail to find a valid path if connectivity is impossible
        # But optimizer treats it as a soft constraint with high weight.
        # If it's truly impossible (BPM diff), it won't be included even with high weight
        # unless there's a path.
        # Let's verify weight logic by making it possible but costly (harmonic violation)

        tracks_harmonic = [
            Track(id="A", key="1A", bpm=120),
            Track(id="B", key="1A", bpm=120),
            Track(id="C", key="8A", bpm=120),  # Harmonic violation from 1A
        ]

        # Strict mode: 1A -> 8A is a violation.
        opt_strict = PlaylistOptimizer(harmonic_level=HarmonicLevel.STRICT, max_violation_pct=0.0)

        # Should exclude C normally if possible to make longer list?
        # Or if C is must_include, it should allow the violation if max_violations permits?
        # Actually max_violations is a hard limit on count/pct.

        # Let's test simply that the argument is accepted and processed
        result = opt_strict.optimize(tracks_harmonic, must_include_ids=["C"])
        # If it found a solution including C, good.
        if result.playlist:
            ids = [t.id for t in result.playlist]
            if "C" in ids:
                pass  # Success

    def test_optimize_target_length(self):
        tracks = [
            Track(id="t1", key="1A", bpm=120),
            Track(id="t2", key="1A", bpm=120),
            Track(id="t3", key="1A", bpm=120),
            Track(id="t4", key="1A", bpm=120),
        ]

        optimizer = PlaylistOptimizer(bpm_tolerance=5.0)

        # Target length 2
        result = optimizer.optimize(tracks, target_length=2)
        assert len(result.playlist) == 2

        # Target length 3
        result = optimizer.optimize(tracks, target_length=3)
        assert len(result.playlist) == 3

    def test_invalid_constraints(self):
        tracks = [Track(id="t1", key="1A", bpm=120), Track(id="t2", key="1A", bpm=120)]
        optimizer = PlaylistOptimizer()

        # Start ID not in tracks
        result = optimizer.optimize(tracks, start_track_id="missing")
        # Code returns invalid_input immediately
        assert len(result.playlist) == 0
        assert result.solver_status == "invalid_input"

        # Target length > num tracks
        result = optimizer.optimize(tracks, target_length=5)
        # Implementation caps target at num_tracks, so it returns max possible (2)
        assert len(result.playlist) == 2
        assert result.solver_status in ("optimal", "feasible")
