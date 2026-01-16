"""DJ Playlist Optimizer - Harmonic mixing with Google OR-Tools."""

from djkr8.bpm import bpm_compatible, get_bpm_difference
from djkr8.camelot import (
    get_compatible_keys,
    is_harmonic_compatible,
    parse_camelot_key,
)
from djkr8.models import (
    HarmonicLevel,
    PlaylistResult,
    PlaylistStatistics,
    Track,
    TransitionInfo,
)
from djkr8.optimizer import PlaylistOptimizer

__version__ = "0.1.0"

__all__ = [
    "HarmonicLevel",
    "PlaylistOptimizer",
    "PlaylistResult",
    "PlaylistStatistics",
    "Track",
    "TransitionInfo",
    "bpm_compatible",
    "get_bpm_difference",
    "get_compatible_keys",
    "is_harmonic_compatible",
    "parse_camelot_key",
]
