# AGENTS.md - src/djkr8

## OVERVIEW
Core logic for harmonic playlist optimization using CP-SAT and Rekordbox integration.

## STRUCTURE
- `optimizer.py`: Main solver using Google OR-Tools CP-SAT (Longest Path/TSP variant).
- `rekordbox.py`: Rekordbox 6/7 database (`master.db`) and XML integration layer.
- `models.py`: Core data carriers: `Track`, `TransitionInfo`, `PlaylistResult`.
- `camelot.py`: Harmonic math (Camelot Wheel) and compatibility strictness levels.
- `bpm.py`: BPM matching logic including halftime (0.5x) and doubletime (2.0x) support.

## WHERE TO LOOK
- **Solver Pattern (Dummy Node)**: `PlaylistOptimizer` uses a dummy node (index `num_tracks`) to transform a pathfinding problem into a circuit. The path is reconstructed from `Dummy -> Start -> ... -> End -> Dummy`.
- **Constraint Graph**: `AddCircuit` arcs are only generated for pairs passing `bpm_compatible`. Harmonic compatibility is treated as a soft constraint or a bounded violation count (`max_violation_pct`).
- **Priority Weights**: "Must Include" tracks use a weight of 100,000 in the objective function to override default length-based maximization.
- **Rekordbox DB Access**: `RekordboxLoader` abstracts `pyrekordbox`. It handles `master.db` locks and maps various tonality formats (e.g., "Abm", "G# Minor") to Camelot keys.
- **XML Export**: `write_rekordbox_xml` generates the `DJ_PLAYLISTS` schema. It maps tracks to unique numeric IDs for the `COLLECTION` section.

## CONVENTIONS
- Refer to root `AGENTS.md` for general project rules.
- **Normalized BPM**: Always use floats for BPM. Loader handles Rekordbox's internal integer scaling (x100).
- **Key Consistency**: Internal logic strictly uses Camelot notation (1A-12B). Convert external keys early via `rekordbox.KEY_MAPPING`.
- **Logging**: Library modules must not use `print()`. Use `logger.info()` for status and `logger.debug()` for solver edge counts.

## ANTI-PATTERNS
- ❌ **Direct SQL**: Avoid raw SQLite queries against `master.db`; use `Rekordbox6Database` methods to maintain data integrity.
- ❌ **Mutable Models**: Do not modify `Track` or `PlaylistStatistics` fields after instantiation.
- ❌ **Concurrency**: The solver is not thread-safe. Avoid running multiple `optimize()` calls on the same `PlaylistOptimizer` instance simultaneously.
- ❌ **DB Write while Active**: Never write to `master.db` if Rekordbox is open; it will likely cause a database lock or corruption.
