"""R03.1: API errors must not create a fake/empty transcript or leak secrets."""
import unittest
from unittest.mock import patch, MagicMock

from transcription import whisper_openai, gpt4o_openai, deepgram


class Unauthorized(Exception):
    status_code = 401

class EngineAuthTests(unittest.TestCase):
    def test_openai_engines_fail_fast_on_401(self):
        for module in (whisper_openai, gpt4o_openai):
            with self.subTest(engine=module.__name__):
                fake_client = MagicMock()
                fake_client.audio.transcriptions.create.side_effect = Unauthorized(
                    "Incorrect API key sk-proj-SECRET_NEVER_SHOW"
                )
                chunks = iter([(0.0, 2.0, b"sample wav")])
                with patch.object(module, "OpenAI", return_value=fake_client), patch.object(
                    module, "iter_wav_chunks_skip_silence",
                    return_value=(chunks, lambda x: x, 2.0)
                ), patch.object(module, "transcript_path") as output_path:
                    with self.assertRaises(RuntimeError) as ctx:
                        module.run("mock.wav", "invalid-key", log=lambda x: None)
                message = str(ctx.exception)
                self.assertIn("HTTP 401", message)
                self.assertNotIn("SECRET_NEVER_SHOW", message)
                output_path.assert_not_called()

    def test_deepgram_401_fails_without_output(self):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 401
        resp.text = '{"err_code":"INVALID_AUTH","err_msg":"Invalid credentials."}'
        with patch.object(deepgram, "iter_wav_chunks", return_value=iter([(0.0, 2.0, b"wav")])), patch.object(
            deepgram.requests, "post", return_value=resp
        ), patch.object(deepgram, "transcript_path") as output_path:
            with self.assertRaises(RuntimeError) as ctx:
                deepgram.run("mock.wav", "rejected", log=lambda x: None)
        self.assertIn("401", str(ctx.exception))
        output_path.assert_not_called()
        sent_params = deepgram.BASE_PARAMS
        self.assertIn(("model", "nova-3"), sent_params)
        self.assertIn(("language", "multi"), sent_params)



if __name__ == "__main__":
    unittest.main()
