import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('generate', Path(__file__).parents[1] / 'generate.py')
generate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate)


class JobTests(unittest.TestCase):
    def test_segments_cover_complete_audio(self):
        for seconds, expected in [(1, 1), (3.72, 1), (3.73, 2), (15, 5), (30, 10), (60, 19), (600, 188)]:
            with self.subTest(seconds=seconds):
                n = generate.segments_for(seconds)
                self.assertEqual(n, expected)
                self.assertGreaterEqual(3.72 + (n-1)*3.2, seconds)

    def test_invalid_duration(self):
        for seconds in [0, -1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError): generate.segments_for(seconds)

    def test_job_paths_and_shell_characters_are_data(self):
        with tempfile.TemporaryDirectory(prefix='longcat test ') as d:
            root = Path(d)
            image, audio = root / 'foto.jpg', root / 'voz.mp3'
            image.touch(); audio.touch()
            prompt = 'A woman says "$HOME; $(whoami)".'
            with patch.object(generate, 'audio_duration', return_value=60):
                job = generate.make_job(image, audio, prompt, runtime=root)
            data = json.loads((job['work'] / 'request.json').read_text())
            self.assertEqual(data['prompt'], prompt)
            self.assertEqual(data['cond_audio']['person1'], str(audio))
            self.assertEqual(job['segments'], 19)
            self.assertIn('--standalone', job['command'])
            self.assertIn('--use_int8', job['command'])

    def test_short_test_does_not_generate_full_audio(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'input'; p.touch()
            with patch.object(generate, 'audio_duration', return_value=180):
                job = generate.make_job(p, p, 'A speaker.', runtime=d, test=True)
            self.assertEqual(job['segments'], 1)
            self.assertEqual(job['duration'], 3.72)

    def test_missing_file_fails_before_creating_job(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): generate.make_job(Path(d)/'absent', Path(d)/'absent', 'Scene', runtime=d)
            self.assertFalse((Path(d)/'jobs').exists())

    def test_file_without_audio_is_rejected(self):
        with patch.object(generate.subprocess, 'check_output', return_value='{"streams":[],"format":{"duration":"10"}}'):
            with self.assertRaises(ValueError): generate.audio_duration('video.mp4')


if __name__ == '__main__': unittest.main()
