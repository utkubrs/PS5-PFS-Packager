"""Synthetic and safety tests for PS4 FFPFSC -> PKG orchestration."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ffpfsc_to_pkg import (inspect_ffpfsc, find_ps4_game_root,
                           convert_ffpfsc_to_ps4_pkg, PKG_MAGIC)
from test_ps4_merge import make_sfo


def image_at(path):
    header = bytearray(80)
    struct.pack_into("<qq", header, 0, 2, 20130315)
    struct.pack_into("<I", header, 0x20, 65536)
    path.write_bytes(bytes(header) + b"\0" * 4096)
    return path


class FfpfscToPkgTest(unittest.TestCase):
    def test_header_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.ffpfsc"
            p.write_bytes(b"not a compressed PFS")
            with self.assertRaises(ValueError):
                inspect_ffpfsc(p)

    def test_rejects_ps5_image(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "sce_sys").mkdir()
            (root / "sce_sys" / "param.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "PS5 image"):
                find_ps4_game_root(root)

    def test_ps4_conversion_mocked_commands_and_original_preservation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            temp = root / "temp"
            output = root / "out"
            temp.mkdir()
            output.mkdir()
            source = image_at(root / "game.ffpfsc")
            original = source.read_bytes()
            exe = root / "OrbisPkgTool.exe"
            exe.write_bytes(b"mock external CLI")
            calls = []
            def run(cmd):
                calls.append(cmd)
                if "unpack" in cmd:
                    game = Path(cmd[-1])
                    (game / "sce_sys").mkdir(parents=True)
                    (game / "eboot.bin").write_bytes(b"ELF")
                    make_sfo(game / "sce_sys" / "param.sfo")
                    (game / "sce_sys" / "param.json").write_text('{"shadowmount":true}')
                elif cmd[1] == "gp4gen":
                    Path(cmd[-1]).write_text("<gp4/>")
                elif cmd[1] == "build":
                    Path(cmd[cmd.index("--out") + 1]).write_bytes(PKG_MAGIC + b"\0" * 2048)
            pkg = output / "game.pkg"
            result = convert_ffpfsc_to_ps4_pkg(source, pkg, temp,
                                               ["mkpfs"], exe, command_runner=run)
            self.assertEqual(result.resolve(), pkg.resolve())
            self.assertEqual(pkg.read_bytes()[:4], PKG_MAGIC)
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[1][1], "gp4gen")
            self.assertEqual(calls[2][1], "build")
            self.assertIn("--validate", calls[2])
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(list(temp.glob("ffpfsc_ps4_pkg_*")))

    def test_direct_embedded_cusa_app_pkg_is_copied_without_builder(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            temp, output = root / "temp", root / "out"
            temp.mkdir()
            output.mkdir()
            image = image_at(root / "game.ffpfsc")
            original = image.read_bytes()
            pkg_contents = PKG_MAGIC + b"EXISTING PS4 PACKAGE" + b"\0" * 4096
            calls = []
            def run(cmd):
                calls.append(cmd)
                if "unpack" in cmd:
                    app = Path(cmd[-1]) / "CUSA54321" / "app.pkg"
                    app.parent.mkdir(parents=True)
                    app.write_bytes(pkg_contents)
            out = output / "recovered.pkg"
            result = convert_ffpfsc_to_ps4_pkg(
                image, out, temp, ["mkpfs"], "",
                command_runner=run)
            self.assertEqual(result.resolve(), out.resolve())
            self.assertEqual(out.read_bytes(), pkg_contents)
            self.assertEqual(image.read_bytes(), original)
            self.assertEqual(len(calls), 1)
            self.assertFalse(list(temp.glob("ffpfsc_ps4_pkg_*")))

    def test_embedded_pkg_inside_additional_wrapper_is_found(self):
        from ffpfsc_to_pkg import find_embedded_ps4_pkg
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / "wrapper" / "CUSA12345" / "app.pkg"
            p.parent.mkdir(parents=True)
            p.write_bytes(PKG_MAGIC + b"\0" * 2048)
            self.assertEqual(find_embedded_ps4_pkg(root), p)

    def test_invalid_embedded_pkg_rejected_instead_of_fallback(self):
        from ffpfsc_to_pkg import find_embedded_ps4_pkg
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pkg = root / "CUSA12345" / "app.pkg"
            pkg.parent.mkdir()
            pkg.write_bytes(b"NOT A PACKAGE" + b"\0" * 2048)
            with self.assertRaisesRegex(ValueError, "signature"):
                find_embedded_ps4_pkg(root)

    def test_multiple_embedded_packages_are_ambiguous(self):
        from ffpfsc_to_pkg import find_embedded_ps4_pkg
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for title in ("CUSA12345", "CUSA99999"):
                pkg = root / title / "app.pkg"
                pkg.parent.mkdir()
                pkg.write_bytes(PKG_MAGIC + b"\0" * 2048)
            with self.assertRaisesRegex(ValueError, "Several"):
                find_embedded_ps4_pkg(root)

    def test_does_not_overwrite_pkg(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            temp = root / "temp"
            temp.mkdir()
            exe = root / "OrbisPkgTool.exe"
            exe.write_bytes(b"mock")
            source = image_at(root / "game.ffpfsc")
            output = root / "game.pkg"
            output.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                convert_ffpfsc_to_ps4_pkg(source, output, temp, ["mkpfs"], exe)
            self.assertEqual(output.read_bytes(), b"original")

    def test_no_ps4_game_tree_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "sce_sys").mkdir()
            (root / "eboot.bin").touch()
            with self.assertRaisesRegex(ValueError, "PS4 game"):
                find_ps4_game_root(root)


if __name__ == "__main__":
    unittest.main()
