# WhaleGirl 3D stage 8: in-place model cache + promoted tray icon

This is the eighth 3D footing. It is still deliberately **not** a game-engine project:

- SDL3 creates a borderless, always-on-top, per-pixel transparent window.
- OpenGL 3.3 core draws a 2,076-triangle skinned low-poly whale girl with idle and walk clips.
- The model is generated from `tools/make_whale_girl_glb.py` and stays inside the in-house GLB loader: one mesh, one skin, one material, one texture atlas, one animation.
- Animation sampling is delegated to **ozz-animation**; the original in-house sampler is kept as a fallback and as an A/B baseline. No glTF importer, VRM runtime or blend/IK layer is pulled in.
- The face is a 3-frame atlas (open / blink / smile) sampled by a shader UV offset. Auto blink is driven by the shell; `E` toggles smile and `B` triggers a blink.
- The shell now has a **native Win32 tray icon, native popup menu and native modal settings page**. No Qt, no PySide6, no UI toolkit.
- Model switching is now a same-process, same-GL-context **model cache**: the first load of a path builds an `Impl`, and switching to a cached path only changes the active pointer. No window hide, no helper, no blank frame. Measured 4 ms for the first placeholder load and 0 ms for cache hits; private bytes stay at 98.0–98.2 MB across four switches. A same-exe `--relaunch` helper remains available via `WHALE3D_SWITCH=relaunch` as an A/B/fallback path.
- The window is borderless, always on top, non-focus-stealing, and draggable with the left mouse button. Right-click opens the tray menu instead of quitting immediately. Only pixels whose alpha is above 16 belong to the Win32 window region, so transparent corners and gaps pass clicks through to the window below.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File F:\WhaleGirlPet\3d\build.ps1
```

Toolchain is portable and lives outside PATH:

- `F:\WhaleGirlPet\.toolchains\w64devkit` — g++ / make / binutils / CMake
- `F:\WhaleGirlPet\.toolchains\SDL3\SDL3-3.4.20\x86_64-w64-mingw32` — SDL3 headers, import lib, DLL

The release build uses `-Os -s -ffunction-sections -fdata-sections -Wl,--gc-sections` to keep the shell small. `build.ps1` compiles `main.cpp`, `model.cpp` and `shell_ui.cpp`, links `-lSDL3`, the three static ozz libraries, `-lopengl32 -lgdi32 -luser32 -lshell32 -ladvapi32`, and deploys `SDL3.dll` next to the exe. If `third_party/ozz-build` is missing, build ozz once with the same w64devkit toolchain (`BUILD_SHARED_LIBS=OFF`, `ozz_build_tools/fbx/gltf/data/samples/howtos/tests` all `OFF`), then rerun the script. Putting the devkit `bin` directory on `PATH` is required because CMake's generated Makefiles call a bare `make`.

## Run

```powershell
F:\WhaleGirlPet\3d\whale3d.exe
```

`SDL3.dll` must sit next to `whale3d.exe`; the model is resolved relative to the exe (`assets/models/whale_girl.glb`), and the tray icon from `assets/ui/pet.ico`. If the primary model fails, the shell falls back to `placeholder.glb`. An explicit model path can be passed as the first argument.

Optional runtime switches:

```powershell
$env:WHALE3D_ANIMATOR = 'ozz'   # default; 'self' uses the in-house sampler
$env:WHALE3D_CLIP = 'idle'      # default; 'walk' plays the 2-second technical clip
$env:WHALE3D_FACE = 'auto'      # auto blink; or open / blink / smile for a fixed frame
```

While the window has focus, `W` cycles `idle → walk`, `O` toggles `ozz ↔ self`, `E` toggles the smile frame and `B` triggers a blink. The log line reports `fps`, `triangles`, `update_us`, `animator`, `clip` and `face` once per second.

## Tray, menu and settings

The tray icon is registered with `Shell_NotifyIconW` on the SDL window's Win32 `HWND`, obtained through `SDL_GetWindowProperties`. The window procedure is subclassed with `SetWindowLongPtrW` so the app receives tray callbacks without a second window class.

On Windows 11 the per-app visibility flag lives at `HKCU\Control Panel\NotifyIconSettings\<hash>\IsPromoted`. `ShellUi::promoteTrayIcon` enumerates that key, matches `ExecutablePath` against the running exe, and writes `IsPromoted=1` as a DWORD. Explorer applies it on its next start (restart Explorer or sign in); the current machine was restarted once and the crop of `(1611,0)-(1643,48)` now shows the blue-haired whale girl, not the overflow chevron.

- **Left-click the tray icon** toggles the pet window.
- **Right-click the tray icon** opens a native popup menu: `隐藏窗口 / 显示窗口`, `动画：切到 Walk / Idle`, an expression submenu (`自动表情 / Open / Blink / Smile`), `设置…`, `退出`.
- **Right-click the pet** opens the same native menu.
- **Settings** is a native modal Win32 window titled `鲸鱼娘 3D · 设置`. It uses only `COMBOBOX`, `BUTTON` and `STATIC` controls:
  - 模型: `鲸鱼娘 v1` (`whale_girl.glb`) or `方块占位` (`placeholder.glb`)
  - 动画: `idle` / `walk`
  - 表情: `auto` / `open` / `blink` / `smile`
  - 采样器: `ozz` / `self`
  - 状态行 shows the current combination and triangle/joint counts
  - `应用` / `关闭`
- The settings client area is 420×360; the outer window is about 426×389. The button row is at y=300, leaving room below for native DPI/font growth.

Two Win32 details are handled explicitly:

1. With `NOTIFYICON_VERSION_4`, the low word of the tray callback `lParam` carries the message; comparing the full `lParam` to `WM_LBUTTONUP` never matches. The code uses `LOWORD(lParam)`.
2. `TrackPopupMenu` uses `TPM_RETURNCMD | TPM_NONOTIFY`, so the selected command comes back as the return value, not as `WM_COMMAND`. The code calls `handleCommand(command)` on that return value.

`SetForegroundWindow` fails for a `SDL_WINDOW_NOT_FOCUSABLE` window, which leaves the menu stuck open after clicking outside. The shell temporarily clears `WS_EX_NOACTIVATE`, calls `SetWindowPos(...SWP_FRAMECHANGED)`, and wraps `SetForegroundWindow` in `AttachThreadInput(foregroundThread, currentThread, TRUE)`, then restores the exstyle. A `SDL_SetWindowFocusable` approach was tried and rejected because it crashed in `SDL_QuitFilesystem`.

## Alpha hit region and click-through

The window still paints a 420×620 transparent frame, but it no longer accepts clicks over the whole rectangle. Each frame `main.cpp` reads back the RGBA alpha of the rendered back buffer into a 420×620 mask (`hitMask`, about 1.04 MB), using `glReadBuffer(GL_BACK)` + `glReadPixels`. `ShellUi::setHitTest` receives the mask and converts client coordinates to mask coordinates; alpha > 16 counts as the character.

Two layers use that mask:

1. `WM_NCHITTEST` returns `HTCLIENT` over character pixels and `HTTRANSPARENT` elsewhere. This is a subclassed Win32 check, independent of SDL's hit test.
2. Because `HTTRANSPARENT` is guaranteed only for windows owned by the same thread, `ShellUi::updateWindowRegion` also builds a horizontal-run `GDI` region with `ExtCreateRegion` from the alpha mask and calls `SetWindowRgn` every 6 frames. Transparent pixels are outside the Win32 window region, so the OS routes clicks to the window below across process boundaries.

Measured:

- `SendMessageW(WM_NCHITTEST)` at character center returns `1` (`HTCLIENT`).
- At the top-left corner, bottom edge and the gap between legs it returns `-1` (`HTTRANSPARENT`).
- `WindowFromPoint` at a transparent corner no longer returns the pet HWND; in a clean topmost-underlay run it returned the test underlay's child `BUTTON`, while the character center still returned the pet `SDL_app` HWND. In an earlier package run with an existing Notepad over the test area it returned that Notepad's `RichEditD2DPT`, also a different process.
- OS-level cursor test (`SetCursorPos` + `mouse_event`, not `PostMessage`): a click at the transparent corner produced `BN_CLICKED id=1 count=1` on the underlay button; a drag starting at the character center moved the pet `(1200,300)-(1620,920)` → `(1235,325)-(1655,945)` and the underlay click count stayed 1. This closes the real-mouse sanity check; it is synthetic OS input rather than a physical hand.
- A drag that starts on the character still moves the window (`(1420,430)-(1840,1050)` → `(1460,450)-(1880,1070)`).
- Screenshot: `docs/_3d_hit_region.png`; log: `3d/region_accept.err.log`; real-mouse log: `3d/real_mouse_accept.log`.
- FPS with mask readback and region updates: 26.8 first sample, then 28.8–29.0.
- Private bytes with mask: 97,366,016 at 5 s, 96,624,640 at 10 s; RSS 70.7 MB. The in-place cache raises the steady baseline to about 98.0–98.2 MB, still below 100 MB.

## Model switching and memory

The first in-process `Model::load` path cleared all CPU state before parsing, but every switch deleted and recreated the shader program plus VBO/EBO/VAO/texture objects. The driver kept those allocations around: whale → placeholder → whale raised private bytes from 95,662,080 to **100,499,456**, then **102,600,704** at idle. That version is now historical.

The current path is a real in-place **model cache**: `Model` owns a vector of `Impl`s. The first load of a path builds one `Impl`; switching to a path already in the cache only changes the active `Impl*`. The same window, same Win32 `HWND` and same OpenGL context stay alive. There is no `SDL_HideWindow`, no `--relaunch` helper and no blank frame. Only a new path pays a load cost (measured 4 ms for placeholder; a cache hit is 0 ms).

`ShellUi::restartWithModel` and `--relaunch` are kept as an optional A/B/fallback path, selected only with `WHALE3D_SWITCH=relaunch`. The helper waits for the old process to exit, then starts the new pet; it is not used by the default Apply button. Its measured numbers remain: helper 2,064,384 B private, old+helper peak 97.3–97.5 MB, new pet ready 1.55–1.61 s.

The old process exit crash was not caused by the tray. It was a double free in `main.cpp`: `SDL_GetBasePath()` returns an internal pointer owned by `SDL_QuitFilesystem`, and the old code called `SDL_free` on it. GDB showed `SDL_Quit_REAL → SDL_QuitFilesystem → msvcrt!free` and `0xC0000374` (`STATUS_HEAP_CORRUPTION`). Removing that `SDL_free` made direct exit, tray-menu exit and settings-close-then-exit all return 0. The old expression package contained the same bug; it was inherited from the 2D→3D base, not introduced by the tray.

## Measured on this machine (2026-11-26)

Hardware: NVIDIA GTX 1060 6GB, driver 582.78, OpenGL 3.3.0.

| Item | Measurement |
| :--- | :--- |
| `whale3d.exe` | 1,302,528 bytes (1.24 MiB), with tray + settings + in-place model cache + alpha region |
| exe SHA256 | `53F6113B757276BA029C2EB16A829FF2D69FF1805D3216782B9965203B6D0478` |
| `SDL3.dll` | 5,385,103 bytes |
| `whale_girl.glb` | 350,332 bytes |
| Runtime payload (exe + DLL + GLB) | 7,037,963 bytes (6.71 MiB) |
| Relaunch helper private (optional A/B path) | 2,064,384 bytes |
| Tray promotion | `HKCU\Control Panel\NotifyIconSettings\674768749172540869\IsPromoted=1`; exact-rect crop shows the blue-haired icon |
| Pet window | 420×620, transparent, borderless, always-on-top, non-focusable |
| Settings client area | 420×360 (outer about 426×389) |
| FPS | 26.8 first sample, then 28.8–29.0 with alpha readback and region updates; 0.7–13 while the modal settings loop blocks the main loop, recovering after close |
| Triangles | 2,076 (whale girl), 216 (placeholder) |
| Animator update, ozz | 6.01–13.30 µs/frame in the restart runs; idle 6.68–8.93, walk 6.01–7.52 |
| Private bytes, in-place cache | 98,004,992 steady; 98,201,600 after placeholder and after whale back; unchanged over 4 switches |
| First in-place load | 4 ms for `placeholder.glb`; cache hit 0 ms |
| In-place identity | same PID 11748, no child process, same window; exit 0 |
| Relaunch handoff peak (optional) | 97,333,248 (whale → placeholder), 97,456,128 (placeholder → whale) |
| CPU | 1.7–3.1% of one core in 10 s windows; first window after launch measured 6.2% |
| Exit code | 0 for direct exit, tray-menu exit and settings-close-then-exit |

The exe grew by 41,984 bytes over the expression build (1,260,544 → 1,302,528). That covers the tray, two native menus, the settings dialog, subclassing, tray promotion, the in-place model cache, the optional relaunch helper and watchdog, the alpha hit-mask readback and the exit bug fix. The 100 MB limit holds in the default path: the cache settles at 98.0–98.2 MB with no growth across four switches; the optional helper peaks at 97.46 MB and starts the new pet only after the old process is gone.

## Runnable package

`F:\WhaleGirlPet\3d\whale3d-whale-girl-v1.zip` is about **2.6 MiB** (the exact ZIP hash and size are recorded in `docs/3d-transition.md`; the README inside the ZIP cannot reliably hash itself). It contains `whale3d.exe` (1,302,528 B, tray/settings/in-place-cache/alpha-region), `SDL3.dll`, `README.md`, `THIRD_PARTY_NOTICES.txt`, `assets/models/whale_girl.glb` (350,332 B), `assets/models/_whale_girl_atlas.png` (32,232 B), `assets/models/placeholder.glb` (38,288 B) and `assets/ui/pet.ico` (9,001 B). It is extracted to a temp folder and launched there; the extracted build logs `Tray icon ready`, loads `whale_girl.glb` with 2,076 triangles, reports `Hit mask ready: 420x620 center_alpha=255`, opens the settings page, switches to `placeholder.glb` in the same process via the model cache, and exits 0.

The previous expression-only package is preserved as `whale3d-whale-girl-v1-expression.zip` (2,695,131 B, exe `1,260,544 B`, SHA256 `534FA2B87C83D2ACFDB5B380B3954F9E07D2815168EE5B20845D11A76C161435`); do not mix its numbers with this build. The older `whale3d-base-step1.zip` (cube) and `whale3d-model-step2.zip` (blocky placeholder) are kept as stage archives.

## Known limitations

1. The model is deliberately stylized/chibi: a curved face decal on a low-poly head, approximated side/back hair, a single-piece fluke and no contact shadow. It is v1, not final art.
2. Facial expression is only open / blink / smile on a UV-offset atlas; there is no eye tracking, lip sync, morph target or facial rig.
3. The GLB itself has only one animation. `walk` is generated procedurally at startup; there is no animation blending, IK, root motion or animation event track yet.
4. Click-through now passed an OS-level cursor test: `SetCursorPos` + `mouse_event` at the transparent corner produced `BN_CLICKED id=1 count=1` on the underlay button; a center drag moved the pet and left the underlay click count unchanged. The earlier synthetic failure was the ctypes WndProc harness truncating LPARAM, not the window-region routing. A physical-hand click is still a user sanity check, not an automated one.
5. The default model switch is now a true in-place **model cache** in the same process and GL context: switch by active `Impl*`, no window hide, no helper, no blank frame. First placeholder load measured 4 ms and cache hits 0 ms; private bytes were 98,004,992 steady and 98,201,600 after four switches, same PID 11748 and no child process. The optional `--relaunch` helper remains for A/B/fallback (`WHALE3D_SWITCH=relaunch`): 2,064,384 B helper, old+helper peak 97.3–97.5 MB, new pet ready 1.55–1.61 s.
6. Windows 11 tray promotion is implemented by matching `ExecutablePath` under `HKCU\Control Panel\NotifyIconSettings` and writing `IsPromoted=1`. Explorer applies it on its next start; this machine was restarted once, and the exact `(1611,0)-(1643,48)` crop shows the blue-haired whale girl icon. A fresh install still needs one Explorer restart/sign-in before the flag takes effect.
7. No behavior state machine, audio, cloud/AI integration or PySide6 replacement yet. The existing `ai_profiles`, `_chat_cloud` and cloud API routes stay in the Python service and are not packaged into this core zip.
8. ozz is used only as a runtime sampling library. The glTF importer, `.ozz` file baking, blend/IK/root-motion layers and VRM extensions are not integrated.

## Not in this step

- ozz blend trees, IK, root motion and `.ozz` asset baking
- VRM loading and VRM expression / spring-bone support
- eye tracking, lip sync or a facial rig beyond the three atlas frames
- behavior/AI integration
- installer / package split
- automatic Explorer restart or first-run promotion notification (the registry flag is written, but Explorer must restart once)
