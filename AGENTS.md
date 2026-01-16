# DJ PLAYLIST OPTIMIZER - PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-16
**Commit:** c523fa1
**Branch:** main

## OVERVIEW

Python library + CLI for optimizing DJ playlists using Google OR-Tools CP-SAT solver. Harmonic mixing (Camelot Wheel) + BPM matching (direct/halftime/doubletime) with constraint programming.

## STRUCTURE

```
.
├── src/dj_playlist_optimizer/   # Core library (7 modules)
│   ├── __init__.py              # Public API exports
│   ├── models.py                # Track, PlaylistResult, statistics
│   ├── optimizer.py             # CP-SAT solver logic
│   ├── bpm.py                   # BPM compatibility (halftime/double)
│   ├── camelot.py               # Camelot wheel harmonic rules
│   └── cli.py                   # dj-optimize command
├── tests/                       # pytest suite (53 tests, 0 fixtures)
├── examples/                    # SDK + CLI usage demos
└── pyproject.toml               # uv-managed, PEP 621
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add BPM logic | `src/dj_playlist_optimizer/bpm.py` | Pure functions, no state |
| Modify harmonic rules | `src/dj_playlist_optimizer/camelot.py` | Circular distance calculations |
| Change solver objective | `src/dj_playlist_optimizer/optimizer.py:113` | `model.maximize(sum(included))` |
| Add CLI flags | `src/dj_playlist_optimizer/cli.py:84-150` | argparse setup |
| New constraints | `src/dj_playlist_optimizer/optimizer.py:66-111` | Before `model.solve()` |
| Edge creation logic | `src/dj_playlist_optimizer/optimizer.py:71-80` | BPM filter for graph edges |

## CONVENTIONS

**Deviations from Python standard**:
- Uses `src/` layout (prevents accidental imports)
- `uv` package manager instead of pip/poetry
- No `tests/__init__.py` (pytest doesn't require it)
- Line length: 100 chars (not 79/88)
- Double quotes enforced by ruff

**BPM Compatibility**:
- Direct match: `|bpm1 - bpm2| <= tolerance`
- Halftime: `|bpm1 - bpm2/2| <= tolerance` (e.g., 128↔64)
- Doubletime: `|bpm1 - bpm2*2| <= tolerance` (e.g., 75↔150)

**Harmonic Levels**:
- `STRICT`: Same key, ±1 hour (same letter), or same hour (diff letter)
- `MODERATE`: STRICT + ±1 hour (diff letter)
- `RELAXED`: MODERATE + ±3 hours

**Commit Messages**:
- Enforced conventional commits via pre-commit hook
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

## ANTI-PATTERNS (THIS PROJECT)

**Forbidden**:
- ❌ `print()` in library code (`src/dj_playlist_optimizer/*.py` except `cli.py`)
- ❌ Use `logging` module instead
- ❌ Type suppression (`type: ignore`, `# noqa`)
- ❌ Modifying `PlaylistStatistics.total_input_tracks` after init (design smell)

**Clean codebase**: Zero `TODO`, `FIXME`, `HACK`, or `DEPRECATED` markers found.

## UNIQUE STYLES

**Solver Pattern**:
- Uses `AddCircuit` constraint (traveling salesman variant)
- Self-loops (`i → i`) represent excluded tracks
- Soft constraint: max non-harmonic transitions via `max_violations`

**No pytest fixtures**: Tests instantiate data inline (no `conftest.py`).

**Class-based tests**: `TestBpmCompatible`, `TestParseCamelotKey`, etc.

**Version hardcoded**: `cli.py:150` has `version="0.1.0"` (not pulled from pyproject.toml).

## COMMANDS

```bash
# Setup
uv sync --dev
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg

# Development
uv run pytest                    # Run tests (53 pass)
uv run ruff check --fix          # Lint + auto-fix
uv run ruff format               # Format code
uv run pre-commit run --all-files

# CLI
uv run dj-optimize tracks.json
uv run dj-optimize tracks.json -v              # INFO logging
uv run dj-optimize tracks.json -vv             # DEBUG logging
uv run dj-optimize tracks.json --bpm-tolerance 8 --harmonic-level moderate

# Examples
uv run python examples/sdk_usage.py
uv run python examples/logging_example.py
```

## NOTES

**Gotchas**:
- Camelot wheel is circular: `1A` and `12A` are adjacent (distance = 1, not 11)
- BPM compatibility is asymmetric due to halftime: `bpm_compatible(128, 64) == True` but context matters
- Empty playlist result if no BPM-compatible edges exist (check `edge_vars`)
- Solver may timeout on large inputs (default 60s limit)
- Pre-commit hook blocks invalid commit messages (use `git commit --no-verify` to bypass, but don't)

**Missing (by design)**:
- No GitHub Actions / remote CI (local pre-commit only)
- No LICENSE file
- No `docs/` directory (README-only documentation)
- Module state coupling: `PlaylistStatistics.total_input_tracks` set externally

**Dependencies**:
- Runtime: `ortools >= 9.8.3296`
- Dev: `pytest`, `ruff`, `pre-commit`
