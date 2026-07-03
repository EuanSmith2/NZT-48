"""Web search via DuckDuckGo — no key, no account, completely free."""


def search(query: str, n: int = 5) -> str:
    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, max_results=n))
        if not results:
            return f"[search: no results for '{query}']"
        lines = [f"WEB SEARCH — {query}"]
        for i, r in enumerate(results, 1):
            lines.append(
                f"\n[{i}] {r.get('title', '')}\n"
                f"{r.get('href', '')}\n"
                f"{r.get('body', '').strip()}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"[search failed: {e}]"
