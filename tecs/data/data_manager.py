# tecs/data/data_manager.py
"""Central data interface for TECS.

Provides point clouds for representation components and benchmark data for
evaluation.  When ``use_external=False`` (the default for development) all
data is generated synthetically with no network or NLTK dependencies.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from tecs.data.synthetic_generator import SyntheticGenerator

logger = logging.getLogger(__name__)


class DataManager:
    """Central data interface.

    Parameters
    ----------
    cache_dir:
        Directory used for caching downloaded external data.
    use_external:
        If ``True`` attempt to load from ConceptNet / WordNet first,
        falling back to synthetic generation when unavailable.
        If ``False`` (default) always use synthetic generation.
    seed:
        Optional random seed forwarded to :class:`SyntheticGenerator`.
    """

    def __init__(
        self,
        cache_dir: str = "data/",
        use_external: bool = False,
        seed: int | None = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.use_external = use_external
        self._synthetic = SyntheticGenerator(seed=seed)

        self._conceptnet: object | None = None
        self._wordnet: object | None = None

        if use_external:
            self._init_external_loaders()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_points(self, n: int, dim: int = 3) -> np.ndarray:
        """Get a point cloud for representation components.

        Parameters
        ----------
        n:   Number of points.
        dim: Dimensionality of each point.

        Returns
        -------
        np.ndarray of shape ``(n, dim)``.
        """
        return self._synthetic.get_points(n=n, dim=dim)

    def get_concept_relations(self, n: int = 100) -> list[dict]:
        """Return concept triples.

        Each element is ``{"head": str, "relation": str, "tail": str}``.
        """
        if self.use_external:
            result = self._try_external_relations(n)
            if result is not None:
                return result
        return self._synthetic.get_concept_relations(n=n)

    def get_contradictions(self, n: int = 50) -> list[dict]:
        """Return contradiction pairs.

        Each element is ``{"positive": triple_dict, "negative": triple_dict}``
        where the negative triple inverts the relation of the positive.
        """
        return self._synthetic.get_contradictions(n=n)

    def get_analogies(self, n: int = 50) -> list[dict]:
        """Return analogy quads (A:B::C:D).

        Each element is ``{"a": str, "b": str, "c": str, "d": str, "relation": str}``.
        """
        return self._synthetic.get_analogies(n=n)

    def download_external(self) -> None:
        """Download ConceptNet / WordNet data to ``cache_dir``.

        Called by: ``python -m tecs.data.data_manager --download``
        """
        print(f"Downloading external data to {self.cache_dir} …")

        # WordNet via NLTK
        try:
            from tecs.data.wordnet_loader import WordNetLoader

            wl = WordNetLoader()
            wl.download()
            print("  [OK] WordNet (NLTK) corpora downloaded.")
        except Exception as exc:
            print(f"  [WARN] WordNet download failed: {exc}")

        # ConceptNet — cache a sample via the API
        try:
            from tecs.data.conceptnet_loader import ConceptNetLoader

            cl = ConceptNetLoader(cache_dir=str(self.cache_dir))
            cl.download(n=1000)
            print(f"  [OK] ConceptNet relations cached to {self.cache_dir}.")
        except Exception as exc:
            print(f"  [WARN] ConceptNet download failed: {exc}")

        print("Done.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_external_loaders(self) -> None:
        try:
            from tecs.data.conceptnet_loader import ConceptNetLoader

            self._conceptnet = ConceptNetLoader(cache_dir=str(self.cache_dir))
        except ImportError:
            logger.warning("ConceptNetLoader unavailable.")

        try:
            from tecs.data.wordnet_loader import WordNetLoader

            self._wordnet = WordNetLoader()
        except ImportError:
            logger.warning("WordNetLoader unavailable.")

    def _try_external_relations(self, n: int) -> list[dict] | None:
        """Try ConceptNet then WordNet; return ``None`` to signal fallback."""
        # Try ConceptNet first
        if self._conceptnet is not None:
            try:
                from tecs.data.conceptnet_loader import ConceptNetLoader

                result = self._conceptnet.get_concept_relations(n=n)  # type: ignore[union-attr]
                if result:
                    return result
            except Exception as exc:
                logger.debug("ConceptNet unavailable, skipping: %s", exc)

        # Try WordNet
        if self._wordnet is not None:
            try:
                result = self._wordnet.get_concept_relations(n=n)  # type: ignore[union-attr]
                if result:
                    return result
            except Exception as exc:
                logger.debug("WordNet unavailable, skipping: %s", exc)

        return None
