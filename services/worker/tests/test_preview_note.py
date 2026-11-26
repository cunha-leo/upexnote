import json
import unittest
from transcription.db import _render_blocks_as_text, _notebook_body_to_text

class PreviewNoteTests(unittest.TestCase):
    def test_native_blocks_and_export(self):
        source = [("T\u00edtulo", '["primeiro", "a \\"quote\\"", "a\u00e7\u00e3o"]'), ("Text", "a < b & c"), ("Objects", '{"key":["one","two"]}')]
        body = _render_blocks_as_text(source)
        blocks = json.loads(body)
        self.assertEqual(blocks[0]["tag"], "H2")
        self.assertEqual(blocks[1]["tag"], "UL")
        self.assertIn("<li>primeiro</li>", blocks[1]["html"])
        self.assertEqual(len({b["id"] for b in blocks}), len(blocks))
        text = _notebook_body_to_text(body)
        self.assertIn("## T\u00edtulo", text)
        self.assertIn('- a "quote"', text)
        self.assertIn("a\u00e7\u00e3o", text)
        self.assertIn("a < b & c", text)
        self.assertIn("- two", text)
    def test_plain_and_empty_content(self):
        blocks = json.loads(_render_blocks_as_text([(None, "[plain text"), (None, []), (None, None)]))
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["html"], "[plain text")
