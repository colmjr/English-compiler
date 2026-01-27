"""Tests for english_compiler.settings module."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from english_compiler.settings import (
    Settings,
    _parse_toml,
    _generate_toml,
    load_settings,
    save_settings,
    delete_settings,
    get_config_path,
    VALID_FRONTENDS,
    VALID_TARGETS,
)


class TestSettings(unittest.TestCase):
    """Tests for Settings dataclass."""

    def test_default_values(self):
        """Default settings should have None frontend and False explain_errors."""
        settings = Settings()
        self.assertIsNone(settings.frontend)
        self.assertFalse(settings.explain_errors)
        self.assertIsNone(settings.target)
        self.assertFalse(settings.regen)
        self.assertFalse(settings.freeze)

    def test_custom_values(self):
        """Settings should accept custom values."""
        settings = Settings(frontend="claude", explain_errors=True, target="python", regen=True, freeze=False)
        self.assertEqual(settings.frontend, "claude")
        self.assertTrue(settings.explain_errors)
        self.assertEqual(settings.target, "python")
        self.assertTrue(settings.regen)
        self.assertFalse(settings.freeze)

    def test_to_dict_empty(self):
        """Default settings should produce empty dict (only non-default values)."""
        settings = Settings()
        self.assertEqual(settings.to_dict(), {})

    def test_to_dict_with_values(self):
        """Settings with values should produce correct dict."""
        settings = Settings(frontend="openai", explain_errors=True, target="javascript", regen=True)
        data = settings.to_dict()
        self.assertEqual(data, {"frontend": "openai", "explain_errors": True, "target": "javascript", "regen": True})

    def test_to_dict_partial(self):
        """Settings with only frontend should not include explain_errors."""
        settings = Settings(frontend="claude")
        data = settings.to_dict()
        self.assertEqual(data, {"frontend": "claude"})

    def test_to_dict_with_target(self):
        """Settings with target should include it."""
        settings = Settings(target="cpp")
        data = settings.to_dict()
        self.assertEqual(data, {"target": "cpp"})

    def test_from_dict_empty(self):
        """Empty dict should produce default settings."""
        settings = Settings.from_dict({})
        self.assertIsNone(settings.frontend)
        self.assertFalse(settings.explain_errors)
        self.assertIsNone(settings.target)
        self.assertFalse(settings.regen)
        self.assertFalse(settings.freeze)

    def test_from_dict_with_values(self):
        """Dict with values should produce correct settings."""
        settings = Settings.from_dict({"frontend": "gemini", "explain_errors": True, "target": "wasm", "freeze": True})
        self.assertEqual(settings.frontend, "gemini")
        self.assertTrue(settings.explain_errors)
        self.assertEqual(settings.target, "wasm")
        self.assertFalse(settings.regen)
        self.assertTrue(settings.freeze)

    def test_from_dict_extra_keys(self):
        """Extra keys in dict should be ignored."""
        settings = Settings.from_dict({"frontend": "mock", "unknown": "value"})
        self.assertEqual(settings.frontend, "mock")
        self.assertFalse(settings.explain_errors)


class TestParseToml(unittest.TestCase):
    """Tests for TOML parsing."""

    def test_empty_string(self):
        """Empty string should produce empty dict."""
        self.assertEqual(_parse_toml(""), {})

    def test_comments_only(self):
        """Comments should be ignored."""
        self.assertEqual(_parse_toml("# comment\n# another"), {})

    def test_simple_section(self):
        """Basic section and key-value pairs."""
        text = """
[defaults]
frontend = "claude"
"""
        result = _parse_toml(text)
        self.assertEqual(result, {"defaults": {"frontend": "claude"}})

    def test_boolean_values(self):
        """Boolean values should be parsed."""
        text = """
[defaults]
enabled = true
disabled = false
"""
        result = _parse_toml(text)
        self.assertTrue(result["defaults"]["enabled"])
        self.assertFalse(result["defaults"]["disabled"])

    def test_string_values(self):
        """Quoted string values should be parsed."""
        text = """
[defaults]
double = "hello"
single = 'world'
"""
        result = _parse_toml(text)
        self.assertEqual(result["defaults"]["double"], "hello")
        self.assertEqual(result["defaults"]["single"], "world")

    def test_integer_values(self):
        """Integer values should be parsed."""
        text = """
[section]
count = 42
negative = -10
"""
        result = _parse_toml(text)
        self.assertEqual(result["section"]["count"], 42)
        self.assertEqual(result["section"]["negative"], -10)

    def test_full_config(self):
        """Full config file should parse correctly."""
        text = """
[defaults]
frontend = "claude"
explain_errors = true
"""
        result = _parse_toml(text)
        self.assertEqual(
            result,
            {
                "defaults": {
                    "frontend": "claude",
                    "explain_errors": True,
                }
            },
        )


class TestGenerateToml(unittest.TestCase):
    """Tests for TOML generation."""

    def test_empty_settings(self):
        """Empty settings should produce section header only."""
        settings = Settings()
        text = _generate_toml(settings)
        self.assertEqual(text, "[defaults]\n")

    def test_with_frontend(self):
        """Settings with frontend should produce correct TOML."""
        settings = Settings(frontend="claude")
        text = _generate_toml(settings)
        self.assertEqual(text, '[defaults]\nfrontend = "claude"\n')

    def test_with_explain_errors(self):
        """Settings with explain_errors should produce correct TOML."""
        settings = Settings(explain_errors=True)
        text = _generate_toml(settings)
        self.assertEqual(text, "[defaults]\nexplain_errors = true\n")

    def test_full_settings(self):
        """Full settings should produce correct TOML."""
        settings = Settings(frontend="openai", explain_errors=True)
        text = _generate_toml(settings)
        # Keys are sorted alphabetically
        self.assertEqual(text, '[defaults]\nexplain_errors = true\nfrontend = "openai"\n')

    def test_roundtrip(self):
        """Generated TOML should parse back to same settings."""
        original = Settings(frontend="gemini", explain_errors=True)
        text = _generate_toml(original)
        parsed = _parse_toml(text)
        restored = Settings.from_dict(parsed.get("defaults", {}))
        self.assertEqual(restored.frontend, original.frontend)
        self.assertEqual(restored.explain_errors, original.explain_errors)


class TestLoadSaveSettings(unittest.TestCase):
    """Tests for load/save operations with temp files."""

    def test_load_nonexistent(self):
        """Loading from nonexistent file should return defaults."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with mock.patch(
                "english_compiler.settings.get_config_path",
                return_value=tmp_path / "nonexistent" / "config.toml",
            ):
                settings = load_settings()
                self.assertIsNone(settings.frontend)
                self.assertFalse(settings.explain_errors)

    def test_save_and_load(self):
        """Saved settings should load correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.toml"
            with mock.patch(
                "english_compiler.settings.get_config_path",
                return_value=config_path,
            ):
                # Save
                original = Settings(frontend="qwen", explain_errors=True)
                self.assertTrue(save_settings(original))

                # Load
                loaded = load_settings()
                self.assertEqual(loaded.frontend, "qwen")
                self.assertTrue(loaded.explain_errors)

    def test_save_creates_directory(self):
        """Save should create parent directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "deep" / "nested" / "config.toml"
            with mock.patch(
                "english_compiler.settings.get_config_path",
                return_value=config_path,
            ):
                settings = Settings(frontend="mock")
                self.assertTrue(save_settings(settings))
                self.assertTrue(config_path.exists())

    def test_delete_nonexistent(self):
        """Deleting nonexistent file should succeed."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "nonexistent.toml"
            with mock.patch(
                "english_compiler.settings.get_config_path",
                return_value=config_path,
            ):
                self.assertTrue(delete_settings())

    def test_delete_existing(self):
        """Deleting existing file should remove it."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.toml"
            config_path.write_text("[defaults]\n")

            with mock.patch(
                "english_compiler.settings.get_config_path",
                return_value=config_path,
            ):
                self.assertTrue(delete_settings())
                self.assertFalse(config_path.exists())

    def test_load_invalid_toml(self):
        """Invalid TOML should return default settings."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.toml"
            config_path.write_text("this is not valid {{{{ toml")

            with mock.patch(
                "english_compiler.settings.get_config_path",
                return_value=config_path,
            ):
                settings = load_settings()
                self.assertIsNone(settings.frontend)


class TestGetConfigPath(unittest.TestCase):
    """Tests for config path detection."""

    def test_returns_path(self):
        """Should return a Path object."""
        path = get_config_path()
        self.assertIsInstance(path, Path)

    def test_ends_with_config_toml(self):
        """Path should end with config.toml."""
        path = get_config_path()
        self.assertEqual(path.name, "config.toml")

    def test_contains_english_compiler(self):
        """Path should contain english-compiler directory."""
        path = get_config_path()
        self.assertIn("english-compiler", str(path))


class TestValidFrontends(unittest.TestCase):
    """Tests for VALID_FRONTENDS constant."""

    def test_contains_expected_values(self):
        """Should contain all expected frontend names."""
        expected = {"mock", "claude", "openai", "gemini", "qwen"}
        self.assertEqual(set(VALID_FRONTENDS), expected)


class TestValidTargets(unittest.TestCase):
    """Tests for VALID_TARGETS constant."""

    def test_contains_expected_values(self):
        """Should contain all expected target names."""
        expected = {"coreil", "python", "javascript", "cpp", "wasm"}
        self.assertEqual(set(VALID_TARGETS), expected)


def run_tests():
    """Run all tests and report results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    for test_class in [
        TestSettings,
        TestParseToml,
        TestGenerateToml,
        TestLoadSaveSettings,
        TestGetConfigPath,
        TestValidFrontends,
        TestValidTargets,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(run_tests())
