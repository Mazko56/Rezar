"""Navigation/keyboard tests, run without a Telegram token or aiogram install.

We extract the actual navigation coroutines from app/main.py and invoke them
with fake Telegram messages, so these assertions exercise production logic.
"""
import ast
import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app import storage


SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"
FUNCTION_NAMES = {"set_section_keyboard", "show_access", "show_korea"}


class FakeMessage:
    def __init__(self):
        self.out = []

    async def answer(self, text, reply_markup=None, **kwargs):
        self.out.append({"kind": "keyboard", "text": text, "reply_markup": reply_markup})
        return SimpleNamespace()


def load_nav_functions(sent_messages):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    defs = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
            and node.name in FUNCTION_NAMES]
    assert len(defs) == len(FUNCTION_NAMES)

    async def fake_send_screen(message, text, *, photo=None, reply_markup=None, parse_mode=None):
        sent_messages.out.append({"kind": "screen", "text": text, "photo": photo,
                                  "reply_markup": reply_markup})
        return SimpleNamespace()

    kb = SimpleNamespace(
        ACCESS="🔐 Безкоштовні доступи до аукціонів",
        KOREA="🇰🇷 Чому авто з Кореї?",
        access_nav_kb=lambda: ("bottom", "menu", "korea", "manager"),
        access_step_kb=lambda n: ("inline", "access", n),
        korea_nav_kb=lambda: ("bottom", "pick", "calc", "menu", "access", "manager"),
        korea_last_nav_kb=lambda: ("bottom", "pick", "calc", "menu", "access", "manager"),
        korea_step_kb=lambda n: ("inline", "korea", n),
    )
    content = SimpleNamespace(
        ACCESS_1="СЕКРЕТНІСТЬ\nТекст", ACCESS_2="ВАЖЛИВІСТЬ\nТекст",
        ACCESS_3="ЕКСКЛЮЗИВНІСТЬ\nТекст",
        KOREA_1="Що взагалі дає корейський ринок саме Вам?\nТекст",
        KOREA_2="Вигода Кореї\nТекст",
        KOREA_3="Перевага Кореї\nТекст",
        KOREA_4="Девіз Rezar\nТекст",
    )
    ns = {"Message": FakeMessage, "storage": storage, "kb": kb,
          "content": content, "screen_html": lambda s: s,
          "send_screen": fake_send_screen}
    exec(compile(ast.Module(body=defs, type_ignores=[]), str(SOURCE), "exec"), ns)
    return ns


class BottomKeyboardDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("BOT_DATA_DIR")
        os.environ["BOT_DATA_DIR"] = self.tmp.name
        self.msg = FakeMessage()
        self.fn = load_nav_functions(self.msg)
        self.uid = 34156

    def tearDown(self):
        if self.old is None:
            os.environ.pop("BOT_DATA_DIR", None)
        else:
            os.environ["BOT_DATA_DIR"] = self.old
        self.tmp.cleanup()

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_first_access_shows_real_bottom_keyboard_and_inline_navigation(self):
        self.run_async(self.fn["show_access"](self.msg, self.uid, 1, entering=True))
        self.assertEqual(len(self.msg.out), 2)
        self.assertEqual(self.msg.out[0]["text"], "🔐 Безкоштовні доступи до аукціонів")
        self.assertEqual(self.msg.out[0]["reply_markup"], ("bottom", "menu", "korea", "manager"))
        self.assertEqual(self.msg.out[1]["reply_markup"], ("inline", "access", 1))
        self.assertEqual(self.msg.out[1]["photo"], "access1")
        self.assertNotIn("\u2063", self.msg.out[0]["text"])

    def test_next_and_back_do_not_create_or_delete_keyboard_messages(self):
        self.run_async(self.fn["show_access"](self.msg, self.uid, 1, entering=True))
        self.run_async(self.fn["show_access"](self.msg, self.uid, 2))
        self.run_async(self.fn["show_access"](self.msg, self.uid, 3))
        self.run_async(self.fn["show_access"](self.msg, self.uid, 2))
        self.assertEqual(len(self.msg.out), 5)
        self.assertEqual(sum(m["kind"] == "keyboard" for m in self.msg.out), 1)
        self.assertEqual([m["photo"] for m in self.msg.out if m["kind"] == "screen"],
                         ["access1", "access2", "access3", "access2"])

    def test_korea_navigation_shows_bottom_keyboard_and_inline_buttons(self):
        self.run_async(self.fn["show_korea"](self.msg, self.uid, 1, entering=True))
        self.run_async(self.fn["show_korea"](self.msg, self.uid, 2))
        self.run_async(self.fn["show_korea"](self.msg, self.uid, 3))
        self.assertEqual(self.msg.out[0]["reply_markup"], ("bottom", "pick", "calc", "menu", "access", "manager"))
        self.assertEqual([m["reply_markup"] for m in self.msg.out[1:]],
                         [("inline", "korea", 1), ("inline", "korea", 2), ("inline", "korea", 3)])

    def test_korea_final_screen_sets_bottom_keyboard_directly_without_extra_bubble(self):
        self.run_async(self.fn["show_korea"](self.msg, self.uid, 1, entering=True))
        self.msg.out.clear()
        self.run_async(self.fn["show_korea"](self.msg, self.uid, 4))
        self.assertEqual(len(self.msg.out), 1)
        self.assertEqual(self.msg.out[0]["kind"], "screen")
        self.assertEqual(self.msg.out[0]["reply_markup"],
                         ("bottom", "pick", "calc", "menu", "access", "manager"))

    def test_switch_between_korea_and_access_updates_bottom_keyboard_once(self):
        self.run_async(self.fn["show_access"](self.msg, self.uid, 1, entering=True))
        self.run_async(self.fn["show_korea"](self.msg, self.uid, 1))
        self.run_async(self.fn["show_access"](self.msg, self.uid, 1))
        self.assertEqual([m["text"] for m in self.msg.out if m["kind"] == "keyboard"],
                         ["🔐 Безкоштовні доступи до аукціонів",
                          "🇰🇷 Чому авто з Кореї?",
                          "🔐 Безкоштовні доступи до аукціонів"])

    def test_no_invisible_anchor_or_auto_deletion_in_nav_code(self):
        code = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn('answer("\\u2063"', code)
        self.assertNotIn("await anchor.delete()", code)
        self.assertNotIn("await asyncio.sleep(0.6)", code)


if __name__ == "__main__":
    unittest.main()
