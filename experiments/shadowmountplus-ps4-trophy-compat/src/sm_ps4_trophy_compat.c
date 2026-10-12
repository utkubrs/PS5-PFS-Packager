#include "sm_ps4_trophy_compat.h"

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

/* Deliberately does not depend on PS5 SDK headers: host unit-testable. */
#define SM_PS4_PATH_CAP 2048

static int ps4_title_id(const char *id) {
  if (!id || strlen(id) != 9 || strncmp(id, "CUSA", 4) != 0)
    return 0;
  for (int i = 4; i < 9; ++i)
    if (!isdigit((unsigned char)id[i]))
      return 0;
  return 1;
}

static int make_path(char out[SM_PS4_PATH_CAP], const char *root,
                     const char *leaf) {
  if (!root || !leaf)
    return -1;
  int n = snprintf(out, SM_PS4_PATH_CAP, "%s/%s", root, leaf);
  return n < 0 || n >= SM_PS4_PATH_CAP ? -1 : 0;
}

static int regular_file(const char *path) {
  struct stat info;
  if (lstat(path, &info) != 0)
    return errno == ENOENT ? 0 : -1;
  return S_ISREG(info.st_mode) ? 1 : -1; /* no symlink traversal */
}

static int make_safe_directory(const char *path) {
  struct stat info;
  if (lstat(path, &info) == 0)
    return S_ISDIR(info.st_mode) ? 0 : -1;
  if (errno != ENOENT)
    return -1;
  if (mkdir(path, 0755) != 0)
    return -1;
  return 0;
}

static int stage_one(const char *source_root, const char *target_root,
                     const char *relative, sm_ps4_trophy_stage_result_t *r) {
  char src[SM_PS4_PATH_CAP];
  char dst[SM_PS4_PATH_CAP];
  if (make_path(src, source_root, relative) != 0 ||
      make_path(dst, target_root, relative) != 0)
    return -1;
  int exists = regular_file(src);
  if (exists < 0)
    return -1;
  if (!exists) {
    ++r->absent;
    return 0;
  }
  exists = regular_file(dst);
  if (exists < 0)
    return -1;
  if (exists) {
    ++r->preserved; /* protect previously registered trophy metadata */
    return 0;
  }
  int in = open(src, O_RDONLY | O_NOFOLLOW);
  if (in < 0)
    return -1;
  int out = open(dst, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0644);
  if (out < 0) {
    close(in);
    if (errno == EEXIST && regular_file(dst) == 1) {
      ++r->preserved;
      return 0;
    }
    return -1;
  }
  int status = 0;
  char buffer[32768];
  for (;;) {
    ssize_t n = read(in, buffer, sizeof(buffer));
    if (n == 0)
      break;
    if (n < 0) {
      if (errno == EINTR)
        continue;
      status = -1;
      break;
    }
    for (ssize_t off = 0; off < n;) {
      ssize_t written = write(out, buffer + off, (size_t)(n - off));
      if (written < 0 && errno == EINTR)
        continue;
      if (written <= 0) {
        status = -1;
        break;
      }
      off += written;
    }
    if (status != 0)
      break;
  }
  if (close(out) != 0)
    status = -1;
  if (close(in) != 0)
    status = -1;
  if (status != 0) {
    unlink(dst); /* only remove the file we exclusively created */
    return -1;
  }
  ++r->copied;
  return 0;
}

int sm_ps4_trophy_stage(const char *title_id, const char *source_sce_sys,
                        const char *destination,
                        sm_ps4_trophy_stage_result_t *result) {
  if (!source_sce_sys || !destination || !result)
    return -1;
  memset(result, 0, sizeof(*result));
  if (!ps4_title_id(title_id))
    return 0;
  char sfo[SM_PS4_PATH_CAP];
  if (make_path(sfo, source_sce_sys, "param.sfo") != 0)
    return -1;
  int sfo_exists = regular_file(sfo);
  if (sfo_exists < 0)
    return -1;
  if (!sfo_exists)
    return 0; /* never touch PS5 titles / ambiguous source trees */
  result->is_ps4 = true;
  if (make_safe_directory(destination) != 0)
    return -1;

  static const char *const root_metadata[] = {
      "param.sfo", "npbind.dat", "nptitle.dat"};
  for (unsigned i = 0; i < sizeof(root_metadata) / sizeof(root_metadata[0]); ++i)
    if (stage_one(source_sce_sys, destination, root_metadata[i], result) != 0)
      return -1;

  char src_trophy[SM_PS4_PATH_CAP];
  char dst_trophy[SM_PS4_PATH_CAP];
  if (make_path(src_trophy, source_sce_sys, "trophy") != 0 ||
      make_path(dst_trophy, destination, "trophy") != 0)
    return -1;
  struct stat st;
  if (lstat(src_trophy, &st) == 0) {
    if (!S_ISDIR(st.st_mode) || make_safe_directory(dst_trophy) != 0)
      return -1;
    /* Conservatively stage only the standard known PS4 trophy archive. */
    if (stage_one(source_sce_sys, destination, "trophy/trophy00.trp", result) != 0)
      return -1;
  } else if (errno != ENOENT) {
    return -1;
  }
  return 0;
}
