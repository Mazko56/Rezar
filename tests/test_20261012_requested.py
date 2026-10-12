import unittest
from app import content, storage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT/'app/main.py').read_text(encoding='utf-8')
KB = (ROOT/'app/keyboards.py').read_text(encoding='utf-8')

class RequestedTests(unittest.TestCase):
    def test_budget_inline(self):
        self.assertIn('return i([[(label, f"budget:{n}")', KB)
        self.assertIn('F.data.startswith("budget:")', MAIN)
        self.assertEqual(len(storage.DEFAULT_AUCTION_CREDENTIALS),8)
    def test_labels(self):
        self.assertEqual(content.PREFERRED_CONTACT, 'Як вам зручніше, щоб ми надали інформацію:')
        self.assertIn('рік виробництва', content.YEAR_QUESTION)
        self.assertIn('не платіть посередникам', content.KOREA_4)
        self.assertNotIn('прижени собі сам', content.KOREA_4)
        self.assertIn('Чат «Гарячі лоти в Кореї»', content.MANAGER)
    def test_link_preview_optout(self):
        self.assertIn('LinkPreviewOptions(is_disabled=True)', MAIN)
        self.assertIn('disable_preview=True', MAIN)
    def test_access_route_from_korea_manager(self):
        self.assertIn('p["view"] in {"korea", "manager"}', MAIN)
        self.assertIn('await send_completed_access_choices(message)', MAIN)

if __name__ == '__main__': unittest.main()
