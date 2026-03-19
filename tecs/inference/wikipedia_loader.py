"""Load knowledge from Wikipedia API — free, no API key."""
from __future__ import annotations
import re
import requests

HEADERS = {"User-Agent": "TECS-Engine/1.0 (research project)"}
BASE_URL = "https://en.wikipedia.org/api/rest_v1"
WIKI_API = "https://en.wikipedia.org/w/api.php"

# Noise patterns to filter out — Wikipedia metadata / maintenance tags
NOISE_PATTERNS = [
    "short description",
    "wikidata",
    "wikipedia",
    "articles with",
    "articles containing",
    "articles needing",
    "cs1 maint",
    "cs1 errors",
    "webarchive",
    "pages using",
    "pages with",
    "all articles",
    "use dmy dates",
    "use mdy dates",
    "commons category",
    "good articles",
    "featured articles",
    "stub",
    "redirects",
    "template",
    "citation needed",
    "orphaned articles",
    "cleanup",
    "accuracy dispute",
]

# Deep extraction patterns for math / science / finance documents.
# Each entry is (regex, relation_name).  relation_name=None means "tag the
# article itself" (we use the match as an object with relation "TaggedAs").
DEEP_PATTERNS = [
    # Mathematical relationships
    (r"(?:described|governed|modeled)\s+by\s+(?:the\s+)?(\w[\w\s]{1,40}?)(?:\.|,)", "ModeledBy"),
    (r"(?:solution|solutions)\s+(?:of|to)\s+(?:the\s+)?(\w[\w\s]{1,40}?)(?:\.|,)", "SolutionOf"),
    (r"(?:derived|derives|derivation)\s+(?:from|of)\s+(?:the\s+)?(\w[\w\s]{1,40}?)(?:\.|,)", "DerivedFrom"),
    (r"(?:generali[sz]es?|generali[sz]ation\s+of)\s+(?:the\s+)?(\w[\w\s]{1,40}?)(?:\.|,)", "Generalizes"),
    (r"(?:special\s+case|particular\s+case)\s+of\s+(?:the\s+)?(\w[\w\s]{1,40}?)(?:\.|,)", "SpecialCaseOf"),
    (r"(?:equivalent|analogous|similar)\s+to\s+(?:the\s+)?(\w[\w\s]{1,40}?)(?:\.|,)", "AnalogousTo"),
    # Process / distribution relationships
    (r"(?:based\s+on|assumes?|using)\s+(?:a\s+)?(\w[\w\s]{1,40}?)\s+(?:process|distribution|model)", "UsesProcess"),
    (r"\b([A-Z][a-z]{2,20}(?:\s+[a-z]{3,15})?)\s+(?:process|distribution|equation|formula|model)\b", "TypeOf"),
    # Causal / functional
    (r"(?:determines?|predicts?|calculates?|computes?)\s+(?:the\s+)?(\w[\w\s]{1,40}?)(?:\.|,)", "Determines"),
    (r"(?:depends?\s+on|function\s+of)\s+(?:the\s+)?(\w[\w\s]{1,40}?)(?:\.|,)", "DependsOn"),
    # Domain bridging
    (r"(?:applied|used|utilized)\s+in\s+(\w[\w\s]{1,40}?)(?:\.|,)", "AppliedIn"),
    (r"(?:fundamental|key|central|important)\s+(?:concept|idea|principle)\s+in\s+(\w[\w\s]{1,40}?)(?:\.|,)", "FundamentalIn"),
    # Structural tags (no capture group — we tag the article)
    (r"(partial\s+differential\s+equation)", "TaggedAs"),
    (r"(stochastic\s+(?:process|calculus|differential))", "TaggedAs"),
    (r"(Brownian\s+motion|Wiener\s+process)", "TaggedAs"),
    (r"(probability\s+(?:amplitude|distribution|density))", "TaggedAs"),
    (r"(Markov\s+(?:process|chain|property))", "TaggedAs"),
]


class WikipediaLoader:
    def __init__(self):
        self.articles: dict[str, str] = {}  # title -> text
        self.links: list[tuple[str, str]] = []  # (from_title, to_title)
        self.categories: dict[str, list[str]] = {}  # title -> [categories]

    # ------------------------------------------------------------------
    # Noise filtering
    # ------------------------------------------------------------------

    def _is_noise(self, text: str) -> bool:
        """Return True if *text* looks like Wikipedia metadata garbage."""
        text_lower = text.lower().strip()
        if len(text_lower) < 2:
            return True
        if len(text_lower) > 50:
            return True
        for pattern in NOISE_PATTERNS:
            if pattern in text_lower:
                return True
        # Filter pure numbers / punctuation sequences
        if text_lower.replace(" ", "").replace(".", "").isdigit():
            return True
        # Filter sentence fragments (starts with lowercase article/preposition/conjunction)
        if text_lower.startswith(("the ", "a ", "an ", "is ", "are ", "was ", "in ", "of ",
                                   "and ", "or ", "to ", "for ", "with ", "by ", "on ",
                                   "that ", "which ", "who ", "this ", "these ", "those ",
                                   "its ", "his ", "her ", "their ", "our ", "your ",
                                   "ed ", "ing ", "tion ", "ment ", "ity ", "ness ")):
            return True
        # Filter if mostly non-alpha (broken extraction)
        alpha_ratio = sum(1 for c in text_lower if c.isalpha()) / max(len(text_lower), 1)
        if alpha_ratio < 0.6:
            return True
        # Filter very short words that are likely fragments
        words = text_lower.split()
        if len(words) == 1 and len(words[0]) < 3:
            return True
        # Filter if all words are common stop-words / function words
        function_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                         "and", "or", "but", "not", "also", "then", "than", "that",
                         "this", "which", "who", "whom", "whose", "what", "where",
                         "when", "how", "if", "so", "as", "at", "by", "for", "from",
                         "in", "into", "of", "on", "to", "with", "its", "his", "her",
                         "their", "our", "your", "my", "it", "he", "she", "they", "we"}
        if all(w in function_words for w in words):
            return True
        # Filter if entity is just a single generic word (adjective, person name, etc.)
        if len(words) == 1:
            # Allow known scientific/technical terms
            science_terms = {"brownian", "gaussian", "markov", "wiener", "hamiltonian",
                           "lagrangian", "newtonian", "euclidean", "riemannian", "boltzmann",
                           "diffusion", "entropy", "quantum", "stochastic", "probability",
                           "thermodynamics", "relativity", "electromagnetism",
                           "neuron", "synapse", "axon", "dendrite", "cortex",
                           "internet", "ethernet", "protocol", "bandwidth",
                           "galaxy", "cosmos", "filament", "quasar", "pulsar",
                           "topology", "manifold", "eigenvalue", "matrix",
                           "algorithm", "encryption", "compiler", "processor",
                           "chromosome", "mitochondria", "ribosome", "cytoplasm",
                           "gravitation", "magnetism", "radiation", "wavelength",
                           "supernova", "nebula", "asteroid", "exoplanet"}
            if text_lower in science_terms:
                return False
            # Filter single words shorter than 5 chars (likely fragments)
            if len(text_lower) < 5:
                return True
        # Filter partial sentence fragments (contains verbs/articles mid-phrase)
        fragment_indicators = {" the ", " is ", " are ", " was ", " a ", " an ",
                              " who ", " that ", " which ", " its ", " has ", " had "}
        if any(ind in f" {text_lower} " for ind in fragment_indicators):
            return True
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_topic(self, topic: str, depth: int = 1, max_related: int = 10) -> None:
        """Load a topic and its related articles.
        depth=0: just the topic
        depth=1: topic + linked articles
        """
        self._fetch_article(topic)
        # Replace summary with full text for deeper extraction
        full_text = self._fetch_full_text(topic)
        if full_text:
            self.articles[topic] = full_text

        if depth >= 1:
            links = self._get_links(topic, max_related)
            for link_title in links:
                self._fetch_article(link_title)
                self.links.append((topic, link_title))

    def _fetch_article(self, title: str) -> str | None:
        """Fetch article summary from Wikipedia REST API."""
        if title in self.articles:
            return self.articles[title]
        try:
            url = f"{BASE_URL}/page/summary/{title.replace(' ', '_')}"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("extract", "")
                self.articles[title] = text
                # Get categories
                self._fetch_categories(title)
                return text
        except Exception:
            pass
        return None

    def _fetch_full_text(self, title: str) -> str | None:
        """Fetch full article text for deeper extraction."""
        try:
            params = {
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "explaintext": "true",
                "exlimit": "1",
                "exsectionformat": "plain",
                "format": "json",
            }
            resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    return page_data.get("extract", "")
        except Exception:
            pass
        return None

    def _get_links(self, title: str, max_links: int = 10) -> list[str]:
        """Get linked article titles from a Wikipedia article."""
        try:
            params = {
                "action": "query", "titles": title, "prop": "links",
                "pllimit": str(max_links), "plnamespace": "0",  # main namespace only
                "format": "json",
            }
            resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    links = page_data.get("links", [])
                    return [l["title"] for l in links]
        except Exception:
            pass
        return []

    def _fetch_categories(self, title: str) -> None:
        """Fetch categories for an article."""
        try:
            params = {
                "action": "query", "titles": title, "prop": "categories",
                "cllimit": "10", "format": "json",
            }
            resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    cats = page_data.get("categories", [])
                    self.categories[title] = [c["title"].replace("Category:", "") for c in cats]
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Triple extraction
    # ------------------------------------------------------------------

    def extract_triples(self) -> list[tuple[str, str, str]]:
        """Extract triples from loaded articles using pattern matching."""
        triples = []

        # From links: (article, RelatedTo, linked_article)
        for from_title, to_title in self.links:
            triples.append((self._normalize(from_title), "RelatedTo", self._normalize(to_title)))

        # From categories: (article, IsA/PartOf, category)
        for title, cats in self.categories.items():
            for cat in cats:
                cat_clean = self._normalize(cat)
                if cat_clean and not cat_clean.startswith(("articles", "pages", "cs1", "webarchive", "all ")):
                    triples.append((self._normalize(title), "IsA", cat_clean))

        # From text: pattern-based extraction (basic + deep)
        for title, text in self.articles.items():
            text_triples = self._extract_from_text(title, text)
            triples.extend(text_triples)

        # Filter noise from all triples
        triples = [
            (h, r, t) for h, r, t in triples
            if not self._is_noise(h) and not self._is_noise(t)
        ]

        return triples

    def _extract_from_text(self, title: str, text: str) -> list[tuple[str, str, str]]:
        """Extract triples from text using basic + deep regex patterns."""
        triples = []
        title_norm = self._normalize(title)

        # ---- Basic "is a / was a / related to …" patterns ----
        basic_patterns = [
            (r"(?:is|are)\s+(?:a|an|the)\s+(\w[\w\s]{1,30}?)(?:\.|,|\s+(?:that|which|who|and|in|of))", "IsA"),
            (r"(?:is|are)\s+(?:also\s+)?(?:known\s+as|called)\s+(\w[\w\s]{1,30}?)(?:\.|,)", "AlsoKnownAs"),
            (r"(?:was|were)\s+(?:a|an|the)\s+(\w[\w\s]{1,30}?)(?:\.|,|\s+(?:that|which|who|and|in))", "IsA"),
            (r"(?:has|have)\s+(?:a|an|the)?\s*(\w[\w\s]{1,30}?)(?:\.|,)", "HasA"),
            (r"(?:part\s+of|belongs?\s+to)\s+(?:the\s+)?(\w[\w\s]{1,30}?)(?:\.|,)", "PartOf"),
            (r"(?:used\s+(?:in|for)|applied\s+(?:in|to))\s+(\w[\w\s]{1,30}?)(?:\.|,)", "UsedIn"),
            (r"(?:proposed|discovered|invented)\s+by\s+(\w[\w\s]{1,30}?)(?:\.|,|\s+in)", "ProposedBy"),
            (r"(?:related\s+to|connected\s+to|associated\s+with)\s+(\w[\w\s]{1,30}?)(?:\.|,)", "RelatedTo"),
        ]

        # First 5 sentences for basic patterns
        sentences = text.split(". ")
        for sent in sentences[:5]:
            for pattern, relation in basic_patterns:
                matches = re.findall(pattern, sent, re.IGNORECASE)
                for match in matches:
                    obj = self._normalize(match.strip())
                    if obj and len(obj) > 1 and obj != title_norm:
                        triples.append((title_norm, relation, obj))

        # ---- Deep patterns — run over ALL sentences ----
        for sent in sentences:
            for pattern, relation in DEEP_PATTERNS:
                if relation is None:
                    continue
                matches = re.findall(pattern, sent, re.IGNORECASE)
                for match in matches:
                    obj = self._normalize(match.strip())
                    if obj and len(obj) > 1 and obj != title_norm:
                        triples.append((title_norm, relation, obj))

        return triples

    def _normalize(self, text: str) -> str:
        """Normalize entity name."""
        return re.sub(r'[^\w\s]', '', text.lower()).strip()
