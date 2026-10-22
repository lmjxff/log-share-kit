# Log Share Kit report

Lines: 14 | Java exception events: 2
Redactions: EMAIL: 1, IP: 1, PHONE: 1, SECRET: 2

> Generated locally. Pattern-based redaction can miss sensitive data; review before sharing.
> The deepest observed cause is evidence from this trace, not a proven business root cause.

## Exception summary

### Event 1 (line 4)

```text
java.lang.IllegalStateException: Unable to import record
  caused by -> java.lang.NumberFormatException: For input string: " 123"
```

Deepest observed cause:

```text
java.lang.NumberFormatException: For input string: " 123"
```

First observed frame of this cause:

```text
java.base/java.lang.Long.parseLong(Long.java:711)
```

Suppressed branch (line 6):

```text
java.io.IOException: Failed to close resource
```

### Event 2 (line 13)

```text
java.lang.NullPointerException: Missing result
```

Deepest observed cause:

```text
java.lang.NullPointerException: Missing result
```

First observed frame of this cause:

```text
example.importer.ExportService.write(ExportService.java:56)
```

## Debugging context to fill in

- What were you doing when this happened?
- What did you expect, and what happened instead?
- What changed recently? Include runtime and dependency versions.

## Sanitized log

```text
2026-01-10 09:30:00 INFO demo request email=<LSK_EMAIL_1> mobile=<LSK_PHONE_1> peer=<LSK_IP_1>
2026-01-10 09:30:01 DEBUG demo password="<LSK_SECRET_1>" access_token=<LSK_SECRET_2>
2026-01-10 09:30:02 ERROR demo request failed
java.lang.IllegalStateException: Unable to import record
	at example.importer.ImportService.run(ImportService.java:42)
	Suppressed: java.io.IOException: Failed to close resource
		at example.importer.Resource.close(Resource.java:18)
Caused by: java.lang.NumberFormatException: For input string: " 123"
	at java.base/java.lang.Long.parseLong(Long.java:711)
	at example.importer.RecordParser.parse(RecordParser.java:27)
	... 1 more
2026-01-10 09:30:03 ERROR demo a separate later failure
java.lang.NullPointerException: Missing result
	at example.importer.ExportService.write(ExportService.java:56)
```
