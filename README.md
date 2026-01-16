# 🎧 djkr8 - Playlist Optimizer for rekordbox

Optimize [rekordbox](https://rekordbox.com) playlists for harmonic mixing using [Google OR-Tools](https://developers.google.com/optimization) constraint programming.

## Features

- ✨ **Longest Path Optimization**: Finds the maximum number of tracks that can be mixed together
- ⚡ **Energy Flow Management**: Enforces non-decreasing energy progression (1-5 range)
- 🎵 **Harmonic Mixing**: Uses the Camelot Wheel system for key compatibility
- 🎧 **Rekordbox Integration**: Read playlists directly from your local Rekordbox 6/7 database (tested with v7.2.8)
- 🔊 **BPM Matching**: Supports direct, halftime, and doubletime BPM compatibility
- ⚙️ **Configurable Strictness**: STRICT, MODERATE, or RELAXED harmonic compatibility levels
- 📤 **Rekordbox Export**: Export results to Rekordbox XML or write directly to the Rekordbox database
- 🚀 **Fast**: Powered by Google OR-Tools CP-SAT solver (award-winning constraint solver)
- 📦 **SDK + CLI**: Use as a Python library or command-line tool

## Installation

```bash
uv add djkr8
```

Or with pip:

```bash
pip install djkr8
```

## Quick Start

### SDK Usage

```python
from djkr8 import PlaylistOptimizer, Track, HarmonicLevel

tracks = [
    Track(id="track_001", key="8A", bpm=128),
    Track(id="track_002", key="8B", bpm=130),
    Track(id="track_003", key="9A", bpm=125),
]

optimizer = PlaylistOptimizer(
    bpm_tolerance=10,
    allow_halftime_bpm=True,
    max_violation_pct=0.10,
    harmonic_level=HarmonicLevel.STRICT,
)

result = optimizer.optimize(tracks)

for i, track in enumerate(result.playlist, 1):
    print(f"{i}. {track.id} ({track.key}, {track.bpm} BPM)")
```

### CLI Usage

```bash
# Basic usage
djkr8 tracks.json

# With custom settings
djkr8 tracks.json --bpm-tolerance 8 --harmonic-level moderate

# Energy flow management
djkr8 tracks.json --energy-weight 5.0      # Prioritize higher energy tracks
djkr8 tracks.json --allow-energy-drops    # Disable strict non-decreasing energy constraint

# Save results to JSON
djkr8 tracks.json --output result.json

# Use with Rekordbox (v6/v7)
krate --rekordbox                                      # List playlists
krate --rekordbox --playlist "Techno"                  # Optimize specific playlist
krate --rekordbox --playlist "Techno" --output r.xml   # Export to Rekordbox XML
krate --rekordbox --playlist "Techno" --write-to-db    # Write directly to Rekordbox DB

# Enable verbose logging
djkr8 tracks.json -v          # INFO level
djkr8 tracks.json -vv         # DEBUG level
```

## Rekordbox Integration

The tool provides two ways to save your optimized playlists back to Rekordbox:

### 1. XML Export (Recommended)

Export the results to an XML file that can be imported into Rekordbox:

```bash
krate --rekordbox --playlist "My Playlist" --output optimized.xml
```

In Rekordbox:
1. Go to **File > Import > Import Playlist**
2. Select `optimized.xml`
3. The playlist will appear in the `ROOT` folder (e.g., `My Playlist_20260115_120000`)

### 2. Direct Database Write (Advanced)

Write the optimized playlist directly to your Rekordbox 6 database:

```bash
krate --rekordbox --playlist "My Playlist" --write-to-db
```

**⚠️ WARNING:**
- **Close Rekordbox** before running this command.
- This modifies your `master.db` file directly.
- **Backup your database** before using this feature.

## Input Format

JSON file with tracks containing `id`, `key` (Camelot notation), and `bpm`:

```json
{
  "tracks": [
    {"id": "track_001", "key": "8A", "bpm": 128},
    {"id": "track_002", "key": "8B", "bpm": 130},
    {"id": "track_003", "key": "9A", "bpm": 125}
  ]
}
```

## How It Works

### 1. BPM Compatibility

Adjacent tracks must have compatible BPMs within tolerance:

| Track A | Track B | Tolerance | Match? | Reason |
|---------|---------|-----------|--------|--------|
| 128 BPM | 130 BPM | ±10 | ✅ | Direct (diff = 2) |
| 128 BPM | 64 BPM | ±10 | ✅ | Half-time (128 = 64×2) |
| 75 BPM | 150 BPM | ±10 | ✅ | Double-time (75×2 = 150) |
| 128 BPM | 100 BPM | ±10 | ❌ | Too far |

### 2. Harmonic Mixing (Camelot Wheel)

Harmonic compatibility levels:

**STRICT** (default):
- Same key (8A → 8A)
- ±1 hour same letter (8A → 7A, 9A)
- Same hour different letter (8A → 8B)

**MODERATE**:
- Above + ±1 hour different letter (8A → 9B, 7B)

**RELAXED**:
- Above + ±3 hours (8A → 5A, 11A)

### 3. Optimization Goal

Maximize playlist length while keeping non-harmonic transitions below the threshold (default: 10%).

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `bpm_tolerance` | 10.0 | Maximum BPM difference for direct match |
| `allow_halftime_bpm` | True | Enable half/double-time matching |
| `max_violation_pct` | 0.10 | Max percentage of non-harmonic transitions |
| `harmonic_level` | STRICT | Harmonic compatibility strictness |
| `enforce_energy_flow` | True | Enforce non-decreasing energy (`next >= current`) |
| `time_limit_seconds` | 60.0 | Solver time limit |

## Examples

See `examples/` directory:
- `example_tracks.json` - Sample input data
- `sdk_usage.py` - SDK usage demonstration
- `logging_example.py` - Logging configuration example

## Development

```bash
# Clone repository
git clone https://github.com/yourusername/djkr8
cd krate

# Install with dev dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg

# Run tests
uv run pytest

# Lint and format
uv run ruff check          # Check for issues
uv run ruff check --fix    # Auto-fix issues
uv run ruff format         # Format code

# Run pre-commit on all files
uv run pre-commit run --all-files

# Run example
uv run python examples/sdk_usage.py
```

## How the Solver Works

The optimizer uses Google OR-Tools CP-SAT solver with:

1. **Binary Variables**: `included[i]` = track i is in playlist
2. **Edge Variables**: `edge[i,j]` = track j follows track i
3. **Circuit Constraint**: `AddCircuit` ensures valid track ordering
4. **BPM Constraints**: Only create edges between BPM-compatible tracks
5. **Harmonic Soft Constraints**: Penalize non-harmonic transitions
6. **Objective**: Maximize `sum(included)`

## License

MIT

## Credits

Built with:
- [Google OR-Tools](https://developers.google.com/optimization) - Constraint programming solver
- [pyrekordbox](https://github.com/dylanljones/pyrekordbox) - Rekordbox database access
- Camelot Wheel system by Mark Davis (Mixed In Key)
