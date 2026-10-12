import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ps4_shadowmount_metadata import prepare_ps4_shadowmount_metadata
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


if __name__ == "__main__":
    unittest.main()
