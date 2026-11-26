// WhaleGirl 3D stage 2: transparent SDL3/OpenGL shell + a skinned low-poly
// glTF placeholder.  No engine, no VRM runtime, no Qt.

#define WIN32_LEAN_AND_MEAN
#include <SDL3/SDL.h>
#include <GL/gl.h>

#include "model.h"
#include "shell_ui.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

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

int main(int argc, char** argv) {
    if (argc >= 2 && std::strcmp(argv[1], "--relaunch") == 0) {
        return runRelaunchHelper(argc, argv);
    }

    if (!SDL_Init(SDL_INIT_VIDEO)) {
        SDL_Log("SDL_Init failed: %s", SDL_GetError());
        return 1;
    }

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

    SDL_Window* win = SDL_CreateWindow("WhaleGirl 3D Placeholder", winW, winH, flags);
    if (!win) {
        SDL_Log("SDL_CreateWindow failed: %s", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    SDL_DisplayID display = SDL_GetPrimaryDisplay();
    SDL_Rect usable{};
    if (SDL_GetDisplayUsableBounds(display, &usable)) {
        SDL_SetWindowPosition(win, usable.x + usable.w - winW - 80,
                                   usable.y + usable.h - winH - 30);
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
    std::string modelPath = argc > 1 ? argv[1] : base + "assets/models/whale_girl.glb";
    Model model;
    if (!model.load(modelPath)) {
        SDL_Log("Primary model load failed: %s", model.error().c_str());
        modelPath = base + "assets/models/placeholder.glb";
        if (!model.load(modelPath)) {
            SDL_Log("Fallback model load failed: %s", model.error().c_str());
            SDL_GL_DestroyContext(ctx);
            SDL_DestroyWindow(win);
            SDL_Quit();
            return 1;
        }
    }
    SDL_Log("Model loaded: %s (%d triangles, %d joints, %d animations)",
            modelPath.c_str(), model.triangleCount(), model.jointCount(), model.animationCount());

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
    Uint64 start = SDL_GetTicks();
    Uint64 lastLog = start;
    int frames = 0;
    Uint64 perfFreq = SDL_GetPerformanceFrequency();
    Uint64 updateTicks = 0;
    int updateFrames = 0;

    while (running && !ui.quitRequested()) {
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

        int pw = 0, ph = 0;
        SDL_GetWindowSizeInPixels(win, &pw, &ph);
        if (pw <= 0 || ph <= 0) {
            SDL_Delay(16);
            continue;
        }

        float t = static_cast<float>(SDL_GetTicks() - start) / 1000.0f;
        Uint64 updateStart = SDL_GetPerformanceCounter();
        model.update(t);
        updateTicks += SDL_GetPerformanceCounter() - updateStart;
        ++updateFrames;

        Mat4 proj = perspective(35.0f * 3.14159265f / 180.0f,
                                static_cast<float>(pw) / static_cast<float>(ph), 0.1f, 20.0f);
        Mat4 viewProj = multiply(proj, view);

        glViewport(0, 0, pw, ph);
        glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        model.draw(viewProj.m);

        if (hitW != pw || hitH != ph) {
            hitW = pw;
            hitH = ph;
            hitMask.assign(static_cast<size_t>(hitW) * hitH * 4, 0);
        }
        glReadBuffer(GL_BACK);
        glReadPixels(0, 0, pw, ph, GL_RGBA, GL_UNSIGNED_BYTE, hitMask.data());
        static bool hitMaskLogged = false;
        if (!hitMaskLogged && hitW > 0 && hitH > 0) {
            const int cx = hitW / 2;
            const int cy = hitH / 2;
            const unsigned char a = hitMask[(static_cast<size_t>(hitH - 1 - cy) * hitW + cx) * 4 + 3];
            SDL_Log("Hit mask ready: %dx%d center_alpha=%u", hitW, hitH, a);
            hitMaskLogged = true;
        }
        static int regionFrame = 0;
        if (regionFrame++ % 6 == 0) {
            ui.updateWindowRegion(hitMask.data(), hitW, hitH);
        }

        SDL_GL_SwapWindow(win);

        ++frames;
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

    ui.shutdown();
    model.shutdown();
    SDL_GL_DestroyContext(ctx);
    SDL_DestroyWindow(win);
    SDL_Quit();
    return 0;
}
