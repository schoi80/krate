"""Command-line interface for DJ playlist optimizer."""

import argparse
import json
import logging
import sys
from pathlib import Path

from dj_playlist_optimizer import (
    HarmonicLevel,
    PlaylistOptimizer,
    Track,
)

logger = logging.getLogger(__name__)


def load_tracks_from_json(filepath: Path) -> list[Track]:
    """Load tracks from JSON file."""
    logger.debug(f"Loading tracks from {filepath}")
    with open(filepath) as f:
        data = json.load(f)

    tracks_data = data.get("tracks", data)

    if not isinstance(tracks_data, list):
        raise ValueError("JSON must contain a 'tracks' array or be an array of tracks")

    tracks = []
    for item in tracks_data:
        if not isinstance(item, dict):
            raise ValueError(f"Each track must be a dictionary, got: {type(item)}")

        required = ["id", "key", "bpm"]
        missing = [f for f in required if f not in item]
        if missing:
            raise ValueError(f"Track missing required fields: {missing}")

        tracks.append(
            Track(
                id=item["id"],
                key=item["key"],
                bpm=float(item["bpm"]),
                energy=int(item.get("energy", 5)),
                duration=float(item.get("duration", 0.0)),
            )
        )

    logger.info(f"Loaded {len(tracks)} tracks from {filepath}")
    return tracks


def save_result_to_json(result, filepath: Path):
    """Save optimization result to JSON file."""
    logger.debug(f"Saving results to {filepath}")
    output = {
        "playlist": [{"id": t.id, "key": t.key, "bpm": t.bpm} for t in result.playlist],
        "transitions": [
            {
                "from": t.from_track.id,
                "to": t.to_track.id,
                "is_harmonic": t.is_harmonic,
                "bpm_difference": t.bpm_difference,
            }
            for t in result.transitions
        ],
        "statistics": {
            "total_input_tracks": result.statistics.total_input_tracks,
            "playlist_length": result.statistics.playlist_length,
            "coverage_pct": round(result.statistics.coverage_pct, 2),
            "harmonic_transitions": result.statistics.harmonic_transitions,
            "non_harmonic_transitions": result.statistics.non_harmonic_transitions,
            "harmonic_pct": round(result.statistics.harmonic_pct, 2),
            "avg_bpm": round(result.statistics.avg_bpm, 2),
            "bpm_range": [
                result.statistics.bpm_range[0],
                result.statistics.bpm_range[1],
            ],
        }
        if result.statistics
        else {},
        "solver": {
            "status": result.solver_status,
            "time_seconds": round(result.solver_time_seconds, 3),
        },
    }

    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"Results saved to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Optimize DJ playlists for harmonic mixing using OR-Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s tracks.json
  %(prog)s tracks.json --bpm-tolerance 8 --harmonic-level moderate
  %(prog)s tracks.json --output result.json --time-limit 120
  %(prog)s tracks.json --no-halftime --max-violations 0.05
        """,
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Input JSON file with tracks (format: {tracks: [{id, key, bpm}, ...]})",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file for results (default: print to stdout)",
    )

    parser.add_argument(
        "--bpm-tolerance",
        type=float,
        default=10.0,
        metavar="N",
        help="Maximum BPM difference for direct match (default: 10)",
    )

    parser.add_argument(
        "--halftime/--no-halftime",
        dest="allow_halftime",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable halftime and doubletime BPM matching (default: enabled)",
    )

    parser.add_argument(
        "--max-violations",
        type=float,
        default=0.10,
        metavar="PCT",
        help="Maximum percentage of non-harmonic transitions (default: 0.10 = 10%%)",
    )

    parser.add_argument(
        "--harmonic-level",
        type=str,
        choices=["strict", "moderate", "relaxed"],
        default="strict",
        help="Harmonic compatibility level (default: strict)",
    )

    parser.add_argument(
        "--time-limit",
        type=float,
        default=60.0,
        metavar="SEC",
        help="Solver time limit in seconds (default: 60)",
    )

    parser.add_argument(
        "--max-duration",
        type=float,
        metavar="SEC",
        help="Maximum total playlist duration in seconds",
    )

    parser.add_argument(
        "--energy-weight",
        type=float,
        default=0.0,
        metavar="W",
        help="Weight for energy level optimization (default: 0.0)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG)",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    args = parser.parse_args()

    if args.verbose == 0:
        log_level = logging.WARNING
    elif args.verbose == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    try:
        tracks = load_tracks_from_json(args.input)
    except Exception as e:
        logger.error(f"Failed to load tracks: {e}")
        print(f"Error loading tracks: {e}", file=sys.stderr)
        return 1

    print(f"Loaded {len(tracks)} tracks from {args.input}")

    harmonic_level_map = {
        "strict": HarmonicLevel.STRICT,
        "moderate": HarmonicLevel.MODERATE,
        "relaxed": HarmonicLevel.RELAXED,
    }

    optimizer = PlaylistOptimizer(
        bpm_tolerance=args.bpm_tolerance,
        allow_halftime_bpm=args.allow_halftime,
        max_violation_pct=args.max_violations,
        harmonic_level=harmonic_level_map[args.harmonic_level],
        time_limit_seconds=args.time_limit,
        max_playlist_duration=args.max_duration,
        energy_weight=args.energy_weight,
    )

    print("Optimizing playlist...")
    result = optimizer.optimize(tracks)

    if not result.playlist:
        print(f"No solution found. Solver status: {result.solver_status}", file=sys.stderr)
        return 1

    print(f"\n✓ Found playlist with {len(result.playlist)} tracks")
    print(f"  Solver: {result.solver_status} ({result.solver_time_seconds:.2f}s)")

    if result.statistics:
        stats = result.statistics
        print(f"  Coverage: {stats.coverage_pct:.1f}% of input tracks")
        print(
            f"  Harmonic: {stats.harmonic_transitions}/{stats.harmonic_transitions + stats.non_harmonic_transitions} transitions ({stats.harmonic_pct:.1f}%)"
        )
        print(
            f"  BPM range: {stats.bpm_range[0]:.0f}-{stats.bpm_range[1]:.0f} (avg: {stats.avg_bpm:.1f})"
        )
        total_duration = sum(t.duration for t in result.playlist)
        if total_duration > 0:
            print(f"  Total Duration: {total_duration:.0f}s")
        avg_energy = sum(t.energy for t in result.playlist) / len(result.playlist)
        print(f"  Average Energy: {avg_energy:.1f}")

    if args.output:
        save_result_to_json(result, args.output)
        print(f"\nResults saved to {args.output}")
    else:
        print("\nPlaylist order:")
        for i, track in enumerate(result.playlist, 1):
            print(
                f"  {i:2d}. {track.id:20s} {track.key:4s} {track.bpm:6.1f} BPM "
                f"(Energy: {track.energy:2d}, Duration: {track.duration:4.0f}s)"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
