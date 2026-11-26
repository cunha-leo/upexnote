import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from transcription import audio_multimodel

class AudioMultimodelTests(unittest.TestCase):
    def test_word_timestamps_are_from_source_audio(self):
        words=[{"start":0.5,"end":0.9,"text":"Olá"},{"start":1.0,"end":1.3,"text":"mundo."}]
        items=audio_multimodel._as_segments("Olá mundo.",10,12,words)
        self.assertEqual(items,[(10.5,11.3,"Olá mundo.")])

    def test_chunk_timestamps_are_marked_as_approximate(self):
        self.assertEqual(audio_multimodel._as_segments("fala",10,12),[(10,12,"fala")])

    def test_blank_transcription_does_not_persist(self):
        with patch.object(audio_multimodel,"iter_wav_chunks",return_value=[(0,10,b"wav")]), \
             patch.dict(audio_multimodel.CALLS,{"gpt_transcribe":lambda wav,key:("",None,[],None)}), \
             patch.object(audio_multimodel,"transcript_path") as path:
            with self.assertRaisesRegex(RuntimeError,"sem transcrição"):
                audio_multimodel.run("audio.wav","dummy",log=lambda _:None,engine_id="gpt_transcribe")
            path.assert_not_called()

    def test_provider_error_redacts_response_text(self):
        class Response:
            status_code=401
            text="CONFIDENTIAL-SECRET"
        with self.assertRaises(RuntimeError) as capture:
            audio_multimodel._provider_error("provider",Response())
        self.assertNotIn("CONFIDENTIAL-SECRET",str(capture.exception))
        self.assertIn("HTTP 401",str(capture.exception))

    def test_cost_unknown_is_null_not_free(self):
        with tempfile.TemporaryDirectory() as d:
            def filename(engine,src,kind): return Path(d)/f"{engine}-{kind}.txt"
            with patch.object(audio_multimodel,"iter_wav_chunks",return_value=[(0,10,b"wav")]), \
                 patch.dict(audio_multimodel.CALLS,{"gpt_transcribe":lambda wav,key:("Olá, este é um teste.",None,[],{"total_tokens":10})}), \
                 patch.object(audio_multimodel,"transcript_path",side_effect=filename):
                result=audio_multimodel.run("audio.wav","dummy",log=lambda _:None,engine_id="gpt_transcribe")
                self.assertTrue(result["ok"])
                self.assertIsNone(result["cost"])
                self.assertEqual(result["timing_precision"],"chunk")
                self.assertTrue(result["raw_path"].is_file())
                self.assertTrue(result["clean_path"].is_file())
