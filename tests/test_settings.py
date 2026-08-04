import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "app"))
import settings


class SystemPromptSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Path(self.temp_dir.name) / "rag.db"
        self.db_patch = patch.object(settings, "DB_PATH", self.db)
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_default_is_used_without_saved_or_environment_value(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(settings.get_system_prompt(), settings.DEFAULT_SYSTEM_PROMPT)

    def test_environment_overrides_default(self):
        with patch.dict(os.environ, {"SYSTEM_PROMPT": " environment prompt "}, clear=True):
            self.assertEqual(settings.get_system_prompt(), " environment prompt ")

    def test_saved_prompt_has_highest_priority_and_persists(self):
        with patch.dict(os.environ, {"SYSTEM_PROMPT": "environment prompt"}, clear=True):
            settings.save_system_prompt("saved prompt")
            self.assertEqual(settings.get_system_prompt(), "saved prompt")
            self.assertEqual(settings.get_saved_system_prompt(), "saved prompt")

    def test_reset_removes_saved_override_and_reveals_environment(self):
        with patch.dict(os.environ, {"SYSTEM_PROMPT": "environment prompt"}, clear=True):
            settings.save_system_prompt("saved prompt")
            self.assertEqual(settings.reset_system_prompt(), "environment prompt")
            self.assertIsNone(settings.get_saved_system_prompt())

    def test_blank_prompt_is_rejected(self):
        with self.assertRaises(ValueError):
            settings.save_system_prompt("  \n  ")


if __name__ == "__main__":
    unittest.main()
