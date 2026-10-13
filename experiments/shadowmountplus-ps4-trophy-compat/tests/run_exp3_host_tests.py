#!/usr/bin/env python3
"""Host regression tests for isolated EXP3 file-copy helper."""
import pathlib
import subprocess
import sys
import tempfile

upstream = pathlib.Path(sys.argv[1])
content = upstream.read_text()
start = content.index("static int exp3_ps4_title_id(")
end = content.index("static void update_registered_title_snd0info", start)
snippet = content[start:end]
assert 'O_EXCL | O_NOFOLLOW' in snippet
assert 'exp3_%s.enable' in snippet
assert '64 * 1024 * 1024' in snippet
assert 'exp3_regular_file(marker) == 1' in snippet

prefix = r"""
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#define MAX_PATH 1024
#define APPMETA_BASE "/tmp/exp3-appmeta"
static int is_under_image_mount_base(const char *path) {
  return strncmp(path, "/mnt/shadowmnt/", 15) == 0;
}
static void log_debug(const char *fmt, ...) {(void)fmt;}
"""
suffix = r"""
static void write_all(const char *path, const char *data) {
  int fd=open(path,O_WRONLY|O_CREAT|O_TRUNC,0644);
  assert(fd>=0);
  assert(write(fd,data,strlen(data))==(ssize_t)strlen(data));
  assert(close(fd)==0);
}
static void read_check(const char *path, const char *expected) {
  char data[128]={0};
  int fd=open(path,O_RDONLY);
  assert(fd>=0);
  ssize_t n=read(fd,data,sizeof(data)-1);
  assert(n>=0);
  assert(close(fd)==0);
  assert(strcmp(data,expected)==0);
}
int main(void) {
  exp3_ps4_mirror_on_mount("PPSA03772", "/tmp", "/tmp");
  assert(exp3_ps4_title_id("CUSA03772"));
  assert(!exp3_ps4_title_id("PPSA03772"));
  assert(!exp3_ps4_title_id("CUSA0377X"));
  assert(!exp3_ps4_title_id("CUSA037720"));
  char base[]="/tmp/ps4-exp3-XXXXXX";
  assert(mkdtemp(base)!=NULL);
  char src[MAX_PATH],dst[MAX_PATH],name[MAX_PATH],target[MAX_PATH];
  snprintf(src,sizeof(src),"%s/src",base);
  snprintf(dst,sizeof(dst),"%s/dst",base);
  assert(exp3_secure_dir(src)==0);
  assert(exp3_secure_dir(dst)==0);
  assert(exp3_format_path(name,sizeof(name),src,"npbind.dat")==0);
  assert(exp3_copy_missing(src,dst,"npbind.dat")==0); /* absent source */
  write_all(name,"first");
  assert(exp3_copy_missing(src,dst,"npbind.dat")==1);
  assert(exp3_format_path(target,sizeof(target),dst,"npbind.dat")==0);
  read_check(target,"first");
  write_all(name,"second");
  assert(exp3_copy_missing(src,dst,"npbind.dat")==2);
  read_check(target,"first"); /* never overwrite */
  assert(unlink(target)==0);
  assert(symlink("/etc/passwd",target)==0);
  assert(exp3_copy_missing(src,dst,"npbind.dat")==-1); /* never follow */
  assert(unlink(target)==0);
  assert(unlink(name)==0);
  assert(symlink("/etc/passwd",name)==0);
  assert(exp3_copy_missing(src,dst,"npbind.dat")==-1);
  assert(unlink(name)==0);
  assert(rmdir(src)==0);
  assert(rmdir(dst)==0);
  assert(rmdir(base)==0);
  puts("PASS EXP3: CUSA guards, absent source, O_EXCL preservation, symlink safety");
  return 0;
}
"""

with tempfile.TemporaryDirectory(prefix="ps4-exp3-test-") as folder:
    source = pathlib.Path(folder, "exp3_test.c")
    binary = pathlib.Path(folder, "exp3_test")
    source.write_text(prefix + "\n" + snippet + "\n" + suffix)
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
