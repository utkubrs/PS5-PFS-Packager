import json
import shutil
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ps4_shadowmount_metadata import prepare_ps4_shadowmount_metadata, prepare_existing_temp_merge, ffpfsc_outer_pfs_profile, validate_ffpfsc_outer_header, PFS_MAGIC
from test_ps4_merge import make_sfo


class PS4ShadowMountMetadataTest(unittest.TestCase):
    def make_game(self, root):
        original = root / "original"
        staged = root / "ps4_merge_f0db1234"
        (original / "sce_sys").mkdir(parents=True)
        (original / "eboot.bin").write_bytes(b"EB00T")
        make_sfo(original / "sce_sys" / "param.sfo",
                 title="Chim Party (TR)", title_id="CUSA12381")
        (original / "sce_sys" / "snd0.at9").write_bytes(b"GAME SOUND")
        shutil.copytree(original, staged)
        return original, staged

    def test_compatible_json_preserves_sfo_and_original_and_optionally_sound(self):
        with tempfile.TemporaryDirectory() as tmp:
            original, staged = self.make_game(Path(tmp))
            base_sfo = (staged / "sce_sys" / "param.sfo").read_bytes()
            result = prepare_ps4_shadowmount_metadata(str(staged), remove_snd0=True)
            self.assertEqual(result["title_id"], "CUSA12381")
            self.assertTrue(result["snd0_removed"])
            self.assertFalse((staged / "sce_sys" / "snd0.at9").exists())
            self.assertTrue((original / "sce_sys" / "snd0.at9").exists())
            self.assertEqual((staged / "sce_sys" / "param.sfo").read_bytes(), base_sfo)
            payload = json.loads((staged / "sce_sys" / "param.json").read_text("utf-8"))
            self.assertEqual(payload["titleId"], "CUSA12381")
            self.assertEqual(payload["titleName"], "Chim Party (TR)")
            self.assertEqual(payload["localizedParameters"]["en-US"]["titleName"], "Chim Party (TR)")
            self.assertEqual(payload["localizedParameters"]["defaultLanguage"], "en-US")

    def test_checkbox_off_retains_sound_and_repairs_existing_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, staged = self.make_game(Path(tmp))
            existing = staged / "sce_sys" / "param.json"
            existing.write_text('{"custom": 123, "titleId": "CUSA00000"}', "utf-8")
            result = prepare_ps4_shadowmount_metadata(str(staged), remove_snd0=False)
            self.assertFalse(result["snd0_removed"])
            self.assertTrue((staged / "sce_sys" / "snd0.at9").exists())
            payload = json.loads(existing.read_text("utf-8"))
            self.assertEqual(payload["titleId"], "CUSA12381")
            self.assertEqual(payload["custom"], 123)

    def test_missing_valid_cusa_fails_without_deleting_sound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sce_sys").mkdir()
            (root / "eboot.bin").touch()
            make_sfo(root / "sce_sys" / "param.sfo", title_id="PPSA12345")
            (root / "sce_sys" / "snd0.at9").touch()
            with self.assertRaisesRegex(ValueError, "CUSA"):
                prepare_ps4_shadowmount_metadata(str(root), remove_snd0=True)
            self.assertTrue((root / "sce_sys" / "snd0.at9").exists())


    def test_repack_old_temp_merge_regenerates_cusa_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp) / "temp"
            temp.mkdir()
            base, staged = self.make_game(temp)
            old = temp / "ps4_merge_eccb0f3a0b"
            staged.rename(old)
            self.assertFalse((old / "sce_sys" / "param.json").exists())
            fixed = prepare_existing_temp_merge(str(old), str(temp), False)
            self.assertEqual(fixed["title_id"], "CUSA12381")
            data = json.loads((old / "sce_sys" / "param.json").read_text("utf-8"))
            self.assertEqual(data["titleId"], "CUSA12381")
            self.assertTrue((old / "sce_sys" / "snd0.at9").exists())

    def test_non_owned_folder_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp) / "temp"
            temp.mkdir()
            original, stage = self.make_game(Path(tmp))
            self.assertIsNone(prepare_existing_temp_merge(str(original), str(temp), True))
            self.assertTrue((original / "sce_sys" / "snd0.at9").exists())
            self.assertFalse((original / "sce_sys" / "param.json").exists())


    def test_ps4_game_uses_ps5_outer_container_profile(self):
        self.assertEqual(ffpfsc_outer_pfs_profile("PS4"), "PS5")
        self.assertEqual(ffpfsc_outer_pfs_profile("PS5"), "PS5")
        with self.assertRaises(ValueError):
            ffpfsc_outer_pfs_profile("PS3")

    def test_outer_header_rejects_old_ps4_pfs_version_one(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "CUSA12381.ffpfsc"
            header = bytearray(0x10000)
            struct.pack_into("<qq", header, 0, 1, PFS_MAGIC)
            struct.pack_into("<I", header, 0x20, 0x10000)
            struct.pack_into("<H", header, 0x1C, 8)
            out.write_bytes(header)
            with self.assertRaisesRegex(ValueError, "version 2"):
                validate_ffpfsc_outer_header(str(out))
            struct.pack_into("<q", header, 0, 2)
            out.write_bytes(header)
            self.assertEqual(validate_ffpfsc_outer_header(str(out)), (2, 65536))

    def test_npbind_sha1_footer_fix_in_staged_copy_only(self):
        with tempfile.TemporaryDirectory() as folder:
            original, staged = self.make_game(Path(folder))
            payload = bytearray(0x80 + 0x180 + 20)
            struct.pack_into(">IIQQQ", payload, 0, 0xD294A018, 1,
                             len(payload), 0x180, 1)
            payload[-20:] = b"X" * 20
            (staged / "sce_sys" / "npbind.dat").write_bytes(payload)
            result = prepare_ps4_shadowmount_metadata(str(staged))
            self.assertTrue(result["npbind_repaired"])
            repaired = (staged / "sce_sys" / "npbind.dat").read_bytes()
            self.assertEqual(repaired[-20:], hashlib.sha1(repaired[:-20]).digest())
            self.assertFalse((original / "sce_sys" / "npbind.dat").exists())


if __name__ == "__main__":
    unittest.main()
