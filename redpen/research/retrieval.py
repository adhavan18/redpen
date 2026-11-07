"""chunking + retrieval. gemini embeddings when available, bm25 when not (no key quota, offline tests)."""

import math
import re
from collections import Counter

import numpy as np

from .. import llm

WORD = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
STOP = set("""a an the and or of to in on for with by is are was were be been it this that as at from
which can will not but if then than so such these those into its their there about also may any each
other more most some only over when where how what who why all you your we our they them he she his her""".split())


def tokens(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOP]


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    """paragraph-aware chunks of roughly `size` characters."""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n(?=[#*-] )", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        while len(p) > size * 1.5:  # very long paragraph: hard split on sentence boundary
            cut = p.rfind(". ", 0, size)
            cut = cut + 1 if cut > size // 2 else size
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(p[:cut].strip())
            p = p[max(0, cut - overlap):].strip()
        if len(cur) + len(p) + 1 > size and cur:
            chunks.append(cur)
            cur = cur[-overlap:].split(" ", 1)[-1] + "\n" + p if overlap else p
        else:
            cur = f"{cur}\n{p}" if cur else p
    if cur.strip():
        chunks.append(cur)
    return [c.strip() for c in chunks if len(c.strip()) > 80]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.4, b: float = 0.75):
        self.docs = [tokens(d) for d in docs]
        self.k1, self.b = k1, b
        self.avg = sum(map(len, self.docs)) / max(1, len(self.docs))
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def scores(self, query: str) -> np.ndarray:
        q = tokens(query)
        out = np.zeros(len(self.docs), dtype=np.float32)
        for i, (tf, d) in enumerate(zip(self.tf, self.docs)):
            s = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    s += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            out[i] = s
        if out.max() > 0:
            out = out / out.max()
        return out


class Index:
    """search over research chunks. vectors are optional; bm25 always works."""

    def __init__(self, chunks: list[dict], vectors: np.ndarray | None):
        self.chunks = chunks
        self.vectors = vectors if vectors is not None and len(vectors) == len(chunks) else None
        self.bm25 = BM25([c["text"] for c in chunks]) if chunks else None
        self._qcache: dict[str, np.ndarray] = {}

    def query_vectors(self, queries: list[str]) -> list[np.ndarray | None]:
        if self.vectors is None:
            return [None] * len(queries)
        missing = [q for q in queries if q not in self._qcache]
        if missing:
            try:
                vecs = llm.embed(missing, task="RETRIEVAL_QUERY")
                self._qcache.update(zip(missing, vecs))
            except Exception:  # noqa: BLE001 - degrade to bm25
                return [None] * len(queries)
        return [self._qcache.get(q) for q in queries]

    def scores(self, query: str, qvec: np.ndarray | None = None) -> np.ndarray:
        if not self.chunks:
            return np.zeros(0)
        lex = self.bm25.scores(query)
        if self.vectors is None or qvec is None:
            return lex
        dense = self.vectors @ qvec
        return 0.75 * dense + 0.25 * lex * max(float(dense.max()), 0.0)

    def search(self, query: str, k: int = 6, per_source: int = 2, source_ids: set[str] | None = None,
               qvec: np.ndarray | None = None) -> list[tuple[dict, float]]:
        if qvec is None and self.vectors is not None:
            qvec = self.query_vectors([query])[0]
        s = self.scores(query, qvec)
        order = np.argsort(-s)
        out, used = [], Counter()
        for i in order:
            c = self.chunks[i]
            if source_ids is not None and c["source_id"] not in source_ids:
                continue
            if used[c["source_id"]] >= per_source:
                continue
            used[c["source_id"]] += 1
            out.append((c, float(s[i])))
            if len(out) >= k:
                break
        return out


def ngram_overlap(a: str, b_index: set[tuple[str, ...]], n: int = 10) -> list[str]:
    """spans of `a` that appear word-for-word (n words or more) in the indexed sources."""
    words = re.findall(r"\w+", a.lower())
    hits, i = [], 0
    while i + n <= len(words):
        if tuple(words[i:i + n]) in b_index:
            j = i + n
            while j < len(words) and tuple(words[j - n + 1:j + 1]) in b_index:
                j += 1
            hits.append(" ".join(words[i:j]))
            i = j
        else:
            i += 1
    return hits


def ngram_index(texts: list[str], n: int = 10) -> set[tuple[str, ...]]:
    idx = set()
    for t in texts:
        w = re.findall(r"\w+", t.lower())
        idx.update(tuple(w[i:i + n]) for i in range(len(w) - n + 1))
    return idx
