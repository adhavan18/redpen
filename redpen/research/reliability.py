"""source reliability tiers.

A  primary / authoritative: standards bodies, official docs, universities, government
B  reputable secondary: encyclopedias, established tutorial sites, vendor learning centres
C  everything else: personal blogs, aggregators, forums

the tier is a heuristic and is shown with its reason so an instructor can disagree with it.
"""

from urllib.parse import urlparse

TIER_A = {
    "rfc-editor.org": "IETF RFC (the standard itself)",
    "datatracker.ietf.org": "IETF datatracker (standards)",
    "ietf.org": "IETF (standards body)",
    "w3.org": "W3C (standards body)",
    "whatwg.org": "WHATWG living standard",
    "developer.mozilla.org": "MDN Web Docs (vendor-neutral reference)",
    "docs.python.org": "official Python documentation",
    "peps.python.org": "Python Enhancement Proposal",
    "nodejs.org": "official Node.js documentation",
    "docs.oracle.com": "official Java documentation",
    "learn.microsoft.com": "official Microsoft documentation",
    "cloud.google.com": "official Google Cloud documentation",
    "developers.google.com": "official Google developer docs",
    "docs.aws.amazon.com": "official AWS documentation",
    "postgresql.org": "official PostgreSQL documentation",
    "dev.mysql.com": "official MySQL documentation",
    "sqlite.org": "official SQLite documentation",
    "git-scm.com": "official Git documentation",
    "react.dev": "official React documentation",
    "kubernetes.io": "official Kubernetes documentation",
    "docs.docker.com": "official Docker documentation",
    "openstax.org": "peer-reviewed open textbook",
    "ncbi.nlm.nih.gov": "NIH / PubMed",
    "nist.gov": "NIST",
    "iso.org": "ISO standards",
    "ecma-international.org": "ECMA standards",
    "tc39.es": "ECMAScript specification",
    "httpwg.org": "HTTP working group",
}

TIER_B = {
    "wikipedia.org": "encyclopedia (secondary, check citations)",
    "britannica.com": "encyclopedia",
    "khanacademy.org": "established education platform",
    "freecodecamp.org": "established education platform",
    "geeksforgeeks.org": "tutorial site (uneven quality)",
    "w3schools.com": "tutorial site (simplified)",
    "realpython.com": "edited tutorial site",
    "digitalocean.com": "edited tutorial site",
    "cloudflare.com": "vendor learning centre",
    "ibm.com": "vendor learning centre",
    "redhat.com": "vendor learning centre",
    "auth0.com": "vendor documentation",
    "stackoverflow.com": "community Q&A (voted, unedited)",
    "tutorialspoint.com": "tutorial site (uneven quality)",
    "javatpoint.com": "tutorial site (uneven quality)",
    "programiz.com": "tutorial site",
    "baeldung.com": "edited tutorial site",
    "smashingmagazine.com": "edited publication",
    "arxiv.org": "preprint (not peer reviewed)",
    "acm.org": "ACM publication",
    "ieee.org": "IEEE publication",
    "restfulapi.net": "reference site",
    "httpstatuses.io": "reference site",
}

BLOCKED = {
    "pinterest.com", "quora.com", "facebook.com", "instagram.com", "tiktok.com", "x.com",
    "twitter.com", "youtube.com", "youtu.be", "linkedin.com", "scribd.com", "coursehero.com",
    "chegg.com", "brainly.com", "slideshare.net",
}


def domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _match(host: str, table: dict) -> str | None:
    for d, why in table.items():
        if host == d or host.endswith("." + d):
            return why
    return None


def is_blocked(url: str) -> bool:
    host = domain(url)
    return any(host == d or host.endswith("." + d) for d in BLOCKED)


def tier(url: str, kind: str = "web") -> tuple[str, str]:
    if kind == "book":
        return "A", "published book (metadata and description only)"
    host = domain(url)
    if why := _match(host, TIER_A):
        return "A", why
    if host.endswith(".edu") or ".ac." in host or host.endswith(".gov") or ".gov." in host:
        return "A", "university or government domain"
    if why := _match(host, TIER_B):
        return "B", why
    if host.startswith("docs.") or host.startswith("developer.") or host.startswith("developers."):
        return "B", "vendor documentation subdomain"
    if host in {"medium.com", "dev.to", "hashnode.com"} or host.endswith(".medium.com") or "blogspot" in host:
        return "C", "self-published blog platform"
    return "C", "unclassified site"


TRUSTED_CHANNELS = {
    "freecodecamp.org": "A", "cs50": "A", "khan academy": "A", "mit opencourseware": "A",
    "crashcourse": "A", "computerphile": "A", "3blue1brown": "A", "ibm technology": "A",
    "google for developers": "A", "microsoft developer": "A", "aws": "A", "hussein nasser": "B",
    "fireship": "B", "web dev simplified": "B", "traversy media": "B", "programming with mosh": "B",
    "neso academy": "B", "bytebytego": "B", "nptel": "A", "gate smashers": "B", "telusko": "B",
    "kunal kushwaha": "B", "apna college": "B", "corey schafer": "B", "tech with tim": "B",
    "the net ninja": "B", "academind": "B", "codevolution": "B", "mdn": "A", "cloudflare": "A",
}


def channel_tier(channel: str, views: int | None) -> tuple[str, str]:
    c = (channel or "").lower()
    for name, t in TRUSTED_CHANNELS.items():
        if name in c:
            return t, f"known educational channel ({channel})"
    if views and views > 500_000:
        return "B", f"unlisted channel with high reach ({views:,} views)"
    return "C", "unknown channel"
