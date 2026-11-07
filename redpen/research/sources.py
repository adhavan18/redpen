"""source fetchers. every function returns plain dicts and raises on failure;
the caller decides whether a failure is fatal (it almost never is)."""

import html
import re
from concurrent.futures import ThreadPoolExecutor

import httpx
import trafilatura

from .. import config
from .reliability import is_blocked, tier

HEADERS = {"User-Agent": config.USER_AGENT, "Accept-Language": "en"}


def http() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=config.HTTP_TIMEOUT, follow_redirects=True)


# ---------- web search ----------

def web_search(query: str, n: int = 6) -> list[dict]:
    """tavily if a key is configured, otherwise duckduckgo. returns [{title, url, snippet}]."""
    if config.TAVILY_API_KEY:
        try:
            with http() as c:
                r = c.post("https://api.tavily.com/search",
                           json={"api_key": config.TAVILY_API_KEY, "query": query, "max_results": n})
                r.raise_for_status()
                return [{"title": x["title"], "url": x["url"], "snippet": x.get("content", "")}
                        for x in r.json().get("results", []) if not is_blocked(x["url"])]
        except Exception:
            pass  # fall through to duckduckgo
    import time

    from ddgs import DDGS

    rows, last = [], None
    # ddgs is flaky under load: retry, then try a shorter query (long ones often return nothing)
    for attempt, (q, backend) in enumerate([(query, "auto"), (query, "auto"),
                                            (" ".join(query.split()[:5]), "auto"), (query, "duckduckgo")]):
        try:
            rows = DDGS().text(q, max_results=n + 4, backend=backend) or []
            if rows:
                break
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(0.8 * (attempt + 1))
    if not rows and last:
        raise last
    out = [{"title": x.get("title", ""), "url": x.get("href", ""), "snippet": x.get("body", "")}
           for x in rows if x.get("href") and not is_blocked(x["href"])]
    return out[:n]


def fetch_page(url: str) -> dict:
    """download a page and extract readable text. raises on http errors or empty pages."""
    with http() as c:
        r = c.get(url)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "html" not in ctype and "text" not in ctype:
        raise ValueError(f"not a text page ({ctype or 'unknown type'})")
    text = trafilatura.extract(r.text, include_comments=False, include_tables=True, favor_recall=True) or ""
    meta = trafilatura.extract_metadata(r.text)
    if tier(str(r.url))[0] == "A" and len(r.text) > 150_000:
        # long specs (rfcs, standards) defeat boilerplate removal: trafilatura keeps a fraction.
        # take the full text; the research step keeps only the passages relevant to the objective.
        import lxml.html

        full = re.sub(r"[ \t]+", " ", lxml.html.fromstring(r.text).text_content())
        full = re.sub(r"\n\s*\n\s*\n+", "\n\n", full)
        if len(full) > len(text) * 4:
            text = full
    if len(text) < 400:
        raise ValueError("page has too little readable text")
    return {
        "text": text[:700_000],
        "title": (meta.title if meta and meta.title else "").strip(),
        "published": (meta.date if meta and meta.date else None),
        "final_url": str(r.url),
        "status": r.status_code,
    }


def fetch_many(urls: list[str], workers: int = 8) -> dict[str, dict]:
    def one(u):
        try:
            return u, fetch_page(u)
        except Exception as e:  # noqa: BLE001 - every failure becomes a recorded source error
            return u, {"error": f"{type(e).__name__}: {str(e)[:160]}"}

    with ThreadPoolExecutor(workers) as ex:
        return dict(ex.map(one, urls))


# ---------- wikipedia ----------

def wikipedia(query: str, n: int = 2) -> list[dict]:
    with http() as c:
        r = c.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query", "list": "search", "srsearch": query, "srlimit": n, "format": "json"})
        r.raise_for_status()
        titles = [x["title"] for x in r.json()["query"]["search"]]
        if not titles:
            return []
        r = c.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query", "prop": "extracts", "explaintext": 1, "titles": "|".join(titles),
            "format": "json", "redirects": 1})
        r.raise_for_status()
    out = []
    for page in r.json()["query"]["pages"].values():
        text = page.get("extract", "")
        if len(text) > 400:
            title = page["title"]
            out.append({"title": f"{title} - Wikipedia",
                        "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
                        "text": text[:40000]})
    return out


# ---------- books ----------

def books(query: str, n: int = 3) -> list[dict]:
    """google books first (has descriptions), open library as a fallback."""
    out = []
    try:
        with http() as c:
            r = c.get("https://www.googleapis.com/books/v1/volumes",
                      params={"q": query, "maxResults": 8, "printType": "books", "langRestrict": "en"})
            r.raise_for_status()
        for item in r.json().get("items", []):
            v = item.get("volumeInfo", {})
            desc = re.sub(r"<[^>]+>", " ", v.get("description", "") or "")
            snippet = html.unescape(item.get("searchInfo", {}).get("textSnippet", "") or "")
            snippet = re.sub(r"<[^>]+>", "", snippet)
            if not v.get("title") or len(desc) < 120:
                continue
            authors = ", ".join(v.get("authors", [])[:3])
            out.append({
                "title": v["title"] + (f": {v['subtitle']}" if v.get("subtitle") else ""),
                "authors": authors,
                "published": v.get("publishedDate"),
                "publisher": v.get("publisher"),
                "url": v.get("infoLink") or v.get("canonicalVolumeLink") or "",
                "text": f"{v['title']} by {authors} ({v.get('publishedDate', 'n.d.')}). {desc} {snippet}".strip(),
                "isbn": next((i["identifier"] for i in v.get("industryIdentifiers", [])
                              if i.get("type") == "ISBN_13"), None),
            })
    except Exception:
        pass
    if len(out) < n:
        try:
            with http() as c:
                r = c.get("https://openlibrary.org/search.json", params={"q": query, "limit": 6})
                r.raise_for_status()
            for d in r.json().get("docs", []):
                if not d.get("title"):
                    continue
                authors = ", ".join(d.get("author_name", [])[:3])
                subjects = ", ".join(d.get("subject", [])[:12])
                out.append({
                    "title": d["title"], "authors": authors,
                    "published": str(d.get("first_publish_year", "")) or None, "publisher": None,
                    "url": f"https://openlibrary.org{d['key']}",
                    "text": f"{d['title']} by {authors} (first published {d.get('first_publish_year', 'n.d.')}). "
                            f"Subjects: {subjects}.",
                    "isbn": None,
                })
        except Exception:
            pass
    return out[:n]


# ---------- stack overflow: real learner confusion ----------

def stackoverflow(query: str, n: int = 6) -> list[dict]:
    """highest-voted questions matching the query. question titles are what confused real people."""
    base = {"site": "stackoverflow", "order": "desc", "sort": "votes", "pagesize": n, "filter": "withbody"}
    with http() as c:
        r = c.get("https://api.stackexchange.com/2.3/search/advanced", params=base | {"title": query})
        r.raise_for_status()
        items = r.json().get("items", [])
        if len(items) < 3:  # title match too strict: fall back to full-text search
            r = c.get("https://api.stackexchange.com/2.3/search/advanced", params=base | {"q": query})
            r.raise_for_status()
            items = r.json().get("items", [])
    out = []
    for q in items:
        body = html.unescape(re.sub(r"<[^>]+>", " ", q.get("body", "")))
        body = re.sub(r"\s+", " ", body).strip()
        out.append({"title": html.unescape(q["title"]), "url": q["link"], "score": q.get("score", 0),
                    "answered": q.get("is_answered", False), "excerpt": body[:600]})
    return out
