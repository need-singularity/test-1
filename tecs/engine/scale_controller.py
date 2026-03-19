# tecs/engine/scale_controller.py
"""Manages adaptive scaling across experiment phases."""
from __future__ import annotations

from tecs.config import ScalingConfig


class ScaleController:
    """Manages adaptive scaling (10² → 10³ → 10⁴ nodes).

    Parameters
    ----------
    config:
        :class:`~tecs.config.ScalingConfig` instance specifying node counts
        and generation limits per phase.
    """

    def __init__(self, config: ScalingConfig) -> None:
        self._cfg = config
        self._current_nodes: int = config.phase1_nodes

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_nodes(self) -> int:
        """Current number of topology nodes."""
        return self._current_nodes

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def on_phase_change(self, new_phase: int) -> None:
        """Update node count based on the new phase number."""
        if new_phase == 1:
            self._current_nodes = self._cfg.phase1_nodes
        elif new_phase in (2, 3, 4):
            self._current_nodes = self._cfg.phase2_nodes
        elif new_phase == 5:
            self._current_nodes = self._cfg.phase5_nodes
        # Phases outside [1, 5] leave the current count unchanged.

    def max_generations(self, phase: int) -> int:
        """Return the maximum generation count for the given phase."""
        if phase == 1:
            return self._cfg.phase1_max_gen
        return self._cfg.phase2_max_gen

    # ------------------------------------------------------------------
    # Resource checks
    # ------------------------------------------------------------------

    def check_memory_ok(self, max_pct: int = 80) -> bool:
        """Return True if system memory usage is below *max_pct* percent."""
        try:
            import psutil  # type: ignore[import-untyped]

            return psutil.virtual_memory().percent < max_pct
        except ImportError:
            return True
