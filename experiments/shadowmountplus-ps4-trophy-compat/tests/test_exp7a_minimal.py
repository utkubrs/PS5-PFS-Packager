#!/usr/bin/env python3
"""EXP7A: static no-write checks and host test of narrow code parser."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

code=Path(sys.argv[1]).read_text()
start=code.index("static int exp7a_hex(")
end=code.index("static void exp7a_observe(",start)
pure=code[start:end]
observer=code[start:code.index("static void process_log_line(",start)]
assert code.count("exp7a_observe(line);")==1
assert "sdk-marker=1" in observer
assert "attribution=unverified api-return=unknown" in observer
assert "g_exp7a_reported >= 8" in observer
assert 'strstr(line, "[PS4-TROPHY-")' in observer
assert "exp7a_observe(line);" in code
assert "EXP7_MAX_REPORT_LINES" not in code
assert "uint32_t exp7_matches" not in code
assert "void sm_mdbg_game_on_exec" in code
for call in ("fopen","open","read","pread","write","pwrite","nmount",
             "mount","unmount","unlink","rmdir","rename","sqlite3_exec",
             "sceNpTrophyRegisterContext","ptrace"):
    assert not re.search(r"\b"+call+r"\s*\(",observer),call
# No output string that is itself a trophy marker.
for literal in re.findall(r'log_debug\((.*?);',observer,flags=re.S):
    assert "trophy" not in literal.lower()

host=r"""
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
""" + pure + r"""
int main(void) {
    uint32_t v=0;
    assert(exp7a_code("trophy 0x80551600", &v));
    assert(v==0x80551600u);
    assert(exp7a_code("case 0X80551601 trailing", &v));
    assert(v==0x80551601u);
    assert(!exp7a_code("0x805516000", &v));
    assert(!exp7a_code("0x80551", &v));
    assert(!exp7a_code("no code", &v));
    assert(!exp7a_code(NULL, &v));
    assert(!exp7a_code("0x80551600", NULL));
    puts("EXP7A host checks OK");
    return 0;
}
"""
with tempfile.TemporaryDirectory(prefix="exp7a-check-") as folder:
    src=Path(folder,"test.c")
    output=Path(folder,"test")
    src.write_text(host)
    subprocess.run(["cc","-std=gnu11","-Wall","-Wextra","-Werror",
                    str(src),"-o",str(output)],check=True)
    subprocess.run([str(output)],check=True)
