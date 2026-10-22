"""Only sanitized text enters a report or exception summary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re

from . import __version__
from .java import ExceptionNode, scan_exceptions
from .redact import Redactor


@dataclass
class Report:
    schema_version: int
    tool_version: str
    line_count: int
    redactions: dict[str, int]
    exceptions: list[ExceptionNode]
    summary_truncated: bool
    sanitized_log: str


def analyze(text: str, *, extra_keys: tuple[str, ...] = (), literals: tuple[str, ...] = ()) -> Report:
    result = Redactor(extra_keys, literals).redact(text)
    summary = scan_exceptions(result.text)
    return Report(1, __version__, len(text.splitlines()), result.counts,
                  summary.events, summary.truncated, result.text)


def render_json(report: Report) -> str:
    data = asdict(report)
    for item, node in zip(data["exceptions"], report.exceptions):
        item["deepest_observed_cause"] = asdict(node.deepest_cause)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _fence(text: str, language: str = "text") -> str:
    longest = max((len(m[0]) for m in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{text.rstrip()}\n{fence}"


def _chain(node: ExceptionNode) -> str:
    entries = []
    while node:
        entries.append(f"{node.type}: {node.message}".rstrip(": "))
        node = node.cause
    return "\n  caused by -> ".join(entries)


def _suppressed(node: ExceptionNode) -> list[ExceptionNode]:
    found: list[ExceptionNode] = []
    while node:
        for branch in node.suppressed:
            found.append(branch)
            found.extend(_suppressed(branch))
        node = node.cause
    return found


def render_markdown(report: Report) -> str:
    counts = ", ".join(f"{kind}: {count}" for kind, count in report.redactions.items()) or "none detected"
    parts = [
        "# Log Share Kit report", "",
        f"Lines: {report.line_count} | Java exception events: {len(report.exceptions)}",
        f"Redactions: {counts}", "",
        "> Generated locally. Pattern-based redaction can miss sensitive data; review before sharing.",
        "> The deepest observed cause is evidence from this trace, not a proven business root cause.", "",
        "## Exception summary", "",
    ]
    if report.summary_truncated:
        parts.extend(["> Summary limited to the first 200 exception headers. The full sanitized log is included below.", ""])
    if not report.exceptions:
        parts.extend(["No supported Java exception traces found. The sanitized log is still included.", ""])
    for index, node in enumerate(report.exceptions, 1):
        root = node.deepest_cause
        parts.extend([f"### Event {index} (line {node.line})", "", _fence(_chain(node)), "",
                      "Deepest observed cause:", "", _fence(f"{root.type}: {root.message}".rstrip(": ")), ""])
        if root.frames:
            parts.extend(["First observed frame of this cause:", "", _fence(root.frames[0]), ""])
        for branch in _suppressed(node):
            parts.extend([f"Suppressed branch (line {branch.line}):", "", _fence(_chain(branch)), ""])
    parts.extend(["## Debugging context to fill in", "",
                  "- What were you doing when this happened?", "- What did you expect, and what happened instead?",
                  "- What changed recently? Include runtime and dependency versions.", "",
                  "## Sanitized log", "", _fence(report.sanitized_log), ""])
    return "\n".join(parts)
