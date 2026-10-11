import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ps4_inputs import is_ps4_game_folder, detect_ps4_title_id, extract_pkg

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

if __name__=="__main__":
    unittest.main()
