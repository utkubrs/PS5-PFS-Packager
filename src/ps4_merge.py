"""PS4 base+update folder merger and conservative PARAM.SFO TITLE editor.

Never changes TITLE_ID or CONTENT_ID, never replaces base artwork with update artwork.
Works with extracted folders. PKG extraction is provided by ps4_inputs, separately.
"""
from __future__ import annotations
import os
import shutil
import struct
from pathlib import Path

ARTWORK={"icon0.png","icon0.dds","pic0.png","pic1.png","snd0.at9","changeinfo","icon0_00.png"}
PROTECTED={"title_id","content_id"}

def _parse_sfo(data: bytes):
    if len(data)<20 or data[:4]!=b"\0PSF":
        raise ValueError("Invalid param.sfo")
    _,version,key_start,data_start,count=struct.unpack_from("<4s4I",data,0)
    if count>4096 or data_start>len(data) or key_start>len(data):
        raise ValueError("Invalid SFO index")
    entries=[]
    for i in range(count):
        pos=20+i*16
        if pos+16>len(data):raise ValueError("Truncated SFO")
        keyoff,fmt,length,maximum,offset=struct.unpack_from("<HHIII",data,pos)
        begin=key_start+keyoff
        end=data.find(b"\0",begin)
        if end<0 or end>data_start:raise ValueError("Invalid SFO key")
        value_offset=data_start+offset
        if value_offset+maximum>len(data) or length>maximum:
            raise ValueError("Invalid SFO data")
        entries.append((data[begin:end].decode("ascii","replace"),fmt,length,maximum,value_offset,pos))
    return entries

def sfo_fields(path: str) -> dict:
    data=Path(path).read_bytes()
    out={}
    for key,fmt,length,maximum,offset,_ in _parse_sfo(data):
        raw=data[offset:offset+length]
        out[key]=raw.split(b"\0",1)[0].decode("utf-8","replace") if fmt==0x0204 else raw.hex()
    return out

def edit_sfo_title(path: str, title: str) -> None:
    if not title.strip():raise ValueError("TITLE cannot be empty")
    target=Path(path)
    original=target.read_bytes()
    data=bytearray(original)
    entry=next((e for e in _parse_sfo(original) if e[0]=="TITLE"),None)
    if entry is None:raise ValueError("TITLE field not found")
    key,fmt,length,maximum,offset,pos=entry
    if fmt!=0x0204:raise ValueError("TITLE is not UTF-8 text")
    encoded=title.encode("utf-8")+b"\0"
    if len(encoded)>maximum:
        raise ValueError(f"TITLE too long: {len(encoded)} bytes, maximum {maximum} bytes")
    data[offset:offset+maximum]=encoded.ljust(maximum,b"\0")
    struct.pack_into("<I",data,pos+4,len(encoded))
    new=bytes(data)
    before=sfo_fields_from_bytes(original)
    after=sfo_fields_from_bytes(new)
    for field in ("TITLE_ID","CONTENT_ID"):
        if before.get(field)!=after.get(field):raise ValueError("Identity field changed")
    tmp=target.with_suffix(target.suffix+".tmp")
    try:
        tmp.write_bytes(new)
        os.replace(tmp,target)
    finally:
        if tmp.exists():tmp.unlink()

def sfo_fields_from_bytes(data: bytes):
    return {key:(data[offset:offset+length].split(b"\0",1)[0].decode("utf-8","replace") if fmt==0x0204 else data[offset:offset+length].hex())
            for key,fmt,length,maximum,offset,_ in _parse_sfo(data)}

def merge_ps4_folders(base: str, update: str | None, destination: str, title: str="", progress=None, move_base: bool=False, move_update: bool=False) -> dict:
    """Copy base into a private destination; overlay an update only when supplied."""
    base,destination=map(lambda p:Path(p).resolve(),(base,destination))
    update=Path(update).resolve() if update else None
    if not base.is_dir() or not (base/"eboot.bin").is_file() or not (base/"sce_sys"/"param.sfo").is_file():
        raise ValueError("Base must contain eboot.bin and sce_sys/param.sfo")
    if update is not None and (not update.is_dir() or not (update/"sce_sys"/"param.sfo").is_file()):
        raise ValueError("Update must contain sce_sys/param.sfo (eboot.bin is optional)")
    if (update is not None and base==update) or destination.exists():raise ValueError("Destination exists or inputs coincide")
    if base in destination.parents or (update is not None and update in destination.parents):raise ValueError("Destination must not be within inputs")
    base_fields=sfo_fields(str(base/"sce_sys"/"param.sfo"))
    update_fields=sfo_fields(str(update/"sce_sys"/"param.sfo")) if update is not None else {}
    if base_fields.get("TITLE_ID") and update_fields.get("TITLE_ID") and base_fields["TITLE_ID"]!=update_fields["TITLE_ID"]:
        raise ValueError("PS4 TITLE_ID mismatch between base game and update")
    if update_fields.get("CATEGORY") not in ("gp","gd",None):
        raise ValueError("Update CATEGORY is not a recognized PS4 game patch")
    def update_file(rel):
        return not (rel.parts and rel.parts[0].lower() == "sce_sys"
                    and rel.name.lower() in ARTWORK.union({"param.sfo"}))

    # Count work before copying so the UI can show real byte-based progress.
    base_files = [p for p in base.rglob("*") if p.is_file()]
    update_files = ([p for p in update.rglob("*") if p.is_file()
                    and update_file(p.relative_to(update))] if update is not None else [])
    total = sum(p.stat().st_size for p in base_files + update_files)
    total_files = len(base_files) + len(update_files)
    copied = 0
    done_files = 0
    def copy_with_progress(src, dst):
        nonlocal copied, done_files
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        with open(src, "rb") as reader, open(dst, "wb") as writer:
            while True:
                chunk = reader.read(4 * 1024 * 1024)
                if not chunk: break
                writer.write(chunk)
                copied += len(chunk)
                if progress:
                    progress(copied, total, done_files, total_files)
        shutil.copystat(src, dst)
        done_files += 1
        if progress:
            progress(copied, total, done_files, total_files)
        return str(dst)
    try:
        if move_base:
            # Only caller-owned extracted TEMP folders may use this fast rename.
            base_bytes = sum(p.stat().st_size for p in base_files)
            os.rename(base, destination)
            copied += base_bytes
            done_files += len(base_files)
            if progress:
                progress(copied, total, done_files, total_files)
        else:
            shutil.copytree(base,destination,copy_function=copy_with_progress)
        for root,dirs,files in os.walk(update) if update is not None else []:
            rel=Path(root).relative_to(update)
            target_dir=destination/rel
            target_dir.mkdir(parents=True,exist_ok=True)
            for filename in files:
                relfile=rel/filename
                # Base game owns pictures, icons and base identities, including SFO.
                if rel.parts and rel.parts[0].lower()=="sce_sys":
                    if filename.lower() in ARTWORK or filename.lower()=="param.sfo":
                        continue
                source_file = Path(root) / filename
                target_file = target_dir / filename
                if move_update:
                    length = source_file.stat().st_size
                    os.replace(source_file, target_file)
                    copied += length
                    done_files += 1
                    if progress:
                        progress(copied, total, done_files, total_files)
                else:
                    copy_with_progress(source_file, target_file)
        if title:
            edit_sfo_title(str(destination/"sce_sys"/"param.sfo"),title)
        return {"folder":str(destination),"title_id":base_fields.get("TITLE_ID",""),"title":title or base_fields.get("TITLE","")}
    except BaseException:
        # Retain partial TEMP output when staged files have been moved; otherwise
        # deleting it would also erase the only remaining extracted copy.
        if destination.exists() and not (move_base or move_update):
            shutil.rmtree(destination, ignore_errors=True)
        raise
