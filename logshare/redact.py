"""Redact merged sensitive spans. No networking or persistent mappings."""

from __future__ import annotations

import ipaddress
import re
from collections import Counter
from dataclasses import dataclass


DEFAULT_KEYS = (
    "password", "passwd", "pwd", "secret", "client_secret", "clientSecret",
    "token", "access_token", "accessToken", "refresh_token", "refreshToken",
    "api_key", "apiKey", "apikey", "app_secret", "appSecret", "private_key",
    "smsCode", "sms_code", "smsTicket", "verificationCode", "authorization",
    "cookie", "set-cookie",
)
_PEM = re.compile(
    r"-----BEGIN (?P<kind>(?:[A-Z0-9]+ )*PRIVATE KEY)-----.*?"
    r"-----END (?P=kind)-----", re.DOTALL,
)
_AUTH = re.compile(r"(?i)\b(?:Bearer|Basic)\s+[^\s\"',;<>]+")
_COOKIE = re.compile(
    r"(?im)(?P<prefix>\b(?:set-cookie|cookie)\s*:\s*)[^\r\n]+"
)
_USERINFO = re.compile(r"(?P<prefix>\b[a-zA-Z][a-zA-Z0-9+.-]*://)[^\s/@]+@")
_JWT = re.compile(r"(?<![\w.-])eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(?![\w.-])")
_PROVIDER_TOKEN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{20,})\b"
)
_EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_PHONE = re.compile(r"(?<![\w])(?:\+?86[- ]?)?1[3-9]\d{9}(?![\w])")
_IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
# Validate candidates with ipaddress, so timestamps and Java locations survive.
_IPV6 = re.compile(r"(?<![\w:])(?:[0-9A-Fa-f]{0,4}:){2,}[0-9A-Fa-f:.]*(?:%[\w.-]+)?(?![\w:])")
_PLACEHOLDER = re.compile(r"<LSK_[A-Z]+_\d+>")


@dataclass
class RedactionResult:
    text: str
    counts: dict[str, int]


class Redactor:
    """One instance per report; repeated values keep the same placeholder."""

    def __init__(self, extra_keys: tuple[str, ...] = (), literals: tuple[str, ...] = ()):
        keys = sorted(set(DEFAULT_KEYS + extra_keys), key=len, reverse=True)
        key_pattern = "|".join(re.escape(key) for key in keys)
        self.key_value = re.compile(
            r"(?i)(?<![\w-])(?P<prefix>[\"']?(?:" + key_pattern
            + r")[\"']?\s*[:=]\s*)"
            + r"(?P<value>\"(?:\\.|[^\"\\\r\n])*\"|'(?:\\.|[^'\\\r\n])*'|\"[^\r\n]*|'[^\r\n]*|[^\s,;&}\]\)\"'<>]+)"
        )
        values = sorted({value for value in literals if value}, key=len, reverse=True)
        self.literals = re.compile("|".join(map(re.escape, values))) if values else None
        self.mapping: dict[tuple[str, str], str] = {}
        self.sequence: Counter[str] = Counter()
        self.counts: Counter[str] = Counter()

    def _mask(self, kind: str, value: str) -> str:
        if _PLACEHOLDER.fullmatch(value):
            return value
        self.counts[kind] += 1
        key = (kind, value)
        if key not in self.mapping:
            self.sequence[kind] += 1
            self.mapping[key] = f"<LSK_{kind}_{self.sequence[kind]}>"
        return self.mapping[key]

    def redact(self, text: str) -> RedactionResult:
        # Detect on the original input, then merge overlaps before replacing.
        # A token inside a quoted password must not split that password into
        # separate fragments that a later rule could accidentally leave behind.
        spans: list[tuple[int, int, str]] = []
        userinfo_matches = list(_USERINFO.finditer(text))
        userinfo_separators = {match.end() - 1 for match in userinfo_matches}
        for match in self.key_value.finditer(text):
            value = match["value"]
            start, end = match.span("value")
            if value[0] in "\"'":
                start += 1
                if len(value) > 1 and value[-1] == value[0]:
                    end -= 1
            if end > start:
                spans.append((start, end, "SECRET"))
        for pattern, kind in ((_PEM, "PRIVATEKEY"), (_AUTH, "AUTH"),
                              (_JWT, "JWT"), (_PROVIDER_TOKEN, "TOKEN"),
                              (_EMAIL, "EMAIL"), (_PHONE, "PHONE")):
            for match in pattern.finditer(text):
                # URL user information ends at @. Treating its password and
                # host together as an email would unnecessarily hide the host.
                if kind == "EMAIL" and match.start() + match[0].index("@") in userinfo_separators:
                    continue
                spans.append((match.start(), match.end(), kind))
        for match in _COOKIE.finditer(text):
            spans.append((match.end("prefix"), match.end(), "COOKIE"))
        for match in userinfo_matches:
            spans.append((match.end("prefix"), match.end() - 1, "USERINFO"))
        if self.literals:
            spans.extend((match.start(), match.end(), "CUSTOM") for match in self.literals.finditer(text))
        for pattern in (_IPV4, _IPV6):
            for match in pattern.finditer(text):
                try:
                    ipaddress.ip_address(match[0])
                except ValueError:
                    continue
                spans.append((match.start(), match.end(), "IP"))

        merged: list[tuple[int, int, str]] = []
        for start, end, kind in sorted(spans, key=lambda span: (span[0], -span[1])):
            if merged and start < merged[-1][1]:
                old_start, old_end, old_kind = merged[-1]
                merged[-1] = (old_start, max(end, old_end), old_kind)
            else:
                merged.append((start, end, kind))
        pieces: list[str] = []
        previous = 0
        for start, end, kind in merged:
            raw = text[start:end]
            pieces.extend((text[previous:start], self._mask(kind, raw), "\n" * raw.count("\n")))
            previous = end
        pieces.append(text[previous:])
        return RedactionResult("".join(pieces), dict(sorted(self.counts.items())))
