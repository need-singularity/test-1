"""Load knowledge from Wikipedia API — free, no API key."""
from __future__ import annotations
import re
import requests

HEADERS = {"User-Agent": "TECS-Engine/1.0 (research project)"}
BASE_URL = "https://en.wikipedia.org/api/rest_v1"
WIKI_API = "https://en.wikipedia.org/w/api.php"


class WikipediaLoader:
    def __init__(self):
        self.articles: dict[str, str] = {}  # title -> text
        self.links: list[tuple[str, str]] = []  # (from_title, to_title)
        self.categories: dict[str, list[str]] = {}  # title -> [categories]

    def load_topic(self, topic: str, depth: int = 1, max_related: int = 10) -> None:
        """Load a topic and its related articles.
        depth=0: just the topic
        depth=1: topic + linked articles
        """
        self._fetch_article(topic)

        if depth >= 1:
            # Get linked articles
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

    def extract_triples(self) -> list[tuple[str, str, str]]:
        """Extract triples from loaded articles using simple pattern matching."""
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

        # From text: simple "X is a Y" pattern extraction
        for title, text in self.articles.items():
            text_triples = self._extract_from_text(title, text)
            triples.extend(text_triples)

        return triples

    def _extract_from_text(self, title: str, text: str) -> list[tuple[str, str, str]]:
        """Extract triples from text using regex patterns."""
        triples = []
        title_norm = self._normalize(title)

        # "X is a Y" / "X is the Y"
        patterns = [
            (r"(?:is|are)\s+(?:a|an|the)\s+(\w[\w\s]{1,30}?)(?:\.|,|\s+(?:that|which|who|and|in|of))", "IsA"),
            (r"(?:is|are)\s+(?:also\s+)?(?:known\s+as|called)\s+(\w[\w\s]{1,30}?)(?:\.|,)", "AlsoKnownAs"),
            (r"(?:was|were)\s+(?:a|an|the)\s+(\w[\w\s]{1,30}?)(?:\.|,|\s+(?:that|which|who|and|in))", "IsA"),
            (r"(?:has|have)\s+(?:a|an|the)?\s*(\w[\w\s]{1,30}?)(?:\.|,)", "HasA"),
            (r"(?:part\s+of|belongs?\s+to)\s+(?:the\s+)?(\w[\w\s]{1,30}?)(?:\.|,)", "PartOf"),
            (r"(?:used\s+(?:in|for)|applied\s+(?:in|to))\s+(\w[\w\s]{1,30}?)(?:\.|,)", "UsedIn"),
            (r"(?:proposed|discovered|invented)\s+by\s+(\w[\w\s]{1,30}?)(?:\.|,|\s+in)", "ProposedBy"),
            (r"(?:related\s+to|connected\s+to|associated\s+with)\s+(\w[\w\s]{1,30}?)(?:\.|,)", "RelatedTo"),
        ]

        # First sentence often defines the topic
        sentences = text.split(". ")
        for sent in sentences[:5]:  # first 5 sentences
            for pattern, relation in patterns:
                matches = re.findall(pattern, sent, re.IGNORECASE)
                for match in matches:
                    obj = self._normalize(match.strip())
                    if obj and len(obj) > 1 and obj != title_norm:
                        triples.append((title_norm, relation, obj))

        return triples

    def _normalize(self, text: str) -> str:
        """Normalize entity name."""
        return re.sub(r'[^\w\s]', '', text.lower()).strip()
