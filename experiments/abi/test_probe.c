#include "probe.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
int main(void) {
  uint64_t a=0,b=0,bad=123;
  assert(gc_probe_version()==1);
  assert(gc_probe_create(NAN,&bad)==GC_INVALID && bad==0);
  assert(gc_probe_create(1,NULL)==GC_INVALID);
  assert(gc_probe_create(12,&a)==GC_OK && a);
  assert(gc_probe_create(7,&b)==GC_OK && b && b!=a);
  uint64_t ids[]={a,b}; double out[]={-1,-1};
  assert(gc_probe_values(ids,2,out)==GC_OK && out[0]==12 && out[1]==7);
  assert(gc_probe_release(b)==GC_OK);
  out[0]=out[1]=-1;
  assert(gc_probe_values(ids,2,out)==GC_NOT_FOUND && out[0]==-1 && out[1]==-1);
  assert(gc_probe_release(b)==GC_NOT_FOUND);
  assert(gc_probe_values(NULL,1,out)==GC_INVALID);
  assert(gc_probe_values(NULL,0,NULL)==GC_OK);
  assert(gc_probe_release(a)==GC_OK);
  assert(gc_probe_create(3,&b)==GC_OK && b!=a && b!=ids[1]);
  assert(gc_probe_release(b)==GC_OK);
  for(int i=0;i<10000;++i){assert(gc_probe_create(i,&a)==GC_OK);assert(gc_probe_release(a)==GC_OK);}
  puts("C ABI checks passed; 10000 create/release cycles");
  return 0;
}
