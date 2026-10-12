import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ps4_cleanup import cleanup_ps4_temp


class PS4CleanupTests(unittest.TestCase):
    def test_owned_temp_removed_but_user_folders_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            r = Path(root)
            temp = r / "temp"
            temp.mkdir()
            user_game = r / "game"
            user_game.mkdir()
            (user_game / "original.bin").write_bytes(b"must persist")
            merge = temp / "ps4_merge_123456789a"
            merge.mkdir()
            (merge / "large.bin").write_bytes(b"merged")
            extract = temp / "ps4_pkg_extract" / "Game_1"
            inner = extract / "inner"
            inner.mkdir(parents=True)
            (inner / "sfo.bin").write_bytes(b"old data")
            kept = temp / "ps4_pkg_extract" / "other_saved"
            kept.mkdir()
            (kept / "keep.txt").write_text("keep")
            cleaned = cleanup_ps4_temp(str(merge), [str(inner)], str(temp))
            self.assertEqual(len(cleaned), 2)
            self.assertFalse(merge.exists())
            self.assertFalse(extract.exists())
            self.assertTrue(kept.exists())
            self.assertTrue((user_game / "original.bin").exists())

    def test_rejects_user_selected_folder_without_deletion(self):
        with tempfile.TemporaryDirectory() as root:
            r = Path(root)
            temp = r / "temp"
            temp.mkdir()
            user = r / "important"
            user.mkdir()
            (user / "keep.txt").write_text("important")
            with self.assertRaises(ValueError):
                cleanup_ps4_temp(str(user), [], str(temp))
            self.assertTrue((user / "keep.txt").exists())

    def test_rejects_extraction_not_owned_by_temp(self):
        with tempfile.TemporaryDirectory() as root:
            r = Path(root)
            temp = r / "temp"
            merge = temp / "ps4_merge_123456789a"
            merge.mkdir(parents=True)
            user = r / "original_update"
            user.mkdir()
            with self.assertRaises(ValueError):
                cleanup_ps4_temp(str(merge), [str(user)], str(temp))
            self.assertTrue(merge.exists())
            self.assertTrue(user.exists())

    def test_does_not_remove_other_failed_extractions(self):
        with tempfile.TemporaryDirectory() as root:
            r = Path(root)
            temp = r / "temp"
            merge = temp / "ps4_merge_123456789a"
            merge.mkdir(parents=True)
            stale = temp / "ps4_merge_fedcba9876"
            stale.mkdir()
            cleanup_ps4_temp(str(merge), [], str(temp))
            self.assertTrue(stale.exists())


if __name__ == "__main__":
    unittest.main()
