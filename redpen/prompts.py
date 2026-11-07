"""prompts live in /prompts as markdown files so they are versioned with git and reviewable in a pr.
placeholders are {{name}}; a missing value is an error, not a silent blank."""

import re

from . import config

_cache: dict[str, str] = {}


def load(name: str) -> str:
    if name not in _cache:
        _cache[name] = (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    return _cache[name]


def render(_prompt: str, **values) -> str:
    text = load(_prompt)

    def sub(m):
        key = m.group(1)
        if key not in values:
            raise KeyError(f"prompt {_prompt!r} needs {key!r}")
        return str(values[key])

    return re.sub(r"\{\{(\w+)\}\}", sub, text)
