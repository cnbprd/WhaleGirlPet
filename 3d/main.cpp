// WhaleGirl 3D stage 2: transparent SDL3/OpenGL shell + a skinned low-poly
// glTF placeholder.  No engine, no VRM runtime, no Qt.

#define WIN32_LEAN_AND_MEAN
#include <SDL3/SDL.h>
#include <GL/gl.h>

#include "model.h"
#include "shell_ui.h"
#include "emotion_bus.h"
#include "sprite.h"
#include "perf_stats.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

static FILE* gLogFile = nullptr;

static std::string moduleLogPath() {
    wchar_t modulePath[MAX_PATH];
    DWORD length = GetModuleFileNameW(nullptr, modulePath, MAX_PATH);
    if (length == 0 || length >= MAX_PATH) return std::string();
    std::wstring wide(modulePath, length);
    const size_t slash = wide.find_last_of(L"\\/");
    if (slash == std::wstring::npos) return std::string();
    wide.erase(slash + 1);
    wide += L"whale3d.log";

    int utf8Length = WideCharToMultiByte(CP_UTF8, 0, wide.c_str(), -1, nullptr, 0, nullptr, nullptr);
    if (utf8Length <= 0) return std::string();
    std::string path(static_cast<size_t>(utf8Length - 1), '\0');
    WideCharToMultiByte(CP_UTF8, 0, wide.c_str(), -1, path.data(), utf8Length, nullptr, nullptr);
    return path;
}

static void fileLog(void*, int, SDL_LogPriority, const char* message) {
    if (!gLogFile || !message) return;
    std::fputs(message, gLogFile);
    std::fputc('\n', gLogFile);
    std::fflush(gLogFile);
}

static void initLog() {
    const char* overridePath = std::getenv("WHALE3D_LOG");
    std::string path = (overridePath && *overridePath) ? overridePath : moduleLogPath();
    if (path.empty()) return;
    gLogFile = std::fopen(path.c_str(), "w");
    if (!gLogFile) return;
    SDL_SetLogOutputFunction(fileLog, nullptr);
    SDL_Log("Log: %s", path.c_str());
}

static bool hasPrefix(const char* value, const char* prefix) {
    return value && std::strncmp(value, prefix, std::strlen(prefix)) == 0;
}

// Accept both "--fixed-dt=0.016667" and "--fixed-dt=1/60".
static double parseSeconds(const char* value) {
    if (!value || !*value) return 0.0;
    const char* slash = std::strchr(value, '/');
    if (!slash) return std::strtod(value, nullptr);
    const std::string numerator(value, static_cast<size_t>(slash - value));
    const double denom = std::strtod(slash + 1, nullptr);
    if (denom <= 0.0) return 0.0;
    return std::strtod(numerator.c_str(), nullptr) / denom;
}

// ---- tiny column-major matrix math for the camera ----
struct Mat4 { GLfloat m[16]; };

static Mat4 identity() {
    Mat4 r{};
    r.m[0] = r.m[5] = r.m[10] = r.m[15] = 1.0f;
    return r;
}

static Mat4 multiply(const Mat4& a, const Mat4& b) {
    Mat4 r{};
    for (int c = 0; c < 4; ++c) {
        for (int row = 0; row < 4; ++row) {
            float v = 0.0f;
            for (int k = 0; k < 4; ++k) v += a.m[k * 4 + row] * b.m[c * 4 + k];
            r.m[c * 4 + row] = v;
        }
    }
    return r;
}

static Mat4 perspective(float fovy, float aspect, float nearZ, float farZ) {
    Mat4 r{};
    float f = 1.0f / std::tan(fovy * 0.5f);
    r.m[0] = f / aspect;
    r.m[5] = f;
    r.m[10] = (farZ + nearZ) / (nearZ - farZ);
    r.m[11] = -1.0f;
    r.m[14] = (2.0f * farZ * nearZ) / (nearZ - farZ);
    return r;
}

static Mat4 lookAt(const float eye[3], const float center[3], const float up[3]) {
    float fx = center[0] - eye[0], fy = center[1] - eye[1], fz = center[2] - eye[2];
    float fl = std::sqrt(fx * fx + fy * fy + fz * fz);
    fx /= fl; fy /= fl; fz /= fl;
    float sx = fy * up[2] - fz * up[1];
    float sy = fz * up[0] - fx * up[2];
    float sz = fx * up[1] - fy * up[0];
    float sl = std::sqrt(sx * sx + sy * sy + sz * sz);
    sx /= sl; sy /= sl; sz /= sl;
    float ux = sy * fz - sz * fy;
    float uy = sz * fx - sx * fz;
    float uz = sx * fy - sy * fx;
    Mat4 r = identity();
    r.m[0] = sx; r.m[4] = sy; r.m[8] = sz;
    r.m[1] = ux; r.m[5] = uy; r.m[9] = uz;
    r.m[2] = -fx; r.m[6] = -fy; r.m[10] = -fz;
    r.m[12] = -(sx * eye[0] + sy * eye[1] + sz * eye[2]);
    r.m[13] = -(ux * eye[0] + uy * eye[1] + uz * eye[2]);
    r.m[14] = (fx * eye[0] + fy * eye[1] + fz * eye[2]);
    return r;
}

// The 3D window keeps its window region on the model pixels only.  The
// sprite card lives in a separate, transparent, topmost OpenGL window so the
// card can stay visible without becoming a hit-test target of the main
// window.  The overlay is clipped to the card rect and forwards clicks to
// the first window underneath it.
static WNDPROC gOverlayOldProc = nullptr;
static HWND gOverlayHwnd = nullptr;
static HWND gOverlayMouseTarget = nullptr;

static HWND findWindowBelow(HWND overlay, POINT screenPoint) {
    HWND candidate = GetWindow(overlay, GW_HWNDNEXT);
    while (candidate) {
        if (candidate != overlay && IsWindowVisible(candidate) &&
            !IsIconic(candidate)) {
            POINT clientPoint = screenPoint;
            if (ScreenToClient(candidate, &clientPoint)) {
                RECT clientRect{};
                if (GetClientRect(candidate, &clientRect) &&
                    PtInRect(&clientRect, clientPoint)) {
                    HRGN region = CreateRectRgn(0, 0, 0, 0);
                    int regionType = GetWindowRgn(candidate, region);
                    const bool inRegion =
                        regionType == ERROR ||
                        (regionType != NULLREGION &&
                         PtInRegion(region, clientPoint.x, clientPoint.y));
                    DeleteObject(region);
                    if (inRegion) {
                        DWORD_PTR hit = 0;
                        const LRESULT sent = SendMessageTimeoutW(
                            candidate, WM_NCHITTEST, 0,
                            MAKELPARAM(screenPoint.x, screenPoint.y),
                            SMTO_ABORTIFHUNG, 50, &hit);
                        if (sent &&
                            hit != static_cast<DWORD_PTR>(HTTRANSPARENT) &&
                            hit != static_cast<DWORD_PTR>(HTNOWHERE)) {
                            return candidate;
                        }
                    }
                }
            }
        }
        candidate = GetWindow(candidate, GW_HWNDNEXT);
    }
    return nullptr;
}

static void forwardMouseToBelow(HWND overlay, UINT msg, WPARAM wParam) {
    POINT screenPoint{};
    GetCursorPos(&screenPoint);
    if (msg == WM_LBUTTONDOWN || msg == WM_RBUTTONDOWN ||
        msg == WM_MBUTTONDOWN) {
        gOverlayMouseTarget = findWindowBelow(overlay, screenPoint);
    }
    HWND target = gOverlayMouseTarget;
    if (!target) target = findWindowBelow(overlay, screenPoint);
    if (!target) return;
    POINT clientPoint = screenPoint;
    if (!ScreenToClient(target, &clientPoint)) return;
    PostMessageW(target, msg, wParam,
                 MAKELPARAM(clientPoint.x, clientPoint.y));
    if (msg == WM_LBUTTONUP || msg == WM_RBUTTONUP ||
        msg == WM_MBUTTONUP) {
        gOverlayMouseTarget = nullptr;
    }
}

static LRESULT CALLBACK overlayInputProc(HWND hwnd, UINT msg,
                                         WPARAM wParam, LPARAM lParam) {
    switch (msg) {
    case WM_MOUSEACTIVATE:
        return MA_NOACTIVATE;
    case WM_NCHITTEST:
        // The overlay is clipped to the card; all points inside its region
        // are a card hit.  The main window never sees this point because it
        // excludes the card from its own region.
        return HTCLIENT;
    case WM_LBUTTONDOWN:
    case WM_LBUTTONUP:
    case WM_LBUTTONDBLCLK:
    case WM_RBUTTONDOWN:
    case WM_RBUTTONUP:
    case WM_MBUTTONDOWN:
    case WM_MBUTTONUP:
        forwardMouseToBelow(hwnd, msg, wParam);
        return 0;
    default:
        break;
    }
    if (gOverlayOldProc) {
        return CallWindowProcW(gOverlayOldProc, hwnd, msg, wParam, lParam);
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

static void configureOverlayWindow(SDL_Window* window) {
    if (!window) return;
    SDL_PropertiesID props = SDL_GetWindowProperties(window);
    HWND hwnd = static_cast<HWND>(SDL_GetPointerProperty(
        props, SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr));
    if (!hwnd) {
        SDL_Log("Sprite overlay: HWND unavailable; clicks may not pass through");
        return;
    }
    gOverlayHwnd = hwnd;
    LONG_PTR exStyle = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
    SetWindowLongPtrW(hwnd, GWL_EXSTYLE,
                      exStyle | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW);
    if (!gOverlayOldProc) {
        gOverlayOldProc = reinterpret_cast<WNDPROC>(
            SetWindowLongPtrW(hwnd, GWLP_WNDPROC,
                              reinterpret_cast<LONG_PTR>(overlayInputProc)));
    }
    SDL_Log("Sprite overlay: exstyle 0x%llx -> 0x%llx",
            static_cast<unsigned long long>(exStyle),
            static_cast<unsigned long long>(
                GetWindowLongPtrW(hwnd, GWL_EXSTYLE)));
}

static void setOverlayCardRegion(const SpriteLayer::PixelRect& rect) {
    if (!gOverlayHwnd) return;
    HRGN region = CreateRectRgn(rect.x, rect.y,
                                rect.x + rect.width,
                                rect.y + rect.height);
    if (!region) return;
    if (!SetWindowRgn(gOverlayHwnd, region, TRUE)) {
        DeleteObject(region);
    }
}

int main(int argc, char** argv) {
    if (argc >= 2 && std::strcmp(argv[1], "--relaunch") == 0) {
        return runRelaunchHelper(argc, argv);
    }

    bool headless = false;
    int headlessFrames = 60;
    double fixedDt = 1.0 / 60.0;
    std::string modelArg;
    std::string summaryPath;
    for (int i = 1; i < argc; ++i) {
        const char* arg = argv[i];
        if (std::strcmp(arg, "--headless") == 0) {
            headless = true;
        } else if (hasPrefix(arg, "--frames=")) {
            const int parsed = std::atoi(arg + std::strlen("--frames="));
            if (parsed > 0) headlessFrames = parsed;
        } else if (hasPrefix(arg, "--fixed-dt=")) {
            const double parsed = parseSeconds(arg + std::strlen("--fixed-dt="));
            if (parsed > 0.0 && parsed <= 0.1) fixedDt = parsed;
        } else if (hasPrefix(arg, "--summary=")) {
            summaryPath = arg + std::strlen("--summary=");
        } else if (arg[0] != '-') {
            modelArg = arg;
        }
    }

    // One desktop pet per user session. Without this guard a second direct
    // launch can create another window/tray icon and race the UDP emotion
    // socket (which intentionally enables address reuse). Headless runs are
    // deliberately exempt so CI can run while the desktop pet is open.
    HANDLE instanceMutex = nullptr;
    if (!headless) {
        SetLastError(0);
        instanceMutex = CreateMutexW(nullptr, TRUE, L"Local\\WhaleGirlPet3D");
        if (!instanceMutex) {
            return 1;
        }
        if (GetLastError() == ERROR_ALREADY_EXISTS) {
            CloseHandle(instanceMutex);
            return 0;
        }
    }

    initLog();
    if (!SDL_Init(SDL_INIT_VIDEO)) {
        SDL_Log("SDL_Init failed: %s", SDL_GetError());
        if (instanceMutex) CloseHandle(instanceMutex);
        return 1;
    }
    PerfStats perf(headless);

    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_ALPHA_SIZE, 8);
    SDL_GL_SetAttribute(SDL_GL_MULTISAMPLEBUFFERS, 1);
    SDL_GL_SetAttribute(SDL_GL_MULTISAMPLESAMPLES, 4);

    const int winW = 420;
    const int winH = 620;
    SDL_WindowFlags flags = static_cast<SDL_WindowFlags>(
        SDL_WINDOW_OPENGL | SDL_WINDOW_TRANSPARENT | SDL_WINDOW_BORDERLESS |
        SDL_WINDOW_ALWAYS_ON_TOP | SDL_WINDOW_HIGH_PIXEL_DENSITY |
        SDL_WINDOW_NOT_FOCUSABLE);
    if (headless) {
        flags = static_cast<SDL_WindowFlags>(
            SDL_WINDOW_OPENGL | SDL_WINDOW_HIDDEN | SDL_WINDOW_HIGH_PIXEL_DENSITY);
    }

    SDL_Window* win = SDL_CreateWindow("鲸鱼娘", winW, winH, flags);
    if (!win) {
        SDL_Log("SDL_CreateWindow failed: %s", SDL_GetError());
        SDL_Quit();
        if (instanceMutex) CloseHandle(instanceMutex);
        return 1;
    }

    if (!headless) {
        SDL_DisplayID display = SDL_GetPrimaryDisplay();
        SDL_Rect usable{};
        if (SDL_GetDisplayUsableBounds(display, &usable)) {
            SDL_SetWindowPosition(win, usable.x + usable.w - winW - 80,
                                       usable.y + usable.h - winH - 30);
        }
    }

    SDL_GLContext ctx = SDL_GL_CreateContext(win);
    if (!ctx) {
        SDL_Log("SDL_GL_CreateContext failed: %s", SDL_GetError());
        SDL_DestroyWindow(win);
        SDL_Quit();
        return 1;
    }
    SDL_GL_MakeCurrent(win, ctx);
    SDL_GL_SetSwapInterval(0);
    glReadBuffer(GL_BACK);

    const GLubyte* renderer = glGetString(GL_RENDERER);
    const GLubyte* version = glGetString(GL_VERSION);
    SDL_Log("GL renderer: %s", renderer ? reinterpret_cast<const char*>(renderer) : "?");
    SDL_Log("GL version : %s", version ? reinterpret_cast<const char*>(version) : "?");

    std::string base = "";
    if (const char* raw = SDL_GetBasePath()) {
        // SDL3 caches this string internally and frees it in SDL_QuitFilesystem;
        // calling SDL_free here corrupts the heap and crashes SDL_Quit on exit.
        base = raw;
    }
    std::string modelPath = modelArg.empty() ? base + "assets/models/whale_girl.vrm" : modelArg;
    Model model;
    if (!model.load(modelPath)) {
        SDL_Log("Primary VRM load failed: %s", model.error().c_str());
        modelPath = base + "assets/models/whale_girl.glb";
        if (!model.load(modelPath)) {
            SDL_Log("GLB fallback load failed: %s", model.error().c_str());
            modelPath = base + "assets/models/placeholder.glb";
            if (!model.load(modelPath)) {
                SDL_Log("Fallback placeholder load failed: %s", model.error().c_str());
                SDL_GL_DestroyContext(ctx);
                SDL_DestroyWindow(win);
                SDL_Quit();
                return 1;
            }
        }
    }
    SDL_Log("Model loaded: %s (%d triangles, %d joints, %d animations)",
            modelPath.c_str(), model.triangleCount(), model.jointCount(), model.animationCount());
    SDL_Log("Spring bones: %d chains, vrm=%d",
            model.springCount(), model.usesVrm() ? 1 : 0);

    if (const char* animator = std::getenv("WHALE3D_ANIMATOR")) {
        if (!model.setAnimator(animator)) {
            SDL_Log("Animator '%s' not available; keeping %s", animator, model.animatorName());
        }
    }
    if (const char* clip = std::getenv("WHALE3D_CLIP")) {
        if (!model.setClip(clip)) {
            SDL_Log("Clip '%s' not available; keeping %s", clip, model.clipName());
        }
    }
    if (const char* face = std::getenv("WHALE3D_FACE")) {
        if (!model.setFace(face)) {
            SDL_Log("Face '%s' not available; keeping auto", face);
        }
    }
    SDL_Log("Animator: %s; clip: %s; face: %s",
            model.animatorName(), model.clipName(), model.faceName());

    if (headless) {
        glEnable(GL_DEPTH_TEST);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        const float eye[3] = { 0.55f, 1.15f, 4.5f };
        const float center[3] = { 0.0f, 1.0f, 0.0f };
        const float up[3] = { 0.0f, 1.0f, 0.0f };
        const Mat4 view = lookAt(eye, center, up);
        int pw = 0, ph = 0;
        SDL_GetWindowSizeInPixels(win, &pw, &ph);
        if (pw <= 0 || ph <= 0) {
            SDL_Log("headless: invalid drawable %dx%d", pw, ph);
            model.shutdown();
            SDL_GL_DestroyContext(ctx);
            SDL_DestroyWindow(win);
            SDL_Quit();
            if (instanceMutex) CloseHandle(instanceMutex);
            return 1;
        }
        std::vector<unsigned char> pixels(static_cast<size_t>(pw) * ph * 4, 0);
        while (glGetError() != GL_NO_ERROR) {}

        int rendered = 0;
        GLenum lastError = GL_NO_ERROR;
        for (int i = 0; i < headlessFrames; ++i) {
            perf.beginFrame();
            const float t = fixedDt * static_cast<float>(i + 1);
            {
                PerfStats::Timer timer(perf, perf.current().updateUs);
                model.update(t);
            }
            const Mat4 proj = perspective(
                35.0f * 3.14159265f / 180.0f,
                static_cast<float>(pw) / static_cast<float>(ph), 0.1f, 20.0f);
            const Mat4 viewProj = multiply(proj, view);
            glViewport(0, 0, pw, ph);
            glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
            {
                PerfStats::Timer timer(perf, perf.current().renderUs);
                model.draw(viewProj.m);
            }
            glReadBuffer(GL_BACK);
            {
                PerfStats::Timer timer(perf, perf.current().readbackUs);
                glReadPixels(0, 0, pw, ph, GL_RGBA, GL_UNSIGNED_BYTE,
                             pixels.data());
            }
            lastError = glGetError();
            SDL_GL_SwapWindow(win);
            perf.endFrame();
            ++rendered;
        }
        perf.writeSummary("headless", summaryPath.empty() ? nullptr : summaryPath.c_str());
        const int cx = pw / 2;
        const int cy = ph / 2;
        const unsigned char centerAlpha =
            pixels[(static_cast<size_t>(ph - 1 - cy) * pw + cx) * 4 + 3];
        SDL_Log("headless done frames=%d gl_error=0x%x center_alpha=%u summary=%s",
                rendered, static_cast<unsigned>(lastError), centerAlpha,
                summaryPath.empty() ? "-" : summaryPath.c_str());

        model.shutdown();
        SDL_GL_DestroyContext(ctx);
        SDL_DestroyWindow(win);
        SDL_Quit();
        if (instanceMutex) CloseHandle(instanceMutex);
        return lastError == GL_NO_ERROR ? 0 : 1;
    }

    EmotionBus emotionBus;
    int emotionPort = 47832;
    if (const char* rawPort = std::getenv("WHALE3D_EMOTION_PORT")) {
        const int parsed = std::atoi(rawPort);
        if (parsed > 0 && parsed <= 65535) emotionPort = parsed;
    }
    if (emotionBus.start(emotionPort)) {
        SDL_Log("Emotion bus: udp://127.0.0.1:%d", emotionPort);
    } else {
        SDL_Log("Emotion bus unavailable on 127.0.0.1:%d", emotionPort);
    }

    ShellUi ui;
    std::vector<unsigned char> hitMask;
    int hitW = 0, hitH = 0;
    if (!ui.init(win, &model, base + "assets/ui/pet.ico", base)) {
        SDL_Log("Tray/settings unavailable; continuing without ShellUi");
    }
    ui.setHitTest([&](int clientX, int clientY) {
        int ww = 0, wh = 0;
        SDL_GetWindowSize(win, &ww, &wh);
        if (ww <= 0 || wh <= 0) return true;
        if (clientX < 0 || clientY < 0 || clientX >= ww || clientY >= wh) return false;
        if (hitW <= 0 || hitH <= 0 || hitMask.empty()) return true;
        const int mx = std::clamp(clientX * hitW / ww, 0, hitW - 1);
        const int my = std::clamp(clientY * hitH / wh, 0, hitH - 1);
        const int imageY = hitH - 1 - my;
        const unsigned char alpha = hitMask[(static_cast<size_t>(imageY) * hitW + mx) * 4 + 3];
        return alpha > 16;
    });

    // The 2D card sprite is a separate screen-space layer. Dev builds can
    // point at the repository's root assets if the exe sits in `3d/`; packaged
    // builds resolve `assets/2d_bridge` next to the exe.
    SpriteLayer sprite;
    std::string spriteBase = base;
    {
        std::ifstream localManifest(spriteBase + "assets/2d_bridge/manifest.json");
        if (!localManifest.good()) {
            const std::string parentBase = base + "../";
            std::ifstream parentManifest(parentBase + "assets/2d_bridge/manifest.json");
            if (parentManifest.good()) spriteBase = parentBase;
        }
    }
    SDL_Window* overlayWin = nullptr;
    SDL_GLContext overlayCtx = nullptr;
    bool spriteOverlay = false;
    bool spriteReady = false;
    {
        // A separate topmost OpenGL window owns the card.  The main window's
        // region contains only model pixels, so a click on the card reaches
        // the desktop/window below instead of being eaten by HTTRANSPARENT.
        SDL_WindowFlags overlayFlags = static_cast<SDL_WindowFlags>(
            SDL_WINDOW_OPENGL | SDL_WINDOW_TRANSPARENT | SDL_WINDOW_BORDERLESS |
            SDL_WINDOW_ALWAYS_ON_TOP | SDL_WINDOW_UTILITY | SDL_WINDOW_HIDDEN |
            SDL_WINDOW_HIGH_PIXEL_DENSITY | SDL_WINDOW_NOT_FOCUSABLE);
        int mainX = 0, mainY = 0;
        SDL_GetWindowPosition(win, &mainX, &mainY);
        overlayWin = SDL_CreateWindow("鲸鱼娘卡面", winW, winH, overlayFlags);
        if (overlayWin) {
            SDL_SetWindowPosition(overlayWin, mainX, mainY);
            SDL_SetWindowAlwaysOnTop(overlayWin, true);
            configureOverlayWindow(overlayWin);
            overlayCtx = SDL_GL_CreateContext(overlayWin);
            if (overlayCtx) {
                SDL_GL_MakeCurrent(overlayWin, overlayCtx);
                SDL_GL_SetSwapInterval(0);
                spriteReady = sprite.init(spriteBase);
                if (spriteReady) {
                    spriteOverlay = true;
                    SDL_Log("Sprite layer: ready (overlay %sassets/2d_bridge)",
                            spriteBase.c_str());
                } else {
                    SDL_Log("Sprite overlay init failed: %s", sprite.error().c_str());
                    sprite.shutdown();
                }
                SDL_GL_MakeCurrent(win, ctx);
            } else {
                SDL_Log("Sprite overlay GL context failed: %s", SDL_GetError());
            }
        } else {
            SDL_Log("Sprite overlay window failed: %s", SDL_GetError());
        }
        if (!spriteReady) {
            SDL_GL_MakeCurrent(win, ctx);
            spriteReady = sprite.init(spriteBase);
            if (spriteReady) {
                SDL_Log("Sprite layer: ready (main %sassets/2d_bridge)",
                        spriteBase.c_str());
            } else {
                SDL_Log("Sprite layer unavailable: %s", sprite.error().c_str());
            }
        }

        if (spriteReady) {
            if (const char* card = std::getenv("WHALE3D_CARD")) {
                float ttlMs = 5000.0f;
                if (const char* rawTtl = std::getenv("WHALE3D_CARD_TTL")) {
                    const float parsed = static_cast<float>(std::atof(rawTtl));
                    if (parsed >= 200.0f && parsed <= 10000.0f) ttlMs = parsed;
                }
                if (sprite.showCard(card, ttlMs)) {
                    SDL_Log("Sprite forced: %s ttl=%.0fms", card, ttlMs);
                } else {
                    SDL_Log("Sprite card rejected: %s", card);
                }
            }
        }
    }

    glEnable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    const float eye[3] = { 0.55f, 1.15f, 4.5f };
    const float center[3] = { 0.0f, 1.0f, 0.0f };
    const float up[3] = { 0.0f, 1.0f, 0.0f };
    Mat4 view = lookAt(eye, center, up);

    bool running = true;
    bool dragging = false;
    float dragStartX = 0.0f, dragStartY = 0.0f;
    int winStartX = 0, winStartY = 0;
    int lastWinX = 0, lastWinY = 0;
    SDL_GetWindowPosition(win, &lastWinX, &lastWinY);
    bool overlayShown = false;
    int overlayX = 0, overlayY = 0;
    int overlayCardX = -1, overlayCardY = -1;
    int overlayCardW = -1, overlayCardH = -1;
    Uint64 start = SDL_GetTicks();
    Uint64 lastLog = start;
    int frames = 0;
    Uint64 perfFreq = SDL_GetPerformanceFrequency();
    Uint64 updateTicks = 0;
    int updateFrames = 0;
    float lastT = 0.0f;

    while (running && !ui.quitRequested()) {
        static bool perfWarmed = false;
        if (!perfWarmed && SDL_GetTicks() - start >= 5000) {
            perf.resetSamples();
            perfWarmed = true;
        }
        perf.beginFrame();
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_EVENT_QUIT) {
                running = false;
            } else if (ev.type == SDL_EVENT_KEY_DOWN) {
                if (ev.key.key == SDLK_ESCAPE) {
                    running = false;
                } else if (ev.key.key == SDLK_W) {
                    model.nextClip();
                    SDL_Log("clip: %s", model.clipName());
                } else if (ev.key.key == SDLK_O) {
                    const bool toOzz = !model.usesOzz();
                    if (model.setAnimator(toOzz ? "ozz" : "self")) {
                        SDL_Log("animator: %s", model.animatorName());
                    } else {
                        SDL_Log("ozz animator unavailable");
                    }
                } else if (ev.key.key == SDLK_E) {
                    model.toggleSmile();
                    SDL_Log("face: %s", model.faceName());
                } else if (ev.key.key == SDLK_B) {
                    float keyTime = static_cast<float>(SDL_GetTicks() - start) / 1000.0f;
                    model.triggerBlink(keyTime);
                    SDL_Log("face: %s", model.faceName());
                }
            } else if (ev.type == SDL_EVENT_MOUSE_BUTTON_DOWN) {
                if (ev.button.button == SDL_BUTTON_RIGHT) {
                    ui.showTrayMenu();
                } else if (ev.button.button == SDL_BUTTON_LEFT) {
                    dragging = true;
                    SDL_GetGlobalMouseState(&dragStartX, &dragStartY);
                    SDL_GetWindowPosition(win, &winStartX, &winStartY);
                    SDL_CaptureMouse(true);
                }
            } else if (ev.type == SDL_EVENT_MOUSE_BUTTON_UP && ev.button.button == SDL_BUTTON_LEFT) {
                dragging = false;
                SDL_CaptureMouse(false);
            } else if (ev.type == SDL_EVENT_MOUSE_MOTION && dragging) {
                float mx = 0.0f, my = 0.0f;
                SDL_GetGlobalMouseState(&mx, &my);
                SDL_SetWindowPosition(win, winStartX + static_cast<int>(mx - dragStartX),
                                           winStartY + static_cast<int>(my - dragStartY));
            }
        }

        EmotionBus::Frame emotion;
        if (emotionBus.poll(emotion)) {
            if (model.applyEmotion(emotion.emotion, emotion.intensity,
                                   emotion.attackMs, emotion.releaseMs)) {
                model.applyGazeLean(emotion.gazeX, emotion.gazeY, emotion.gazeWeight,
                                    emotion.leanX, emotion.leanY, emotion.leanWeight);
                SDL_Log("Emotion: %s intensity=%.2f attack=%.0fms release=%.0fms "
                        "gaze=(%.2f,%.2f)@%.2f lean=(%.2f,%.2f)@%.2f source=%s face=%s "
                        "card=%s card_ttl=%.0fms",
                        emotion.emotion.c_str(), emotion.intensity,
                        emotion.attackMs, emotion.releaseMs,
                        emotion.gazeX, emotion.gazeY, emotion.gazeWeight,
                        emotion.leanX, emotion.leanY, emotion.leanWeight,
                        emotion.source.empty() ? "unknown" : emotion.source.c_str(),
                        model.faceName(), emotion.card.empty() ? "-" : emotion.card.c_str(),
                        emotion.cardTtlMs);
            } else {
                SDL_Log("Emotion ignored: %s (raw %.80s)", emotion.emotion.c_str(),
                        emotion.raw.c_str());
            }
            if (spriteReady && !emotion.card.empty() && emotion.cardTtlMs > 0.0f) {
                if (sprite.showCard(emotion.card, emotion.cardTtlMs)) {
                    SDL_Log("Sprite card: %s ttl=%.0fms", emotion.card.c_str(),
                            emotion.cardTtlMs);
                } else {
                    SDL_Log("Sprite card rejected: %s", emotion.card.c_str());
                }
            }
        }

        int pw = 0, ph = 0;
        SDL_GetWindowSizeInPixels(win, &pw, &ph);
        if (pw <= 0 || ph <= 0) {
            SDL_Delay(16);
            continue;
        }

        int winX = 0, winY = 0;
        SDL_GetWindowPosition(win, &winX, &winY);
        model.setMotionInput(static_cast<float>(winX - lastWinX),
                             static_cast<float>(winY - lastWinY));
        lastWinX = winX;
        lastWinY = winY;

        float t = static_cast<float>(SDL_GetTicks() - start) / 1000.0f;
        float dt = std::clamp(t - lastT, 0.0f, 0.1f);
        lastT = t;
        Uint64 updateStart = SDL_GetPerformanceCounter();
        {
            PerfStats::Timer timer(perf, perf.current().updateUs);
            model.update(t);
            sprite.update(dt);
        }
        updateTicks += SDL_GetPerformanceCounter() - updateStart;
        ++updateFrames;

        Mat4 proj = perspective(35.0f * 3.14159265f / 180.0f,
                                static_cast<float>(pw) / static_cast<float>(ph), 0.1f, 20.0f);
        Mat4 viewProj = multiply(proj, view);

        glViewport(0, 0, pw, ph);
        glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        {
            PerfStats::Timer timer(perf, perf.current().renderUs);
            model.draw(viewProj.m);
        }

        if (hitW != pw || hitH != ph) {
            hitW = pw;
            hitH = ph;
            hitMask.assign(static_cast<size_t>(hitW) * hitH * 4, 0);
        }
        glReadBuffer(GL_BACK);
        {
            PerfStats::Timer timer(perf, perf.current().readbackUs);
            glReadPixels(0, 0, pw, ph, GL_RGBA, GL_UNSIGNED_BYTE, hitMask.data());
        }
        static bool hitMaskLogged = false;
        if (!hitMaskLogged && hitW > 0 && hitH > 0) {
            const int cx = hitW / 2;
            const int cy = hitH / 2;
            const unsigned char a = hitMask[(static_cast<size_t>(hitH - 1 - cy) * hitW + cx) * 4 + 3];
            SDL_Log("Hit mask ready: %dx%d center_alpha=%u", hitW, hitH, a);
            hitMaskLogged = true;
        }

        // The overlay owns the card when available.  Keep the fallback path
        // for machines where a second transparent GL window cannot be created.
        if (!spriteOverlay) sprite.draw(pw, ph);
        const SpriteLayer::PixelRect cardRect =
            sprite.visible() ? sprite.lastRect() : SpriteLayer::PixelRect{};
        if (std::getenv("WHALE3D_SPRITE_TRACE") && cardRect.width > 0 && cardRect.height > 0) {
            static int traceFrame = 0;
            if (traceFrame++ % 30 == 0) {
                SDL_Log("Sprite rect: (%d,%d %dx%d)",
                        cardRect.x, cardRect.y, cardRect.width, cardRect.height);
            }
        }
        static int regionFrame = 0;
        if (regionFrame++ % 6 == 0) {
            PerfStats::Timer timer(perf, perf.current().regionUs);
            if (spriteOverlay) {
                // Card pixels are intentionally excluded from the main
                // window region; the overlay window draws them and is
                // click-through.
                ui.updateWindowRegion(hitMask.data(), hitW, hitH, 0, 0, 0, 0);
            } else {
                ui.updateWindowRegion(hitMask.data(), hitW, hitH,
                                      cardRect.x, cardRect.y,
                                      cardRect.x + cardRect.width,
                                      cardRect.y + cardRect.height);
            }
        }
        if (spriteOverlay && cardRect.width > 0 &&
            (cardRect.x != overlayCardX || cardRect.y != overlayCardY ||
             cardRect.width != overlayCardW || cardRect.height != overlayCardH)) {
            PerfStats::Timer timer(perf, perf.current().regionUs);
            setOverlayCardRegion(cardRect);
            overlayCardX = cardRect.x;
            overlayCardY = cardRect.y;
            overlayCardW = cardRect.width;
            overlayCardH = cardRect.height;
        }

        {
            PerfStats::Timer timer(perf, perf.current().swapUs);
            SDL_GL_SwapWindow(win);
        }

        if (spriteOverlay && overlayWin && overlayCtx) {
            const bool mainHidden =
                (SDL_GetWindowFlags(win) & SDL_WINDOW_HIDDEN) != 0;
            const bool wantOverlay = !mainHidden && sprite.visible();
            if (wantOverlay) {
                if (!overlayShown) {
                    SDL_SetWindowPosition(overlayWin, winX, winY);
                    SDL_SetWindowAlwaysOnTop(overlayWin, true);
                    SDL_ShowWindow(overlayWin);
                    configureOverlayWindow(overlayWin);
                    overlayShown = true;
                    overlayX = winX;
                    overlayY = winY;
                } else if (overlayX != winX || overlayY != winY) {
                    SDL_SetWindowPosition(overlayWin, winX, winY);
                    overlayX = winX;
                    overlayY = winY;
                }
                SDL_GL_MakeCurrent(overlayWin, overlayCtx);
                int ow = 0, oh = 0;
                SDL_GetWindowSizeInPixels(overlayWin, &ow, &oh);
                glViewport(0, 0, ow, oh);
                glDisable(GL_DEPTH_TEST);
                glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
                glClear(GL_COLOR_BUFFER_BIT);
                {
                    PerfStats::Timer timer(perf, perf.current().overlayUs);
                    sprite.draw(ow, oh);
                    SDL_GL_SwapWindow(overlayWin);
                }
                SDL_GL_MakeCurrent(win, ctx);
                glEnable(GL_DEPTH_TEST);
            } else if (overlayShown) {
                SDL_HideWindow(overlayWin);
                overlayShown = false;
            }
        }

        ++frames;
        perf.endFrame();
        perf.maybeLog();
        Uint64 now = SDL_GetTicks();
        if (now - lastLog >= 1000) {
            float fps = static_cast<float>(frames) * 1000.0f / static_cast<float>(now - lastLog);
            double updateUs = updateFrames > 0
                ? (double)updateTicks * 1e6 / (double)perfFreq / (double)updateFrames
                : 0.0;
            SDL_Log("fps=%.1f triangles=%d update_us=%.2f animator=%s clip=%s face=%s",
                    fps, model.triangleCount(), updateUs, model.animatorName(),
                    model.clipName(), model.faceName());
            frames = 0;
            updateFrames = 0;
            updateTicks = 0;
            lastLog = now;
        }

        Uint64 target = 33;
        Uint64 elapsed = SDL_GetTicks() - now;
        if (elapsed < target) SDL_Delay(static_cast<Uint32>(target - elapsed));
    }

    if (spriteOverlay && overlayWin && overlayCtx) {
        SDL_GL_MakeCurrent(overlayWin, overlayCtx);
    } else {
        SDL_GL_MakeCurrent(win, ctx);
    }
    sprite.shutdown();
    if (overlayCtx) SDL_GL_DestroyContext(overlayCtx);
    if (overlayWin) SDL_DestroyWindow(overlayWin);
    ui.shutdown();
    emotionBus.stop();
    model.shutdown();
    SDL_GL_DestroyContext(ctx);
    SDL_DestroyWindow(win);
    SDL_Quit();
    return 0;
}
