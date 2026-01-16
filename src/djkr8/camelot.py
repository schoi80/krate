"""Camelot wheel harmonic compatibility checking."""

import logging

from djkr8.models import HarmonicLevel

logger = logging.getLogger(__name__)


def parse_camelot_key(key: str) -> tuple[int, str]:
    """
    Parse Camelot key notation into (hour, letter).

    Args:
        key: Camelot notation (e.g., "8A", "12B")

    Returns:
        Tuple of (hour: 1-12, letter: 'A' or 'B')

    Raises:
        ValueError: If key format is invalid

    Examples:
        >>> parse_camelot_key("8A")
        (8, 'A')
        >>> parse_camelot_key("12B")
        (12, 'B')
    """
    key = key.strip().upper()

    if len(key) < 2:
        logger.warning(f"Invalid Camelot key format: '{key}'")
        raise ValueError(f"Invalid Camelot key: '{key}'")

    letter = key[-1]
    hour_str = key[:-1]

    if letter not in ("A", "B"):
        raise ValueError(f"Invalid Camelot key letter: '{letter}' (must be A or B)")

    try:
        hour = int(hour_str)
    except ValueError as err:
        raise ValueError(f"Invalid Camelot key hour: '{hour_str}'") from err

    if not (1 <= hour <= 12):
        raise ValueError(f"Camelot hour must be 1-12, got: {hour}")

    return hour, letter


def get_hour_distance(hour1: int, hour2: int) -> int:
    """
    Get circular distance between two hours on the Camelot wheel.

    Examples:
        >>> get_hour_distance(8, 9)
        1
        >>> get_hour_distance(1, 12)
        1
        >>> get_hour_distance(1, 7)
        6
    """
    diff = abs(hour1 - hour2)
    return min(diff, 12 - diff)


def is_harmonic_compatible(
    key1: str, key2: str, level: HarmonicLevel = HarmonicLevel.STRICT
) -> bool:
    """
    Check if two Camelot keys are harmonically compatible.

    Compatibility rules by level:
    - STRICT: Same key, ±1 hour same letter, same hour different letter
    - MODERATE: Above + ±1 hour different letter (dominant/subdominant)
    - RELAXED: Above + ±3 hours (mood changes)

    Args:
        key1: First Camelot key (e.g., "8A")
        key2: Second Camelot key (e.g., "8B")
        level: Harmonic strictness level

    Returns:
        True if keys are compatible for the given level

    Examples:
        >>> is_harmonic_compatible("8A", "8A")  # Perfect match
        True
        >>> is_harmonic_compatible("8A", "8B")  # Relative major/minor
        True
        >>> is_harmonic_compatible("8A", "9A")  # Energy boost
        True
        >>> is_harmonic_compatible("8A", "9B", HarmonicLevel.MODERATE)  # Dominant
        True
        >>> is_harmonic_compatible("8A", "9B", HarmonicLevel.STRICT)  # Not strict
        False
    """
    try:
        hour1, letter1 = parse_camelot_key(key1)
        hour2, letter2 = parse_camelot_key(key2)
    except ValueError:
        return False

    hour_dist = get_hour_distance(hour1, hour2)
    same_letter = letter1 == letter2

    if hour_dist == 0:
        return True

    if hour_dist == 1 and same_letter:
        return True

    if level == HarmonicLevel.STRICT:
        return False

    if hour_dist == 1 and not same_letter:
        return True

    return level == HarmonicLevel.RELAXED and hour_dist == 3


def get_compatible_keys(key: str, level: HarmonicLevel = HarmonicLevel.STRICT) -> list[str]:
    """
    Get all compatible keys for a given Camelot key.

    Args:
        key: Camelot key (e.g., "8A")
        level: Harmonic strictness level

    Returns:
        List of compatible Camelot keys

    Examples:
        >>> sorted(get_compatible_keys("8A", HarmonicLevel.STRICT))
        ['7A', '8A', '8B', '9A']
        >>> len(get_compatible_keys("8A", HarmonicLevel.MODERATE))
        6
    """
    parse_camelot_key(key)
    compatible = []

    for h in range(1, 13):
        for letter in ["A", "B"]:
            test_key = f"{h}{letter}"
            if is_harmonic_compatible(key, test_key, level):
                compatible.append(test_key)

    return compatible
