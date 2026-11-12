#!/usr/bin/env python3
"""Test real stream suspension wrappers with controlled SDL outcomes."""
from pathlib import Path
import subprocess
import tempfile

snd = Path('work/upstream/runtime/rt_snd.c').read_text().split('int snd_movie_pause(void) {', 1)[1].split('\nstatic FILE *dump;', 1)[0]
cd = Path('work/upstream/runtime/rt_cd.c').read_text().split('int cd_movie_pause(void) {', 1)[1].split('\nstatic uint64_t pcm_bytes', 1)[0]
prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define USE_SDL 1
typedef struct { int paused, fail, pauses, resumes; } SDL_AudioStream;
static SDL_AudioStream sound, disc, *sfx_stream=&sound, *stream_h=&disc;
static int have_dev=1, have_audio=1;
static double hl_t0=10, headless_t0=20;
static bool SDL_AudioStreamDevicePaused(SDL_AudioStream *s) { return s->paused; }
static bool SDL_PauseAudioStreamDevice(SDL_AudioStream *s) { s->pauses++; if(s->fail) return false; s->paused=1; return true; }
static bool SDL_ResumeAudioStreamDevice(SDL_AudioStream *s) { s->resumes++; s->paused=0; return true; }
static const char *SDL_GetError(void) { return "mock"; }
'''
suffix = r'''
int main(void) {
    int s=snd_movie_pause(), c=cd_movie_pause();
    assert(s==1 && c==1 && sound.paused && disc.paused);
    snd_movie_resume(s, 5); cd_movie_resume(c, 5);
    assert(!sound.paused && !disc.paused && sound.resumes==1 && disc.resumes==1);
    sound.paused=disc.paused=1;
    assert(snd_movie_pause()==0 && cd_movie_pause()==0);
    snd_movie_resume(0,5); cd_movie_resume(0,5);
    assert(sound.paused && disc.paused && sound.resumes==1 && disc.resumes==1);
    sound.paused=disc.paused=0; sound.fail=disc.fail=1;
    assert(snd_movie_pause()==-1 && cd_movie_pause()==-1);
    sfx_stream=stream_h=NULL; have_dev=have_audio=0;
    assert(snd_movie_pause()==0 && cd_movie_pause()==0);
    snd_movie_resume(0,5); cd_movie_resume(0,5);
    assert(hl_t0==15 && headless_t0==25);
}
'''
Path('build').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='fmv-audio-', dir='build') as tmp:
    tmp=Path(tmp)
    (tmp/'test.c').write_text(prefix+'int snd_movie_pause(void) {'+snd+'\nint cd_movie_pause(void) {'+cd+suffix)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(tmp/'test.c'),'-o',str(tmp/'test')],check=True)
    subprocess.run([str(tmp/'test')],check=True)
print('FMV audio pause/resume, pre-paused, failure and no-device paths passed')
