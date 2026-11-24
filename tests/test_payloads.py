"""Tests for QR payload formatting and escaping."""
import unittest

from KODIGO.payloads import build


class VCardPayloadTests(unittest.TestCase):
    def test_website_newlines_are_escaped_not_emitted_as_properties(self):
        payload = build("contact", {"first": "Alex", "website": "https://example.com\r\nX-ATTACK:injected"})
        self.assertIn(r"URL:https://example.com\nX-ATTACK:injected", payload)
        self.assertNotIn("\r", payload)

    def test_contact_fields_escape_newlines_and_delimiters(self):
        payload = build("contact", {"first": "Alex\nX-EVIL:yes", "email": "a,b@example.com"})
        self.assertIn(r"FN:Alex\nX-EVIL:yes", payload)
        self.assertIn(r"EMAIL;TYPE=INTERNET:a\,b@example.com", payload)


if __name__ == "__main__":
    unittest.main()
