import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ps4_temp_cleanup import cleanup_ps4_merge, owned_merge_paths


class CleanupTests(unittest.TestCase):
    def test_success_removes_only_generated_folders(self):
        with tempfile.TemporaryDirectory() as root:
            temp=Path(root)/"temp"
            temp.mkdir()
            merged=temp/"ps4_merge_aabbcc"
            merged.mkdir()
            (merged/"eboot.bin").write_bytes(b"a")
            extracted=temp/"ps4_pkg_extract"/"Patch_12"
            extracted.mkdir(parents=True)
            (extracted/"discard.bin").write_bytes(b"patch")
            user=Path(root)/"user_game"
            user.mkdir()
            (user/"keep.bin").write_bytes(b"original")
            output=Path(root)/"CUSA12381.ffpfsc"
            output.write_bytes(b"FFPFSC"+b"0"*2048)
            cleanup_ps4_merge(str(temp),str(merged),[str(extracted)],str(output))
            self.assertFalse(merged.exists())
            self.assertFalse(extracted.exists())
            self.assertTrue((user/"keep.bin").exists())
            self.assertTrue(output.exists())

    def test_failed_output_never_deletes(self):
        with tempfile.TemporaryDirectory() as root:
            temp=Path(root)/"temp"
            temp.mkdir()
            merged=temp/"ps4_merge_aabbcc"
            merged.mkdir()
            output=Path(root)/"output.ffpfsc"
            output.write_bytes(b"")
            with self.assertRaises(ValueError):
                cleanup_ps4_merge(str(temp),str(merged),[],str(output))
            self.assertTrue(merged.exists())

    def test_user_folder_outside_temp_never_deletes(self):
        with tempfile.TemporaryDirectory() as root:
            temp=Path(root)/"temp"
            temp.mkdir()
            user=Path(root)/"my_game"
            user.mkdir()
            with self.assertRaises(ValueError):
                owned_merge_paths(str(temp),str(user),[])


if __name__=="__main__":
    unittest.main()
