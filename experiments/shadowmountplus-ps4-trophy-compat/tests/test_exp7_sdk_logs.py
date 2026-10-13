#!/usr/bin/env python3
"""EXP7: host-test bounded, passive SDK log candidate parser."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

code=Path(sys.argv[1]).read_text()
start=code.index("static bool exp7_is_cusa(")
end=code.index("static void exp7_observe_sdk_line(",start)
pure=code[start:end]
probe=code[start:code.index("static void clear_tracked_game(",start)]
for phrase in (
    "source=shared-sdk-log", "attribution=unverified",
    "api-return=unknown", "direct-trophy-api-captured=0",
    "trophy-marker=1",
    "summary=complete matched=%u", "candidate-hex-count=%u"):
    assert phrase in probe, f"missing attribution or safety label: {phrase}"
assert "#define EXP7_MAX_REPORT_LINES 12u" in code
assert "exp7_observe_sdk_line(line);" in code
assert "exp7_log_summary();" in code
assert "MDBG_MONITOR_WINDOW_US (60ull * 1000000ull)" in code
assert "MDBG_FETCH_LOG_TEXT sceKernelDebugGetSdkLogText" in code

for forbidden in (
    "nmount", "mount", "unmount", "fopen", "open", "write",
    "unlink", "rename", "sqlite3_exec", "sceNpTrophyRegisterContext",
    "sceLncUtilLaunchApp", "kernel_set_ucred_authid", "ptrace",
    "sceKernelDebugGetPrivateLogText"):
    assert not re.search(r"\b"+forbidden+r"\s*\(", probe), \
        f"Unexpected side-effect or privileged call in EXP7: {forbidden}"

fixture = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
''' + pure + r'''
int main(void) {
    uint32_t value = 0;
    assert(exp7_is_cusa("CUSA03772"));
    assert(exp7_is_cusa("CUSA08005"));
    assert(!exp7_is_cusa("PPSA08005"));
    assert(!exp7_is_cusa("CUSA0800X"));
    assert(!exp7_is_cusa("CUSA080050"));
    assert(!exp7_is_cusa(NULL));
    assert(exp7_has_trophy_marker("[sceNpTrophy] Registration failed"));
    assert(exp7_has_trophy_marker("NP_TROPHY error"));
    assert(exp7_has_trophy_marker("TROPHY"));
    assert(!exp7_has_trophy_marker("[npdrm] license failed"));
    assert(!exp7_has_trophy_marker(NULL));
    assert(exp7_find_hex8("trophy err 0x80551600", &value));
    assert(value == 0x80551600u);
    assert(exp7_find_hex8("Trophy: 0X80551601;", &value));
    assert(value == 0x80551601u);
    assert(!exp7_find_hex8("Trophy: 0x1122334455667788", &value));
    assert(!exp7_find_hex8("Trophy: no numeric status", &value));
    assert(!exp7_find_hex8(NULL,&value));
    assert(!exp7_find_hex8("0x80551600",NULL));
    puts("PASS EXP7: narrow trophy markers, 8-digit candidates, no code injection");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="exp7-candidates-") as d:
    f=Path(d,"test.c");binary=Path(d,"test")
    f.write_text(fixture)
    subprocess.run(["cc","-std=gnu11","-Wall","-Wextra","-Werror",
                    str(f),"-o",str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
