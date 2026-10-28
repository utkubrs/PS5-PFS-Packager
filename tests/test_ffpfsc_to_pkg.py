"""Synthetic and safety tests for PS4 FFPFSC -> PKG orchestration."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ffpfsc_to_pkg import (inspect_ffpfsc, find_ps4_game_root,
                           convert_ffpfsc_to_ps4_pkg, prepare_gp4_for_orbis,
                           validate_orbis_pub_cmd, PKG_MAGIC)
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
            exe = root / "orbis-pub-cmd.exe"
            exe.write_bytes(b"mock external Orbis CLI")
            (root / "ext").mkdir()
            (root / "ext" / "sc.exe").touch()
            (root / "orbis-pub-prx.dll").touch()
            generator = root / "OrbisPkgTool.exe"
            generator.write_bytes(b"mock GP4 generator")
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
                    Path(cmd[-1]).write_text(
                        '<psproject><volume><volume_type>pkg_ps4_app</volume_type>'
                        '<package content_id="TEST"/></volume><files>'
                        '<file targ_path="eboot.bin" orig_path="eboot.bin"/>'
                        '<file targ_path="sce_sys/param.sfo" orig_path="sce_sys/param.sfo"/>'
                        '</files></psproject>', encoding="utf-8")
                elif cmd[1] == "img_create":
                    import xml.etree.ElementTree as ET
                    gp4 = ET.parse(cmd[-2]).getroot()
                    for element in gp4.findall("files/file"):
                        self.assertTrue(Path(element.get("orig_path")).exists())
                    outdir = Path(cmd[-1])
                    (outdir / "UP0000-TEST.pkg").write_bytes(PKG_MAGIC + b"\0" * 2048)
            pkg = output / "game.pkg"
            result = convert_ffpfsc_to_ps4_pkg(source, pkg, temp,
                                               ["mkpfs"], exe, command_runner=run,
                                               gp4_generator=generator)
            self.assertEqual(result.resolve(), pkg.resolve())
            self.assertEqual(pkg.read_bytes()[:4], PKG_MAGIC)
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[1][1], "gp4gen")
            self.assertEqual(calls[2][1], "img_create")
            self.assertEqual(calls[2][2:4], ["--oformat", "pkg"])
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(list(temp.glob("ffpfsc_ps4_pkg_*")))

    def test_does_not_overwrite_pkg(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            temp = root / "temp"
            temp.mkdir()
            exe = root / "orbis-pub-cmd.exe"
            exe.write_bytes(b"mock")
            (root / "ext").mkdir()
            (root / "ext" / "sc.exe").touch()
            (root / "orbis-pub-prx.dll").touch()
            generator = root / "OrbisPkgTool.exe"
            generator.write_bytes(b"mock")
            source = image_at(root / "game.ffpfsc")
            output = root / "game.pkg"
            output.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                convert_ffpfsc_to_ps4_pkg(source, output, temp, ["mkpfs"], exe,
                                           gp4_generator=generator)
            self.assertEqual(output.read_bytes(), b"original")

    def test_orbis_sdk_requires_ext(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "orbis-pub-cmd.exe"
            exe.touch()
            with self.assertRaisesRegex(ValueError, "ext"):
                validate_orbis_pub_cmd(exe)
            (Path(d) / "ext").mkdir()
            (Path(d) / "ext" / "sc.exe").touch()
            (Path(d) / "orbis-pub-prx.dll").touch()
            self.assertEqual(validate_orbis_pub_cmd(exe), exe.resolve())

    def test_gp4_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            game = root / "game"
            game.mkdir()
            gp4 = root / "test.gp4"
            gp4.write_text(
                '<psproject><volume><volume_type>pkg_ps4_app</volume_type>'
                '<package content_id="TEST"/></volume><files>'
                '<file targ_path="../outside.bin" orig_path="../outside.bin"/>'
                '</files></psproject>')
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                prepare_gp4_for_orbis(gp4, game)

    def test_no_ps4_game_tree_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "sce_sys").mkdir()
            (root / "eboot.bin").touch()
            with self.assertRaisesRegex(ValueError, "PS4 game"):
                find_ps4_game_root(root)


if __name__ == "__main__":
    unittest.main()
