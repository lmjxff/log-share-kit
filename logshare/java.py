"""Extract observed Java cause chains; never infer links between log events."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


_CLASS = r"(?:[\w$]+[./])*[\w$]*(?:Exception|Error|Throwable)"
_HEADER = re.compile(
    r"^\s*(?P<relation>Caused by:|Suppressed:)\s*(?P<type>" + _CLASS + r")(?::\s*(?P<message>.*))?$"
)
_TOP = re.compile(r"(?<![\w.$/])(?P<type>" + _CLASS + r")(?::\s*(?P<message>.*))?$")
_FRAME = re.compile(r"^\s*at\s+(?P<frame>[^\s]+\([^\r\n]*\))\s*$")
_MORE = re.compile(r"^\s*\.\.\.\s+\d+\s+more\s*$")
SUMMARY_NODE_LIMIT = 200


@dataclass
class ExceptionNode:
    type: str
    message: str
    line: int
    frames: list[str] = field(default_factory=list)
    cause: ExceptionNode | None = None
    suppressed: list[ExceptionNode] = field(default_factory=list)

    @property
    def deepest_cause(self) -> ExceptionNode:
        node = self
        while node.cause is not None:
            node = node.cause
        return node


@dataclass
class TraceSummary:
    events: list[ExceptionNode]
    truncated: bool = False


def scan_exceptions(text: str) -> TraceSummary:
    events: list[ExceptionNode] = []
    active: list[tuple[int, ExceptionNode]] = []
    node_count = 0
    lines = text.splitlines()
    for index, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" \t"))
        match = _HEADER.search(line)
        if match:
            if node_count >= SUMMARY_NODE_LIMIT:
                return TraceSummary(events, truncated=True)
            node_count += 1
            relation = match["relation"]
            node = ExceptionNode(match["type"], match["message"] or "", index + 1)
            if relation == "Suppressed:":
                while active and active[-1][0] >= indent:
                    active.pop()
                if active:
                    active[-1][1].suppressed.append(node)
                else:
                    events.append(node)
                active.append((indent, node))
            else:
                # Suppressed branches are indented; a main cause at column 0
                # must not become the cause of a suppressed exception.
                while len(active) > 1 and active[-1][0] > indent:
                    active.pop()
                if active:
                    active[-1][1].cause = node
                else:
                    events.append(node)
                if active and active[-1][0] == indent:
                    active[-1] = (indent, node)
                else:
                    active.append((indent, node))
            continue
        frame = _FRAME.match(line)
        if frame:
            if active:
                active[-1][1].frames.append(frame["frame"])
            continue
        if _MORE.match(line):
            continue
        match = _TOP.search(line)
        # A standalone exception header is accepted only when its beginning is
        # recognizable or a following stack frame confirms it is a trace.
        if match:
            prefix = line[:match.start()].strip()
            next_frame = index + 1 < len(lines) and bool(_FRAME.match(lines[index + 1]))
            recognizable = (not prefix and "." in match["type"]) or prefix.startswith('Exception in thread "')
            if recognizable or next_frame:
                if node_count >= SUMMARY_NODE_LIMIT:
                    return TraceSummary(events, truncated=True)
                node_count += 1
                node = ExceptionNode(match["type"], match["message"] or "", index + 1)
                events.append(node)
                active = [(0, node)]
                continue
        # A non-trace line is an event boundary, including blank lines. This
        # intentionally avoids joining unrelated or interleaved log messages.
        active = []
    return TraceSummary(events)


def extract_exceptions(text: str) -> list[ExceptionNode]:
    return scan_exceptions(text).events
