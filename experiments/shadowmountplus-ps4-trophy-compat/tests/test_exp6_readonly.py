#!/usr/bin/env python3
"""EXP6 host-test plus static audit: read-only file metadata, no trophy calls."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

text = Path(sys.argv[1]).read_text()
guard_start = text.index("static bool exp5_is_cusa(")
guard_end = text.index("static void exp5_mount_at(", guard_start)
guards = text[guard_start:guard_end]

start = text.index("typedef struct {", text.index("static void exp5_phase_snapshot("))
end = text.index("static int handle_launch_request(", start)
probe = text[start:end]

for phrase in (
    "sandbox-app0-sce-sys", "system-ex-app-sce-sys",
    "user-app-sce-sys", "user-appmeta", "system-priv-appmeta",
    "param.sfo", "npbind.dat", "nptitle.dat",
    "trophy/trophy00.trp", "S_ISREG(", "S_ISLNK(",
    "lstat(path, &st)", "mode=readonly",
    "snapshot=complete roots=", "if (!exp5_is_cusa(title_id))",
    "errno = saved_errno;"):
    assert phrase in probe, f"EXP6 probe missing {phrase}"

assert ('exp6_metadata_namespace_probe(effective_title_id);' in text)
assert text.count("exp6_metadata_namespace_probe(effective_title_id);") == 1

# Verify EXP6 cannot read raw metadata contents or alter the filesystem.
for call in (
    "open", "fopen", "read", "pread", "fread", "write", "pwrite",
    "unlink", "rename", "mkdir", "rmdir", "mount", "nmount",
    "unmount", "sqlite3_exec", "sqlite3_open", "sceNpTrophyRegisterContext",
    "sceLncUtilLaunchApp", "kernel_set_ucred_authid", "copy_file"):
    assert not re.search(r"\b" + call + r"\s*\(", probe), \
        f"Unsafe EXP6 call: {call}"

host_code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <sys/stat.h>
#include <errno.h>
#define MAX_PATH 1024
static void log_debug(const char *fmt, ...) { (void)fmt; }
''' + guards + probe + r'''
int main(void) {
    char buffer[64];
    assert(exp5_is_cusa("CUSA03772"));
    assert(exp5_is_cusa("CUSA08005"));
    assert(!exp5_is_cusa("PPSA08005"));
    assert(!exp5_is_cusa("CUSA0800X"));
    assert(!exp5_is_cusa("CUSA080050"));
    assert(!exp5_is_cusa(NULL));
    assert(exp5_join(buffer, sizeof(buffer), "/user/appmeta", "CUSA03772"));
    assert(strcmp(buffer, "/user/appmeta/CUSA03772") == 0);
    assert(!exp5_join(buffer, 8, "/user/appmeta", "CUSA03772"));
    exp6_metadata_namespace_probe("PPSA08005");  /* Should bail out */
    exp6_metadata_namespace_probe("CUSA03772"); /* Only lstat, no writes */
    puts("PASS EXP6: CUSA-only, safe path lengths, 5 read-only metadata roots");
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix="ps4-exp6-test-") as tmp:
    src = Path(tmp, "main.c")
    binpath = Path(tmp, "test")
    src.write_text(host_code)
    subprocess.run(
        ["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
         str(src), "-o", str(binpath)],
        check=True,
    )
    subprocess.run([str(binpath)], check=True)
