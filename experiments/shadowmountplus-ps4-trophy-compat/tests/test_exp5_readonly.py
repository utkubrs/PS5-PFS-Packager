#!/usr/bin/env python3
"""EXP5 tests: compile harmless guards and verify diagnostic path is passive."""
import pathlib, re, subprocess, sys, tempfile
src=pathlib.Path(sys.argv[1]).read_text()
begin=src.index("static bool exp5_is_cusa(")
end=src.index("static void exp5_mount_at(",begin)
guards=src[begin:end]
probe_end=src.index("static int handle_launch_request(",begin)
probe=src[begin:probe_end]
for v in ("launch-request", "launch-prepared", "sandbox-ready"):
    assert src.count(f'exp5_phase_snapshot(') >= 4, "missing stages"
    assert f'"{v}"' in src, f"missing stage: {v}"
for v in ("native-pfsmnt-app0", "native-pfsmnt-nest", "system-ex-title",
          "sandbox-app0", "trophy2/npbind.dat", "uds/npbind.dat",
          "phase=%s snapshot=complete", "mode=readonly"):
    assert v in probe, f"missing read-only probe: {v}"
assert "if (!exp5_is_cusa(title_id))" in probe
assert "bool exact = strcmp(fs.f_mntonname, path) == 0;" in probe
assert "int saved_errno = errno;" in probe
assert "errno = saved_errno;" in probe
for forbidden in ("nmount", "mount", "unmount", "mkdir", "unlink", "rename",
                  "open", "fopen", "sqlite3_exec", "sqlite3_open",
                  "write", "pwrite", "kernel_write", "copy_file",
                  "sceAppInstUtilAppInstallTitleDir"):
    assert not re.search(r"\b"+forbidden+r"\s*\(",probe), \
        f"unsafe mutation in EXP5 probe: {forbidden}"

host= r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
''' + guards + r'''
int main(void) {
    char out[64];
    assert(exp5_is_cusa("CUSA08005"));
    assert(exp5_is_cusa("CUSA03772"));
    assert(!exp5_is_cusa("PPSA00001"));
    assert(!exp5_is_cusa("CUSA0800X"));
    assert(!exp5_is_cusa("CUSA080050"));
    assert(!exp5_is_cusa("CUSA0800"));
    assert(!exp5_is_cusa(NULL));
    assert(exp5_join(out,sizeof(out),"/system_ex/app","CUSA03772"));
    assert(strcmp(out,"/system_ex/app/CUSA03772")==0);
    assert(!exp5_join(out,5,"/system_ex/app","CUSA03772"));
    puts("PASS EXP5: CUSA-only, path guards, read-only phased calls");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="ps4-exp5-") as tmp:
    path=pathlib.Path(tmp,"test.c")
    exe=pathlib.Path(tmp,"test")
    path.write_text(host)
    subprocess.run(["cc","-std=gnu11","-Wall","-Wextra","-Werror",
                    str(path),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
