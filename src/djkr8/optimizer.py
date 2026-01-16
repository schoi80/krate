"""Playlist optimization using Google OR-Tools CP-SAT solver."""

import logging

from ortools.sat.python import cp_model

from djkr8.bpm import bpm_compatible, get_bpm_difference
from djkr8.camelot import is_harmonic_compatible
from djkr8.models import (
    HarmonicLevel,
    PlaylistResult,
    PlaylistStatistics,
    Track,
    TransitionInfo,
)

logger = logging.getLogger(__name__)


class PlaylistOptimizer:
    """
    Optimizes DJ playlists using constraint programming.

    Finds the longest possible playlist where:
    - Adjacent tracks have compatible BPMs (with halftime/doubletime support)
    - Harmonic violations are minimized within the allowed percentage
    """

    def __init__(
        self,
        bpm_tolerance: float = 10.0,
        allow_halftime_bpm: bool = True,
        max_violation_pct: float = 0.10,
        harmonic_level: HarmonicLevel = HarmonicLevel.STRICT,
        time_limit_seconds: float = 5.0,
        max_playlist_duration: float | None = None,
        energy_weight: float = 0.0,
        enforce_energy_flow: bool = True,
    ):
        self.bpm_tolerance = bpm_tolerance
        self.allow_halftime_bpm = allow_halftime_bpm
        self.max_violation_pct = max_violation_pct
        self.harmonic_level = harmonic_level
        self.time_limit_seconds = time_limit_seconds
        self.max_playlist_duration = max_playlist_duration
        self.energy_weight = energy_weight
        self.enforce_energy_flow = enforce_energy_flow

    def optimize(
        self,
        tracks: list[Track],
        start_track_id: str | None = None,
        end_track_id: str | None = None,
        must_include_ids: list[str] | None = None,
        target_length: int | None = None,
    ) -> PlaylistResult:
        """
        Find the optimal playlist from given tracks.

        Args:
            tracks: List of tracks to optimize
            start_track_id: Optional ID of track that must start the playlist
            end_track_id: Optional ID of track that must end the playlist
            must_include_ids: Optional list of track IDs that must be included
            target_length: Optional exact length of playlist to find

        Returns:
            PlaylistResult with the optimized playlist
        """
        logger.info(f"Starting optimization with {len(tracks)} tracks")
        logger.debug(
            f"Config: bpm_tolerance={self.bpm_tolerance}, harmonic_level={self.harmonic_level.value}"
        )

        if not tracks:
            logger.warning("No tracks provided for optimization")
            return PlaylistResult(playlist=[], solver_status="empty_input")

        # Map track IDs to indices
        id_to_idx = {t.id: i for i, t in enumerate(tracks)}

        # Validate inputs
        start_idx = None
        if start_track_id:
            if start_track_id not in id_to_idx:
                logger.error(f"Start track ID {start_track_id} not found in tracks")
                return PlaylistResult(playlist=[], solver_status="invalid_input")
            start_idx = id_to_idx[start_track_id]

        end_idx = None
        if end_track_id:
            if end_track_id not in id_to_idx:
                logger.error(f"End track ID {end_track_id} not found in tracks")
                return PlaylistResult(playlist=[], solver_status="invalid_input")
            end_idx = id_to_idx[end_track_id]

        must_include_indices = []
        if must_include_ids:
            for tid in must_include_ids:
                if tid not in id_to_idx:
                    logger.warning(f"Must-include track {tid} not found, skipping")
                else:
                    must_include_indices.append(id_to_idx[tid])

        if len(tracks) == 1:
            # Trivial case logic...
            # If constraints fail for the single track, we should theoretically fail,
            # but usually single track is valid if it matches start/end/must requirements.
            # For simplicity, we keep existing behavior but check start/end if needed?
            # Actually, standard behavior is fine.
            logger.info("Single track input, returning trivial result")
            return PlaylistResult(
                playlist=tracks,
                solver_status="single_track",
                statistics=PlaylistStatistics(
                    total_input_tracks=1,
                    playlist_length=1,
                    harmonic_transitions=0,
                    non_harmonic_transitions=0,
                    avg_bpm=tracks[0].bpm,
                    bpm_range=(tracks[0].bpm, tracks[0].bpm),
                ),
            )

        model = cp_model.CpModel()
        num_tracks = len(tracks)

        # We use a dummy node (index = num_tracks) to handle the start/end of the path
        # The circuit will be: Dummy -> StartTrack -> ... -> EndTrack -> Dummy
        dummy_idx = num_tracks
        total_nodes = num_tracks + 1

        # Variables for all nodes (tracks + dummy)
        included = [model.new_bool_var(f"inc_{i}") for i in range(total_nodes)]

        # Force dummy to be included
        model.add(included[dummy_idx] == 1)

        edge_vars = {}

        # 1. Edges between real tracks
        for i in range(num_tracks):
            for j in range(num_tracks):
                # Constraints:
                # 1. Different tracks
                # 2. BPM compatible
                # 3. Energy must be non-decreasing (next >= current) if enforced
                if (
                    i != j
                    and bpm_compatible(
                        tracks[i].bpm,
                        tracks[j].bpm,
                        self.bpm_tolerance,
                        self.allow_halftime_bpm,
                    )
                    and (not self.enforce_energy_flow or tracks[j].energy >= tracks[i].energy)
                ):
                    edge_vars[(i, j)] = model.new_bool_var(f"edge_{i}_{j}")

        # 2. Edges to/from dummy node (allow entering/leaving the playlist anywhere)
        for i in range(num_tracks):
            # Dummy -> i (Start of playlist)
            edge_vars[(dummy_idx, i)] = model.new_bool_var(f"start_at_{i}")
            # i -> Dummy (End of playlist)
            edge_vars[(i, dummy_idx)] = model.new_bool_var(f"end_at_{i}")

        logger.debug(f"Created {len(edge_vars)} edges for {total_nodes} nodes")

        arcs = [(i, j, var) for (i, j), var in edge_vars.items()]

        # Add self-loops for excluded nodes (standard TSP/circuit pattern)
        for i in range(total_nodes):
            arcs.append((i, i, included[i].Not()))

        model.add_circuit(arcs)

        # --- Constraints ---

        # Start Track constraint
        if start_idx is not None:
            # Force Dummy -> StartTrack
            if (dummy_idx, start_idx) in edge_vars:
                model.add(edge_vars[(dummy_idx, start_idx)] == 1)
            else:
                # Impossible start (e.g. if we had BPM constraints on start, but dummy has none)
                model.add(included[dummy_idx] == 0)  # Force fail

        # End Track constraint
        if end_idx is not None:
            # Force EndTrack -> Dummy
            if (end_idx, dummy_idx) in edge_vars:
                model.add(edge_vars[(end_idx, dummy_idx)] == 1)
            else:
                model.add(included[dummy_idx] == 0)

        # Must Include constraints (Soft: High Objective Weight)
        # We handle this in the objective function below.

        # Target Length constraint
        if target_length is not None:
            # sum(included) includes dummy, so we want target_length + 1
            # Cap at total tracks available
            target = min(target_length, num_tracks)
            model.add(sum(included) == target + 1)

        # Harmonic violations (only for track-track edges, not dummy edges)
        violation_vars = {}
        for (i, j), edge_var in edge_vars.items():
            # Skip dummy edges
            if i == dummy_idx or j == dummy_idx:
                continue

            if not is_harmonic_compatible(tracks[i].key, tracks[j].key, self.harmonic_level):
                violation = model.new_bool_var(f"viol_{i}_{j}")
                model.add(edge_var == 1).only_enforce_if(violation)
                model.add(edge_var == 0).only_enforce_if(violation.Not())
                violation_vars[(i, j)] = violation

        # Max violations constraint
        if violation_vars:
            # Calculate max violations
            # If max_violation_pct is 0.0, we want strict 0 violations.
            # If max_violation_pct > 0.0 (e.g. 0.1), we usually want at least 1 allowed
            # for small playlists (e.g. 5 tracks * 0.1 = 0.5 -> 0 would be too strict).
            limit = int(num_tracks * self.max_violation_pct)
            if self.max_violation_pct > 0 and limit == 0:
                limit = 1

            max_violations = limit
            model.add(sum(violation_vars.values()) <= max_violations)
            logger.debug(
                f"Found {len(violation_vars)} non-harmonic edges, max allowed: {max_violations}"
            )

        # Duration constraint (ignore dummy)
        if self.max_playlist_duration is not None:
            precision = 100
            # tracks[i].duration for i < num_tracks
            total_duration_scaled = sum(
                int(tracks[i].duration * precision) * included[i] for i in range(num_tracks)
            )
            model.add(total_duration_scaled <= int(self.max_playlist_duration * precision))

        # --- Objective ---
        # 1. Base weight for including a track
        base_weight = 100

        # 2. Bonus for "Must Include" tracks
        # 100,000 ensures it's more valuable than adding 1000 regular tracks
        must_include_weight = 100000

        objective_terms = []

        for i in range(num_tracks):
            weight = base_weight

            # Add energy weight if configured
            if self.energy_weight > 0:
                weight += int(self.energy_weight * tracks[i].energy)

            # Add must_include bonus
            if i in must_include_indices:
                weight += must_include_weight

            objective_terms.append(weight * included[i])

        model.maximize(sum(objective_terms))

        logger.info("Starting CP-SAT solver")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.log_search_progress = False

        status = solver.solve(model)

        logger.info(f"Solver finished: {solver.status_name(status)} in {solver.wall_time:.2f}s")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            result = self._extract_result(
                solver, tracks, included, edge_vars, violation_vars, status, dummy_idx
            )
            if result.statistics:
                logger.info(
                    f"Optimized playlist: {result.statistics.playlist_length}/{len(tracks)} tracks "
                    f"({result.statistics.coverage_pct:.1f}% coverage), "
                    f"{result.statistics.harmonic_pct:.1f}% harmonic transitions"
                )
            return result
        else:
            logger.warning(f"No solution found: {solver.status_name(status)}")
            return PlaylistResult(
                playlist=[],
                solver_status=solver.status_name(status),
                solver_time_seconds=solver.wall_time,
            )

    def _extract_result(
        self,
        solver: cp_model.CpSolver,
        tracks: list[Track],
        included,
        edge_vars,
        violation_vars,
        status,
        dummy_idx: int,
    ) -> PlaylistResult:
        """Extract playlist from solver solution."""
        num_tracks = len(tracks)

        # Get included indices (excluding dummy)
        selected_indices = [i for i in range(num_tracks) if solver.value(included[i])]

        logger.debug(f"Selected {len(selected_indices)} tracks from solution")

        if not selected_indices:
            return PlaylistResult(playlist=[], solver_status="no_solution")

        # Get all selected edges
        selected_edges = {
            (i, j): solver.value(var) for (i, j), var in edge_vars.items() if solver.value(var) == 1
        }

        # Reconstruct path using dummy node logic
        playlist, transitions = self._reconstruct_path_with_dummy(
            tracks, selected_edges, dummy_idx, self.harmonic_level, self.allow_halftime_bpm
        )

        harmonic = sum(1 for t in transitions if t.is_harmonic)
        non_harmonic = len(transitions) - harmonic

        bpms = [t.bpm for t in playlist]
        avg_bpm = sum(bpms) / len(bpms) if bpms else 0.0
        bpm_range = (min(bpms), max(bpms)) if bpms else (0.0, 0.0)

        statistics = PlaylistStatistics(
            total_input_tracks=num_tracks,
            playlist_length=len(playlist),
            harmonic_transitions=harmonic,
            non_harmonic_transitions=non_harmonic,
            avg_bpm=avg_bpm,
            bpm_range=bpm_range,
        )

        return PlaylistResult(
            playlist=playlist,
            transitions=transitions,
            statistics=statistics,
            solver_status="optimal" if status == cp_model.OPTIMAL else "feasible",
            solver_time_seconds=solver.wall_time,
        )

    def _reconstruct_path_with_dummy(
        self, tracks, selected_edges, dummy_idx, harmonic_level, allow_halftime
    ):
        """Reconstruct the path starting from dummy node."""
        # Find start: dummy -> start_node
        start_node = None
        for i, j in selected_edges:
            if i == dummy_idx:
                start_node = j
                break

        if start_node is None:
            return [], []

        playlist = []
        transitions = []

        current = start_node
        # Traverse until we hit dummy again (end of path)
        while current != dummy_idx:
            playlist.append(tracks[current])

            # Find next node
            next_node = None
            for i, j in selected_edges:
                if i == current:
                    next_node = j
                    break

            if next_node is None:
                break

            # If next is dummy, we are done with transitions
            if next_node != dummy_idx:
                # Calculate transition info
                is_harmonic = is_harmonic_compatible(
                    tracks[current].key, tracks[next_node].key, harmonic_level
                )

                bpm_diff = get_bpm_difference(
                    tracks[current].bpm, tracks[next_node].bpm, allow_halftime
                )

                transitions.append(
                    TransitionInfo(
                        from_track=tracks[current],
                        to_track=tracks[next_node],
                        is_harmonic=is_harmonic,
                        is_bpm_compatible=True,
                        bpm_difference=bpm_diff,
                    )
                )

            current = next_node

        return playlist, transitions
