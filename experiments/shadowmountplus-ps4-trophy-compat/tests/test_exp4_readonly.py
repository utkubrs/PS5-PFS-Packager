#!/usr/bin/env python3
"""EXP4 read-only probe host test & static audit (before PS5 cross-build)."""
import pathlib
import re
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).read_text()
start = source.index("static bool exp4_valid_cusa(")
end = source.index("static bool dispatch_game_launch(", start)
probe = source[start:end]
checks = [
    "sm_mount_table_snapshot(&table)",
    "statfs(path, &fs)",
    "lstat(file, &st)",
    "read_mount_link(title_id, source, sizeof(source))",
    "stage=game-start",
    "snapshot=complete",
    "if (!exp4_valid_cusa(title_id))",
    "matches > printed",
]
for check in checks:
    assert check in probe, f"missing EXP4 guard or read-only probe: {check}"
assert "exp4_snapshot_on_game_start(title_id, pid, app_id);" in source
for func in ("nmount", "mount", "unmount", "mkdir", "unlink", "rmdir",
             "rename", "open", "fopen", "sqlite3_exec", "sqlite3_open",
             "write", "pwrite", "sceAppInstUtilAppInstallTitleDir",
             "copy_file"):
    assert not re.search(r"\b" + func + r"\s*\(", probe), \
        f"Unexpected write/mutation function in EXP4 snapshot: {func}"
assert not re.search(r"(?m)^\s*#include", probe)
assert "for (int i = 4; i < 9; ++i)" in probe
assert "if (printed >= 24)" in probe

only_guards = probe[:probe.index("static void exp4_stat_mount(")]
test = r"""
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#define MAX_PATH 1024
""" + only_guards + r"""
int main(void) {
    char path[MAX_PATH];
    assert(exp4_valid_cusa("CUSA03772"));
    assert(exp4_valid_cusa("CUSA08005"));
    assert(!exp4_valid_cusa("PPSA03772"));
    assert(!exp4_valid_cusa("CUSA0377X"));
    assert(!exp4_valid_cusa("CUSA037720"));
    assert(!exp4_valid_cusa("CUSA037"));
    assert(!exp4_valid_cusa(NULL));
    assert(exp4_path2(path, sizeof(path), "/user/appmeta", "CUSA03772"));
    assert(strcmp(path, "/user/appmeta/CUSA03772") == 0);
    char short_path[8];
    assert(!exp4_path2(short_path, sizeof(short_path),
                        "/user/appmeta", "CUSA03772"));
    puts("PASS EXP4 guards: CUSA only, path bounds; no mutations in probe");
    return 0;
}
"""
with tempfile.TemporaryDirectory(prefix="ps4-exp4-host-") as folder:
    src = pathlib.Path(folder, "main.c")
    exe = pathlib.Path(folder, "main")
    src.write_text(test)
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
