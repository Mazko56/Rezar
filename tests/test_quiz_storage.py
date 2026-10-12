"""Run from project root: python -m unittest discover -s tests -v"""
import os
import tempfile
import unittest
from app import storage


class QuizStorageTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.old = os.environ.get("BOT_DATA_DIR")
        os.environ["BOT_DATA_DIR"] = self.dir.name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("BOT_DATA_DIR", None)
        else:
            os.environ["BOT_DATA_DIR"] = self.old
        self.dir.cleanup()

    def test_independent_resumable_sections(self):
        storage.begin_quiz(123, "pick")
        storage.update_quiz(123, "pick", stage="year", car="Audi")
        storage.begin_quiz(123, "calc")
        self.assertEqual(storage.read_quiz(123, "calc")["stage"], "car")
        storage.begin_quiz(123, "pick")
        self.assertEqual(storage.read_quiz(123, "pick")["stage"], "year")
        self.assertEqual(storage.read_quiz(123, "pick")["car"], "Audi")

    def test_new_request_after_completion(self):
        storage.begin_quiz(456, "pick")
        storage.update_quiz(456, "pick", car="BMW", year="2022", budget="20–30 тис.")
        storage.complete_quiz(456, "pick")
        self.assertTrue(storage.has_completed_quiz(456))
        storage.begin_quiz(456, "calc")
        self.assertEqual(storage.read_quiz(456, "calc")["stage"], "car")
        storage.begin_quiz(456, "pick")
        q = storage.read_quiz(456, "pick")
        self.assertFalse(q["completed"])
        self.assertEqual(q["stage"], "car")
        self.assertIsNone(q["car"])

    def test_admin_photos_persist_and_reset(self):
        storage.set_photo_override("access2", "test_file_id")
        self.assertEqual(storage.get_photo_override("access2"), "test_file_id")
        storage.remove_photo_override("access2")
        self.assertIsNone(storage.get_photo_override("access2"))

    def test_legacy_migration(self):
        storage.update(789, source="pick", stage="year", car="Mercedes")
        storage.begin_quiz(789, "calc")
        self.assertEqual(storage.read_quiz(789, "pick")["car"], "Mercedes")


if __name__ == "__main__":
    unittest.main()
