#!/usr/bin/env python3
"""Apply original QuarantineNX edits to exact upstream files, locally.

Each tuple is (character offset, characters removed, text inserted), measured
against the pinned UTF-8 input. Inputs and outputs are SHA-256 checked; edits
are applied backwards so offsets remain valid. This recipe carries the edits,
not upstream file bodies. Inspect the fetched source and resulting diff locally.
"""
from pathlib import Path
import hashlib
import sys

EDITS = {'runtime/disc.h': ('6171ae5cbda5440670751f657c898dea7022a0add38e3c5ea328d0025c2ebd69',
                    'ac3a2cf01d47095b39449c91c5f4101c448253addb223ad2d60ef0100bb2b41e',
                    [(934,
                      0,
                      '// Progress may return nonzero to cancel; an incomplete install has no '
                      'marker.\n'),
                     (969, 2, ''),
                     (972, 1, 'nt')]),
 'runtime/rt_config.c': ('3a4c084e4c90447c387ee9a1e9542c2272197a26b85eb3f7020406e5bda61c63',
                         '026d7380b1595491f665fc137fdc3dde6d56cb66cfd4e12a622daa4da905a94f',
                         [(819,
                           0,
                           '__SWITCH__\n'
                           '        else {\n'
                           '            mkdir("sdmc:/switch", 0755);\n'
                           '            snprintf(dir, sizeof dir, "sdmc:/switch/quarantinenx/");\n'
                           '        }\n'
                           '#elif defined('),
                          (826, 0, ')')]),
 'runtime/rt_core.c': ('44c7ddea16bd52e03213be99a5ef7e942ae8b22565bdaa4e879222a4f2519173',
                       'a4678b5bc54940855b3552f9c974f793c1bcdec511754cc276803b526ec904a4',
                       [(216, 1, ' !'),
                        (220, 1, 'ined('),
                        (227, 0, ') && !defined(__SWITCH__)'),
                        (1280, 1, ' !'),
                        (1284, 1, 'ined('),
                        (1291, 0, ') && !defined(__SWITCH__)')]),
 'runtime/rt_disc.c': ('4343c47bfd75c67ba9fce9dbb9c0513be265f5d076510693c1857896d8284ce6',
                       '4400f195529ced0403b01dca882e628a19634383d738546418a09665e3688ffd',
                       [(533,
                         0,
                         '#include <errno.h>\n'
                         '\n'
                         '#ifdef __SWITCH__\n'
                         '// libnx newlib has no pread. These descriptors are used only for '
                         'positioned\n'
                         '// reads here; serialize seek/read pairs so concurrent disc reads cannot '
                         'race.\n'
                         '#include <pthread.h>\n'
                         'static pthread_mutex_t disc_read_mutex = PTHREAD_MUTEX_INITIALIZER;\n'
                         'static ssize_t disc_pread(int fd, void *buf, size_t size, off_t offset) '
                         '{\n'
                         '    pthread_mutex_lock(&disc_read_mutex);\n'
                         '    ssize_t result = lseek(fd, offset, SEEK_SET) == (off_t)-1 ? -1 : '
                         'read(fd, buf, size);\n'
                         '    pthread_mutex_unlock(&disc_read_mutex);\n'
                         '    return result;\n'
                         '}\n'
                         '#define pread disc_pread\n'
                         '#endif\n'),
                        (15404, 2, ''),
                        (15407, 1, 'nt'),
                        (15474,
                         0,
                         'static int cancelled(struct inst *in) {\n'
                         '    if (in->progress && in->progress(in->done, in->total, in->u)) {\n'
                         '        fail(in->err, in->en, "Installation cancelled", 0);\n'
                         '        return 1;\n'
                         '    }\n'
                         '    return 0;\n'
                         '}\n'),
                        (15980,
                         0,
                         '        if ((done % (64 * 2048) == 0) && cancelled(in)) { fclose(f); '
                         'return -1; }\n'),
                        (16107, 3, 's'),
                        (16111, 0, 'ze_'),
                        (16112, 6, ''),
                        (16119, 2, 'n ='),
                        (16161, 0, ';\n        if (fwrite(sec, 1, n'),
                        (16165, 0, ' != n) { fclose(f)'),
                        (16166,
                         0,
                         ' fail(in->err, in->en, "Write failed for %s", p); return -1; }'),
                        (16280, 64, ''),
                        (16355, 0, 'cancelled(in) ? -1 : '),
                        (16396, 2, ''),
                        (16399, 1, 'nt'),
                        (16667, 0, '\n'),
                        (16668, 0, '   if ('),
                        (16677,
                         0,
                         ' && errno != ENOENT) return fail(err, en, "Can\'t remove %s", m)'),
                        (16742, 0, 'if ('),
                        (16765, 0, ') return fail(err, en, "Read error in the disc image", 0)'),
                        (16767, 0, '    if (cancelled(&in)) return -1;\n'),
                        (16810, 0, '    if (cancelled(&in)) return -1;\n'),
                        (16893, 0, ' int written ='),
                        (16959, 0, 'int closed = '),
                        (16970,
                         0,
                         '    if (written < 0 || closed) { unlink(m); return fail(err, en, "Can\'t '
                         'write %s", m); }\n')]),
 'runtime/rt_launcher.c': ('6dd43812bae2c682e2a162598c79b8b1038a973f64f5322d2d8323987a1304ad',
                           '4e542fbc1fcecc144bb2cfcce7972d3753482abad86ce9828c0458341b0aebd7',
                           [(3048, 0, '#ifndef __SWITCH__\n'),
                            (3791,
                             0,
                             '#else\n'
                             'static void use_path(const char *p);\n'
                             'static void choose_disc(void) {\n'
                             '    static const char *const paths[] = {\n'
                             '        "sdmc:/switch/quarantinenx/game.cue", '
                             '"sdmc:/switch/quarantinenx/game.nrg",\n'
                             '        "sdmc:/switch/quarantinenx/game.iso", '
                             '"sdmc:/switch/quarantinenx/game"\n'
                             '    };\n'
                             '    int next = 0;\n'
                             '    for (int i = 0; i < 4; i++)\n'
                             '        if (!strcmp(cfg.disc, paths[i])) { next = (i + 1) % 4; '
                             'break; }\n'
                             '    use_path(paths[next]);\n'
                             '}\n'
                             '#endif\n'),
                            (4395, 1, '\n#ifndef __SWITCH__'),
                            (4414, 0, ' ,'),
                            (4451, 0, '\n#endif\n                  '),
                            (4860, 0, '#ifndef __SWITCH__\n'),
                            (4923, 0, '#endif\n'),
                            (7226,
                             0,
                             '#ifdef __SWITCH__\n'
                             '        if (!status_ok) text_wrap_c(404, 1, DIM, "Select Disc image '
                             'to cycle game.cue, game.nrg, game.iso and game folder in '
                             'sdmc:/switch/quarantinenx/.", 72);\n'
                             '#else\n'),
                            (7421, 0, '#endif\n'),
                            (8451, 2, ''),
                            (8454, 1, 'nt'),
                            (8510, 43, ''),
                            (8575,
                             0,
                             '    SDL_Event e;\n'
                             '    if (SDL_PeepEvents(&e, 1, SDL_GETEVENT, SDL_EVENT_QUIT, '
                             'SDL_EVENT_QUIT) > 0) { quit = 1; return 1; }\n'
                             '    static Uint64 last_draw;\n'
                             '    Uint64 now = SDL_GetTicks();\n'
                             '    if (now - last_draw < 100 && done != total) return 0;\n'
                             '    last_draw = now;\n'),
                            (8882, 0, '    return 0;\n'),
                            (14865, 0, '            if (quit) break;\n')]),
 'runtime/rt_sys.c': ('48013a3c8ff0c30351c6246daccb80a2830ce4bfed53954951fca7354dd3a6c8',
                      '698dff1fbb3c180ace078718710efd03c525603500f466060698be3e11fa3faf',
                      [(510,
                        0,
                        '#endif\n'
                        '#if defined(USE_SDL) && defined(USE_FMV)\n'
                        'int fmv_intro(SDL_Renderer *renderer, const char *dir);\n'
                        'static void fmv_before_still(const char *name, int mode);\n'),
                       (17630,
                        0,
                        '#if defined(USE_SDL) && defined(USE_FMV)\n'
                        '        fmv_before_still(name, mode);\n'
                        '#endif\n'),
                       (32386,
                        0,
                        '#ifdef USE_FMV\n'
                        '// Deliberate Switch presentation order: title, AVI, still montage, guest '
                        'FLIC.\n'
                        '// The original QVIDAUD batch plays the AVI before starting the guest.\n'
                        'static void fmv_before_still(const char *name, int mode) {\n'
                        '    static int attempted;\n'
                        '    if (attempted || headless || mode || strcasecmp(base_of(name), '
                        '"DRAKESS4.IMG")) return;\n'
                        '    attempted = 1;  // Includes missing and skipped movies; never replay '
                        'on a later open.\n'
                        '    double start = now_s();\n'
                        '    int snd_token = snd_movie_pause();\n'
                        '    if (snd_token < 0) { fprintf(stderr, "sound: cannot pause for '
                        'intro\\n"); return; }\n'
                        '    int cd_token = cd_movie_pause();\n'
                        '    if (cd_token < 0) {\n'
                        '        fprintf(stderr, "CD audio: cannot pause for intro\\n");\n'
                        '        snd_movie_resume(snd_token, now_s() - start);\n'
                        '        return;\n'
                        '    }\n'
                        '    int result = fmv_intro(ren, data_dir);\n'
                        '    double end = now_s(), elapsed = end - start;\n'
                        '    cd_movie_resume(cd_token, elapsed);\n'
                        '    snd_movie_resume(snd_token, elapsed);\n'
                        '    // Exclude movie time from guest clocks and scripted input; do not '
                        'build a PIT backlog.\n'
                        '    t_start += elapsed;\n'
                        '    retrace_t0 += elapsed;\n'
                        '    if (flip_end_t) flip_end_t += elapsed;\n'
                        '    last_tick_t = last_present = end;\n'
                        '    if (result == 2) { sys_shutdown(); exit(0); }\n'
                        '}\n'
                        '#endif\n'),
                       (43572,
                        0,
                        '#ifdef __SWITCH__\n'
                        '    // Keep the controller-accessible launcher available even if saved '
                        'settings skip it.\n'
                        '    want_launcher = 1;\n'
                        '#endif\n')]),
 'runtime/rt_cd.c': ('81a3cc21c87ebf33a205afcb4e82c61637b056ae75983c6278e62da87e69c214',
                     '06c9885b89132539b9bfce6c3f3f6e16458b6a85f2e78b2cabf9d04e5a92d214',
                     [(1150, 0, 'static int have_audio;\n'),
                      (1177, 7, ''),
                      (1188,
                       0,
                       'cd_movie_pause(void) {\n'
                       '#ifdef USE_SDL\n'
                       '    if (stream_h && !SDL_AudioStreamDevicePaused(stream_h))\n'
                       '        return SDL_PauseAudioStreamDevice(stream_h) ? 1 : -1;\n'
                       '#endif\n'
                       '    return 0;\n'
                       '}\n'
                       'void cd_movie_resume(int token, double elapsed) {\n'
                       '    if (!'),
                      (1198, 0, ') headless_t0 += elapsed'),
                      (1200,
                       0,
                       '#ifdef USE_SDL\n'
                       '    if (token == 1 && !SDL_ResumeAudioStreamDevice(stream_h))\n'
                       '        fprintf(stderr, "CD audio: cannot resume after intro: %s\\n", '
                       'SDL_GetError());\n'
                       '#else\n'
                       '    (void)token;\n'
                       '#endif\n'
                       '}\n')]),
 'runtime/rt_snd.c': ('5a1c819823478a2e261b04444b73705aea616ab9d19d0d09c2bba920a8ca58e1',
                      '57c10d360b46d317fe692d8b474a54f47f89a3be19e7442772dcf3989ed9586a',
                      [(2078,
                        0,
                        '// Return 1 only if this call paused a running logical device, 0 if none '
                        'or\n'
                        '// already paused, and -1 on error. Never resume an independently paused '
                        'device.\n'
                        'int snd_movie_pause(void) {\n'
                        '#ifdef USE_SDL\n'
                        '    if (sfx_stream && !SDL_AudioStreamDevicePaused(sfx_stream))\n'
                        '        return SDL_PauseAudioStreamDevice(sfx_stream) ? 1 : -1;\n'
                        '#endif\n'
                        '    return 0;\n'
                        '}\n'
                        'void snd_movie_resume(int token, double elapsed) {\n'
                        '    if (!have_dev) hl_t0 += elapsed;\n'
                        '#ifdef USE_SDL\n'
                        '    if (token == 1 && !SDL_ResumeAudioStreamDevice(sfx_stream))\n'
                        '        fprintf(stderr, "sound: cannot resume after intro: %s\\n", '
                        'SDL_GetError());\n'
                        '#else\n'
                        '    (void)token;\n'
                        '#endif\n'
                        '}\n'
                        '\n')]),
 'runtime/sys.h': ('87cd8d9fba1c1fd94cb97818f354e7034babe507a2a6116d44d06e33c4679e6a',
                   'c50307cdc36d42fd3a8fb1e23f58655fc0055a473123b383782d4aaedbcfaef4',
                   [(1124,
                     0,
                     'int snd_movie_pause(void);\n'
                     'void snd_movie_resume(int token, double elapsed);\n'
                     'int cd_movie_pause(void);\n'
                     'void cd_movie_resume(int token, double elapsed);\n')])}

def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_switch.py /path/to/upstream")
    root = Path(sys.argv[1])
    # Validate every input and every result before touching any file.
    outputs = {}
    for name, (expected_input, expected_output, edits) in EDITS.items():
        path = root / name
        text = path.read_text(encoding="utf-8")
        if digest(text) != expected_input:
            raise SystemExit(f"unexpected input: {name}")
        for offset, count, inserted in reversed(edits):
            text = text[:offset] + inserted + text[offset + count:]
        if digest(text) != expected_output:
            raise SystemExit(f"unexpected output: {name}")
        outputs[path] = text
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    print("Applied and verified Switch edits to pinned upstream files")


if __name__ == "__main__":
    main()
