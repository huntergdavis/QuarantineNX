# Third-party notices

QuarantineNX is derived from [Quarantine Recomp](https://github.com/ACR-GD/quarantine-recomp),
originally developed by Antoine Clerc-Renaud and upstream contributors, through
[huntergdavis/quarantine-recomp](https://github.com/huntergdavis/quarantine-recomp)
revision `4b785be`. The upstream repository did not declare a source license at
the time of this notice. This notice does not grant rights on its behalf.

The experimental Switch build uses [SDL](https://github.com/libsdl-org/SDL)
and the third-party [neomody77/sdl3-switch](https://github.com/neomody77/sdl3-switch)
homebrew backend. Neither dependency is vendored in full here. The backend's
README describes it as an AI-generated, modified SDL backend under the zlib
license; our `patches/sdl3-switch-audio-prime.patch` further modifies it and is
marked as a QuarantineNX modification. Retain the upstream notices when
building or redistributing those dependencies. The SDL notice follows:

Copyright (C) 1997-2026 Sam Lantinga <slouken@libsdl.org>

This software is provided 'as-is', without any express or implied
warranty.  In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.


The toolchain and libraries supplied by devkitPro, libnx, Mesa and other
build-time or linked dependencies have their own notices and licenses. Review
the relevant distribution requirements before distributing compiled artifacts.
Game names and content belong to their respective rights holders.
