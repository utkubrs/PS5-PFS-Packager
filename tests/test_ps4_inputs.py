import tempfile
import unittest
import os
from unittest import mock
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ps4_inputs import is_ps4_game_folder, detect_ps4_title_id, inspect_ps4_source, extract_pkg, find_pkg_extractor

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

    def test_sidecar_tools_from_real_exe_dir_even_if_runtime_is_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            app=root/"Installed Program"
            run=root/"onefile_runtime"
            (app/"tools").mkdir(parents=True)
            run.mkdir()
            extractor=app/"tools"/"pkgextract.exe"
            extractor.write_bytes(b"placeholder")
            with mock.patch.object(sys, "executable", str(run/"PS5-PFS-Packager.exe")):
                with mock.patch.object(sys, "argv", [str(app/"PS5-PFS-Packager.exe")]):
                    with mock.patch.dict(os.environ, {"PS4_PKG_EXTRACTOR": ""}):
                        self.assertEqual(find_pkg_extractor(app_dir=str(app)), str(extractor.resolve()))

    def test_extractor_can_be_found_inside_onefile_payload_without_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            included=root/"unpacked"/"tools"/"pkgextract.exe"
            included.parent.mkdir(parents=True)
            included.touch()
            with mock.patch.dict(os.environ, {"PS4_PKG_EXTRACTOR": ""}):
                self.assertEqual(
                    find_pkg_extractor(app_dir=str(root/"desktop"),
                                       bundled_path=str(included)),
                    str(included.resolve()))

    def test_explicit_extractor_override_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            extractor=Path(tmp)/"custom_pkgextract.exe"
            extractor.touch()
            with mock.patch.dict(os.environ, {"PS4_PKG_EXTRACTOR": str(extractor)}):
                self.assertEqual(find_pkg_extractor(), str(extractor.resolve()))

    def test_missing_extractor_never_silently_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            pkg=base/"Sample.pkg"
            pkg.touch()
            with mock.patch.dict(os.environ, {"PS4_PKG_EXTRACTOR": ""}):
                with mock.patch("ps4_inputs.find_pkg_extractor", return_value=None):
                    with self.assertRaisesRegex(RuntimeError, "PKG extractor missing"):
                        extract_pkg(str(pkg), str(base), app_dir=str(base/"nonexistent"))

    def test_previous_extraction_is_preserved_and_new_folder_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root/"Game.pkg"
            pkg.write_bytes(b"PKG")
            previous = root/"ps4_pkg_extract"/"Game"
            previous.mkdir(parents=True)
            (previous/"keep.txt").write_text("DO NOT DELETE")
            observed = []

            def fake_popen(args, **kwargs):
                output = Path(args[-1])
                observed.append(output)
                (output/"sce_sys").mkdir(parents=True)
                (output/"sce_sys"/"param.sfo").write_bytes(b"Test")
                (output/"eboot.bin").touch()
                child = mock.Mock()
                child.communicate.return_value = ("", None)
                child.returncode = 0
                return child

            with mock.patch("ps4_inputs.find_pkg_extractor", return_value="fake-pkgextract.exe"):
                with mock.patch("ps4_inputs.subprocess.Popen", side_effect=fake_popen):
                    result = extract_pkg(str(pkg), str(root))
            self.assertEqual(Path(result), observed[0])
            self.assertNotEqual(Path(result), previous)
            self.assertEqual((previous/"keep.txt").read_text(), "DO NOT DELETE")

if __name__=="__main__":
    unittest.main()
