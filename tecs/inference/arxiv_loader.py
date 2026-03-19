"""Load knowledge from arXiv API — free, no API key."""
from __future__ import annotations
import re
import time
import requests
import xml.etree.ElementTree as ET

ARXIV_API = "http://export.arxiv.org/api/query"
HEADERS = {"User-Agent": "TECS-Engine/1.0 (research)"}

# Noise filter for arXiv
ARXIV_NOISE = {"we", "our", "this", "paper", "show", "prove", "study", "result",
               "method", "approach", "new", "novel", "recent", "also", "using",
               "given", "case", "work", "problem", "question", "answer"}

# Deep extraction patterns for math/physics papers
PAPER_PATTERNS = [
    (r"(?:equivalent|analogous|isomorphic|dual)\s+to\s+(?:the\s+)?(\w[\w\s\-]{2,40}?)(?:\.|,)", "AnalogousTo"),
    (r"(?:generali[sz]es?|extends?)\s+(?:the\s+)?(\w[\w\s\-]{2,40}?)(?:\.|,)", "Generalizes"),
    (r"(?:implies?|leads?\s+to|yields?)\s+(?:the\s+)?(\w[\w\s\-]{2,40}?)(?:\.|,)", "Implies"),
    (r"(?:connects?|relates?|links?)\s+(?:the\s+)?(\w[\w\s\-]{2,40}?)\s+(?:to|and|with)", "RelatedTo"),
    (r"(?:conjecture[ds]?|hypothesi[sz]e[ds]?)\s+that\s+(?:the\s+)?(\w[\w\s\-]{2,40}?)(?:\.|,)", "Conjectures"),
    (r"(?:depends?\s+on|requires?|assumes?)\s+(?:the\s+)?(\w[\w\s\-]{2,40}?)(?:\.|,)", "DependsOn"),
    (r"(?:contradicts?|disproves?|refutes?)\s+(?:the\s+)?(\w[\w\s\-]{2,40}?)(?:\.|,)", "Contradicts"),
    (r"(?:open\s+problem|unsolved|unknown|remains?\s+open)\s+(?:whether\s+)?(?:the\s+)?(\w[\w\s\-]{2,40}?)(?:\.|,)", "OpenProblem"),
]


class ArxivLoader:
    def __init__(self):
        self.papers: list[dict] = []
        self.concepts: set[str] = set()

    def search(self, query: str, max_results: int = 100, categories: str = "") -> None:
        """Search arXiv for papers. Free API, no key needed."""
        search_query = f"all:{query}"
        if categories:
            search_query = f"cat:{categories} AND all:{query}"

        batch_size = 50
        fetched = 0

        while fetched < max_results:
            params = {
                "search_query": search_query,
                "start": fetched,
                "max_results": min(batch_size, max_results - fetched),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            try:
                resp = requests.get(ARXIV_API, params=params, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    break
                root = ET.fromstring(resp.text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entries = root.findall("atom:entry", ns)
                if not entries:
                    break

                for entry in entries:
                    title = entry.find("atom:title", ns)
                    summary = entry.find("atom:summary", ns)
                    published = entry.find("atom:published", ns)
                    cats = [c.get("term", "") for c in entry.findall("atom:category", ns)]

                    paper = {
                        "title": title.text.strip().replace("\n", " ") if title is not None else "",
                        "abstract": summary.text.strip().replace("\n", " ") if summary is not None else "",
                        "date": published.text[:10] if published is not None else "",
                        "categories": cats,
                    }
                    self.papers.append(paper)

                fetched += len(entries)
                time.sleep(1)  # arXiv rate limit: 1 req/sec
            except Exception as e:
                print(f"    [arXiv fetch error: {e}]")
                break

        print(f"    arXiv: {len(self.papers)}편 논문 로드됨")

    def extract_triples(self) -> list[tuple[str, str, str]]:
        """Extract triples from paper titles and abstracts."""
        triples = []

        for paper in self.papers:
            title_norm = self._normalize(paper["title"])
            abstract = paper["abstract"]

            # Title-level: paper IsA category
            for cat in paper["categories"][:2]:
                if cat:
                    triples.append((title_norm, "IsA", self._normalize(cat)))

            # Extract from abstract
            abstract_triples = self._extract_from_abstract(title_norm, abstract)
            triples.extend(abstract_triples)

        # Filter noise
        triples = [(h, r, t) for h, r, t in triples
                   if not self._is_noise(h) and not self._is_noise(t)]

        # Deduplicate
        triples = list(set(triples))
        return triples

    def _extract_from_abstract(self, paper_title: str, abstract: str) -> list[tuple[str, str, str]]:
        """Extract concept relationships from abstract."""
        triples = []
        sentences = abstract.split(". ")

        for sent in sentences:
            for pattern, relation in PAPER_PATTERNS:
                matches = re.findall(pattern, sent, re.IGNORECASE)
                for match in matches:
                    obj = self._normalize(match.strip())
                    if obj and len(obj) > 3 and not self._is_noise(obj):
                        triples.append((paper_title, relation, obj))

            # Extract key noun phrases as concepts related to the paper
            key_phrases = self._extract_key_phrases(sent)
            for phrase in key_phrases:
                if phrase != paper_title:
                    triples.append((paper_title, "RelatedTo", phrase))
                    self.concepts.add(phrase)

        return triples

    def _extract_key_phrases(self, text: str) -> list[str]:
        """Extract key technical phrases from text."""
        phrases = []
        # Match capitalized multi-word terms or known patterns
        patterns = [
            r"\b([A-Z][a-z]+(?:\s+[A-Za-z]+){1,3})\s+(?:conjecture|hypothesis|theorem|equation|formula|function|theory|model|group|algebra|space|operator)",
            r"\b((?:quantum|spectral|random|stochastic|analytic|algebraic|arithmetic|geometric)\s+\w+(?:\s+\w+)?)\b",
            r"\b(\w+\s+(?:zeta|L-function|matrix|eigenvalue|trace|operator|spectrum|distribution))\b",
        ]
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                norm = self._normalize(m)
                if norm and len(norm) > 5 and not self._is_noise(norm):
                    phrases.append(norm)
        return phrases[:5]  # max 5 per sentence

    def _normalize(self, text: str) -> str:
        return re.sub(r'[^\w\s\-]', '', text.lower()).strip()

    def _is_noise(self, text: str) -> bool:
        text_lower = text.lower().strip()
        if len(text_lower) < 4 or len(text_lower) > 60:
            return True
        words = text_lower.split()
        if all(w in ARXIV_NOISE for w in words):
            return True
        if sum(1 for c in text_lower if c.isalpha()) / max(len(text_lower), 1) < 0.6:
            return True
        return False
