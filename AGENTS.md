# DJKR8 - PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-16

## OVERVIEW
Python library + CLI for optimizing DJ playlists using Google OR-Tools CP-SAT solver. Features harmonic mixing (Camelot Wheel), BPM matching (direct/halftime/doubletime), and Rekordbox integration (DB/XML).

## STRUCTURE
```
.
├── src/djkr8/   # Core logic (solver, models, integrations)
├── tests/                       # Unit + integration tests (pure pytest, no fixtures)
├── examples/                    # Usage demos (SDK + logging)
└── pyproject.toml               # uv-managed dependencies + tool config
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Core Solver** | `src/djkr8/optimizer.py` | Uses `AddCircuit` constraint for TSP-like pathfinding |
| **Data Models** | `src/djkr8/models.py` | `Track`, `PlaylistResult`, `HarmonicLevel` |
| **BPM Logic** | `src/djkr8/bpm.py` | Pure functions for BPM compatibility |
| **Harmonic Rules** | `src/djkr8/camelot.py` | Camelot Wheel math + `KEY_MAPPING` |
| **Rekordbox** | `src/djkr8/rekordbox.py` | Direct DB read/write + XML export |
| **CLI** | `src/djkr8/cli.py` | `argparse` entry point + logging setup |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `PlaylistOptimizer` | Class | `optimizer.py` | Main facade for configuring and running the solver |
| `Track` | Class | `models.py` | Data carrier for ID, Key, BPM, Energy (1-5), Duration |
| `HarmonicLevel` | Enum | `models.py` | STRICT, MODERATE, RELAXED compatibility modes |
| `RekordboxLoader` | Class | `rekordbox.py` | Interface for reading playlists from `master.db` (auto-normalizes ratings to 1-5) |
| `write_rekordbox_xml` | Func | `rekordbox.py` | Generates XML for re-importing optimized lists |

## CONVENTIONS
- **Layout**: `src/` layout with `uv` package manager.
- **Energy Range**: Strictly **1-5**. Track validation enforces this.
- **Energy Flow**: By default, the solver enforces non-decreasing energy (`next >= current`). This can be toggled via `enforce_energy_flow`.
- **Line Length**: **100 chars** (enforced by ruff).
- **Quotes**: Double quotes always.
- **Commits**: Conventional Commits (feat, fix, docs, etc.) enforced by pre-commit.
- **Tests**: Pure `pytest` class-based structure. **NO fixtures**, **NO conftest.py**. Data instantiated inline.

## USER PREFERENCES
- **Testing**: Maintain high coverage (~90%). Mock external dependencies (DB/filesystem) heavily. Avoid shared fixtures in favor of inline instantiation for clarity.
- **Integration**: Prioritize safer XML export over direct DB writes, but maintain the DB write capability for advanced users.
- **Style**: Strict linting (ruff, pre-commit) is mandatory. No unused variables or complex nested contexts.

## ANTI-PATTERNS (THIS PROJECT)
- ❌ **Print**: Forbidden in library code (`src/`). Use `logging`. Allowed ONLY in `cli.py`.
- ❌ **Suppression**: No `# type: ignore` or `# noqa`.
- ❌ **Mutable State**: Do not modify `PlaylistStatistics` fields after init.
- ❌ **Direct DB Write**: Avoid writing to Rekordbox DB while the app is open (corruption risk).

## UNIQUE STYLES
- **Solver**: Uses a "dummy node" pattern in `AddCircuit` to find longest paths (TSP variant).
- **Soft Constraints**: "Must Include" logic implemented via massive objective weights (100,000).
- **Versioning**: Hybrid approach. `pyproject.toml` (1.0.0) vs `cli.py` fallback (0.0.0).

## COMMANDS
```bash
# Dev Cycle
uv sync --dev
uv run pytest
uv run ruff check --fix && uv run ruff format
uv run pre-commit run --all-files

# CLI Usage
uv run djkr8 tracks.json --harmonic-level moderate
uv run djkr8 --rekordbox --playlist "Techno" --output result.xml
uv run djkr8 --rekordbox --playlist "Techno" --write-to-db
```

## NOTES
- **Camelot Math**: `1A` and `12A` are adjacent. Code handles circular distance.
- **Halftime BPM**: `128` matches `64`. Asymmetric relationship supported.
- **DB Write Risk**: Direct write requires Rekordbox to be closed to avoid SQLite lock errors.
- **Missing**: No `docs/` dir (README only). No remote CI (local pre-commit only).
