import struct
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from ps4_merge import merge_ps4_folders, edit_sfo_title, sfo_fields

def make_sfo(path, title="Base Game", title_id="CUSA12345", category="gd"):
    values={"TITLE":title,"TITLE_ID":title_id,"CONTENT_ID":"UP0000-CUSA12345_00-EXAMPLE000000000","CATEGORY":category}
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
    def test_title_edit_preserves_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"param.sfo"
            make_sfo(path)
            edit_sfo_title(str(path),"Blair Witch (TR)")
            fields=sfo_fields(str(path))
            self.assertEqual(fields["TITLE"],"Blair Witch (TR)")
            self.assertEqual(fields["TITLE_ID"],"CUSA12345")
            self.assertTrue(fields["CONTENT_ID"].startswith("UP0000-"))
    def test_update_keeps_base_game_artwork(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/"base";update=Path(tmp)/"update";merged=Path(tmp)/"merged"
            for p in (base,update):
                (p/"sce_sys").mkdir(parents=True)
                if p == base:
                    (p/"eboot.bin").write_text(p.name)
                make_sfo(p/"sce_sys"/"param.sfo",category="gp" if p==update else "gd")
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
            self.assertEqual(sfo_fields(str(merged/"sce_sys"/"param.sfo"))["TITLE"],"Merged TR")
    def test_fast_merge_moves_only_extracted_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp); base=temp/"extracted_game"; update=temp/"extracted_patch"; dst=temp/"merged"
            for path in (base,update):
                (path/"sce_sys").mkdir(parents=True)
                make_sfo(path/"sce_sys"/"param.sfo",category="gp" if path==update else "gd")
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
            self.assertTrue(values)
            self.assertEqual(values[-1][0:2],(values[-1][1],values[-1][1]))
            self.assertEqual(values[-1][2:4],(values[-1][3],values[-1][3]))

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
