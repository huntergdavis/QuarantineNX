#!/usr/bin/env python3
"""Exercise the patched SDL Switch queue functions with a host AUDOUT mock.

Usage: python3 tools/test_switch_audio_queue.py /path/to/patched/SDL
This checks queue ownership, not libnx or hardware timing.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit("pass the patched SDL source directory")
source = (Path(sys.argv[1]) / "src/audio/switch/SDL_switchaudio.c").read_text()
start = source.index("static bool SWITCHAUDIO_PlayDevice")
end = source.index("static void SWITCHAUDIO_CloseDevice", start)
pre = '#include <assert.h>\n#include <stdbool.h>\n#include <stdint.h>\n#include <string.h>\ntypedef uint64_t u64; typedef uint32_t u32; typedef unsigned char Uint8;\ntypedef struct AudioOutBuffer { void *buffer; u64 data_size; } AudioOutBuffer;\nstruct SDL_PrivateAudioData { AudioOutBuffer buffers[2]; bool queued[2]; };\ntypedef struct { struct SDL_PrivateAudioData *hidden; int buffer_size; } SDL_AudioDevice;\nstatic AudioOutBuffer *active[2], *done[3]; static int na,nd,fail_append;\nstatic int audoutAppendAudioOutBuffer(AudioOutBuffer *b) { if(fail_append) return 1; for(int i=0;i<na;i++) assert(active[i]!=b); assert(na<2); active[na++]=b; return 0; }\nstatic void finish(int i) { done[nd++]=active[i]; active[i]=active[--na]; }\nstatic int audoutGetReleasedAudioOutBuffer(AudioOutBuffer **b,u32 *count) { *count=nd ? 1 : 0; if(nd) { *b=done[0]; for(int i=1;i<nd;i++) done[i-1]=done[i]; nd--; } return 0; }\nstatic int audoutWaitPlayFinish(AudioOutBuffer **b,u32 *count,u64 timeout) { (void)timeout; if(!nd) finish(0); return audoutGetReleasedAudioOutBuffer(b,count); }\n#define NUM_AUDIO_BUFFERS 2\n#define R_FAILED(x) ((x)!=0)\n#define SDL_SetError(...) false\n#define SDL_memcpy memcpy\n#define SDL_memset memset\n'
post = '\nint main(void) { unsigned char mem[2][4]={{0}}, a[4]={1,2,3,4}; struct SDL_PrivateAudioData p={0}; SDL_AudioDevice d={&p,4}; p.buffers[0].buffer=mem[0]; p.buffers[1].buffer=mem[1]; assert(SWITCHAUDIO_PlayDevice(&d,a,4) && na==2); assert(mem[0][0]==0 && mem[1][0]==1); assert(SWITCHAUDIO_WaitDevice(&d) && na==1); assert(SWITCHAUDIO_PlayDevice(&d,a,4) && na==2); finish(1); finish(0); assert(SWITCHAUDIO_WaitDevice(&d) && na==0 && !p.queued[0] && !p.queued[1]); assert(SWITCHAUDIO_PlayDevice(&d,a,4) && na==2 && mem[0][0]==0); assert(SWITCHAUDIO_WaitDevice(&d)); fail_append=1; assert(!SWITCHAUDIO_PlayDevice(&d,a,4)); assert(na==1); AudioOutBuffer unknown={0}; assert(!SWITCHAUDIO_MarkReleased(&d,&unknown,1)); assert(!SWITCHAUDIO_MarkReleased(&d,&p.buffers[0],2)); return 0; }\n'
scratch = Path("build")
scratch.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="audio-test-", dir=scratch) as tmp:
    path = Path(tmp)
    (path / "test.c").write_text(pre + source[start:end] + post)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", str(path / "test.c"), "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], check=True)
print("Switch audio queue mock passed; hardware behavior untested")
