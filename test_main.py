import os
import unittest
from unittest.mock import patch

import main


class GeminiConfigTests(unittest.TestCase):
    def test_prefers_cloud_run_env_var(self):
        with patch.dict(os.environ, {"_GEMINI_API_KEY": "secret-from-cloud-run"}, clear=True):
            self.assertEqual(main.get_gemini_api_key(), "secret-from-cloud-run")

    def test_falls_back_to_other_names(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fallback-key"}, clear=True):
            self.assertEqual(main.get_gemini_api_key(), "fallback-key")


if __name__ == "__main__":
    unittest.main()
