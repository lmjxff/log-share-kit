"""Command-line boundary: strict decoding, bounded input, safe output writes."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from . import __version__
from .report import analyze, render_json, render_markdown


MAX_INPUT_BYTES = 20 * 1024 * 1024


def _read(path: str, encoding: str) -> str:
    if path == "-":
        stream = getattr(sys.stdin, "buffer", None)
        if stream is None:
            text = sys.stdin.read(MAX_INPUT_BYTES + 1)
            if len(text.encode(encoding)) > MAX_INPUT_BYTES:
                raise ValueError("input exceeds the 20 MiB limit; extract a smaller incident window")
            return text
        data = stream.read(MAX_INPUT_BYTES + 1)
    else:
        with Path(path).open("rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds the 20 MiB limit; extract a smaller incident window")
    return data.decode(encoding)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an offline, redacted debugging report from a local log.",
        epilog="No network access. Review the report before sharing: pattern matching is not exhaustive.",
    )
    parser.add_argument("input", help="log file, or - to read standard input")
    parser.add_argument("-o", "--output", help="output file; defaults to standard output")
    parser.add_argument("--format", choices=("markdown", "json", "text"), default="markdown")
    parser.add_argument("--encoding", default="utf-8-sig", help="input encoding (default: utf-8-sig; try gb18030 for older logs)")
    parser.add_argument("--redact-key", action="append", default=[], metavar="KEY", help="also redact this key's value; repeatable")
    parser.add_argument("--redact-file", metavar="FILE", help="UTF-8 file of extra literal values, one per line; never stored in reports")
    parser.add_argument("--force", action="store_true", help="replace an existing output file (never the input or redaction-values file)")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        if args.output:
            target = Path(args.output).resolve()
            for source in (args.input if args.input != "-" else None, args.redact_file):
                if source:
                    source_path = Path(source).resolve()
                    if target == source_path or (target.exists() and os.path.samefile(target, source_path)):
                        raise ValueError("output must not overwrite the input or the redaction-values file")
        literals = tuple(_read(args.redact_file, "utf-8-sig").splitlines()) if args.redact_file else ()
        report = analyze(_read(args.input, args.encoding), extra_keys=tuple(args.redact_key), literals=literals)
        render = {"markdown": render_markdown, "json": render_json, "text": lambda item: item.sanitized_log}
        output = render[args.format](report)
        if args.output:
            with Path(args.output).open("w" if args.force else "x", encoding="utf-8", newline="\n") as stream:
                stream.write(output)
        else:
            # Use the same UTF-8 encoding for files and Windows console output.
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="strict")
            sys.stdout.write(output)
    except FileExistsError:
        print("logshare: output already exists; choose a new file or use --force", file=sys.stderr)
        return 2
    except UnicodeError:
        # Codec error messages can contain raw bytes from the original log.
        print("logshare: cannot decode input; choose the correct --encoding", file=sys.stderr)
        return 2
    except (OSError, ValueError, LookupError):
        # Paths and exception details can contain private data; do not echo them.
        print("logshare: cannot process files; check paths, input size, encoding, and output location", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    return 0
