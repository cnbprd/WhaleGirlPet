# WhaleGirl 3D stage 10: VRM body + spring bones + emotion bus

This is the ninth 3D footing. It keeps the deliberately small SDL3/OpenGL shell and adds the first **body layer**:

- SDL3 creates a borderless, always-on-top, per-pixel transparent window.
- OpenGL 3.3 core draws a 2,076-triangle skinned low-poly whale girl with idle and walk clips.
- The primary character file is now `assets/models/whale_girl.vrm` (351,708 B), a minimal **VRM 1.0** container generated from the existing GLB by `tools/make_whale_girl_vrm.py`: 19 humanoid bones and four two-bone spring chains (`hair_side.L/R`, `hair_back`, `tail`).
- Animation sampling is delegated to **ozz-animation**; the original in-house sampler is kept as a fallback and as an A/B baseline. No glTF importer, game engine, blend tree or IK layer is pulled in.
- VRM `VRMC_springBone` is parsed at load time and solved every frame as a damped angular spring. Window drag displacement feeds the solver as inertial input; the visual result is independent of the base idle clip. `WHALE3D_SPRING=0` disables the layer for A/B measurement.
- The face is a 3-frame atlas (open / blink / smile) sampled by a shader UV offset. Auto blink is driven by the shell; `E` toggles smile and `B` triggers a blink.
- **v3.2 step 1:** a localhost UDP emotion bus (`127.0.0.1:47832`) accepts `{"emotion":"happy","intensity":0.8,"source":"llm"}` and maps it to the same three face frames. It is data-only; ASR/LLM/TTS stay outside the render process. See `docs/3d-emotion-bus.md`.
- The shell has a **native Win32 tray icon, native popup menu and native modal settings page**. No Qt, no PySide6, no UI toolkit.
- Model switching is a same-process, same-GL-context **model cache**: the first load of a path builds an `Impl`, and switching to a cached path only changes the active pointer. No window hide, no helper, no blank frame.
- The window is borderless, always on top, non-focus-stealing, and draggable with the left mouse button. Right-click opens the tray menu instead of quitting immediately. Only pixels whose alpha is above 16 belong to the Win32 window region, so transparent corners and gaps pass clicks through to the window below.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File F:\WhaleGirlPet\3d\build.ps1
```

Toolchain is portable and lives outside PATH:

- `F:\WhaleGirlPet\.toolchains\w64devkit` — g++ / make / binutils / CMake
- `F:\WhaleGirlPet\.toolchains\SDL3\SDL3-3.4.20\x86_64-w64-mingw32` — SDL3 headers, import lib, DLL

The release build uses `-Os -s -ffunction-sections -fdata-sections -Wl,--gc-sections` to keep the shell small. `build.ps1` compiles `main.cpp`, `model.cpp`, `shell_ui.cpp` and `emotion_bus.cpp`, links `-lSDL3`, the three static ozz libraries, `-lopengl32 -lgdi32 -luser32 -lshell32 -ladvapi32 -lws2_32`, and deploys `SDL3.dll` next to the exe. If `third_party/ozz-build` is missing, build ozz once with the same w64devkit toolchain (`BUILD_SHARED_LIBS=OFF`, `ozz_build_tools/fbx/gltf/data/samples/howtos/tests` all `OFF`), then rerun the script. Putting the devkit `bin` directory on `PATH` is required because CMake's generated Makefiles call a bare `make`.

## Run

```powershell
F:\WhaleGirlPet\3d\whale3d.exe
```

`SDL3.dll` must sit next to `whale3d.exe`; the model is resolved relative to the exe (`assets/models/whale_girl.vrm`), and the tray icon from `assets/ui/pet.ico`. If the VRM fails, the shell falls back to `whale_girl.glb` (same named spring chains), then `placeholder.glb`. An explicit model path can be passed as the first argument.

Optional runtime switches:

```powershell
$env:WHALE3D_ANIMATOR = 'ozz'   # default; 'self' uses the in-house sampler
$env:WHALE3D_CLIP = 'idle'      # default; 'walk' plays the 2-second technical clip
$env:WHALE3D_FACE = 'auto'      # auto blink; or open / blink / smile for a fixed frame
$env:WHALE3D_SPRING = '0'       # disable VRM spring bones for A/B; default on
```

While the window has focus, `W` cycles `idle → walk`, `O` toggles `ozz ↔ self`, `E` toggles the smile frame and `B` triggers a blink. The log line reports `fps`, `triangles`, `update_us`, `animator`, `clip` and `face` once per second.

## Emotion bus (v3.2 step 1)

The 3D process listens on `udp://127.0.0.1:47832` (override with `WHALE3D_EMOTION_PORT`) for a small JSON frame:

```json
{"emotion":"happy","intensity":0.8,"source":"llm"}
```

Inject one manually while the pet is running:

```powershell
.venv\Scripts\python.exe 3d\tools\send_emotion.py happy 0.8
```

The log then shows `Emotion: happy intensity=0.80 source=manual face=smile`. The current atlas maps positive/high-intensity emotions to `smile`, neutral to auto blink, and negative/low-arousal emotions to `open`; unknown labels are ignored. This is a transport + face-mapping slice only: cross-fade, gaze/body lean, and the Python ASR/LLM/TTS producer are later v3.2 work. See `docs/3d-emotion-bus.md`.

## Tray, menu and settings

The tray icon is registered with `Shell_NotifyIconW` on the SDL window's Win32 `HWND`, obtained through `SDL_GetWindowProperties`. The window procedure is subclassed with `SetWindowLongPtrW` so the app receives tray callbacks without a second window class.

On Windows 11 the per-app visibility flag lives at `HKCU\Control Panel\NotifyIconSettings\<hash>\IsPromoted`. `ShellUi::promoteTrayIcon` enumerates that key, matches `ExecutablePath` against the running exe, and writes `IsPromoted=1` as a DWORD. Explorer applies it on its next start (restart Explorer or sign in); the current machine was restarted once and the crop of `(1611,0)-(1643,48)` now shows the blue-haired whale girl, not the overflow chevron.

- **Left-click the tray icon** toggles the pet window.
- **Right-click the tray icon** opens a native popup menu: `隐藏窗口 / 显示窗口`, `动画：切到 Walk / Idle`, an expression submenu (`自动表情 / Open / Blink / Smile`), `设置…`, `退出`.
- **Right-click the pet** opens the same native menu.
- **Settings** is a native modal Win32 window titled `鲸鱼娘 3D · 设置`. It uses only `COMBOBOX`, `BUTTON` and `STATIC` controls:
  - 模型: `鲸鱼娘 v1 (VRM)` (`whale_girl.vrm`) or `方块占位` (`placeholder.glb`)
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

## VRM body and spring bones

`whale_girl.vrm` is a minimal VRM 1.0 container, not a full VRM avatar: it declares `VRMC_vrm` (19 humanoid bones) and `VRMC_springBone` (four two-bone chains), and keeps the original mesh, skin, atlas and idle clip. `model.cpp` parses both VRM 1.0 `extensions.VRMC_springBone.springs[].joints` and VRM 0.x `extensions.VRM.springBone.boneGroups[].bones`; if neither exists, it falls back to the named chains in the GLB.

Per frame the solver integrates a damped angular spring with semi-implicit Euler:

```text
accel = -k * (angle - target) - drag * velocity
velocity += accel * dt
angle += velocity * dt
```

The target is driven by the window's per-frame displacement (`setMotionInput(dx, dy)`) plus a small breathing sine. The root bone is rotated, then the tip is reconstructed from `newRoot * inverse(oldRoot) * oldTip`, so the chain swings as a unit rather than each bone rotating independently. VRM `stiffness` / `dragForce` are mapped to `k = 50 + stiffness * 100` and `drag = 9 + dragForce * 20`.

`3d/spring_accept.py` runs two otherwise identical processes with the base clip frozen (`WHALE3D_FREEZE=1`), one with `WHALE3D_SPRING=0` and one with it enabled. The three captured pairs are saved as `docs/_3d_spring_off_*.png` and `docs/_3d_spring_on_*.png`; the per-frame mean RGB deltas were `0.797`, `0.765`, `1.523`, and the frame-2 region sums were `14.3` over the hair/head crop and `96.7` over the tail crop. The tail visibly lifts in the on frame; the hair/head region also differs. This is screen-level evidence, not a formal spring-physics benchmark.

## Measured on this machine (2026-11-26)

Hardware: NVIDIA GTX 1060 6GB, driver 582.78, OpenGL 3.3.0.

| Item | Measurement |
| :--- | :--- |
| `whale3d.exe` | 1,315,840 bytes (1.25 MiB), with VRM + spring bones + tray + settings + in-place model cache + alpha region |
| exe SHA256 | `1290AC3A9E304465A00636DF67FBFB4C2BCFF6F5628FDCA792DE7E18DEE40E57` |
| `SDL3.dll` | 5,385,103 bytes |
| `whale_girl.vrm` | 351,708 bytes; SHA256 `BFD19124F1435E1CD2936F451AB4DEEFF0CABD5CA9A99B72E57E037D2BDECB87` |
| `whale_girl.glb` fallback | 350,332 bytes |
| Runtime payload (exe + DLL + VRM) | 7,052,651 bytes (6.72 MiB) |
| Spring chains | 4 (`hair_side.L/R`, `hair_back`, `tail`); 19 VRM humanoid bones |
| Spring solver | 7.63–10.80 µs/frame idle; 4 spring chains on 28 joints |
| Tray promotion | `HKCU\Control Panel\NotifyIconSettings\674768749172540869\IsPromoted=1`; exact-rect crop shows the blue-haired icon |
| Pet window | 420×620, transparent, borderless, always-on-top, non-focusable |
| Settings client area | 420×360 (outer about 426×389) |
| FPS | 28.3–29.0 with VRM + spring + alpha readback; 5.0–6.2 on the first frame after an in-place switch, then recovered |
| Triangles | 2,076 (whale girl), 216 (placeholder) |
| Animator update, ozz | 4.34–17.26 µs/frame across switch runs; steady 8–9 µs |
| Private bytes, in-place cache | 97,837,056 steady at first sample; 98,078,720 after placeholder and after whale back; unchanged over 4 switches |
| First in-place load | 8 ms for `placeholder.glb`; cache hit 0 ms; `.vrm` back 0 ms |
| In-place identity | same PID 15860, no child process, same window; exit 0 |
| CPU | 31.1–35.8% of one core in a 10 s window (spring on vs off; render/hit-mask readback dominates) |
| RSS | about 70.1 MB |
| Exit code | 0 for direct exit, tray-menu exit and settings-close-then-exit |

The exe grew by 13,312 bytes over the v3.0.28 shell (1,302,528 → 1,315,840). That covers the VRM/GLB extension parser, the per-frame spring solver, motion input plumbing and the `.vrm` settings path. The 100 MB limit holds: private bytes stay at 97.8–98.1 MB across the initial load and four in-place switches, with no growth after the second sample.

## Runnable package

`F:\WhaleGirlPet\3d\whale3d-whale-girl-v2.zip` is about **2.7 MiB** (the exact ZIP hash and size are recorded in `docs/3d-transition.md`; the README inside the ZIP cannot reliably hash itself). It contains `whale3d.exe` (1,315,840 B, VRM+spring/tray/settings/in-place-cache/alpha-region), `SDL3.dll`, `README.md`, `THIRD_PARTY_NOTICES.txt`, `assets/models/whale_girl.vrm` (351,708 B), `assets/models/whale_girl.glb` (350,332 B, fallback), `assets/models/_whale_girl_atlas.png` (32,232 B), `assets/models/placeholder.glb` (38,288 B) and `assets/ui/pet.ico` (9,001 B). It is extracted to a temp folder and launched there; the extracted build logs `Model springs: 4 chains, vrm=1`, loads `whale_girl.vrm` with 2,076 triangles, reports `Hit mask ready: 420x620 center_alpha=255`, opens the settings page, switches to `placeholder.glb` in the same process via the model cache, and exits 0.

The v3.0.28 package remains as `whale3d-whale-girl-v1.zip` (2,727,089 B, exe `1,302,528 B`, SHA256 `9EB9CCAAA1B42D5CFA440E77FFB4E331A0746F6EF35A07D0843B47CE712BE461`); the expression-only package is preserved as `whale3d-whale-girl-v1-expression.zip` (2,695,131 B, exe `1,260,544 B`, SHA256 `534FA2B87C83D2ACFDB5B380B3954F9E07D2815168EE5B20845D11A76C161435`). Do not mix their numbers with this build.

Windows installers are built from the release ZIPs by `installer/whale3d.iss` (compiled with `installer/build_3d_installers.ps1`). `WhaleGirlPet-3D-Setup-3.1.0.exe` and `WhaleGirlPet-3D-Setup-3.0.28.exe` install under `%LOCALAPPDATA%\WhaleGirlPet3D` without elevation, add Start Menu shortcuts plus an optional desktop shortcut, and register an uninstaller. Both use the same AppId, so installing 3.1.0 upgrades 3.0.28 in place. The installers are unsigned; verify the adjacent `.sha256` before running if SmartScreen warns.

## Known limitations

1. The model is deliberately stylized/chibi: a curved face decal on a low-poly head, approximated side/back hair, a single-piece fluke and no contact shadow. It is v1, not final art.
2. Facial expression is only open / blink / smile on a UV-offset atlas; there is no eye tracking, lip sync, morph target or facial rig.
3. The GLB itself has only one animation. `walk` is generated procedurally at startup; there is no animation blending, IK, root motion or animation event track yet.
4. Click-through now passed an OS-level cursor test: `SetCursorPos` + `mouse_event` at the transparent corner produced `BN_CLICKED id=1 count=1` on the underlay button; a center drag moved the pet and left the underlay click count unchanged. The earlier synthetic failure was the ctypes WndProc harness truncating LPARAM, not the window-region routing. A physical-hand click is still a user sanity check, not an automated one.
5. The default model switch is now a true in-place **model cache** in the same process and GL context: switch by active `Impl*`, no window hide, no helper, no blank frame. First placeholder load measured 8 ms and cache hits 0 ms; private bytes were 97,837,056 at the first sample and 98,078,720 after four switches, same PID 15860 and no child process. The optional `--relaunch` helper remains for A/B/fallback (`WHALE3D_SWITCH=relaunch`): 2,064,384 B helper, old+helper peak 97.3–97.5 MB, new pet ready 1.55–1.61 s.
6. Windows 11 tray promotion is implemented by matching `ExecutablePath` under `HKCU\Control Panel\NotifyIconSettings` and writing `IsPromoted=1`. Explorer applies it on its next start; this machine was restarted once, and the exact `(1611,0)-(1643,48)` crop shows the blue-haired whale girl icon. A fresh install still needs one Explorer restart/sign-in before the flag takes effect.
7. No behavior state machine, audio, cloud/AI integration or PySide6 replacement yet. The existing `ai_profiles`, `_chat_cloud` and cloud API routes stay in the Python service and are not packaged into this core zip.
8. The VRM support is a deliberately minimal subset: `VRMC_vrm` humanoid mapping and `VRMC_springBone` two-bone chains only. MToon materials, expressions, look-at, spring colliders and full per-joint spring bones are not integrated. The runtime does not import arbitrary VRM avatars yet; the `.vrm` is generated from the project's own GLB.
9. The spring layer is wired into the default `ozz` path. Selecting the `self` sampler in the settings page bypasses `applySpringBones`; this is a known gap, not a claim that both samplers are equivalent.

## Not in this step

- ozz blend trees, IK, root motion and `.ozz` asset baking
- VRM MToon materials, expressions / BlendShape, look-at, spring colliders and per-joint full spring chains
- arbitrary third-party VRM avatars; the loader currently handles the project's minimal humanoid + two-bone spring subset
- eye tracking, lip sync or a facial rig beyond the three atlas frames
- behavior/AI integration
- installer / package split
- automatic Explorer restart or first-run promotion notification (the registry flag is written, but Explorer must restart once)
