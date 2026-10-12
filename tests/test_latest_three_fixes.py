"""Regression checks for 12.10: 5-button Korea, blue menu, manager links."""
import ast
import unittest
from pathlib import Path
from app import content

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')
KEYBOARDS = (ROOT / 'app' / 'keyboards.py').read_text(encoding='utf-8')


class LatestThreeFixes(unittest.TestCase):
    def test_manager_link_labels_and_urls(self):
        self.assertIn('Телеграм канал - https://t.me/+Lr5L8xRGZa9kZGRi', content.MANAGER)
        self.assertIn('Чат «Гарячі лоти в Кореї» - https://t.me/+YuRmEjW__dplMTZi', content.MANAGER)
        self.assertNotIn('канал линк', content.MANAGER)
        self.assertNotIn('чат “Гарячі Лоти”', content.MANAGER)

    def test_command_handlers_are_registered_and_call_screens(self):
        tree = ast.parse(MAIN)
        func_to_target = {
            'on_pick_command': 'begin_quiz',
            'on_calc_command': 'begin_quiz',
            'on_korea_command': 'show_korea',
            'on_manager_command': 'show_manager',
            'on_access_command': 'open_access',
        }
        found = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef) or node.name not in func_to_target:
                continue
            declared = []
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                for arg in dec.args:
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'Command':
                        declared.extend(a.value for a in arg.args if isinstance(a, ast.Constant))
            inner_calls = [x.func.id for x in ast.walk(node) if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)]
            found[node.name] = (declared, inner_calls)
        self.assertEqual(set(found), set(func_to_target))
        for handler, target in func_to_target.items():
            self.assertIn(target, found[handler][1])
        self.assertEqual({x for commands, _ in found.values() for x in commands},
                         {'pick', 'calc', 'korea', 'manager', 'access'})
        self.assertIn('set_my_commands(kb.default_commands()', MAIN)
        self.assertIn('set_my_commands(kb.admin_commands()', MAIN)

    def test_all_korea_pages_use_proper_bottom_keyboard(self):
        self.assertIn('reply_markup=kb.korea_last_nav_kb()', MAIN)
        self.assertIn('reply_markup=kb.korea_step_kb(page)', MAIN)
        self.assertIn('set_section_keyboard(message, kb.KOREA, kb.korea_nav_kb())', MAIN)
        self.assertIn('return korea_nav_kb()', KEYBOARDS)


if __name__ == '__main__':
    unittest.main()
