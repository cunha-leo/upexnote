import io
import json
import unittest

from transcription.protocol import emit


class CliProtocolEncodingTests(unittest.TestCase):
    def test_emit_is_ascii_safe_and_round_trips_unicode(self):
        event = {
            "type": "document_item",
            "title": "Onboarding e Orientação",
            "content": "início → meio → fim",
        }
        stream = io.StringIO()

        emit(stream, event)

        wire = stream.getvalue()
        self.assertTrue(wire.endswith("\n"))
        self.assertTrue(wire.isascii())
        self.assertIn(r"\u2192", wire)
        self.assertEqual(json.loads(wire), event)


if __name__ == "__main__":
    unittest.main()
