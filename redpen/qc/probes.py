"""live http probes: claims about http behaviour get tested against real public test servers.

only allow-listed hosts are ever contacted, and the planner is told that httpbin's /status/{code}
endpoint proves nothing (it returns whatever code you ask for).
"""

import json
import time
from urllib.parse import urlparse

import httpx

from .. import config, llm, prompts
from ..schemas import ProbePlan

ALLOWED_HOSTS = {"httpbin.org", "postman-echo.com", "jsonplaceholder.typicode.com"}


def allowed(url: str) -> bool:
    u = urlparse(url)
    return u.scheme == "https" and (u.hostname or "") in ALLOWED_HOSTS and "/status/" not in u.path


def plan(claims: list[dict]) -> list[dict]:
    testable = [(i, c) for i, c in enumerate(claims) if c.get("testable")]
    if not testable:
        return []
    listing = "\n".join(f"{i}: {c['claim']}" for i, c in testable)
    result = llm.generate(prompts.render("qc_probe_plan", claims=listing), ProbePlan, temperature=0.0, fast=True,
                          what="probe planning")
    out = []
    for p in result.probes:
        if not allowed(p.url) or not (0 <= p.claim_index < len(claims)):
            continue
        out.append(p.model_dump())
    return out[:10]


def execute(probe: dict) -> dict:
    body = None
    if probe.get("body_json"):
        try:
            body = json.loads(probe["body_json"])
        except json.JSONDecodeError:
            body = None
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=config.HTTP_TIMEOUT, follow_redirects=False,
                          headers={"User-Agent": config.USER_AGENT}) as c:
            r = c.request(probe["method"], probe["url"], json=body)
        ms = int((time.perf_counter() - t0) * 1000)
        ok = probe["expect_status_min"] <= r.status_code <= probe["expect_status_max"]
        return probe | {"status_code": r.status_code, "reason": r.reason_phrase, "passed": ok, "ms": ms,
                        "response_excerpt": r.text[:300], "error": None}
    except httpx.HTTPError as e:
        return probe | {"status_code": None, "reason": None, "passed": None, "ms": None,
                        "response_excerpt": None, "error": f"{type(e).__name__}: {e}"[:200]}
