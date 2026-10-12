#define _GNU_SOURCE
#include "sm_ps4_trophy_compat.h"
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void file(const char *path, const char *data) {
  FILE *f = fopen(path,"wb");
  assert(f);
  assert(fwrite(data,1,strlen(data),f) == strlen(data));
  assert(fclose(f) == 0);
}
static void content(const char *path, const char *expected) {
  char b[100] = {0};
  FILE *f = fopen(path,"rb");
  assert(f);
  assert(fread(b,1,99,f) == strlen(expected));
  assert(fclose(f) == 0);
  assert(strcmp(b,expected) == 0);
}
int main(void) {
  char root[]="/tmp/smps4_XXXXXX";
  assert(mkdtemp(root));
  char src[256], dst[256], path[1024], linkpath[1024];
  snprintf(src,sizeof(src),"%s/sce_sys",root);
  snprintf(dst,sizeof(dst),"%s/appmeta",root);
  assert(mkdir(src,0700) == 0 && mkdir(dst,0700) == 0);
  sm_ps4_trophy_stage_result_t r;
  assert(sm_ps4_trophy_stage("PPSA00001",src,dst,&r) == 0 && !r.is_ps4);
  assert(sm_ps4_trophy_stage("CUSA12345",src,dst,&r) == 0 && !r.is_ps4);
  snprintf(path,sizeof(path),"%s/param.sfo",src); file(path,"SFO");
  snprintf(path,sizeof(path),"%s/npbind.dat",src); file(path,"BIND");
  snprintf(path,sizeof(path),"%s/nptitle.dat",src); file(path,"TITLE");
  snprintf(path,sizeof(path),"%s/trophy",src); assert(mkdir(path,0700)==0);
  snprintf(path,sizeof(path),"%s/trophy/trophy00.trp",src);file(path,"TRP");
  assert(sm_ps4_trophy_stage("CUSA12345",src,dst,&r)==0);
  assert(r.is_ps4 && r.copied==4 && r.preserved==0 && r.absent==0);
  snprintf(path,sizeof(path),"%s/npbind.dat",dst);content(path,"BIND");
  file(path,"EXISTING");
  assert(sm_ps4_trophy_stage("CUSA12345",src,dst,&r)==0);
  assert(r.preserved==4 && r.copied==0);
  content(path,"EXISTING");
  assert(sm_ps4_trophy_stage("CUSA1234X",src,dst,&r)==0 && !r.is_ps4);
  snprintf(linkpath,sizeof(linkpath),"%s/nptitle.dat",dst);
  assert(unlink(linkpath)==0);
  assert(symlink("/tmp/invalid-target",linkpath)==0);
  assert(sm_ps4_trophy_stage("CUSA12345",src,dst,&r)==-1);
  assert(unlink(linkpath)==0);
  snprintf(path,sizeof(path),"%s/nptitle.dat",src);
  assert(unlink(path)==0);
  assert(sm_ps4_trophy_stage("CUSA12345",src,dst,&r)==0 && r.absent==1);
  printf("PASS: PS4 metadata staging, PS5 isolation, preservation, symlink guard, missing optional metadata\n");
  return 0;
}
