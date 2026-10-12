import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ps4_inputs import is_ps4_game_folder, detect_ps4_title_id, inspect_ps4_source, extract_pkg

class PS4InputsTests(unittest.TestCase):
    def test_ps4_folder_requires_param_sfo(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"CUSA12345-app"
            (p/"sce_sys").mkdir(parents=True)
            (p/"eboot.bin").touch()
            self.assertFalse(is_ps4_game_folder(str(p)))
            (p/"sce_sys"/"param.sfo").write_bytes(b"PSF\\x00CUSA12345")
            self.assertTrue(is_ps4_game_folder(str(p)))
            self.assertEqual(detect_ps4_title_id(str(p)), "CUSA12345")

    def test_invalid_pkg_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                extract_pkg(str(Path(folder)/"missing.pkg"),folder)

    def test_pkg_header_cusa_and_human_title(self):
        with tempfile.TemporaryDirectory() as folder:
            pkg=Path(folder)/"Batman Arkham Knight-1.pkg"
            pkg.write_bytes(b"\\x7fCNT" + b"\\0"*48 + b"EP0001-CUSA00135_00-SOMEGAME" + b"\\0"*64)
            data=inspect_ps4_source(str(pkg))
            self.assertEqual(data["title_id"], "CUSA00135")
            self.assertEqual(data["title"], "Batman Arkham Knight")

    def test_missing_pkg_header_uses_name_before_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            pkg=Path(folder)/"Batman Arkham Knight-2-TR.pkg"
            pkg.write_bytes(b"not a full pkg header")
            data=inspect_ps4_source(str(pkg))
            self.assertEqual(data["title"], "Batman Arkham Knight")
            self.assertEqual(data["title_id"], "")

if __name__=="__main__":
    unittest.main()
