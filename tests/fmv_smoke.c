// Host smoke test; point at your own extracted game directory, never commit media.
#include <SDL3/SDL.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libavformat/avformat.h>

int fmv_intro(SDL_Renderer *, const char *);
const char *cfg_dir(void) { return "build/fmv-logs/"; }
static int frames, bytes, changed;
static unsigned long long previous_hash;
static Uint64 first_audio, first_video;
static int max_queued;
static int invalid_audio;
static int fail_demux, video_packets;
int __real_av_read_frame(AVFormatContext *, AVPacket *);
int __wrap_av_read_frame(AVFormatContext *ctx, AVPacket *packet) {
    int rc = __real_av_read_frame(ctx, packet);
    if (!rc && fail_demux && packet->stream_index == 0 && ++video_packets > 3) {
        av_packet_unref(packet);
        return AVERROR(EIO);
    }
    if (!rc && invalid_audio && packet->stream_index == 1) {
        if (invalid_audio == 1) packet->pts = AV_NOPTS_VALUE;
        else packet->size = 22051; // rejected before use; do not read beyond packet data
        invalid_audio = 0;
    }
    return rc;
}
bool __real_SDL_RenderPresent(SDL_Renderer *);
bool __wrap_SDL_RenderPresent(SDL_Renderer *r) {
    if (!frames) first_video = SDL_GetTicks();
    SDL_Surface *surface = SDL_RenderReadPixels(r, NULL);
    assert(surface && SDL_LockSurface(surface));
    const unsigned char *p = surface->pixels;
    unsigned long long hash = 1469598103934665603ULL;
    for (int i = 0; i < surface->pitch * surface->h; i++) hash = (hash ^ p[i]) * 1099511628211ULL;
    if (frames && hash != previous_hash) changed++;
    previous_hash = hash;
    SDL_UnlockSurface(surface); SDL_DestroySurface(surface);
    frames++;
    return __real_SDL_RenderPresent(r);
}
bool __real_SDL_PutAudioStreamData(SDL_AudioStream *, const void *, int);
bool __wrap_SDL_PutAudioStreamData(SDL_AudioStream *s, const void *p, int n) {
    if (!bytes) first_audio = SDL_GetTicks();
    bytes += n;
    bool ok = __real_SDL_PutAudioStreamData(s, p, n);
    int queued = SDL_GetAudioStreamQueued(s);
    if (queued > max_queued) max_queued = queued;
    return ok;
}
static Uint32 SDLCALL trigger(void *arg, SDL_TimerID id, Uint32 interval) {
    (void)id; (void)interval;
    SDL_Event e = {0}; e.type = *(const Uint32 *)arg; SDL_PushEvent(&e); return 0;
}
int main(int argc, char **argv) {
    assert(argc == 3 || argc == 4); // valid media directory, empty/invalid directory, optional full run
    assert(SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_GAMEPAD));
    SDL_Window *w = SDL_CreateWindow("fmv smoke", 320, 184, 0); assert(w);
    SDL_Renderer *r = SDL_CreateRenderer(w, "software"); assert(r);
    assert(fmv_intro(r, argv[2]) == 0); // absent or invalid video: continue
    if (argc == 4 && !strcmp(argv[3], "demux")) {
        fail_demux = 1;
        assert(fmv_intro(r, argv[1]) == 0 && frames >= 2 && frames <= 3);
        printf("injected demux error after %d frames; returned to caller\n", frames);
        SDL_DestroyRenderer(r); SDL_DestroyWindow(w); SDL_Quit();
        return 0;
    }
    if (argc == 4 && !strcmp(argv[3], "full")) {
        Uint64 start = SDL_GetTicks();
        assert(fmv_intro(r, argv[1]) == 0);
        Uint64 elapsed = SDL_GetTicks() - start;
        assert(elapsed >= 2500 && elapsed < 8000 && frames >= 35 && changed && bytes > 50000);
        long long gap = (long long)first_video - (long long)first_audio;
        assert(gap > -250 && gap < 250 && max_queued <= 44100);
        printf("full playback %llu ms, %d frames (%d changes), %d PCM bytes, first A/V submit gap %lld ms, max source queue %d bytes\n", (unsigned long long)elapsed, frames, changed, bytes, gap, max_queued);
        SDL_DestroyRenderer(r); SDL_DestroyWindow(w); SDL_Quit();
        return 0;
    }
    if (argc == 4 && strcmp(argv[3], "early")) invalid_audio = !strcmp(argv[3], "badpts") ? 1 : 2;
    Uint32 key = SDL_EVENT_KEY_DOWN;
    bool early = argc == 4 && !strcmp(argv[3], "early");
    assert(SDL_AddTimer(early ? 220 : 1500, trigger, &key));
    Uint64 start = SDL_GetTicks();
    assert(fmv_intro(r, argv[1]) == 0); // skip
    Uint64 elapsed = SDL_GetTicks() - start;
    assert(elapsed >= (early ? 150 : 1000) && elapsed < 6000 && frames >= (early ? 2 : 5) && changed);
    assert(argc == 4 && !early ? bytes == 0 : bytes > 1000);
    printf("skip after %llu ms, %d presented frames (%d changes), %d PCM bytes submitted\n", (unsigned long long)elapsed, frames, changed, bytes);
    Uint32 quit = SDL_EVENT_QUIT;
    assert(SDL_AddTimer(250, trigger, &quit));
    assert(fmv_intro(r, argv[1]) == 2);
    SDL_DestroyRenderer(r); SDL_DestroyWindow(w); SDL_Quit();
    puts("quit propagated; missing/invalid input falls through");
    return 0;
}
