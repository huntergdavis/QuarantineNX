// Optional local player for the user's original Duck AVI; no movie is bundled.
#if defined(USE_SDL) && defined(USE_FMV)
#include <SDL3/SDL.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
#include <dirent.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include "disc.h"
#ifdef __SWITCH__
#include <switch/arm/counter.h>
static Uint64 fmv_counter(void) { return armGetSystemTick(); }
static Uint64 fmv_counter_elapsed(Uint64 start) { return armTicksToNs(armGetSystemTick() - start); }
#else
#include <time.h>
static Uint64 fmv_counter(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (Uint64)t.tv_sec * 1000000000ULL + t.tv_nsec; }
static Uint64 fmv_counter_elapsed(Uint64 start) { return fmv_counter() - start; }
#endif

// Diagnostic files are created exclusively so earlier runs are never replaced.
static FILE *fmv_log_open(void) {
    char path[1200];
    for (int n = 0; n < 1000; n++) {
        int len = snprintf(path, sizeof path, "%sfmv-diagnostic-%03d.log", cfg_dir(), n);
        if (len < 0 || (size_t)len >= sizeof path) return NULL;
        int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (fd >= 0) {
            FILE *f = fdopen(fd, "w");
            if (!f) close(fd);
            return f;
        }
        if (errno != EEXIST) return NULL;
    }
    return NULL;
}
#define FMV_LOG(f, ...) do { if (f) { fprintf((f), __VA_ARGS__); fflush(f); } } while (0)

static int fmv_events(FILE *log) {
    SDL_Event e;
    while (SDL_PollEvent(&e)) {
        if (e.type == SDL_EVENT_QUIT) { FMV_LOG(log, "event=quit\n"); return 2; }
        if (e.type == SDL_EVENT_KEY_DOWN || e.type == SDL_EVENT_GAMEPAD_BUTTON_DOWN ||
            e.type == SDL_EVENT_MOUSE_BUTTON_DOWN) {
            FMV_LOG(log, "event=skip type=%u button=%d\n", (unsigned)e.type,
                    e.type == SDL_EVENT_GAMEPAD_BUTTON_DOWN ? (int)e.gbutton.button : -1);
            return 1;
        }
    }
    return 0;
}

typedef struct {
    SDL_Renderer *renderer;
    SDL_Texture *texture;
    AVCodecContext *decoder;
    AVStream *video;
    AVFrame *frame;
    struct SwsContext *scale;
    Uint8 *pixels;
    Uint64 started, counter_started;
    int width, height, result, frames, decoded;
    int64_t last_pts_ns;
    FILE *log;
} movie;

// Receive all frames made available by the decoder. Return <0 on decode error,
// 0 on EAGAIN, 1 on EOF. A skip/quit is recorded separately in m->result.
static int receive_frames(movie *m, int *produced) {
    int rc;
    while ((rc = avcodec_receive_frame(m->decoder, m->frame)) == 0) {
        (*produced)++;
        m->decoded++;
        int64_t pts = m->frame->best_effort_timestamp;
        if (pts == AV_NOPTS_VALUE) { FMV_LOG(m->log, "video_error=missing_pts frame=%d\n", m->frames); m->result = 1; return -1; }
        int64_t origin = m->video->start_time == AV_NOPTS_VALUE ? 0 : m->video->start_time;
        int64_t ns = av_rescale_q(pts - origin, m->video->time_base, (AVRational){1, 1000000000});
        m->last_pts_ns = ns;
        Uint64 elapsed = SDL_GetTicksNS() - m->started;
        // A corrupt timestamp must not leave the user waiting indefinitely.
        bool sample = m->frames < 10 || m->frames % 15 == 0;
        if (sample)
            FMV_LOG(m->log, "decoded=%d presented=%d raw_pts=%lld pts_ns=%lld sdl_elapsed_ns=%llu counter_elapsed_ns=%llu\n",
                    m->decoded, m->frames, (long long)pts, (long long)ns, (unsigned long long)elapsed,
                    (unsigned long long)fmv_counter_elapsed(m->counter_started));
        if (ns < 0 || (Uint64)ns > elapsed + 5000000000ULL) { FMV_LOG(m->log, "video_error=invalid_pts\n"); m->result = 1; return -1; }
        while (!m->result && SDL_GetTicksNS() - m->started < (Uint64)ns) {
            m->result = fmv_events(m->log);
            if (!m->result) SDL_Delay(1);
        }
        if (m->result) return 0;
        m->scale = sws_getCachedContext(m->scale, m->width, m->height, m->frame->format,
                                       m->width, m->height, AV_PIX_FMT_BGRA, SWS_BILINEAR, NULL, NULL, NULL);
        if (!m->scale) { FMV_LOG(m->log, "video_error=scale_init\n"); m->result = 1; return -1; }
        uint8_t *dst[] = {m->pixels, NULL, NULL, NULL}; int stride[] = {m->width * 4, 0, 0, 0};
        if (sws_scale(m->scale, (const uint8_t *const *)m->frame->data, m->frame->linesize,
                      0, m->height, dst, stride) != m->height ||
            !SDL_UpdateTexture(m->texture, NULL, m->pixels, m->width * 4) ||
            !SDL_SetRenderDrawColor(m->renderer, 0, 0, 0, 255) || !SDL_RenderClear(m->renderer) ||
            !SDL_RenderTexture(m->renderer, m->texture, NULL, NULL)) {
            FMV_LOG(m->log, "video_error=render error=%s\n", SDL_GetError()); m->result = 1; return -1;
        }
        if (sample) FMV_LOG(m->log, "present_begin frame=%d sdl_elapsed_ns=%llu counter_elapsed_ns=%llu\n", m->frames,
                            (unsigned long long)(SDL_GetTicksNS() - m->started), (unsigned long long)fmv_counter_elapsed(m->counter_started));
        bool presented = SDL_RenderPresent(m->renderer);
        if (sample) FMV_LOG(m->log, "present_end frame=%d ok=%d sdl_elapsed_ns=%llu counter_elapsed_ns=%llu\n", m->frames, (int)presented,
                            (unsigned long long)(SDL_GetTicksNS() - m->started), (unsigned long long)fmv_counter_elapsed(m->counter_started));
        if (!presented) { FMV_LOG(m->log, "video_error=present error=%s\n", SDL_GetError()); m->result = 1; return -1; }
        m->frames++;
        av_frame_unref(m->frame);
    }
    if (rc != AVERROR_EOF && rc != AVERROR(EAGAIN)) FMV_LOG(m->log, "video_error=receive code=%d\n", rc);
    return rc == AVERROR_EOF ? 1 : rc == AVERROR(EAGAIN) ? 0 : -1;
}

static void send_video(movie *m, const AVPacket *packet) {
    int rc;
    while (!m->result && (rc = avcodec_send_packet(m->decoder, packet)) == AVERROR(EAGAIN)) {
        int produced = 0;
        if (receive_frames(m, &produced) < 0 || !produced) { FMV_LOG(m->log, "video_error=send_eagain_no_progress\n"); m->result = 1; return; }
    }
    if (m->result) return;
    if (rc < 0 && rc != AVERROR_EOF) { FMV_LOG(m->log, "video_error=send code=%d\n", rc); m->result = 1; return; }
    int produced = 0;
    if (receive_frames(m, &produced) < 0) m->result = 1;
}

// Return 2 on system quit, 0 after playback, skip or an unavailable/invalid AVI.
int fmv_intro(SDL_Renderer *renderer, const char *dir) {
    FILE *log = fmv_log_open();
    FMV_LOG(log, "fmv diagnostic v1\n");
    char path[1200] = "";
    DIR *d = opendir(dir);
    if (!d) { FMV_LOG(log, "error=data_dir_open\n"); if (log) fclose(log); return 0; }
    struct dirent *entry;
    while ((entry = readdir(d))) if (!strcasecmp(entry->d_name, "BQUAR1DK.AVI")) {
        int n = snprintf(path, sizeof path, "%s/%s", dir, entry->d_name);
        if (n < 0 || (size_t)n >= sizeof path) path[0] = 0;
        break;
    }
    closedir(d);
    if (!path[0]) { FMV_LOG(log, "error=avi_missing\n"); if (log) fclose(log); return 0; }
    // A libnx path begins with "sdmc:", which FFmpeg otherwise interprets as
    // a protocol name. Explicitly select its local-file protocol instead.
    char url[sizeof path + 6];
    int url_len = snprintf(url, sizeof url, "file:%s", path);
    if (url_len < 0 || (size_t)url_len >= sizeof url) {
        FMV_LOG(log, "error=path_too_long\n"); if (log) fclose(log); return 0;
    }
    FILE *probe = fopen(path, "rb");
    bool probe_opened = probe != NULL;
    int probe_errno = probe_opened ? 0 : errno;
    if (probe) fclose(probe);
    const char *plain_protocol = avio_find_protocol_name(path);
    const char *file_protocol = avio_find_protocol_name(url);
    FMV_LOG(log, "local_open=%s errno=%d protocol_plain=%s protocol_file=%s\n", probe_opened ? "ok" : "failed", probe_errno,
            plain_protocol ? plain_protocol : "unknown", file_protocol ? file_protocol : "unknown");

    AVFormatContext *format = NULL;
    AVPacket *packet = NULL;
    SDL_AudioStream *audio = NULL;
    SDL_Gamepad *pad = NULL;
    movie m = { .renderer = renderer, .log = log };
    int video = -1, audio_index = -1, audio_queued = 0;
    int audio_rate = 0, audio_samples = 0;
    SDL_RendererLogicalPresentation old_mode = SDL_LOGICAL_PRESENTATION_DISABLED;
    int old_w = 0, old_h = 0;
    SDL_GetRenderLogicalPresentation(renderer, &old_w, &old_h, &old_mode);
    bool logical_changed = false;
    int numpads = 0;
    SDL_JoystickID *ids = SDL_GetGamepads(&numpads);
    if (ids && numpads > 0) pad = SDL_OpenGamepad(ids[0]);
    SDL_free(ids);

    int rc = avformat_open_input(&format, url, NULL, NULL);
    if (rc < 0) {
        char error[AV_ERROR_MAX_STRING_SIZE]; av_strerror(rc, error, sizeof error);
        FMV_LOG(log, "error=demux_open code=%d detail=%s\n", rc, error);
        goto done;
    }
    rc = avformat_find_stream_info(format, NULL);
    if (rc < 0) {
        char error[AV_ERROR_MAX_STRING_SIZE]; av_strerror(rc, error, sizeof error);
        FMV_LOG(log, "error=stream_info code=%d detail=%s\n", rc, error);
        goto done;
    }
    video = av_find_best_stream(format, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    if (video < 0) { FMV_LOG(log, "error=no_video\n"); goto done; }
    m.video = format->streams[video];
    FMV_LOG(log, "video codec=%d timebase=%d/%d start=%lld\n", m.video->codecpar->codec_id, m.video->time_base.num, m.video->time_base.den, (long long)m.video->start_time);
    if (m.video->codecpar->codec_id != AV_CODEC_ID_TRUEMOTION1) { FMV_LOG(log, "error=unsupported_codec\n"); goto done; }
    const AVCodec *codec = avcodec_find_decoder(m.video->codecpar->codec_id);
    if (!codec || !(m.decoder = avcodec_alloc_context3(codec)) ||
        avcodec_parameters_to_context(m.decoder, m.video->codecpar) < 0 || avcodec_open2(m.decoder, codec, NULL) < 0) { FMV_LOG(log, "error=decoder_init\n"); goto done; }
    m.width = m.decoder->width; m.height = m.decoder->height;
    FMV_LOG(log, "dimensions=%dx%d\n", m.width, m.height);
    if (m.width <= 0 || m.height <= 0 || m.width > 1024 || m.height > 1024) { FMV_LOG(log, "error=dimensions\n"); goto done; }
    m.texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, m.width, m.height);
    m.pixels = SDL_malloc((size_t)m.width * m.height * 4);
    packet = av_packet_alloc(); m.frame = av_frame_alloc();
    if (!m.texture || !m.pixels || !packet || !m.frame) { FMV_LOG(log, "error=alloc_or_texture sdl=%s\n", SDL_GetError()); goto done; }
    SDL_SetRenderLogicalPresentation(renderer, m.width, m.height, SDL_LOGICAL_PRESENTATION_LETTERBOX);
    logical_changed = true;

    int ai = av_find_best_stream(format, AVMEDIA_TYPE_AUDIO, -1, -1, NULL, 0);
    if (ai >= 0) {
        AVCodecParameters *ap = format->streams[ai]->codecpar;
        if (ap->codec_id == AV_CODEC_ID_PCM_U8 && ap->sample_rate == 22050 && ap->ch_layout.nb_channels == 1 && SDL_InitSubSystem(SDL_INIT_AUDIO)) {
            SDL_AudioSpec spec = { SDL_AUDIO_U8, 1, 22050 };
            audio = SDL_OpenAudioDeviceStream(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec, NULL, NULL);
            if (audio && SDL_ResumeAudioStreamDevice(audio)) {
                SDL_AudioSpec output;
                if (SDL_GetAudioDeviceFormat(SDL_GetAudioStreamDevice(audio), &output, &audio_samples) && output.freq > 0 && audio_samples > 0) {
                    audio_rate = output.freq; audio_index = ai;
                }
            }
        }
    }

    m.counter_started = fmv_counter();
    m.started = SDL_GetTicksNS();
    FMV_LOG(log, "start ticks_ns=%llu audio_rate=%d audio_buffer=%d\n", (unsigned long long)m.started, audio_rate, audio_samples);
    int64_t audio_next = 0;
    int packets = 0, demux_rc = 0;
    while (!m.result && (demux_rc = av_read_frame(format, packet)) >= 0) {
        packets++;
        m.result = fmv_events(log);
        if (!m.result && packet->stream_index == audio_index) {
            AVStream *as = format->streams[audio_index];
            int64_t origin = as->start_time == AV_NOPTS_VALUE ? 0 : as->start_time;
            int64_t pts = packet->pts == AV_NOPTS_VALUE ? -1 : av_rescale_q(packet->pts - origin, as->time_base, (AVRational){1, 22050});
            int queued = SDL_GetAudioStreamQueued(audio);
            // This player accepts contiguous, timestamped mono PCM only. Do
            // not let unexpected interleaving or a stalled device buffer grow.
            if (pts != audio_next || packet->size <= 0 || packet->size > 22050 || queued < 0 ||
                queued + packet->size > 44100 || !SDL_PutAudioStreamData(audio, packet->data, packet->size)) {
                FMV_LOG(log, "audio_disabled pts=%lld expected=%lld size=%d queued=%d error=%s\n", (long long)pts, (long long)audio_next, packet->size, queued, SDL_GetError());
                SDL_DestroyAudioStream(audio); audio = NULL; audio_index = -1;
            } else { audio_next += packet->size; audio_queued = 1; }
        } else if (!m.result && packet->stream_index == video) send_video(&m, packet);
        av_packet_unref(packet);
    }
    if (!m.result && demux_rc == AVERROR_EOF) {
        FMV_LOG(log, "demux=eof\n");
        send_video(&m, NULL); // flush any delayed video frames
    } else if (!m.result) {
        FMV_LOG(log, "demux=error code=%d\n", demux_rc);
        m.result = 1;
    }
    if (!m.result && audio && audio_queued && SDL_FlushAudioStream(audio)) {
        // Queued/available cover SDL conversion, not hardware playback. After
        // they drain, allow two physical buffers plus margin. The bound avoids
        // hanging on a stalled device; actual hardware latency remains unproved.
        Uint64 deadline = SDL_GetTicksNS() + 4000000000ULL;
        int q, available;
        while (!m.result && SDL_GetTicksNS() < deadline) {
            q = SDL_GetAudioStreamQueued(audio); available = SDL_GetAudioStreamAvailable(audio);
            if (q < 0 || available < 0 || (!q && !available)) break;
            m.result = fmv_events(log); if (!m.result) SDL_Delay(5);
        }
        Uint64 delay = (Uint64)audio_samples * 2 * 1000000000ULL / (Uint64)audio_rate + 100000000ULL;
        Uint64 until = SDL_GetTicksNS() + delay;
        if (until > deadline) until = deadline;
        while (!m.result && SDL_GetTicksNS() < until) { m.result = fmv_events(log); if (!m.result) SDL_Delay(5); }
    }
    FMV_LOG(log, "finish decoded=%d presented=%d packets=%d last_pts_ns=%lld audio_samples=%lld result=%d sdl_elapsed_ns=%llu counter_elapsed_ns=%llu\n",
            m.decoded, m.frames, packets, (long long)m.last_pts_ns, (long long)audio_next, m.result,
            (unsigned long long)(SDL_GetTicksNS() - m.started), (unsigned long long)fmv_counter_elapsed(m.counter_started));
done:
    if (audio) SDL_DestroyAudioStream(audio);
    if (pad) SDL_CloseGamepad(pad);
    if (logical_changed) SDL_SetRenderLogicalPresentation(renderer, old_w, old_h, old_mode);
    SDL_DestroyTexture(m.texture); SDL_free(m.pixels); sws_freeContext(m.scale);
    av_frame_free(&m.frame); av_packet_free(&packet);
    avcodec_free_context(&m.decoder); avformat_close_input(&format);
    if (log) fclose(log);
    return m.result == 2 ? 2 : 0;
}
#endif
