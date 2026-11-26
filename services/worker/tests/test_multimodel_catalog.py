import unittest
from unittest.mock import patch
from transcription import registry, credentials

class MultimodelCatalogTests(unittest.TestCase):
    def test_existing_engine_ids_preserved(self):
        for key in ("assemblyai", "deepgram", "whisper_openai", "gpt4o_openai"):
            self.assertIn(key, registry.ENGINES)
    def test_two_new_transcription_models(self):
        self.assertEqual(registry.ENGINES["assemblyai_stt37"]["model"], "assemblyai-stt-3-7")
        self.assertEqual(registry.ENGINES["gpt4o_mini"]["model"], "gpt-4o-mini-transcribe")
    def test_all_models_have_provider_and_key(self):
        for table in (registry.ENGINES, registry.FORMAT_ENGINES):
            for engine in table.values():
                self.assertTrue(engine["provider"])
                self.assertIn(engine["key_name"], credentials.KNOWN_KEYS)
    def test_additional_keys_do_not_require_internal(self):
        for name in ("ELEVENLABS_API_KEY", "GROQ_API_KEY"):
            self.assertIn(name, credentials.KNOWN_KEYS)
    def test_assembly_new_model_uses_distinct_paths(self):
        with patch("transcription.assemblyai.run", return_value={"ok": True}) as runner:
            self.assertEqual(registry.ENGINES["assemblyai_stt37"]["run"]("sample", "dummy"), {"ok": True})
            self.assertEqual(runner.call_args.kwargs["engine_id"], "assemblyai_stt37")
            self.assertEqual(runner.call_args.kwargs["speech_models"], ["assemblyai-stt-3-7"])
    def test_openai_mini_uses_distinct_paths(self):
        with patch("transcription.gpt4o_openai.run", return_value={"ok": True}) as runner:
            self.assertEqual(registry.ENGINES["gpt4o_mini"]["run"]("sample", "dummy"), {"ok": True})
            self.assertEqual(runner.call_args.kwargs["engine_id"], "gpt4o_mini")
            self.assertEqual(runner.call_args.kwargs["model_id"], "gpt-4o-mini-transcribe")

    def test_catalog_has_six_stt_providers_and_thirteen_models(self):
        from collections import Counter
        counts = Counter(engine["provider"] for engine in registry.ENGINES.values())
        self.assertEqual(counts, {"assemblyai": 3, "openai": 4, "deepgram": 2, "groq": 2, "gemini": 1, "grok": 1})
    def test_format_has_thirteen_models(self):
        self.assertEqual(len(registry.FORMAT_ENGINES), 13)
        for engine_id in ("deepseek_pro", "grok_43", "openai_nano", "openai_mini", "claude_haiku55", "claude_sonnet55", "gemini_lite31"):
            self.assertIn(engine_id, registry.FORMAT_ENGINES)
    def test_all_new_audio_wrappers_use_distinct_ids(self):
        for engine_id in ("gpt_transcribe", "gemini_audio", "grok_voice_stt"):
            with patch("transcription.audio_multimodel.run", return_value={"ok": True}) as runner:
                self.assertTrue(registry.ENGINES[engine_id]["run"]("sample", "dummy")["ok"])
                self.assertEqual(runner.call_args.kwargs["engine_id"], engine_id)
    def test_groq_adapters_point_to_groq_api_and_distinct_output(self):
        for eid, model in [("groq_v3_turbo", "whisper-large-v3-turbo"), ("groq_v3", "whisper-large-v3")]:
            with patch("transcription.whisper_openai.run", return_value={"ok": True}) as runner:
                self.assertTrue(registry.ENGINES[eid]["run"]("sample", "dummy")["ok"])
                self.assertEqual(runner.call_args.kwargs["model_id"], model)
                self.assertEqual(runner.call_args.kwargs["engine_id"], eid)
                self.assertEqual(runner.call_args.kwargs["base_url"], "https://api.groq.com/openai/v1")
    def test_nova2_adapter(self):
        with patch("transcription.deepgram.run", return_value={"ok": True}) as runner:
            self.assertTrue(registry.ENGINES["deepgram_nova2"]["run"]("sample", "dummy")["ok"])
            self.assertEqual(runner.call_args.kwargs["model_id"], "nova-2")
    def test_universal2_adapter(self):
        with patch("transcription.assemblyai.run", return_value={"ok": True}) as runner:
            self.assertTrue(registry.ENGINES["assemblyai_u2"]["run"]("sample", "dummy")["ok"])
            self.assertEqual(runner.call_args.kwargs["speech_models"], ["universal-2"])

if __name__ == "__main__":
    unittest.main()
