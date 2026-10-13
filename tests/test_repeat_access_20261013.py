import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class AccessRegression(unittest.TestCase):
    def test_repeat_access_routes_to_choice(self):
        tree = ast.parse((ROOT / 'app/main.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'open_access')
        cond = next(n for n in fn.body if isinstance(n, ast.If))
        calls = [n.func.id for n in ast.walk(cond.body[0]) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)] if False else [n.func.id for stmt in cond.body for n in ast.walk(stmt) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertIn('send_completed_access_choices', calls)
        self.assertNotIn('show_auctions', calls)

    def test_buttons_are_two_full_rows(self):
        text = (ROOT / 'app/keyboards.py').read_text()
        self.assertIn('return i([[(AUCTIONS, "open:auctions")], [(DEALERS, "open:dealers")]])', text)
