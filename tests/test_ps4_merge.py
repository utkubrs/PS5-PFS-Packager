import struct
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from ps4_merge import merge_ps4_folders, edit_sfo_title, sfo_fields

def make_sfo(path, title="Base Game", title_id="CUSA12345", category="gd", app_ver="1.00", localized_titles=None):
    values={"TITLE":title,"TITLE_ID":title_id,"CONTENT_ID":"UP0000-CUSA12345_00-EXAMPLE000000000","CATEGORY":category,"APP_VER":app_ver}
    values.update(localized_titles or {})
    keys=bytearray();data=bytearray();entries=[]
    for name,value in values.items():
        keyoff=len(keys);keys+=name.encode()+b"\0"
        raw=value.encode()+b"\0";maximum=max(128,len(raw))
        off=len(data);data+=raw.ljust(maximum,b"\0")
        entries.append((keyoff,0x0204,len(raw),maximum,off))
    keyoff=20+len(entries)*16
    dataoff=keyoff+len(keys)
    blob=bytearray(struct.pack("<4s4I",b"\0PSF",0x101,keyoff,dataoff,len(entries)))
    for row in entries:blob+=struct.pack("<HHIII",*row)
    blob+=keys+data
    path.write_bytes(blob)

class PS4MergeTest(unittest.TestCase):
    def test_missing_pic0_artwork_renamed_only_in_merge_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, out = root / "base", root / "merged"
            (base / "sce_sys").mkdir(parents=True)
            (base / "eboot.bin").write_bytes(b"GAME")
            make_sfo(base / "sce_sys" / "param.sfo")
            (base / "sce_sys" / "pic1.png").write_bytes(b"PNG SOURCE")
            (base / "sce_sys" / "pic1.dds").write_bytes(b"DDS SOURCE")
            result = merge_ps4_folders(str(base), None, str(out))
            self.assertEqual((out / "sce_sys" / "pic0.png").read_bytes(), b"PNG SOURCE")
            self.assertEqual((out / "sce_sys" / "pic0.dds").read_bytes(), b"DDS SOURCE")
            self.assertFalse((out / "sce_sys" / "pic1.png").exists())
            self.assertFalse((out / "sce_sys" / "pic1.dds").exists())
            self.assertTrue((base / "sce_sys" / "pic1.png").exists())
            self.assertTrue((base / "sce_sys" / "pic1.dds").exists())
            self.assertEqual(len(result["artwork_renamed"]), 2)

    def test_existing_pic0_kept_and_missing_dds_renamed_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, out = root / "base", root / "merged"
            (base / "sce_sys").mkdir(parents=True)
            (base / "eboot.bin").write_bytes(b"GAME")
            make_sfo(base / "sce_sys" / "param.sfo")
            (base / "sce_sys" / "pic0.png").write_bytes(b"KEEP PNG")
            (base / "sce_sys" / "pic1.png").write_bytes(b"OTHER PNG")
            (base / "sce_sys" / "pic1.dds").write_bytes(b"FALLBACK DDS")
            result = merge_ps4_folders(str(base), None, str(out))
            self.assertEqual((out / "sce_sys" / "pic0.png").read_bytes(), b"KEEP PNG")
            self.assertEqual((out / "sce_sys" / "pic1.png").read_bytes(), b"OTHER PNG")
            self.assertEqual((out / "sce_sys" / "pic0.dds").read_bytes(), b"FALLBACK DDS")
            self.assertFalse((out / "sce_sys" / "pic1.dds").exists())
            self.assertEqual(result["artwork_renamed"], ["pic1.dds -> pic0.dds"])

    def test_update_artwork_does_not_override_base_fallback_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, update, out = root / "base", root / "patch", root / "merged"
            for folder in (base, update):
                (folder / "sce_sys").mkdir(parents=True)
            (base / "eboot.bin").write_bytes(b"GAME")
            make_sfo(base / "sce_sys" / "param.sfo", app_ver="1.00")
            make_sfo(update / "sce_sys" / "param.sfo", app_ver="1.02", category="gp")
            (base / "sce_sys" / "pic1.png").write_bytes(b"BASE PNG")
            (base / "sce_sys" / "pic1.dds").write_bytes(b"BASE DDS")
            (update / "sce_sys" / "pic0.png").write_bytes(b"PATCH PNG")
            (update / "sce_sys" / "pic0.dds").write_bytes(b"PATCH DDS")
            result = merge_ps4_folders(str(base), str(update), str(out))
            self.assertEqual((out / "sce_sys" / "pic0.png").read_bytes(), b"BASE PNG")
            self.assertEqual((out / "sce_sys" / "pic0.dds").read_bytes(), b"BASE DDS")
            self.assertEqual((update / "sce_sys" / "pic0.png").read_bytes(), b"PATCH PNG")
            self.assertEqual(result["app_ver"], "1.02")
            self.assertEqual(len(result["artwork_renamed"]), 2)

    def test_missing_both_pic_images_leaves_missing_and_temp_move_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, out = root / "temp_extracted", root / "merged"
            (base / "sce_sys").mkdir(parents=True)
            (base / "eboot.bin").write_bytes(b"GAME")
            make_sfo(base / "sce_sys" / "param.sfo")
            result = merge_ps4_folders(str(base), None, str(out), move_base=True)
            self.assertFalse((out / "sce_sys" / "pic0.png").exists())
            self.assertFalse((out / "sce_sys" / "pic0.dds").exists())
            self.assertFalse(base.exists())
            self.assertEqual(result["artwork_renamed"], [])

    def test_title_edit_preserves_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"param.sfo"
            make_sfo(path)
            edit_sfo_title(str(path),"Blair Witch (TR)")
            fields=sfo_fields(str(path))
            self.assertEqual(fields["TITLE"],"Blair Witch (TR)")
            self.assertEqual(fields["TITLE_ID"],"CUSA12345")
            self.assertTrue(fields["CONTENT_ID"].startswith("UP0000-"))
    def test_base_only_without_update_preserves_source_and_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            merged = Path(tmp) / "merged"
            (base / "sce_sys").mkdir(parents=True)
            make_sfo(base / "sce_sys" / "param.sfo", title="My Game")
            (base / "eboot.bin").write_bytes(b"GAME")
            (base / "sce_sys" / "icon0.png").write_bytes(b"ORIGINAL")
            (base / "data.bin").write_bytes(b"DATA")
            samples = []
            result = merge_ps4_folders(
                str(base), None, str(merged), "My Game (TR)",
                progress=lambda *data: samples.append(data),
            )
            self.assertEqual(result["title_id"], "CUSA12345")
            self.assertEqual((base / "data.bin").read_bytes(), b"DATA")
            self.assertEqual(sfo_fields(str(base / "sce_sys" / "param.sfo"))["TITLE"], "My Game")
            self.assertEqual((merged / "data.bin").read_bytes(), b"DATA")
            self.assertEqual((merged / "sce_sys" / "icon0.png").read_bytes(), b"ORIGINAL")
            self.assertEqual(sfo_fields(str(merged / "sce_sys" / "param.sfo"))["TITLE"], "My Game (TR)")
            self.assertTrue(samples)
            self.assertEqual(samples[-1][0], samples[-1][1])

    def test_custom_game_title_applies_to_all_existing_locales_without_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, merged = root / "base", root / "merged"
            (base / "sce_sys").mkdir(parents=True)
            (base / "eboot.bin").write_bytes(b"GAME")
            source = base / "sce_sys" / "param.sfo"
            make_sfo(source, localized_titles={
                "TITLE_00": "Original Japanese",
                "TITLE_01": "Original English",
                "TITLE_20": "Original German",
                "TITLE_29": "Original Last",
            })
            original = source.read_bytes()
            merge_ps4_folders(str(base), None, str(merged), "How to Survive (TR)")
            result = sfo_fields(str(merged / "sce_sys" / "param.sfo"))
            for key in ("TITLE", "TITLE_00", "TITLE_01", "TITLE_20", "TITLE_29"):
                self.assertEqual(result[key], "How to Survive (TR)", key)
            self.assertNotIn("TITLE_02", result)
            self.assertEqual(result["TITLE_ID"], "CUSA12345")
            self.assertEqual(result["APP_VER"], "1.00")
            self.assertEqual(source.read_bytes(), original)

    def test_custom_game_title_applies_to_patch_locales_and_keeps_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, update, merged = root / "base", root / "update", root / "merged"
            for folder in (base, update):
                (folder / "sce_sys").mkdir(parents=True)
            (base / "eboot.bin").write_bytes(b"GAME")
            make_sfo(base / "sce_sys" / "param.sfo", localized_titles={"TITLE_00": "Base JP"})
            patch_sfo = update / "sce_sys" / "param.sfo"
            make_sfo(patch_sfo, category="gp", app_ver="1.02",
                     localized_titles={"TITLE_00": "Patch JP", "TITLE_01": "Patch EN",
                                       "TITLE_12": "Patch TR", "TITLE_29": "Patch Extra"})
            patch_original = patch_sfo.read_bytes()
            merge_ps4_folders(str(base), str(update), str(merged), "Survive v1.02 (TR)")
            result = sfo_fields(str(merged / "sce_sys" / "param.sfo"))
            for key in ("TITLE", "TITLE_00", "TITLE_01", "TITLE_12", "TITLE_29"):
                self.assertEqual(result[key], "Survive v1.02 (TR)", key)
            self.assertEqual(result["APP_VER"], "1.02")
            self.assertEqual(result["CATEGORY"], "gd")
            self.assertEqual(result["TITLE_ID"], "CUSA12345")
            self.assertEqual(patch_sfo.read_bytes(), patch_original)

    def test_base_only_moves_only_caller_owned_temp_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "staged_base"
            destination = Path(tmp) / "staged_merged"
            (base / "sce_sys").mkdir(parents=True)
            make_sfo(base / "sce_sys" / "param.sfo")
            (base / "eboot.bin").write_bytes(b"EXEC")
            merge_ps4_folders(str(base), "", str(destination), move_base=True)
            self.assertFalse(base.exists())
            self.assertEqual((destination / "eboot.bin").read_bytes(), b"EXEC")

    def test_update_keeps_base_game_artwork(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/"base";update=Path(tmp)/"update";merged=Path(tmp)/"merged"
            for p in (base,update):
                (p/"sce_sys").mkdir(parents=True)
                if p == base:
                    (p/"eboot.bin").write_text(p.name)
                make_sfo(p/"sce_sys"/"param.sfo",category="gp" if p==update else "gd",
                         app_ver="1.01" if p==update else "1.00",
                         title="Updated Game" if p==update else "Base Game")
            (base/"sce_sys"/"icon0.png").write_text("ORIGINAL")
            (update/"sce_sys"/"icon0.png").write_text("UPDATE")
            (update/"new_data.bin").write_text("PATCH")
            calls=[]
            merge_ps4_folders(str(base),str(update),str(merged),"Merged TR",progress=lambda *v:calls.append(v))
            self.assertTrue(calls)
            self.assertEqual(calls[-1][0],calls[-1][1])
            self.assertEqual(calls[-1][2],calls[-1][3])
            self.assertEqual((merged/"sce_sys"/"icon0.png").read_text(),"ORIGINAL")
            self.assertEqual((merged/"new_data.bin").read_text(),"PATCH")
            merged_fields = sfo_fields(str(merged/"sce_sys"/"param.sfo"))
            self.assertEqual(merged_fields["TITLE"], "Merged TR")
            self.assertEqual(merged_fields["APP_VER"], "1.01")
            self.assertEqual(merged_fields["CATEGORY"], "gd")
            self.assertEqual(sfo_fields(str(base/"sce_sys"/"param.sfo"))["APP_VER"], "1.00")
            self.assertEqual(sfo_fields(str(update/"sce_sys"/"param.sfo"))["CATEGORY"], "gp")
    def test_fast_merge_moves_only_extracted_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp); base=temp/"extracted_game"; update=temp/"extracted_patch"; dst=temp/"merged"
            for path in (base,update):
                (path/"sce_sys").mkdir(parents=True)
                make_sfo(path/"sce_sys"/"param.sfo",category="gp" if path==update else "gd",
                         app_ver="1.01" if path==update else "1.00")
            (base/"eboot.bin").write_bytes(b"GAME")
            (base/"sce_sys"/"icon0.png").write_bytes(b"BASE ICON")
            (base/"data.bin").write_bytes(b"ORIGINAL")
            (update/"data.bin").write_bytes(b"PATCHED")
            (update/"new.bin").write_bytes(b"NEW")
            (update/"sce_sys"/"icon0.png").write_bytes(b"PATCH ICON")
            values=[]
            result=merge_ps4_folders(str(base),str(update),str(dst),
                                     move_base=True,move_update=True,
                                     progress=lambda *v: values.append(v))
            self.assertEqual(result["title_id"],"CUSA12345")
            self.assertFalse(base.exists())
            self.assertEqual((dst/"data.bin").read_bytes(),b"PATCHED")
            self.assertEqual((dst/"new.bin").read_bytes(),b"NEW")
            self.assertEqual((dst/"sce_sys"/"icon0.png").read_bytes(),b"BASE ICON")
            self.assertEqual(sfo_fields(str(dst/"sce_sys"/"param.sfo"))["CATEGORY"],"gd")
            self.assertEqual(sfo_fields(str(dst/"sce_sys"/"param.sfo"))["APP_VER"],"1.01")
            self.assertEqual(result["sfo_source"],"update")
            self.assertEqual(result["app_ver"],"1.01")
            self.assertTrue(values)
            self.assertEqual(values[-1][0:2],(values[-1][1],values[-1][1]))
            self.assertEqual(values[-1][2:4],(values[-1][3],values[-1][3]))

    def test_update_sfo_used_without_title_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            update = Path(tmp) / "update"
            merged = Path(tmp) / "merged"
            for p in (base, update):
                (p / "sce_sys").mkdir(parents=True)
            (base / "eboot.bin").write_bytes(b"EXECUTABLE")
            make_sfo(base / "sce_sys" / "param.sfo", title="Old Name",
                     category="gd", app_ver="1.00")
            make_sfo(update / "sce_sys" / "param.sfo", title="Updated Name",
                     category="gp", app_ver="1.05")
            result = merge_ps4_folders(str(base), str(update), str(merged))
            fields = sfo_fields(str(merged / "sce_sys" / "param.sfo"))
            self.assertEqual(fields["TITLE"], "Updated Name")
            self.assertEqual(fields["APP_VER"], "1.05")
            self.assertEqual(fields["CATEGORY"], "gd")
            self.assertEqual(result["sfo_source"], "update")

    def test_no_update_sfo_preserves_base_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            merged = Path(tmp) / "merged"
            (base / "sce_sys").mkdir(parents=True)
            (base / "eboot.bin").write_bytes(b"EXECUTABLE")
            make_sfo(base / "sce_sys" / "param.sfo",
                     category="gd", app_ver="1.00")
            result = merge_ps4_folders(str(base), None, str(merged))
            fields = sfo_fields(str(merged / "sce_sys" / "param.sfo"))
            self.assertEqual(fields["APP_VER"], "1.00")
            self.assertEqual(fields["CATEGORY"], "gd")
            self.assertEqual(result["sfo_source"], "base")

    def test_mismatched_patch_does_not_move_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp); base=temp/"base"; update=temp/"patch"; dst=temp/"merged"
            for path in (base,update):
                (path/"sce_sys").mkdir(parents=True)
            (base/"eboot.bin").touch()
            make_sfo(base/"sce_sys"/"param.sfo",title_id="CUSA12345")
            make_sfo(update/"sce_sys"/"param.sfo",title_id="CUSA99999",category="gp")
            with self.assertRaises(ValueError):
                merge_ps4_folders(str(base),str(update),str(dst),
                                  move_base=True,move_update=True)
            self.assertTrue(base.exists())
            self.assertTrue(update.exists())
            self.assertFalse(dst.exists())

if __name__=="__main__":unittest.main()
