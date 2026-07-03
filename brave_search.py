"""Brave Search API wrapper — used by the research agent for live web results."""
import httpx
from config import BRAVE_API_KEY


def search(query: str, n: int = 5) -> str:
    if not BRAVE_API_KEY:
        return "[brave search: BRAVE_API_KEY not set]"
    try:
        r = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": n, "text_decorations": False},
            headers={"Accept": "application/json",
                     "X-Subscription-Token": BRAVE_API_KEY},
            timeout=10,
        )
        r.raise_for_status()
        results = r.json().get("web", {}).get("results", [])
        if not results:
            return f"[brave search: no results for '{query}']"
        lines = [f"BRAVE SEARCH — {query}"]
        for i, res in enumerate(results, 1):
            lines.append(
                f"\n[{i}] {res.get('title', '')}\n"
                f"{res.get('url', '')}\n"
                f"{res.get('description', '').strip()}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"[brave search failed: {e}]"
