"""Tests for the local-only URL ingestion edge and caption conversion."""
import unittest
from unittest.mock import patch

from transcription.url_ingest import IngestError, analyze, validate_url, _vtt_text


class TestUrlIngest(unittest.TestCase):
    def test_video_forms(self):
        expected = "https://www.youtube.com/watch?v=abcdefghijk"
        for url in [
            "https://youtu.be/abcdefghijk?t=10",
            "https://www.youtube.com/watch?v=abcdefghijk&list=PLAYLIST",
            "https://youtube.com/live/abcdefghijk",
            "https://m.youtube.com/shorts/abcdefghijk",
        ]:
            self.assertEqual(validate_url(url), expected)

    def test_reject_unrelated_and_invalid(self):
        for url in [
            "https://evil.example/watch?v=abcdefghijk",
            "file:///etc/passwd",
            "https://www.youtube.com.evil.example/watch?v=abcdefghijk",
            "https://youtube.com/watch?v=short",
            "http://user:password@youtube.com/watch?v=abcdefghijk",
        ]:
            with self.subTest(url=url), self.assertRaises(IngestError):
                validate_url(url)

    def test_analysis_tracks(self):
        import json
        data = {"id":"abcdefghijk","title":"Teste","duration":120,
                "subtitles":{"pt":[{"ext":"vtt"}]},
                "automatic_captions":{"en":[{"ext":"vtt"}]}}
        with patch("transcription.url_ingest._run", return_value=json.dumps(data)):
            result = analyze("https://youtu.be/abcdefghijk")
        self.assertEqual(result["manual_languages"], ["pt"])
        self.assertEqual(result["automatic_languages"], ["en"])
        self.assertTrue(result["has_captions"])

    def test_vtt_does_not_remove_repeated_speech(self):
        content = ("WEBVTT\n\n"
                   "00:00:00.280 --> 00:00:02.000\nUm novo tempo\n\n"
                   "00:00:02.000 --> 00:00:03.000\nUm novo tempo\n\n"
                   "00:00:03.000 --> 00:00:05.000\nUm novo tempo começa hoje\n")
        self.assertEqual(_vtt_text(content),
                         "Um novo tempo\nUm novo tempo\nUm novo tempo começa hoje")

    def test_vtt_retains_original_words_without_timestamps(self):
        content = ("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n"
                   "<c>Olá &amp; bem-vindos</c>\n\n"
                   "00:00:02.000 --> 00:00:03.000\nOutra frase\n")
        self.assertEqual(_vtt_text(content),
                         "Olá & bem-vindos\nOutra frase")


if __name__ == "__main__":
    unittest.main()
