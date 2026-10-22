from pathlib import Path
import unittest

from logshare.java import extract_exceptions
from logshare.report import analyze, render_json, render_markdown


class JavaTraceTests(unittest.TestCase):
    def test_demo_keeps_main_cause_suppressed_and_later_event_separate(self):
        text = (Path(__file__).parents[1] / "examples" / "demo.log").read_text(encoding="utf-8")
        events = extract_exceptions(text)
        self.assertEqual(len(events), 2)
        first = events[0]
        self.assertEqual(first.type, "java.lang.IllegalStateException")
        self.assertEqual(first.deepest_cause.type, "java.lang.NumberFormatException")
        self.assertEqual(first.suppressed[0].type, "java.io.IOException")
        self.assertEqual(events[1].type, "java.lang.NullPointerException")
        self.assertEqual(first.deepest_cause.line, 8)

    def test_multiple_wrappers(self):
        events = extract_exceptions("java.lang.RuntimeException: outer\n\tat demo.App.go(App.java:1)\nCaused by: java.lang.IllegalStateException: inner\n\tat demo.App.go(App.java:2)\nCaused by: java.io.IOException: root\n\tat demo.App.go(App.java:3)")
        self.assertEqual(events[0].deepest_cause.type, "java.io.IOException")
        self.assertEqual(events[0].deepest_cause.frames, ["demo.App.go(App.java:3)"])

    def test_suppressed_cause_and_siblings(self):
        events = extract_exceptions("java.lang.RuntimeException: outer\n\tat demo.App.go(App.java:1)\n\tSuppressed: java.io.IOException: cleanup\n\t\tat demo.App.close(App.java:2)\n\tCaused by: java.lang.IllegalArgumentException: cleanup cause\n\t\tat demo.App.close(App.java:3)\n\tSuppressed: java.lang.AssertionError: second cleanup\n\t\tat demo.App.close(App.java:4)\nCaused by: java.lang.NumberFormatException: main cause\n\tat demo.App.parse(App.java:5)")
        self.assertEqual(events[0].deepest_cause.type, "java.lang.NumberFormatException")
        self.assertEqual(len(events[0].suppressed), 2)
        self.assertEqual(events[0].suppressed[0].deepest_cause.type, "java.lang.IllegalArgumentException")

    def test_logged_header_and_exception_in_thread(self):
        events = extract_exceptions('2026-01-01 ERROR demo java.lang.RuntimeException: bad\n\tat demo.App.go(App.java:1)\nException in thread "main" java.lang.AssertionError: broken\n\tat demo.App.go(App.java:2)')
        self.assertEqual(len(events), 2)

    def test_unrelated_text_is_a_boundary(self):
        events = extract_exceptions("java.lang.RuntimeException: a\n\tat demo.App.go(App.java:1)\nINFO another request\nCaused by: java.io.IOException: orphan")
        self.assertEqual(len(events), 2)
        self.assertIsNone(events[0].cause)

    def test_mention_of_exception_is_not_a_trace(self):
        self.assertEqual(extract_exceptions("INFO got a java.lang.RuntimeException: text only"), [])

    def test_markdown_fences_cannot_be_broken_by_log(self):
        output = render_markdown(analyze("```\n# injected heading\n```"))
        self.assertIn("````text\n```\n# injected heading\n```\n````", output)

    def test_empty_and_non_java_input(self):
        for text in ("", "a normal log\n", "Traceback (most recent call last):\nValueError: example"):
            report = analyze(text)
            self.assertEqual(report.exceptions, [])
            self.assertIn('"schema_version": 1', render_json(report))
            self.assertIn("No supported Java", render_markdown(report))


    def test_deep_or_large_traces_have_a_bounded_summary(self):
        source = "java.lang.RuntimeException: wrapper\n" + "Caused by: java.io.IOException: nested\n" * 1200
        report = analyze(source)
        self.assertTrue(report.summary_truncated)
        self.assertIn('"summary_truncated": true', render_json(report))
        self.assertIn("first 200 exception headers", render_markdown(report))
        self.assertEqual(report.sanitized_log, source)


if __name__ == "__main__":
    unittest.main()
