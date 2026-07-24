"""Strict YAML-subset frontmatter parser for gate inputs.

Deliberately minimal: scalars, flow lists ``[a, b]``, block lists, and
one-level nested maps. Anything fancier (anchors, multiline strings, deep
nesting) is a validation ERROR — gate inputs must be boring. Zero deps.
"""
from __future__ import annotations

from pathlib import Path


class FrontmatterError(ValueError):
    pass


def _parse_scalar(raw: str):
    s = raw.strip()
    if not s:
        return ""
    if s[0] in "\"'" and len(s) >= 2 and s[-1] == s[0]:
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s in ("null", "~"):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    for banned in ("&", "*", "|", ">"):
        if s.startswith(banned):
            raise FrontmatterError(
                f"unsupported YAML feature {banned!r} in value {raw!r} — "
                "gate inputs allow plain scalars, [flow lists], block lists, "
                "and one-level nested maps only"
            )
    return s


def _parse_flow_list(raw: str) -> list:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(part) for part in inner.split(",")]


def parse(text: str) -> dict:
    """Parse a strict-subset YAML mapping (frontmatter body, no --- fences)."""
    result: dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            raise FrontmatterError(f"unexpected indentation at top level: {line!r}")
        if ":" not in line:
            raise FrontmatterError(f"expected 'key: value', got {line!r}")
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest.startswith("[") and rest.endswith("]"):
            result[key] = _parse_flow_list(rest)
        elif rest:
            result[key] = _parse_scalar(rest)
        else:
            # block list or one-level nested map
            items: list = []
            nested: dict = {}
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    i += 1
                    continue
                if not nxt.startswith((" ", "\t")):
                    break
                stripped = nxt.strip()
                if stripped.startswith("- "):
                    items.append(_parse_scalar(stripped[2:]))
                elif stripped == "-":
                    raise FrontmatterError("empty block-list item")
                elif ":" in stripped:
                    nk, _, nv = stripped.partition(":")
                    if not nv.strip():
                        raise FrontmatterError(
                            f"nesting deeper than one level under {key!r}: {stripped!r}"
                        )
                    nested[nk.strip()] = _parse_scalar(nv)
                else:
                    raise FrontmatterError(f"cannot parse line under {key!r}: {stripped!r}")
                i += 1
            if items and nested:
                raise FrontmatterError(f"mixed list and map under {key!r}")
            result[key] = items if items else (nested if nested else None)
    return result


def read_frontmatter(path: str | Path) -> tuple[dict, str]:
    """Return (frontmatter dict, body) from a markdown file with --- fences."""
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise FrontmatterError(f"{path}: no frontmatter fence on line 1")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise FrontmatterError(f"{path}: unterminated frontmatter fence")
    return parse(parts[1]), parts[2]
