"""run the lesson's code examples and compare against the output the lesson claims.

this is a guard, not a sandbox: snippets run in a temp dir with a timeout, an isolated
interpreter and a deny-list for obviously destructive calls. it is meant for an author's
own machine reviewing their own lesson.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from .. import config

BLOCK = re.compile(
    r"```(?P<lang>python|py|python3|javascript|js|node)[^\n]*\n(?P<code>.*?)```"
    r"(?:\s*```(?:output|text|console|plaintext)[^\n]*\n(?P<out>.*?)```)?",
    re.S | re.I)

DENY = re.compile(
    r"\b(subprocess|os\.system|os\.popen|shutil\.rmtree|os\.remove|os\.unlink|os\.rmdir|rmSync|unlinkSync|"
    r"child_process|__import__|ctypes|socket\.bind|winreg|eval\s*\(|exec\s*\()", re.I)


def extract(sections: list[dict]) -> list[dict]:
    out = []
    for s in sections:
        for m in BLOCK.finditer(s["body_md"]):
            lang = "python" if m.group("lang").lower() in ("python", "py", "python3") else "javascript"
            out.append({"section_id": s["id"], "language": lang, "code": m.group("code").rstrip(),
                        "expected": (m.group("out") or "").rstrip() or None})
    return out


def _line_matches(expected: str, actual: str) -> bool:
    expected, actual = expected.strip(), actual.strip()
    if "..." not in expected:
        return expected == actual
    pattern = ".*?".join(re.escape(p.strip()) for p in expected.split("..."))
    return re.fullmatch(pattern, actual, re.S) is not None or re.search(pattern, actual) is not None


def compare(expected: str, actual: str) -> tuple[bool, list[str]]:
    """every expected line must match an actual line, in order ("..." is a wildcard)."""
    exp = [ln for ln in expected.splitlines() if ln.strip()]
    act = [ln for ln in actual.splitlines() if ln.strip()]
    missing, j = [], 0
    for e in exp:
        if e.strip() == "...":
            continue
        k = j
        while k < len(act) and not _line_matches(e, act[k]):
            k += 1
        if k == len(act):
            missing.append(e)
        else:
            j = k + 1
    return not missing, missing


def run_one(block: dict) -> dict:
    res = dict(block)
    if DENY.search(block["code"]):
        return res | {"status": "skipped", "note": "contains a call on the deny-list; not executed", "actual": None,
                      "stderr": None, "ms": 0}
    if block["language"] == "javascript" and not shutil.which("node"):
        return res | {"status": "skipped", "note": "node is not installed", "actual": None, "stderr": None, "ms": 0}
    with tempfile.TemporaryDirectory(prefix="redpen-") as tmp:
        ext = ".py" if block["language"] == "python" else ".js"
        path = os.path.join(tmp, "snippet" + ext)
        with open(path, "w", encoding="utf-8") as f:
            f.write(block["code"])
        cmd = [sys.executable, "-I", path] if block["language"] == "python" else ["node", path]
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE")}
        env["PYTHONIOENCODING"] = "utf-8"
        t0 = time.perf_counter()
        try:
            p = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=config.EXEC_TIMEOUT, env=env,
                               encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return res | {"status": "timeout", "note": f"did not finish in {config.EXEC_TIMEOUT}s", "actual": None,
                          "stderr": None, "ms": config.EXEC_TIMEOUT * 1000}
        ms = int((time.perf_counter() - t0) * 1000)
    actual, stderr = p.stdout[-4000:], p.stderr[-2000:]
    if p.returncode != 0:
        return res | {"status": "error", "note": (stderr.strip().splitlines() or ["non-zero exit"])[-1][:300],
                      "actual": actual, "stderr": stderr, "ms": ms}
    if not block["expected"]:
        return res | {"status": "ran", "note": "ran cleanly; the lesson shows no expected output to compare",
                      "actual": actual, "stderr": stderr, "ms": ms}
    ok, missing = compare(block["expected"], actual)
    return res | {"status": "pass" if ok else "mismatch",
                  "note": "output matches the lesson" if ok else f"{len(missing)} expected line(s) not produced",
                  "missing": missing, "actual": actual, "stderr": stderr, "ms": ms}


def run_all(sections: list[dict]) -> list[dict]:
    return [run_one(b) for b in extract(sections)]
