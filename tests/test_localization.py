import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class LocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

    def test_english_is_the_default_interface_language(self):
        self.assertIn('<html lang="en">', self.index)
        self.assertIn("Start chatting with your documents", self.index)
        self.assertIn('value="en">English</option>', self.index)

    def test_settings_include_english_and_turkish_options(self):
        self.assertIn('id="language-select"', self.index)
        self.assertIn('value="tr">Türkçe</option>', self.index)

    def test_language_choice_is_persisted(self):
        self.assertIn('localStorage.getItem("corgue-language")', self.javascript)
        self.assertIn('localStorage.setItem("corgue-language", state.language)', self.javascript)

    def test_chat_requests_include_selected_language(self):
        self.assertIn("language: state.language", self.javascript)


if __name__ == "__main__":
    unittest.main()
