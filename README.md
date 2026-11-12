# QuarantineNX build recipe

Experimental Nintendo Switch homebrew build recipe for the static recompilation
of Quarantine (1994, DOS). This repository contains only build instructions,
hash-checked Switch transformations, host tests, an intro player, and an
original icon source. It does not contain the game, a compiled NRO, generated
guest code, extracted media, or the
upstream project's source history. You need your own matching 572,501-byte
`SKIPIT.EXE` and game disc image. Locally generated NROs contain translated
game code; their redistribution rights have not been established.

The owner reported that a local Switch build reached gameplay with working
controls and that the audio candidate sounded good. The owner reported that the
live-action intro played correctly in a local Switch test. A later startup
candidate moves the AVI after the title and before the
game's still-image montage, at the owner's request. This differs from the
original video-enabled DOS batch, which plays it before the game. The changed
placement and audio pause behavior have not yet been device-tested. This is not
a verified release or a guarantee of compatibility.

## Prepare

Requires Git, SHA-256 tools, ImageMagick 7, Docker, Python 3 and Capstone
(5.0.7 was used). Run `./prepare.sh`. It fetches exact revisions of
[huntergdavis/quarantine-recomp](https://github.com/huntergdavis/quarantine-recomp)
(`4b785beba28ada9105ac42d7f58431cb9b851fee`),
[SDL](https://github.com/libsdl-org/SDL) (`683181b47cfabd293e3ea409f838915b8297a4fd`)
and [neomody77/sdl3-switch](https://github.com/neomody77/sdl3-switch)
(`182e511214d7600e4bdab8606d7caf0ef744afd6`). It refuses to overwrite existing
checkouts. All downloaded source and generated files remain under ignored
`work/`. The transformation script checks input and output hashes and applies only the
Switch edits to the downloaded files. Review upstream terms and third-party
notices before use.

Build the experimental SDL library using a workspace-backed temporary directory:

```sh
mkdir -p work/SDL/tmp
docker run --rm -u "$(id -u):$(id -g)" -e TMPDIR=/src/tmp -v "$PWD/work/SDL:/src" -w /src \
  devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282 \
  cmake -S . -B build-switch -DCMAKE_TOOLCHAIN_FILE=/opt/devkitpro/cmake/Switch.cmake \
  -DSDL_SHARED=OFF -DSDL_STATIC=ON -DSDL_TESTS=OFF -DSDL_EXAMPLES=OFF
docker run --rm -u "$(id -u):$(id -g)" -e TMPDIR=/src/tmp -v "$PWD/work/SDL:/src" -w /src \
  devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282 \
  cmake --build build-switch -j4
```

Place your own matching `SKIPIT.EXE` at `work/upstream/extracted/cd/SKIPIT.EXE`.
Inside `work/upstream`, follow upstream instructions to install Capstone in a
virtual environment and run `make gen PYTHON=.venv/bin/python`. Then from the
recipe root:

```sh
mkdir -p work/upstream/build-switch-fmv/tmp
docker run --rm -u "$(id -u):$(id -g)" -e TMPDIR=/src/build-switch-fmv/tmp \
  -v "$PWD/work/upstream:/src" -v "$PWD/work/SDL:/sdl" -w /src \
  devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282 \
  make -f Makefile.switch -j4 DEVKITPRO=/opt/devkitpro SDL3_SWITCH=/sdl
```

The local NRO is `work/upstream/build-switch-fmv/QuarantineNX.nro`. A source-generated
guest has 54 unimplemented call lines for the tested executable, including
repeated addresses; reaching one is fatal and their reachability is unknown.

The default build links the image-provided FFmpeg package (metadata: GPL); see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before distributing binaries.
Pass `ENABLE_FMV=0` to build without the intro player and FFmpeg.

## Device test

Copy your local NRO to `sdmc:/switch/quarantinenx/` and launch it from the
homebrew menu. Put your own disc image at `sdmc:/switch/quarantinenx/game.nrg`,
`game.cue` (with its referenced BIN files), `game.iso` (no CD music), or an
extracted `game/` folder. The launcher cycles those paths on the Disc image item.
Configuration, installed image data and saves use the same directory; preserve
existing files and saves before testing. Place your own `BQUAR1DK.AVI` in the installed game data directory to play the
intro; absent or unsupported video falls through to the game. The player creates
numbered diagnostic logs in the app directory. The startup candidate pauses
the game audio streams while playing the movie and skips the movie if a stream
cannot be paused. Audio, startup behavior and
lifecycle still require broader device validation.

## Provenance

The upstream static recompilation was developed by Antoine Clerc-Renaud and
contributors; see [the original repository](https://github.com/ACR-GD/quarantine-recomp)
and its history. The upstream project has no declared source license. This
recipe does not grant rights to upstream code, game data or translated output.
The third-party SDL Switch backend is an AI-generated modification according to
its author and is not an official SDL or devkitPro backend. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Quarantine and its content
belong to their respective rights holders; this project is unaffiliated.
