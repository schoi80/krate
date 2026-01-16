"""Data models for DJ playlist optimizer."""

from dataclasses import dataclass, field
from enum import Enum


class HarmonicLevel(str, Enum):
    """
    Defines which harmonic transitions are considered 'safe' (non-violations).

    - STRICT: Only same key, ±1 hour same letter, same hour different letter
    - MODERATE: Above + ±1 hour different letter (dominant/subdominant)
    - RELAXED: Above + ±3 hours (mood changes)
    """

    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"


@dataclass
class Track:
    """Represents a music track with mixing metadata."""

    id: str
    key: str  # Camelot notation (e.g., "8A", "12B")
    bpm: float
    energy: int = 5
    duration: float = 0.0

    def __post_init__(self):
        """Validate track data."""
        if not self.id:
            raise ValueError("Track id cannot be empty")
        if not isinstance(self.bpm, (int, float)) or self.bpm <= 0:
            raise ValueError(f"Invalid BPM: {self.bpm}")
        # Basic Camelot key validation
        if not self.key or len(self.key) < 2:
            raise ValueError(f"Invalid Camelot key: {self.key}")
        if not (1 <= self.energy <= 10):
            raise ValueError(f"Energy must be between 1 and 10, got: {self.energy}")
        if self.duration < 0:
            raise ValueError(f"Duration cannot be negative, got: {self.duration}")


@dataclass
class TransitionInfo:
    """Information about a transition between two tracks."""

    from_track: Track
    to_track: Track
    is_harmonic: bool
    is_bpm_compatible: bool
    bpm_difference: float


@dataclass
class PlaylistStatistics:
    """Statistics about the generated playlist."""

    total_input_tracks: int
    playlist_length: int
    harmonic_transitions: int
    non_harmonic_transitions: int
    avg_bpm: float
    bpm_range: tuple[float, float]

    @property
    def coverage_pct(self) -> float:
        """Percentage of input tracks included in playlist."""
        if self.total_input_tracks == 0:
            return 0.0
        return (self.playlist_length / self.total_input_tracks) * 100

    @property
    def harmonic_pct(self) -> float:
        """Percentage of harmonic transitions."""
        total_transitions = self.harmonic_transitions + self.non_harmonic_transitions
        if total_transitions == 0:
            return 100.0
        return (self.harmonic_transitions / total_transitions) * 100


@dataclass
class PlaylistResult:
    """Result from playlist optimization."""

    playlist: list[Track]
    transitions: list[TransitionInfo] = field(default_factory=list)
    statistics: PlaylistStatistics | None = None
    solver_status: str = "unknown"
    solver_time_seconds: float = 0.0

    def __post_init__(self):
        """Calculate statistics if not provided."""
        if self.statistics is None and self.playlist:
            self._calculate_statistics()

    def _calculate_statistics(self):
        """Calculate playlist statistics."""
        if not self.playlist:
            return

        harmonic = sum(1 for t in self.transitions if t.is_harmonic)
        non_harmonic = len(self.transitions) - harmonic

        bpms = [t.bpm for t in self.playlist]
        avg_bpm = sum(bpms) / len(bpms) if bpms else 0.0
        bpm_range = (min(bpms), max(bpms)) if bpms else (0.0, 0.0)

        self.statistics = PlaylistStatistics(
            total_input_tracks=0,  # Set by optimizer
            playlist_length=len(self.playlist),
            harmonic_transitions=harmonic,
            non_harmonic_transitions=non_harmonic,
            avg_bpm=avg_bpm,
            bpm_range=bpm_range,
        )
