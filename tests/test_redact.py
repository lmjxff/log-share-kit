import unittest

from logshare.redact import Redactor
from logshare.report import analyze, render_json, render_markdown


class RedactionTests(unittest.TestCase):
    def test_values_and_repeated_identifiers(self):
        result = Redactor().redact('email=a@example.test again=a@example.test mobile=13800000000 ip=203.0.113.8')
        self.assertEqual(result.counts, {"EMAIL": 2, "PHONE": 1, "IP": 1})
        self.assertEqual(result.text.count("<LSK_EMAIL_1>"), 2)
        self.assertNotIn("13800000000", result.text)

    def test_quoted_and_escaped_credentials(self):
        values = ['{"password":"example secret with spaces"}',
                  '{"password":"example\\\"quoted"}', "pwd='example two words'",
                  "client_secret=example-value&safe=keep", "accessToken: example-value"]
        for source in values:
            with self.subTest(source=source):
                result = Redactor().redact(source)
                self.assertNotIn("example", result.text)
                self.assertIn("<LSK_SECRET_1>", result.text)
        self.assertIn("safe=keep", Redactor().redact(values[3]).text)

    def test_authorization_header_and_json_value(self):
        for source in ['Authorization: Bearer example-credential',
                       '{"Authorization":"Bearer example-credential"}',
                       'Basic ZXhhbXBsZTpvbmx5']:
            with self.subTest(source=source):
                result = Redactor().redact(source)
                self.assertNotIn("example-credential", result.text)
                self.assertNotIn("ZXhhbXBsZTpvbmx5", result.text)

    def test_truncated_quoted_secret_masks_rest_of_line(self):
        for source in ['password="example secret incomplete', "password='example secret incomplete"]:
            self.assertNotIn("example", Redactor().redact(source).text)

    def test_sensitive_quoted_value_can_contain_auth_words(self):
        for embedded in ("Bearer example-secret", "Authorization: Bearer example-secret", "Cookie: sid=example-secret"):
            source = '{"password":"prefix ' + embedded + ' suffix"}'
            result = Redactor().redact(source)
            for word in ("prefix", "example-secret", "suffix"):
                self.assertNotIn(word, result.text)

    def test_cookie_headers_and_json(self):
        for source in ['Cookie: sid=example-a; session=example-b',
                       'Set-Cookie: sid=example-a; Secure; HttpOnly',
                       '{"cookie":"sid=example-a; session=example-b"}']:
            with self.subTest(source=source):
                self.assertNotIn("example-", Redactor().redact(source).text)

    def test_url_userinfo_and_query_password(self):
        result = Redactor().redact("jdbc:mysql://example-user:example-pass@db.example.test/app?password=example-query&useSSL=true")
        self.assertNotIn("example-user", result.text)
        self.assertNotIn("example-pass", result.text)
        self.assertNotIn("example-query", result.text)
        self.assertIn("db.example.test/app", result.text)
        self.assertIn("useSSL=true", result.text)

    def test_jwt_and_known_token_shapes(self):
        source = "eyJhbGciOiJub25lIn0.eyJzdWIiOiJleGFtcGxlIn0.ZXhhbXBsZQ " + "ghp_" + "x" * 30
        result = Redactor().redact(source)
        self.assertEqual(set(result.counts), {"JWT", "TOKEN"})
        self.assertNotIn("eyJ", result.text)

    def test_private_key_keeps_line_numbers(self):
        source = "-----BEGIN RSA PRIVATE KEY-----\nexample-only\n-----END RSA PRIVATE KEY-----\njava.lang.RuntimeException: problem"
        result = Redactor().redact(source)
        self.assertNotIn("example-only", result.text)
        self.assertEqual(result.text.count("\n"), source.count("\n"))
        self.assertEqual(analyze(source).exceptions[0].line, 4)

    def test_valid_ips_and_non_ip_numbers(self):
        result = Redactor().redact("203.0.113.1 [2001:db8::1] ::1 999.999.999.999 09:30:02 Import.java:42")
        self.assertEqual(result.counts, {"IP": 3})
        self.assertIn("999.999.999.999", result.text)
        self.assertIn("09:30:02 Import.java:42", result.text)

    def test_custom_keys_literals_and_marker_collision(self):
        source = 'tenantId=example-tenant private-project LSK password=example-secret'
        result = Redactor(("tenantId",), ("private-project", "LSK")).redact(source)
        self.assertNotIn("example-", result.text)
        self.assertNotIn("private-project", result.text)
        self.assertEqual(result.counts, {"CUSTOM": 2, "SECRET": 2})
        self.assertNotIn("\x00", result.text)

    def test_custom_keys_are_literal_not_regex(self):
        result = Redactor(("api.key",)).redact("api.key=example-secret apiXkey=keep")
        self.assertNotIn("example-secret", result.text)
        self.assertIn("apiXkey=keep", result.text)

    def test_all_exported_fields_are_sanitized(self):
        source = 'java.lang.RuntimeException: password="example-secret" email=a@example.test\n\tat example.App.main(App.java:12)'
        report = analyze(source)
        for rendered in (render_json(report), render_markdown(report), report.sanitized_log):
            self.assertNotIn("example-secret", rendered)
            self.assertNotIn("a@example.test", rendered)

    def test_no_cross_report_identifier_mapping(self):
        first = analyze("a@example.test")
        second = analyze("b@example.test")
        self.assertEqual(first.sanitized_log, second.sanitized_log)


if __name__ == "__main__":
    unittest.main()
