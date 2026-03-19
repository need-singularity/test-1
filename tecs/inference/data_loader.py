"""Data loaders for GloVe, ConceptNet, and WordNet."""
from __future__ import annotations


def load_glove_vectors(path: str, max_words: int = 50000) -> dict:
    """Load GloVe vectors from a text file.

    Each line: word float float ...
    Returns dict mapping word -> list of floats.
    """
    import numpy as np

    vectors: dict[str, np.ndarray] = {}
    with open(path) as f:
        for i, line in enumerate(f):
            if i >= max_words:
                break
            parts = line.strip().split()
            word = parts[0]
            vec = np.array([float(x) for x in parts[1:]], dtype=np.float32)
            vectors[word] = vec
    return vectors


def load_conceptnet_triples(path: str, max_triples: int = 10000) -> list[tuple[str, str, str]]:
    """Load ConceptNet triples from a TSV file.

    Each line: head<TAB>relation<TAB>tail
    """
    triples = []
    with open(path) as f:
        for i, line in enumerate(f):
            if i >= max_triples:
                break
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                triples.append((parts[0], parts[1], parts[2]))
    return triples


def load_wordnet_hypernyms(max_synsets: int = 5000) -> list[tuple[str, str, str]]:
    """Load WordNet hypernym (IsA) triples via NLTK."""
    from nltk.corpus import wordnet as wn

    triples = []
    for synset in list(wn.all_synsets())[:max_synsets]:
        word = synset.lemmas()[0].name()
        for hyper in synset.hypernyms():
            parent = hyper.lemmas()[0].name()
            triples.append((word, "IsA", parent))
    return triples
