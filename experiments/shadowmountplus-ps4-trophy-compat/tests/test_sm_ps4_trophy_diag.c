#define _GNU_SOURCE
#include "sm_ps4_trophy_diag.h"
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sqlite3.h>
#include <unistd.h>

static char captured[262144];
static size_t used=0;
void log_debug(const char *fmt, ...) {
  assert(used < sizeof(captured));
  va_list ap;
  va_start(ap,fmt);
  int n=vsnprintf(captured+used,sizeof(captured)-used,fmt,ap);
  va_end(ap);
  assert(n>=0 && (size_t)n+2 < sizeof(captured)-used);
  used+=(size_t)n;
  captured[used++]='\n';
  captured[used]='\0';
}
static void sql(sqlite3 *db,const char *script) {
  char *err=NULL;
  int rc=sqlite3_exec(db,script,NULL,NULL,&err);
  if(rc!=SQLITE_OK){fprintf(stderr,"sqlite: %s\n",err?err:"unknown");}
  assert(rc==SQLITE_OK);
  sqlite3_free(err);
}
static int contains(const char *s){return strstr(captured,s)!=NULL;}
int main(void) {
  char path[]="/tmp/smp-exp2-db.XXXXXX";
  int fd=mkstemp(path);
  assert(fd>=0);
  close(fd);
  sqlite3 *db=NULL;
  assert(sqlite3_open(path,&db)==SQLITE_OK);
  sql(db,"CREATE TABLE tbl_appinfo(titleId TEXT, appType INTEGER, status INTEGER);"
         "CREATE TABLE tbl_contentinfo(titleId TEXT, contentLocation INTEGER, category TEXT);"
         "INSERT INTO tbl_appinfo VALUES('CUSA12381',7,1);"
         "INSERT INTO tbl_contentinfo VALUES('CUSA12381',2,'gd');"
         "INSERT INTO tbl_contentinfo VALUES('CUSA55555',1,'gd');");
  assert(sqlite3_close(db)==SQLITE_OK);
  sm_ps4_trophy_diag_snapshot_db("PPSA12345","ignore",NULL,path);
  assert(used==0);
  sm_ps4_trophy_diag_snapshot_db("CUSA1238X","ignore",NULL,path);
  assert(used==0);
  sm_ps4_trophy_diag_snapshot_db("CUSA12381","test",NULL,path);
  assert(contains("phase=test title=CUSA12381 readonly=1"));
  assert(contains("table=tbl_contentinfo field=contentLocation value=2"));
  assert(contains("table=tbl_appinfo field=appType value=7"));
  assert(contains("table=tbl_contentinfo field=category value=gd"));
  used=0;captured[0]='\0';
  sm_ps4_trophy_diag_snapshot_db("CUSA55555","test",NULL,path);
  assert(contains("table=tbl_appinfo row=missing"));
  assert(contains("table=tbl_contentinfo field=contentLocation value=1"));
  unlink(path);
  puts("PASS EXP2: PS4-only read-only SQLite inspection, missing row, allowlisted fields");
  return 0;
}
