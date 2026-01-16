"""BPM compatibility checking with halftime/doubletime support."""

import logging

logger = logging.getLogger(__name__)


def bpm_compatible(
    bpm1: float, bpm2: float, tolerance: float = 10.0, allow_halftime: bool = True
) -> bool:
    """
    Check if two BPMs are mixable.

    Args:
        bpm1: First track's BPM
        bpm2: Second track's BPM
        tolerance: Maximum BPM difference allowed (default: 10)
        allow_halftime: Also check half-time and double-time ratios (default: True)

    Returns:
        True if BPMs are compatible for mixing

    Examples:
        >>> bpm_compatible(128, 130, tolerance=10)  # Direct match
        True
        >>> bpm_compatible(128, 64, tolerance=10)   # Half-time (128 = 64*2)
        True
        >>> bpm_compatible(75, 150, tolerance=10)   # Double-time (75*2 = 150)
        True
        >>> bpm_compatible(140, 68, tolerance=10)   # Half-time with tolerance
        True
        >>> bpm_compatible(128, 100, tolerance=10)  # Too far
        False
    """
    # Direct match: |bpm1 - bpm2| <= tolerance
    if abs(bpm1 - bpm2) <= tolerance:
        return True

    if not allow_halftime:
        return False

    # Half-time: bpm1 matches half of bpm2
    # Example: 128 BPM matches 64 BPM (128/2 = 64)
    if abs(bpm1 - bpm2 / 2) <= tolerance:
        return True

    # Double-time: bpm1 matches double of bpm2
    # Example: 75 BPM matches 150 BPM (75*2 = 150)
    return abs(bpm1 - bpm2 * 2) <= tolerance


def get_bpm_difference(bpm1: float, bpm2: float, allow_halftime: bool = True) -> float:
    """
    Get the minimum BPM difference considering halftime/doubletime.

    Args:
        bpm1: First track's BPM
        bpm2: Second track's BPM
        allow_halftime: Consider half/double time ratios

    Returns:
        Minimum BPM difference

    Examples:
        >>> get_bpm_difference(128, 130)
        2.0
        >>> get_bpm_difference(128, 64)
        0.0
        >>> get_bpm_difference(140, 68)
        2.0
    """
    direct = abs(bpm1 - bpm2)

    if not allow_halftime:
        return direct

    half = abs(bpm1 - bpm2 / 2)
    double = abs(bpm1 - bpm2 * 2)

    return min(direct, half, double)
