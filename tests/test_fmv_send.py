#!/usr/bin/env python3
"""Exercise the actual packet-send loop with synthetic decoder responses."""
from pathlib import Path
import subprocess
import tempfile

source = Path("runtime/rt_fmv.c").read_text()
start = source.index("static void send_video(")
end = source.index("// Return 2 on system quit", start)
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#define AVERROR(e) (-(e))
#define AVERROR_EOF (-9999)
typedef struct { int unused; } AVPacket;
typedef struct { int result; void *decoder; void *log; } movie;
#define FMV_LOG(...) ((void)0)
static int send_responses[4], send_count, receive_result, receive_produced, received;
static int avcodec_send_packet(void *decoder, const AVPacket *packet) {
    (void)decoder; (void)packet; return send_responses[send_count++];
}
static int receive_frames(movie *m, int *produced) {
    (void)m; received++; *produced = receive_produced; return receive_result;
}
'''
suffix = r'''
int main(void) {
    movie m = {0}; AVPacket p = {0};
    send_responses[0] = AVERROR(EAGAIN); send_responses[1] = 0; receive_produced = 1;
    send_video(&m, &p); assert(!m.result && send_count == 2 && received == 2);
    m.result = 0; send_count = received = 0; receive_produced = 0;
    send_video(&m, &p); assert(m.result == 1 && send_count == 1 && received == 1);
    m.result = 0; send_count = received = 0; send_responses[0] = -42;
    send_video(&m, &p); assert(m.result == 1 && received == 0);
    m.result = 0; send_count = received = 0; send_responses[0] = 0; receive_result = 1;
    send_video(&m, NULL); assert(!m.result && received == 1);
    return 0;
}
'''
Path("build").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="fmv-test-", dir="build") as tmp:
    test = Path(tmp) / "test.c"
    binary = Path(tmp) / "test"
    test.write_text(prefix + source[start:end] + suffix)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", str(test), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("FMV decoder EAGAIN, error and EOF paths passed with a mock")
