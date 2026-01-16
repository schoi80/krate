"""Playlist optimization using Google OR-Tools CP-SAT solver."""

import logging

from ortools.sat.python import cp_model

from dj_playlist_optimizer.bpm import bpm_compatible, get_bpm_difference
from dj_playlist_optimizer.camelot import is_harmonic_compatible
from dj_playlist_optimizer.models import (
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
        time_limit_seconds: float = 60.0,
        max_playlist_duration: float | None = None,
        energy_weight: float = 0.0,
    ):
        self.bpm_tolerance = bpm_tolerance
        self.allow_halftime_bpm = allow_halftime_bpm
        self.max_violation_pct = max_violation_pct
        self.harmonic_level = harmonic_level
        self.time_limit_seconds = time_limit_seconds
        self.max_playlist_duration = max_playlist_duration
        self.energy_weight = energy_weight

    def optimize(self, tracks: list[Track]) -> PlaylistResult:
        """
        Find the optimal playlist from given tracks.

        Args:
            tracks: List of tracks to optimize

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

        if len(tracks) == 1:
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
        n = len(tracks)

        included = [model.new_bool_var(f"inc_{i}") for i in range(n)]

        edge_vars = {}
        for i in range(n):
            for j in range(n):
                if i != j and bpm_compatible(
                    tracks[i].bpm,
                    tracks[j].bpm,
                    self.bpm_tolerance,
                    self.allow_halftime_bpm,
                ):
                    edge_vars[(i, j)] = model.new_bool_var(f"edge_{i}_{j}")

        logger.debug(f"Created {len(edge_vars)} BPM-compatible edges out of {n * (n - 1)} possible")

        arcs = [(i, j, var) for (i, j), var in edge_vars.items()]

        for i in range(n):
            arcs.append((i, i, included[i].Not()))

        model.add_circuit(arcs)

        for i in range(n):
            incoming = [edge_vars[(j, i)] for j in range(n) if (j, i) in edge_vars]
            if incoming:
                model.add(sum(incoming) == included[i])
            else:
                model.add(included[i] == 0)

        violation_vars = {}
        for (i, j), edge_var in edge_vars.items():
            if not is_harmonic_compatible(tracks[i].key, tracks[j].key, self.harmonic_level):
                violation = model.new_bool_var(f"viol_{i}_{j}")
                model.add(edge_var == 1).only_enforce_if(violation)
                model.add(edge_var == 0).only_enforce_if(violation.Not())
                violation_vars[(i, j)] = violation

        total_transitions_var = model.new_int_var(0, n, "total_transitions")
        model.add(total_transitions_var == sum(edge_vars.values()))

        if violation_vars:
            max_violations = max(1, int(n * self.max_violation_pct))
            model.add(sum(violation_vars.values()) <= max_violations)
            logger.debug(
                f"Found {len(violation_vars)} non-harmonic edges, max allowed: {max_violations}"
            )

        if self.max_playlist_duration is not None:
            precision = 100
            total_duration_scaled = sum(
                int(tracks[i].duration * precision) * included[i] for i in range(n)
            )
            model.add(total_duration_scaled <= int(self.max_playlist_duration * precision))
            logger.debug(f"Added duration constraint: {self.max_playlist_duration}s")

        length_weight = 100
        objective_terms = [length_weight * included[i] for i in range(n)]

        if self.energy_weight > 0:
            objective_terms.extend(
                [int(self.energy_weight * tracks[i].energy) * included[i] for i in range(n)]
            )

        model.maximize(sum(objective_terms))

        logger.info("Starting CP-SAT solver")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.log_search_progress = False

        status = solver.solve(model)

        logger.info(f"Solver finished: {solver.status_name(status)} in {solver.wall_time:.2f}s")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            result = self._extract_result(
                solver, tracks, included, edge_vars, violation_vars, status
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
    ) -> PlaylistResult:
        """Extract playlist from solver solution."""
        n = len(tracks)

        selected_indices = [i for i in range(n) if solver.value(included[i])]

        logger.debug(f"Selected {len(selected_indices)} tracks from solution")

        if not selected_indices:
            return PlaylistResult(playlist=[], solver_status="no_solution")

        selected_edges = {
            (i, j): solver.value(var) for (i, j), var in edge_vars.items() if solver.value(var) == 1
        }

        if not selected_edges:
            if len(selected_indices) == 1:
                playlist = [tracks[selected_indices[0]]]
                transitions = []
            else:
                playlist = [tracks[i] for i in selected_indices]
                transitions = []
        else:
            playlist, transitions = self._reconstruct_path(
                tracks, selected_edges, selected_indices, violation_vars, solver
            )

        harmonic = sum(1 for t in transitions if t.is_harmonic)
        non_harmonic = len(transitions) - harmonic

        bpms = [t.bpm for t in playlist]
        avg_bpm = sum(bpms) / len(bpms) if bpms else 0.0
        bpm_range = (min(bpms), max(bpms)) if bpms else (0.0, 0.0)

        statistics = PlaylistStatistics(
            total_input_tracks=len(tracks),
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

    def _reconstruct_path(self, tracks, selected_edges, selected_indices, violation_vars, solver):
        """Reconstruct the track order from selected edges."""
        edge_map = {i: j for (i, j) in selected_edges if i != j}

        if not edge_map:
            return [tracks[i] for i in selected_indices], []

        start = min(edge_map.keys())

        playlist = []
        transitions = []
        current = start
        visited = set()

        while current in edge_map and current not in visited:
            visited.add(current)
            playlist.append(tracks[current])

            next_idx = edge_map[current]

            if next_idx in edge_map:
                is_harmonic = is_harmonic_compatible(
                    tracks[current].key, tracks[next_idx].key, self.harmonic_level
                )

                bpm_diff = get_bpm_difference(
                    tracks[current].bpm, tracks[next_idx].bpm, self.allow_halftime_bpm
                )

                transitions.append(
                    TransitionInfo(
                        from_track=tracks[current],
                        to_track=tracks[next_idx],
                        is_harmonic=is_harmonic,
                        is_bpm_compatible=True,
                        bpm_difference=bpm_diff,
                    )
                )

            current = next_idx

        if current not in visited:
            playlist.append(tracks[current])

        return playlist, transitions
