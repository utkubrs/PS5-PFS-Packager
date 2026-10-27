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
            self.assertEqual(result, pkg)
            self.assertEqual(pkg.read_bytes()[:4], PKG_MAGIC)
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[1][1], "gp4gen")
            self.assertEqual(calls[2][1], "build")
            self.assertIn("--validate", calls[2])
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(list(temp.glob("ffpfsc_ps4_pkg_*")))

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
