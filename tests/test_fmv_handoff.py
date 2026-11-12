#!/usr/bin/env python3
"""Exercise the actual startup handoff with a mock movie, clock and mixer."""
from pathlib import Path
import subprocess
import tempfile

source = Path('work/upstream/runtime/rt_sys.c').read_text()
start = source.index('static void fmv_before_still(const char *name, int mode) {')
end = source.index('\n#endif\nstatic void update_present_hz', start)
function = source[start:end]
prefix = r'''
#include <assert.h>
#include <setjmp.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
typedef struct {} SDL_Renderer;
static SDL_Renderer *ren;
static char data_dir[] = "game";
static int headless, calls, quit, shutdowns, snd, cd, snd_calls, cd_calls, fail_snd, fail_cd;
static double t_start=1, retrace_t0=2, flip_end_t=3, last_tick_t, last_present;
static int clock_calls;
static jmp_buf out;
static const char *base_of(const char *p) { const char *b=p; for (; *p; p++) if (*p=='/' || *p=='\\' || *p==':') b=p+1; return b; }
static double now_s(void) { return clock_calls++ ? 15 : 10; }
static int snd_movie_pause(void) { snd_calls++; if (fail_snd) return -1; snd=1; return 1; }
static int cd_movie_pause(void) { cd_calls++; if (fail_cd) return -1; cd=1; return 1; }
static void snd_movie_resume(int token, double elapsed) { assert(token==1 && elapsed==5); snd=0; snd_calls++; }
static void cd_movie_resume(int token, double elapsed) { assert(token==1 && elapsed==5); cd=0; cd_calls++; }
static int fmv_intro(SDL_Renderer *r, const char *dir) { (void)r; assert(!strcmp(dir,"game") && snd && cd); calls++; return quit ? 2 : 0; }
static void sys_shutdown(void) { shutdowns++; }
static void fake_exit(int status) { assert(status==0); longjmp(out,1); }
#define exit fake_exit
'''
suffix = r'''
int main(int argc, char **argv) {
    assert(argc == 2);
    int test = atoi(argv[1]);
    if (test == 1) {
        fmv_before_still("TITLE.FLI",0); fmv_before_still("DRAKESS4.IMG",1);
        headless=1; fmv_before_still("DRAKESS4.IMG",0); headless=0;
        assert(!calls && !clock_calls);
        fmv_before_still("C:\\DATA\\drakess4.img",0);
        assert(calls==1 && !snd && !cd && snd_calls==2 && cd_calls==2);
        assert(t_start==6 && retrace_t0==7 && flip_end_t==8 && last_tick_t==15 && last_present==15);
        fmv_before_still("DRAKESS4.IMG",0); assert(calls==1);
    } else if (test == 2) {
        quit=1;
        if (!setjmp(out)) { fmv_before_still("DRAKESS4.IMG",0); assert(0); }
        assert(calls==1 && shutdowns==1 && !snd && !cd);
    } else if (test == 3) {
        fail_snd=1; fmv_before_still("DRAKESS4.IMG",0); assert(!calls && !snd && !cd && !cd_calls);
    } else {
        fail_cd=1; fmv_before_still("DRAKESS4.IMG",0); assert(!calls && !snd && !cd && snd_calls==2);
    }
    return 0;
}
'''
Path('build').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='fmv-handoff-', dir='build') as tmp:
    tmp = Path(tmp)
    (tmp / 'test.c').write_text(prefix + function + suffix)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(tmp / 'test.c'), '-o', str(tmp / 'test')], check=True)
    for scenario in ('1', '2', '3', '4'):
        subprocess.run([str(tmp / 'test'), scenario], check=True)
print('FMV handoff matching, once-only, pause, clock, failure and quit paths passed')
