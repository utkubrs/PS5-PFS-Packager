#include "sm_ps4_trophy_diag.h"

#include <ctype.h>
#include <errno.h>
#include <sqlite3.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>

#include "sm_log.h"
#include "sm_paths.h"

#define PS4_DIAG_PATH_MAX 1024
#define PS4_DIAG_TEXT_MAX 80

static int valid_cusa(const char *id) {
  if (!id || strlen(id) != 9 || memcmp(id, "CUSA", 4) != 0)
    return 0;
  for (int i = 4; i < 9; ++i)
    if (!isdigit((unsigned char)id[i]))
      return 0;
  return 1;
}

static int allowed_column(const char *name) {
  static const char *const allow[] = {
      "contentLocation", "content_location", "category", "appType",
      "contentType", "status", "appStatus", "isVisible", "canRemove",
      "metaDataPath", "contentPath", "contentId", "appCategory"};
  if (!name)
    return 0;
  for (unsigned i = 0; i < sizeof(allow) / sizeof(allow[0]); ++i)
    if (strcasecmp(name, allow[i]) == 0)
      return 1;
  return 0;
}

static void sanitize(const unsigned char *value, char out[PS4_DIAG_TEXT_MAX]) {
  unsigned i = 0;
  if (value) {
    while (i < PS4_DIAG_TEXT_MAX - 1 && value[i]) {
      unsigned char c = value[i];
      out[i] = (isalnum(c) || c == '.' || c == '_' || c == '-' ||
                c == '/' || c == ':' || c == ' ')
                   ? (char)c
                   : '?';
      ++i;
    }
  }
  out[i] = '\0';
}

static const char *file_kind(const char *path) {
  struct stat st;
  if (lstat(path, &st) != 0)
    return errno == ENOENT ? "missing" : "unavailable";
  if (S_ISREG(st.st_mode))
    return "file";
  if (S_ISDIR(st.st_mode))
    return "directory";
  if (S_ISLNK(st.st_mode))
    return "symlink";
  return "other";
}

static void report_file(const char *phase, const char *root,
                        const char *leaf) {
  if (!root || !root[0])
    return;
  char path[PS4_DIAG_PATH_MAX];
  int len = snprintf(path, sizeof(path), "%s/%s", root, leaf);
  if (len < 0 || len >= (int)sizeof(path)) {
    log_debug("  [PS4-TROPHY-EXP2] phase=%s root=too-long name=%s",
              phase, leaf);
    return;
  }
  /* Names and file types only; never read or copy license/trophy bytes. */
  log_debug("  [PS4-TROPHY-EXP2] phase=%s root=%s name=%s kind=%s",
            phase, root, leaf, file_kind(path));
}

static void report_table(sqlite3 *db, const char *phase,
                         const char *title_id, const char *table) {
  const char *sql = strcmp(table, "tbl_appinfo") == 0
                        ? "SELECT * FROM tbl_appinfo WHERE titleId=?1 LIMIT 1;"
                        : "SELECT * FROM tbl_contentinfo WHERE titleId=?1 LIMIT 1;";
  sqlite3_stmt *stmt = NULL;
  int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
  if (rc != SQLITE_OK) {
    log_debug("  [PS4-TROPHY-EXP2] phase=%s table=%s query=unavailable rc=%d",
              phase, table, rc);
    return;
  }
  if (sqlite3_bind_text(stmt, 1, title_id, -1, SQLITE_TRANSIENT) != SQLITE_OK) {
    log_debug("  [PS4-TROPHY-EXP2] phase=%s table=%s bind=failed", phase,
              table);
    (void)sqlite3_finalize(stmt);
    return;
  }
  rc = sqlite3_step(stmt);
  if (rc == SQLITE_ROW) {
    int observed = 0;
    int columns = sqlite3_column_count(stmt);
    log_debug("  [PS4-TROPHY-EXP2] phase=%s table=%s row=found", phase, table);
    for (int i = 0; i < columns; ++i) {
      const char *col = sqlite3_column_name(stmt, i);
      if (!allowed_column(col))
        continue;
      int type = sqlite3_column_type(stmt, i);
      if (type != SQLITE_TEXT && type != SQLITE_INTEGER && type != SQLITE_FLOAT)
        continue;
      char value[PS4_DIAG_TEXT_MAX];
      sanitize(sqlite3_column_text(stmt, i), value);
      log_debug("  [PS4-TROPHY-EXP2] phase=%s table=%s field=%s value=%s",
                phase, table, col, value);
      ++observed;
    }
    if (!observed)
      log_debug("  [PS4-TROPHY-EXP2] phase=%s table=%s matched-fields=0",
                phase, table);
  } else if (rc == SQLITE_DONE) {
    log_debug("  [PS4-TROPHY-EXP2] phase=%s table=%s row=missing", phase,
              table);
  } else {
    log_debug("  [PS4-TROPHY-EXP2] phase=%s table=%s step=unavailable rc=%d",
              phase, table, rc);
  }
  (void)sqlite3_finalize(stmt);
}

void sm_ps4_trophy_diag_snapshot_db(const char *title_id, const char *phase,
                                    const char *source_sce_sys,
                                    const char *database_path) {
  if (!valid_cusa(title_id) || !phase || !database_path)
    return;

  log_debug("  [PS4-TROPHY-EXP2] phase=%s title=%s readonly=1", phase,
            title_id);

  char appmeta[PS4_DIAG_PATH_MAX];
  char usermeta[PS4_DIAG_PATH_MAX];
  char mounted[PS4_DIAG_PATH_MAX];
  char sandbox[PS4_DIAG_PATH_MAX];
  snprintf(appmeta, sizeof(appmeta), "/system_data/priv/appmeta/%s", title_id);
  snprintf(usermeta, sizeof(usermeta), "/user/appmeta/%s", title_id);
  snprintf(mounted, sizeof(mounted), "/system_ex/app/%s/sce_sys", title_id);
  snprintf(sandbox, sizeof(sandbox), "/mnt/sandbox/%s_000/app0/sce_sys", title_id);

  if (source_sce_sys) {
    report_file(phase, source_sce_sys, "param.sfo");
    report_file(phase, source_sce_sys, "npbind.dat");
    report_file(phase, source_sce_sys, "nptitle.dat");
    report_file(phase, source_sce_sys, "trophy/trophy00.trp");
  }
  report_file(phase, appmeta, "param.sfo");
  report_file(phase, appmeta, "npbind.dat");
  report_file(phase, appmeta, "nptitle.dat");
  report_file(phase, appmeta, "trophy/trophy00.trp");
  report_file(phase, usermeta, "param.sfo");
  report_file(phase, mounted, "npbind.dat");
  report_file(phase, mounted, "nptitle.dat");
  report_file(phase, sandbox, "npbind.dat");

  sqlite3 *db = NULL;
  int rc = sqlite3_open_v2(database_path, &db, SQLITE_OPEN_READONLY, NULL);
  if (rc != SQLITE_OK) {
    log_debug("  [PS4-TROPHY-EXP2] phase=%s appdb=unavailable rc=%d", phase,
              rc);
    if (db)
      sqlite3_close(db);
    return;
  }
  sqlite3_busy_timeout(db, 50);
  report_table(db, phase, title_id, "tbl_appinfo");
  report_table(db, phase, title_id, "tbl_contentinfo");
  (void)sqlite3_close(db);
}

void sm_ps4_trophy_diag_snapshot(const char *title_id, const char *phase,
                                 const char *source_sce_sys) {
  sm_ps4_trophy_diag_snapshot_db(title_id, phase, source_sce_sys, APP_DB_PATH);
}
