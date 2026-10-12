"""Tests executable without aiogram, alongside original storage tests."""
import os
import sys
import types
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import storage, content


class CredentialsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original = os.environ.get("BOT_DATA_DIR")
        os.environ["BOT_DATA_DIR"] = self.temp_dir.name

    def tearDown(self):
        if self.original is None:
            os.environ.pop("BOT_DATA_DIR", None)
        else:
            os.environ["BOT_DATA_DIR"] = self.original
        self.temp_dir.cleanup()

    def test_all_eight_credentials_can_be_saved_and_survive_reconnect(self):
        expected = (
            "HAPPYCAR_ID", "HAPPYCAR_PASSWORD", "DUOCAR_ID", "DUOCAR_PASSWORD",
            "JENO_ID", "JENO_PASSWORD", "GLOVIS_LOGIN", "GLOVIS_PASSWORD",
        )
        for idx, key in enumerate(expected):
            storage.set_auction_credential(key, f"new-{idx}")
        for idx, key in enumerate(expected):
            self.assertEqual(storage.get_auction_credential(key), f"new-{idx}")
        self.assertEqual(len(expected), len(storage.AUCTION_CREDENTIALS))

    def test_fallback_to_environment_before_admin_override(self):
        with patch.dict(os.environ, {"DUOCAR_ID": "env-ID"}):
            self.assertEqual(storage.get_auction_credential("DUOCAR_ID"), "env-ID")
            storage.set_auction_credential("DUOCAR_ID", "admin-ID")
            self.assertEqual(storage.get_auction_credential("DUOCAR_ID"), "admin-ID")

    def test_admin_pending_is_scoped_to_user(self):
        storage.set_admin_pending(5138418509, "credential:GLOVIS_PASSWORD")
        self.assertEqual(storage.get_admin_pending(5138418509), "credential:GLOVIS_PASSWORD")
        self.assertIsNone(storage.get_admin_pending(12345))


class Dummy:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class ButtonPlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake = types.ModuleType("aiogram")
        fake_types = types.ModuleType("aiogram.types")
        for name in ("BotCommand", "InlineKeyboardButton", "InlineKeyboardMarkup",
                     "KeyboardButton", "ReplyKeyboardMarkup"):
            setattr(fake_types, name, Dummy)
        with patch.dict(sys.modules, {"aiogram": fake, "aiogram.types": fake_types}):
            import importlib
            cls.kb = importlib.import_module("app.keyboards")

    def test_only_start_in_default_command_menu(self):
        self.assertEqual([c.command for c in self.kb.default_commands()], ["start"])
        self.assertEqual([c.command for c in self.kb.admin_commands()], ["start", "admin"])

    def test_access_top_and_bottom_are_separate(self):
        for page in (1, 2, 3):
            top = self.kb.access_step_kb(page)
            self.assertEqual(len(top.inline_keyboard), 1)
            self.assertEqual(len(top.inline_keyboard[0]), 2)
        self.assertEqual(
            [[b.text for b in row] for row in self.kb.access_nav_kb().keyboard],
            [[self.kb.MENU, self.kb.KOREA_SHORT, self.kb.SHORT_MANAGER]],
        )

    def test_korea_navigation_and_final_buttons(self):
        for page in (1, 2, 3):
            self.assertEqual(len(self.kb.korea_step_kb(page).inline_keyboard[0]), 2)
        self.assertEqual(
            [[b.text for b in row] for row in self.kb.korea_nav_kb().keyboard],
            [[self.kb.MENU, self.kb.SHORT_MANAGER, self.kb.KOREA_SHORT]],
        )
        self.assertEqual(
            [[b.text for b in row] for row in self.kb.korea_last_nav_kb().keyboard],
            [[self.kb.PICK, self.kb.CALC], [self.kb.MENU, self.kb.AUCTIONS, self.kb.SHORT_MANAGER]],
        )

    def test_screen_texts_not_split_at_hardcoded_points(self):
        for key in ("ACCESS_1", "ACCESS_2", "ACCESS_3", "KOREA_1", "KOREA_2", "KOREA_3", "KOREA_4"):
            self.assertLessEqual(len(getattr(content, key)), 1024, key)


if __name__ == "__main__":
    unittest.main()
