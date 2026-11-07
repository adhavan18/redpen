import re

SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[])")


def lesson_text(doc: dict, with_quiz: bool = True, with_answers: bool = True) -> str:
    out = [f"# {doc['title']}", f"Objective: {doc['objective']}", ""]
    for i, s in enumerate(doc["sections"]):
        out.append(f"[section {i}] ## {s['title']} ({s['kind']}, {s['minutes']} min)\n{s['body_md']}\n")
    if with_quiz and doc.get("quiz"):
        out.append(f"[quiz] ## Knowledge check ({doc.get('quiz_minutes', 0)} min)")
        for qi, q in enumerate(doc["quiz"]):
            out.append(f"Q{qi}. {q['question']}")
            for oi, o in enumerate(q["options"]):
                mark = " (correct)" if with_answers and oi == q["answer_index"] else ""
                out.append(f"   {oi}) {o}{mark}")
            if with_answers and q.get("explanation"):
                out.append(f"   explanation: {q['explanation']}")
    return "\n".join(out)


def prose(md: str) -> str:
    """markdown body without code blocks, tables-as-text kept, for sentence-level analysis."""
    md = re.sub(r"```.*?```", " ", md, flags=re.S)
    md = re.sub(r"`([^`]*)`", r"\1", md)
    md = re.sub(r"^\s*[#>]+\s*", "", md, flags=re.M)
    md = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", md, flags=re.M)
    md = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", md)
    return md


def sentences(md: str) -> list[str]:
    out = []
    for block in re.split(r"\n\s*\n|\n", prose(md)):
        block = block.strip()
        if not block or block.startswith("|") and block.count("|") > 2 and set(block) <= set("|-: "):
            continue
        out.extend(s.strip() for s in SENT.split(block) if len(s.strip()) > 2)
    return out


def norm(s: str) -> str:
    """letters and digits only, lowercased. a quote counts as verbatim if its words appear in the
    source in the same order; table pipes, markdown and curly quotes in between do not matter."""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def contains(haystack: str, needle: str) -> bool:
    n = norm(needle)
    return len(n) >= 12 and n in norm(haystack)


def section_ref(doc: dict, index: int) -> str | None:
    if index == -2:
        return "quiz"
    if 0 <= index < len(doc["sections"]):
        return doc["sections"][index]["id"]
    return None


class Issues:
    def __init__(self, prefix: str, layer: str):
        self.prefix, self.layer, self.items = prefix, layer, []

    def add(self, severity: str, category: str, section_id: str | None, description: str, evidence: str = "",
            suggestion: str = "", origin: str = "check", **extra) -> dict:
        item = {"id": f"{self.prefix}{len(self.items) + 1}", "layer": self.layer, "severity": severity,
                "category": category, "section_id": section_id, "description": description, "evidence": evidence,
                "suggestion": suggestion, "origin": origin, "status": "open", "note": None} | extra
        self.items.append(item)
        return item

    def sorted(self) -> list[dict]:
        rank = {"high": 0, "medium": 1, "low": 2}
        return sorted(self.items, key=lambda i: (rank[i["severity"]], int(i["id"][len(self.prefix):])))
