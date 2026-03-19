# tecs/data/wordnet_loader.py
"""Thin WordNet loader using NLTK.
Falls back gracefully when NLTK data is not downloaded.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class WordNetLoader:
    """Load concept relations from WordNet via NLTK.

    When NLTK corpora are unavailable the loader raises
    ``WordNetUnavailable`` so callers can fall back gracefully.
    """

    class WordNetUnavailable(RuntimeError):
        """Raised when WordNet data cannot be obtained."""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_concept_relations(self, n: int = 100) -> list[dict]:
        """Return up to *n* hypernym/hyponym triples from WordNet."""
        wn = self._get_wordnet()
        triples: list[dict] = []
        for synset in wn.all_synsets():
            if len(triples) >= n:
                break
            head = synset.name().split(".")[0].replace("_", " ")
            for hyper in synset.hypernyms():
                if len(triples) >= n:
                    break
                tail = hyper.name().split(".")[0].replace("_", " ")
                triples.append({"head": head, "relation": "IsA", "tail": tail})
            for hypo in synset.hyponyms():
                if len(triples) >= n:
                    break
                tail = hypo.name().split(".")[0].replace("_", " ")
                triples.append({"head": head, "relation": "HasA", "tail": tail})
        return triples

    def download(self) -> None:
        """Download required NLTK corpora."""
        import nltk

        for corpus in ("wordnet", "omw-1.4"):
            nltk.download(corpus, quiet=True)
        logger.info("NLTK WordNet corpora downloaded.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_wordnet(self):
        """Return the NLTK wordnet corpus reader, raising WordNetUnavailable on failure."""
        try:
            from nltk.corpus import wordnet as wn

            # Trigger a lookup to verify the corpus is actually present
            _ = list(wn.all_synsets())[:1]
            return wn
        except Exception as exc:
            raise self.WordNetUnavailable(
                f"NLTK WordNet corpus unavailable: {exc}. "
                "Run WordNetLoader().download() or "
                "python -m tecs.data.data_manager --download"
            ) from exc
