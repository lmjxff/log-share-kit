# Log Share Kit

**Turn a local log into a redacted debugging report, ready for a GitHub Issue or a teammate.**

[简体中文使用说明](README.zh-CN.md) · [Example report](examples/report.md) · [Contributing](CONTRIBUTING.md)

Log Share Kit is a small, offline command-line tool. It masks common secrets and identifiers, extracts observed Java exception chains, and exports Markdown, JSON, or plain text. It uses only the Python standard library at runtime. No account, API key, server, or AI service is required.

## What it helps with

- Prepare logs before asking for help in an issue, chat, or support ticket.
- Read a Java wrapper exception together with its deepest observed `Caused by` entry.
- Keep `Suppressed` exceptions and separate log events distinct.
- Replace repeated sensitive values consistently inside one report, so relationships remain visible.

This is an early `0.1.0` release. Redaction uses patterns and **can miss sensitive information**. Review every report before sharing. The deepest observed exception is a trace summary; it does not prove the business root cause.

## Requirements

- Python **3.10 or newer** on Windows, macOS, or Linux.
- Git to clone the source, or download and extract the repository ZIP from GitHub.

## Quick start: no installation

Clone the source and run the synthetic example:

```bash
git clone https://github.com/lmjxff/log-share-kit.git
cd log-share-kit
python -m logshare examples/demo.log -o report.md
```

Open `report.md` in a Markdown viewer. The bundled input is entirely synthetic. Its report contains a `NumberFormatException` cause, an independent suppressed cleanup error, and a separate later `NullPointerException` event. See the [generated example](examples/report.md).

If you downloaded the ZIP, skip `git clone` and `cd`; run the final command from the extracted directory containing `pyproject.toml`.

On Windows, use `py -3` in place of `python` if that is your Python launcher. On macOS/Linux, your command may be `python3`.

## Install the command (optional)

From the downloaded source directory:

```bash
python -m pip install .
logshare examples/demo.log -o installed-report.md
```

This installs the local project and the `logshare` command. Build tooling may be downloaded during installation. Log processing itself does not use the network. This project is not yet published to PyPI; `pip install log-share-kit` is not an installation instruction for this release.

For an isolated environment:

```bash
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` on macOS/Linux, then run `python -m pip install .`.

## Usage

```text
logshare INPUT [-o OUTPUT] [--format {markdown,json,text}]
         [--encoding ENCODING] [--redact-key KEY]
         [--redact-file FILE] [--force]
```

All examples also work with `python -m logshare` when run from the source directory.

| Argument | Behavior |
| --- | --- |
| `INPUT` | Path to a log file; `-` reads standard input. |
| `-o`, `--output` | Write a UTF-8 file; omit to print to standard output. Parent directories must already exist. |
| `--format markdown` | Default: exception summary, context checklist, and the full sanitized log. |
| `--format json` | Machine-readable report, schema version 1. |
| `--format text` | Only the sanitized log, without a report wrapper. |
| `--encoding` | Input encoding; defaults to `utf-8-sig`, which accepts UTF-8 with or without a BOM. |
| `--redact-key KEY` | Mask another key/value field. Repeat for multiple keys; names are matched literally, case-insensitively. |
| `--redact-file FILE` | UTF-8 file containing extra literal values to hide, one per line. Blank lines are ignored. |
| `--force` | Replace an existing output file. Input and extra-values files remain protected against overwriting, including hardlink aliases. |
| `--version`, `--help` | Print version or command help. |

### Export JSON or sanitized text

```bash
logshare application.log --format json -o report.json
logshare application.log --format text -o sanitized.txt
```

JSON has `schema_version`, `tool_version`, `line_count`, `redactions`, `exceptions`, and `sanitized_log` fields. Every exception includes its type, sanitized message, source line, observed frames, cause, and suppressed branches. Top-level events also include `deepest_observed_cause`. Reports contain no original-to-placeholder mapping and no input filename.

### Read a pipe

macOS/Linux:

```bash
cat application.log | logshare - -o report.md
```

PowerShell 7 with UTF-8 pipe output:

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
Get-Content -Raw -Encoding UTF8 .\application.log | logshare - -o report.md
```

Passing the file directly avoids shell-dependent pipe encodings.

### Read a legacy Chinese log

```bash
logshare application.log --encoding gb18030 -o report.md
```

Decoding is strict. Invalid input stops with an error rather than silently replacing characters. Output files always use UTF-8.

### Add project-specific redaction

```bash
logshare application.log --redact-key tenantId --redact-key managerUuid -o report.md
logshare application.log --redact-file local.secrets -o report.md
```

For example, `local.secrets` can contain synthetic values like:

```text
example-private-project
example-internal-host.test
```

The file is a **literal value list**, not a regex file. Matching is case-sensitive; values keep their leading and trailing spaces. Keep real values in a local, untracked file. `*.secrets`, `.env*`, raw `*.log` files, and `reports/` are ignored by the repository's `.gitignore` (the synthetic demo log is explicitly included). Do not place actual credentials on the command line.

## Redaction behavior

```text
Before:
email=developer@example.test password="example-only-value" peer=203.0.113.42

After:
email=<LSK_EMAIL_1> password="<LSK_SECRET_1>" peer=<LSK_IP_1>
```

Built-in patterns cover:

- Common credential keys, including password, token, API key, client secret, and SMS code/ticket forms.
- Bearer/Basic authorization values, cookie headers, and quoted cookie fields.
- JWT-shaped strings, selected common provider-token shapes, and complete PEM private-key blocks.
- URL user information (`scheme://user:password@host`).
- Common email forms, mainland China mobile numbers, and valid IPv4/IPv6 literals.

Placeholders are sequential within each category. The same value in the same category receives the same placeholder inside a report; mappings reset between reports. Counts are matched occurrences, not a count of people or unique secrets. Multiline replacements preserve newline counts so reported trace line numbers refer to the original input.

## Reading the exception summary

An exception event includes:

1. The observed wrapper-to-cause chain.
2. Its deepest observed cause and the first observed stack frame for that cause.
3. Suppressed branches listed separately.
4. A source line number, followed by the full sanitized log in the report.

The tool does not execute code, contact a database, or look up source files. It cannot link a swallowed earlier exception to a later failure. A non-trace line ends the current event; incomplete or interleaved traces can therefore appear as separate events. Java exception class names ending in `Exception`, `Error`, or `Throwable` are supported; unusual class names and JSON-wrapped/escaped stack traces are not decoded. Non-Java logs can still be sanitized without an exception summary.

## Limits and data handling

- The summary includes at most 200 exception headers (including causes and suppressed branches). Additional headers set JSON `summary_truncated` to `true` and add a Markdown notice. The full sanitized log remains available.
- Each input file/stream and extra-values file is limited to **20 MiB**. Extract a smaller incident window from larger files.
- Text is processed in memory. The tool writes only the requested output file, or standard output. No telemetry or network client is included.
- Patterns do not cover every secret, phone format, address, customer identifier, hostname, encoded value, or malformed/truncated private key. Add keys or literal values and review the output.
- Request paths, timestamps, class names, SQL, and business data may remain. A redacted report is not a guarantee of anonymity or permission to publish.
- Avoid using a terminal redirection such as `> application.log` with the input file: the shell truncates it before this program starts. Prefer `-o` for overwrite protection.
- Exit codes: `0` success, `2` command/file/encoding/size error, `130` keyboard interruption. Errors avoid echoing input bytes and private paths.

## Development

```bash
python -m unittest discover -s tests -v
python -m logshare examples/demo.log -o examples/report.md --force
```

Tests exercise redaction leaks, quoted values, authorization, custom rules, original line numbers, cause/suppressed separation, UTF-8 and legacy encodings, stdin, size limits, Markdown fences, and overwrite protection. Use synthetic fixtures when adding cases. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE).
