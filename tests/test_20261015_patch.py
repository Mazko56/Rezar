import unittest
from app import content
from pathlib import Path
KB = (Path(__file__).resolve().parents[1] / "app/keyboards.py").read_text(encoding="utf-8")

class Patch20261015(unittest.TestCase):
    def test_intro(self):
        self.assertIn('доставимо за 2 місяці!\n- розмитнюємо', content.BOT_INTRO)
        self.assertNotIn('без змін в дорозі!', content.BOT_INTRO)
    def test_budget(self):
        self.assertIn('"40–50 тис.", "50+ тис."', KB)
        self.assertEqual(content.BUDGET_QUESTION, '3. Який бюджет на авто під ключ в Україні? ($)')
    def test_contact(self):
        self.assertIn("п'яти авто", content.QUIZ_READY)
        self.assertIn('return i([[(CHAT, "preferred:chat"), (CALL, "preferred:call")]])', KB)
    def test_access(self):
        self.assertIn('return i([[(AUCTIONS, "open:auctions")], [(DEALERS, "open:dealers")]])', KB)
    def test_texts(self):
        self.assertIn('<b>Умови співпраці:</b>', content.AUCTIONS)
        self.assertIn('морський фрахт 2 місяці', content.AUCTIONS)
        self.assertIn('Audi A6 C8', content.KOREA_2)
        self.assertIn('20.000$</b>', content.KOREA_2)
        self.assertIn('вигідніше', content.KOREA_2)
        self.assertIn('виробництва', content.KOREA_2)
        self.assertIn('відкрита історія', content.KOREA_3)
        self.assertIn('«кота в мішку»', content.KOREA_3)
        self.assertIn('65058, м. Одеса, вул. Зоопаркова', content.MANAGER)
        self.assertIn('<b>Умови співпраці:</b>', content.MANAGER)

if __name__ == '__main__':
    unittest.main()
