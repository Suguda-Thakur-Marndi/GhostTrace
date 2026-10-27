"""Unit tests for the persona system: loading, validation, custom personas, and security checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ghostd import PersonaManager


class TestPersonaManager(unittest.TestCase):
    """Tests for PersonaManager loading, security, and fallback behaviors."""

    def setUp(self):
        self.mgr = PersonaManager()

    def test_list_builtin_personas(self):
        personas = self.mgr.list_personas()
        expected = ["abuela", "cobol_ghost", "poltergeist", "unix_elder", "victorian_medium"]
        for exp in expected:
            self.assertIn(exp, personas, f"Missing expected persona '{exp}'")

    def test_load_poltergeist(self):
        p = self.mgr.load_persona("poltergeist")
        self.assertEqual(p.name, "poltergeist")
        self.assertIn("poltergeist", p.system_prompt.lower())
        self.assertTrue(len(p.canned_normal) > 0)
        self.assertTrue(len(p.canned_failure) > 0)
        self.assertTrue(len(p.canned_dramatic) > 0)

    def test_load_cobol_ghost_all_caps(self):
        p = self.mgr.load_persona("cobol_ghost")
        self.assertEqual(p.name, "cobol_ghost")
        self.assertIn("COBOL_GHOST", p.system_prompt)
        # All canned whispers must be uppercase
        for whisper in p.canned_normal:
            self.assertEqual(whisper, whisper.upper(), f"Canned whisper was not uppercase: {whisper}")
        for whisper in p.canned_failure:
            self.assertEqual(whisper, whisper.upper(), f"Canned whisper was not uppercase: {whisper}")

    def test_load_victorian_medium(self):
        p = self.mgr.load_persona("victorian_medium")
        self.assertEqual(p.name, "victorian_medium")
        self.assertIn("Victorian Medium", p.system_prompt)
        self.assertTrue(any("spirit" in w.lower() or "séance" in w.lower() or "planchette" in w.lower() for w in p.canned_normal))

    def test_load_abuela_warmth(self):
        p = self.mgr.load_persona("abuela")
        self.assertEqual(p.name, "abuela")
        self.assertIn("Abuela", p.system_prompt)
        self.assertTrue(any("corazón" in w.lower() or "marigold" in w.lower() or "rest" in w.lower() for w in p.canned_normal))

    def test_load_unix_elder_terse(self):
        p = self.mgr.load_persona("unix_elder")
        self.assertEqual(p.name, "unix_elder")
        self.assertIn("Unix Elder", p.system_prompt)
        self.assertTrue(any("unix" in w.lower() or "pdp-11" in w.lower() or "silence" in w.lower() for w in p.canned_normal))

    def test_reject_directory_traversal(self):
        # Attempt path traversal
        p = self.mgr.load_persona("../../etc/passwd")
        # Should fall back safely to poltergeist without error
        self.assertIn(p.name, ["poltergeist", "default"])

    def test_reject_special_characters_in_name(self):
        p = self.mgr.load_persona("ghost; rm -rf /")
        self.assertIn(p.name, ["poltergeist", "default"])

    def test_load_custom_persona_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            custom_file = tmp_path / "glitch_phantom"
            custom_content = (
                "# Custom persona\n"
                "[system_prompt]\n"
                "You are Glitch Phantom, a stuttering spirit in the bus wires.\n"
                "[canned_normal]\n"
                "Glitch... 0xDEADBEEF in the bus.\n"
                "[canned_failure]\n"
                "Stack corrupted in sector zero.\n"
            )
            custom_file.write_text(custom_content, encoding="utf-8")

            mgr = PersonaManager(ghosts_dir=tmp_path)
            personas = mgr.list_personas()
            self.assertIn("glitch_phantom", personas)

            p = mgr.load_persona("glitch_phantom")
            self.assertEqual(p.name, "glitch_phantom")
            self.assertIn("Glitch Phantom", p.system_prompt)
            self.assertEqual(p.canned_normal, ["Glitch... 0xDEADBEEF in the bus."])
            self.assertEqual(p.canned_failure, ["Stack corrupted in sector zero."])


if __name__ == "__main__":
    unittest.main()
