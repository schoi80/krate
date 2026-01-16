"""SDK usage example for DJ Playlist Optimizer."""

from djkr8 import (
    HarmonicLevel,
    PlaylistOptimizer,
    Track,
)


def main():
    tracks = [
        Track(id="track_001", key="8A", bpm=128),
        Track(id="track_002", key="8B", bpm=130),
        Track(id="track_003", key="9A", bpm=125),
        Track(id="track_004", key="7A", bpm=132),
        Track(id="track_005", key="8A", bpm=64),
        Track(id="track_006", key="10A", bpm=140),
        Track(id="track_007", key="5A", bpm=150),
        Track(id="track_008", key="12B", bpm=75),
        Track(id="track_009", key="1B", bpm=128),
        Track(id="track_010", key="8B", bpm=126),
    ]

    print(f"Optimizing playlist from {len(tracks)} tracks...")

    optimizer = PlaylistOptimizer(
        bpm_tolerance=10,
        allow_halftime_bpm=True,
        max_violation_pct=0.10,
        harmonic_level=HarmonicLevel.STRICT,
        time_limit_seconds=60,
    )

    result = optimizer.optimize(tracks)

    print(f"\n✓ Found playlist with {len(result.playlist)} tracks")
    print(f"  Solver: {result.solver_status} ({result.solver_time_seconds:.2f}s)")

    if result.statistics:
        stats = result.statistics
        print("\n📊 Statistics:")
        print(
            f"  Coverage: {stats.playlist_length}/{stats.total_input_tracks} tracks ({stats.coverage_pct:.1f}%)"
        )
        print(
            f"  Harmonic: {stats.harmonic_transitions}/{len(result.transitions)} transitions ({stats.harmonic_pct:.1f}%)"
        )
        print(
            f"  BPM range: {stats.bpm_range[0]:.0f}-{stats.bpm_range[1]:.0f} (avg: {stats.avg_bpm:.1f})"
        )

    print("\n🎵 Playlist order:")
    for i, track in enumerate(result.playlist, 1):
        print(f"  {i:2d}. {track.id:12s} | {track.key:4s} | {track.bpm:6.1f} BPM")

    if result.transitions:
        print("\n🔗 Transitions:")
        for t in result.transitions:
            harmonic_symbol = "✓" if t.is_harmonic else "⚠️ "
            print(
                f"  {t.from_track.id} → {t.to_track.id} | {harmonic_symbol} | ±{t.bpm_difference:.1f} BPM"
            )


if __name__ == "__main__":
    main()
