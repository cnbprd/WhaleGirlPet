// WhaleGirl 3D base prototype.
// Goal: prove a small transparent, always-on-top OpenGL 3.3 window can run
// without pulling in a full game engine.

#define WIN32_LEAN_AND_MEAN
#include <SDL3/SDL.h>
#include <GL/gl.h>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>

// ---- Minimal GL 3.3 loader (only the entry points this prototype uses) ----
typedef ptrdiff_t GLsizeiptr;
typedef char GLchar;
typedef void (APIENTRY *PFNGLGENVERTEXARRAYS)(GLsizei, GLuint*);
typedef void (APIENTRY *PFNGLBINDVERTEXARRAY)(GLuint);
typedef void (APIENTRY *PFNGLDELETEVERTEXARRAYS)(GLsizei, const GLuint*);
typedef void (APIENTRY *PFNGLGENBUFFERS)(GLsizei, GLuint*);
typedef void (APIENTRY *PFNGLBINDBUFFER)(GLenum, GLuint);
typedef void (APIENTRY *PFNGLBUFFERDATA)(GLenum, GLsizeiptr, const void*, GLenum);
typedef void (APIENTRY *PFNGLDELETEBUFFERS)(GLsizei, const GLuint*);
typedef void (APIENTRY *PFNGLVERTEXATTRIBPOINTER)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void*);
typedef void (APIENTRY *PFNGLENABLEVERTEXATTRIBARRAY)(GLuint);
typedef GLuint (APIENTRY *PFNGLCREATESHADER)(GLenum);
typedef void (APIENTRY *PFNGLSHADERSOURCE)(GLuint, GLsizei, const GLchar* const*, const GLint*);
typedef void (APIENTRY *PFNGLCOMPILESHADER)(GLuint);
typedef void (APIENTRY *PFNGLGETSHADERIV)(GLuint, GLenum, GLint*);
typedef void (APIENTRY *PFNGLGETSHADERINFOLOG)(GLuint, GLsizei, GLsizei*, GLchar*);
typedef void (APIENTRY *PFNGLDELETESHADER)(GLuint);
typedef GLuint (APIENTRY *PFNGLCREATEPROGRAM)(void);
typedef void (APIENTRY *PFNGLATTACHSHADER)(GLuint, GLuint);
typedef void (APIENTRY *PFNGLLINKPROGRAM)(GLuint);
typedef void (APIENTRY *PFNGLGETPROGRAMIV)(GLuint, GLenum, GLint*);
typedef void (APIENTRY *PFNGLGETPROGRAMINFOLOG)(GLuint, GLsizei, GLsizei*, GLchar*);
typedef void (APIENTRY *PFNGLDELETEPROGRAM)(GLuint);
typedef void (APIENTRY *PFNGLUSEPROGRAM)(GLuint);
typedef GLint (APIENTRY *PFNGLGETUNIFORMLOCATION)(GLuint, const GLchar*);
typedef void (APIENTRY *PFNGLUNIFORMMATRIX4FV)(GLint, GLsizei, GLboolean, const GLfloat*);
typedef void (APIENTRY *PFNGLUNIFORM3F)(GLint, GLfloat, GLfloat, GLfloat);
typedef void (APIENTRY *PFNGLUNIFORM1F)(GLint, GLfloat);
typedef void (APIENTRY *PFNGLUNIFORM2F)(GLint, GLfloat, GLfloat);

#define GL_ARRAY_BUFFER 0x8892
#define GL_STATIC_DRAW 0x88E4
#define GL_FRAGMENT_SHADER 0x8B30
#define GL_VERTEX_SHADER 0x8B31
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82
#define GL_INFO_LOG_LENGTH 0x8B84
#define GL_MULTISAMPLE 0x809D

static PFNGLGENVERTEXARRAYS pglGenVertexArrays = nullptr;
static PFNGLBINDVERTEXARRAY pglBindVertexArray = nullptr;
static PFNGLDELETEVERTEXARRAYS pglDeleteVertexArrays = nullptr;
static PFNGLGENBUFFERS pglGenBuffers = nullptr;
static PFNGLBINDBUFFER pglBindBuffer = nullptr;
static PFNGLBUFFERDATA pglBufferData = nullptr;
static PFNGLDELETEBUFFERS pglDeleteBuffers = nullptr;
static PFNGLVERTEXATTRIBPOINTER pglVertexAttribPointer = nullptr;
static PFNGLENABLEVERTEXATTRIBARRAY pglEnableVertexAttribArray = nullptr;
static PFNGLCREATESHADER pglCreateShader = nullptr;
static PFNGLSHADERSOURCE pglShaderSource = nullptr;
static PFNGLCOMPILESHADER pglCompileShader = nullptr;
static PFNGLGETSHADERIV pglGetShaderiv = nullptr;
static PFNGLGETSHADERINFOLOG pglGetShaderInfoLog = nullptr;
static PFNGLDELETESHADER pglDeleteShader = nullptr;
static PFNGLCREATEPROGRAM pglCreateProgram = nullptr;
static PFNGLATTACHSHADER pglAttachShader = nullptr;
static PFNGLLINKPROGRAM pglLinkProgram = nullptr;
static PFNGLGETPROGRAMIV pglGetProgramiv = nullptr;
static PFNGLGETPROGRAMINFOLOG pglGetProgramInfoLog = nullptr;
static PFNGLDELETEPROGRAM pglDeleteProgram = nullptr;
static PFNGLUSEPROGRAM pglUseProgram = nullptr;
static PFNGLGETUNIFORMLOCATION pglGetUniformLocation = nullptr;
static PFNGLUNIFORMMATRIX4FV pglUniformMatrix4fv = nullptr;
static PFNGLUNIFORM3F pglUniform3f = nullptr;
static PFNGLUNIFORM1F pglUniform1f = nullptr;
static PFNGLUNIFORM2F pglUniform2f = nullptr;

template <typename T>
static bool loadGL(T& out, const char* name) {
    out = reinterpret_cast<T>(SDL_GL_GetProcAddress(name));
    if (!out) {
        SDL_Log("Missing OpenGL entry point: %s", name);
        return false;
    }
    return true;
}

static bool loadGLFunctions() {
    return loadGL(pglGenVertexArrays, "glGenVertexArrays")
        && loadGL(pglBindVertexArray, "glBindVertexArray")
        && loadGL(pglDeleteVertexArrays, "glDeleteVertexArrays")
        && loadGL(pglGenBuffers, "glGenBuffers")
        && loadGL(pglBindBuffer, "glBindBuffer")
        && loadGL(pglBufferData, "glBufferData")
        && loadGL(pglDeleteBuffers, "glDeleteBuffers")
        && loadGL(pglVertexAttribPointer, "glVertexAttribPointer")
        && loadGL(pglEnableVertexAttribArray, "glEnableVertexAttribArray")
        && loadGL(pglCreateShader, "glCreateShader")
        && loadGL(pglShaderSource, "glShaderSource")
        && loadGL(pglCompileShader, "glCompileShader")
        && loadGL(pglGetShaderiv, "glGetShaderiv")
        && loadGL(pglGetShaderInfoLog, "glGetShaderInfoLog")
        && loadGL(pglDeleteShader, "glDeleteShader")
        && loadGL(pglCreateProgram, "glCreateProgram")
        && loadGL(pglAttachShader, "glAttachShader")
        && loadGL(pglLinkProgram, "glLinkProgram")
        && loadGL(pglGetProgramiv, "glGetProgramiv")
        && loadGL(pglGetProgramInfoLog, "glGetProgramInfoLog")
        && loadGL(pglDeleteProgram, "glDeleteProgram")
        && loadGL(pglUseProgram, "glUseProgram")
        && loadGL(pglGetUniformLocation, "glGetUniformLocation")
        && loadGL(pglUniformMatrix4fv, "glUniformMatrix4fv")
        && loadGL(pglUniform3f, "glUniform3f")
        && loadGL(pglUniform1f, "glUniform1f")
        && loadGL(pglUniform2f, "glUniform2f");
}

// ---- Tiny column-major matrix math ----
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

static Mat4 translate(float x, float y, float z) {
    Mat4 r = identity();
    r.m[12] = x; r.m[13] = y; r.m[14] = z;
    return r;
}

static Mat4 rotateX(float rad) {
    Mat4 r = identity();
    float c = std::cos(rad), s = std::sin(rad);
    r.m[5] = c; r.m[6] = s; r.m[9] = -s; r.m[10] = c;
    return r;
}

static Mat4 rotateY(float rad) {
    Mat4 r = identity();
    float c = std::cos(rad), s = std::sin(rad);
    r.m[0] = c; r.m[2] = -s; r.m[8] = s; r.m[10] = c;
    return r;
}

static Mat4 scale3(float s) {
    Mat4 r = identity();
    r.m[0] = s; r.m[5] = s; r.m[10] = s;
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

// ---- Shader helpers ----
static GLuint compileShader(GLenum type, const char* src) {
    GLuint s = pglCreateShader(type);
    pglShaderSource(s, 1, &src, nullptr);
    pglCompileShader(s);
    GLint ok = 0;
    pglGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        GLint len = 0;
        pglGetShaderiv(s, GL_INFO_LOG_LENGTH, &len);
        char* log = static_cast<char*>(std::malloc(len > 1 ? len : 1));
        pglGetShaderInfoLog(s, len, nullptr, log);
        SDL_Log("Shader compile failed: %s", log);
        std::free(log);
        pglDeleteShader(s);
        return 0;
    }
    return s;
}

static GLuint makeProgram(const char* vs, const char* fs) {
    GLuint v = compileShader(GL_VERTEX_SHADER, vs);
    GLuint f = compileShader(GL_FRAGMENT_SHADER, fs);
    if (!v || !f) return 0;
    GLuint p = pglCreateProgram();
    pglAttachShader(p, v);
    pglAttachShader(p, f);
    pglLinkProgram(p);
    pglDeleteShader(v);
    pglDeleteShader(f);
    GLint ok = 0;
    pglGetProgramiv(p, GL_LINK_STATUS, &ok);
    if (!ok) {
        GLint len = 0;
        pglGetProgramiv(p, GL_INFO_LOG_LENGTH, &len);
        char* log = static_cast<char*>(std::malloc(len > 1 ? len : 1));
        pglGetProgramInfoLog(p, len, nullptr, log);
        SDL_Log("Program link failed: %s", log);
        std::free(log);
        pglDeleteProgram(p);
        return 0;
    }
    return p;
}

// ---- Cube geometry: 6 faces, per-face normal, 36 vertices ----
struct Vec3 { float x, y, z; };
struct Vertex { Vec3 p; Vec3 n; };

static const Vertex kCube[] = {
    // +Z
    {{-0.5f,-0.5f, 0.5f},{0,0,1}}, {{ 0.5f,-0.5f, 0.5f},{0,0,1}}, {{ 0.5f, 0.5f, 0.5f},{0,0,1}},
    {{-0.5f,-0.5f, 0.5f},{0,0,1}}, {{ 0.5f, 0.5f, 0.5f},{0,0,1}}, {{-0.5f, 0.5f, 0.5f},{0,0,1}},
    // -Z
    {{ 0.5f,-0.5f,-0.5f},{0,0,-1}}, {{-0.5f,-0.5f,-0.5f},{0,0,-1}}, {{-0.5f, 0.5f,-0.5f},{0,0,-1}},
    {{ 0.5f,-0.5f,-0.5f},{0,0,-1}}, {{-0.5f, 0.5f,-0.5f},{0,0,-1}}, {{ 0.5f, 0.5f,-0.5f},{0,0,-1}},
    // +X
    {{ 0.5f,-0.5f, 0.5f},{1,0,0}}, {{ 0.5f,-0.5f,-0.5f},{1,0,0}}, {{ 0.5f, 0.5f,-0.5f},{1,0,0}},
    {{ 0.5f,-0.5f, 0.5f},{1,0,0}}, {{ 0.5f, 0.5f,-0.5f},{1,0,0}}, {{ 0.5f, 0.5f, 0.5f},{1,0,0}},
    // -X
    {{-0.5f,-0.5f,-0.5f},{-1,0,0}}, {{-0.5f,-0.5f, 0.5f},{-1,0,0}}, {{-0.5f, 0.5f, 0.5f},{-1,0,0}},
    {{-0.5f,-0.5f,-0.5f},{-1,0,0}}, {{-0.5f, 0.5f, 0.5f},{-1,0,0}}, {{-0.5f, 0.5f,-0.5f},{-1,0,0}},
    // +Y
    {{-0.5f, 0.5f, 0.5f},{0,1,0}}, {{ 0.5f, 0.5f, 0.5f},{0,1,0}}, {{ 0.5f, 0.5f,-0.5f},{0,1,0}},
    {{-0.5f, 0.5f, 0.5f},{0,1,0}}, {{ 0.5f, 0.5f,-0.5f},{0,1,0}}, {{-0.5f, 0.5f,-0.5f},{0,1,0}},
    // -Y
    {{-0.5f,-0.5f,-0.5f},{0,-1,0}}, {{ 0.5f,-0.5f,-0.5f},{0,-1,0}}, {{ 0.5f,-0.5f, 0.5f},{0,-1,0}},
    {{-0.5f,-0.5f,-0.5f},{0,-1,0}}, {{ 0.5f,-0.5f, 0.5f},{0,-1,0}}, {{-0.5f,-0.5f, 0.5f},{0,-1,0}},
};

static const char* kVS = R"(
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
uniform mat4 uMVP;
uniform mat4 uModel;
out vec3 vNormal;
out vec3 vWorldPos;
void main() {
    vec4 world = uModel * vec4(aPos, 1.0);
    vWorldPos = world.xyz;
    vNormal = mat3(uModel) * aNormal;
    gl_Position = uMVP * vec4(aPos, 1.0);
}
)";

static const char* kFS = R"(
#version 330 core
in vec3 vNormal;
in vec3 vWorldPos;
uniform vec3 uColor;
uniform vec3 uLightDir;
uniform float uAlpha;
out vec4 fragColor;
void main() {
    vec3 n = normalize(vNormal);
    float ndl = max(dot(n, normalize(uLightDir)), 0.0);
    float rim = pow(1.0 - max(dot(n, vec3(0.0, 0.0, 1.0)), 0.0), 2.0);
    vec3 lit = uColor * (0.42 + 0.58 * ndl) + vec3(0.16, 0.30, 0.38) * rim * 0.55;
    fragColor = vec4(lit, uAlpha);
}
)";

static void printGLInfo() {
    const GLubyte* vendor = glGetString(GL_VENDOR);
    const GLubyte* renderer = glGetString(GL_RENDERER);
    const GLubyte* version = glGetString(GL_VERSION);
    SDL_Log("GL vendor  : %s", vendor ? reinterpret_cast<const char*>(vendor) : "?");
    SDL_Log("GL renderer: %s", renderer ? reinterpret_cast<const char*>(renderer) : "?");
    SDL_Log("GL version : %s", version ? reinterpret_cast<const char*>(version) : "?");
}

int main(int, char**) {
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
    const int winH = 560;
    SDL_WindowFlags flags = static_cast<SDL_WindowFlags>(
        SDL_WINDOW_OPENGL | SDL_WINDOW_TRANSPARENT | SDL_WINDOW_BORDERLESS |
        SDL_WINDOW_ALWAYS_ON_TOP | SDL_WINDOW_HIGH_PIXEL_DENSITY |
        SDL_WINDOW_NOT_FOCUSABLE);

    SDL_Window* win = SDL_CreateWindow("WhaleGirl 3D Base", winW, winH, flags);
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

    if (!loadGLFunctions()) {
        SDL_GL_DestroyContext(ctx);
        SDL_DestroyWindow(win);
        SDL_Quit();
        return 1;
    }
    printGLInfo();

    GLuint cubeProg = makeProgram(kVS, kFS);
    if (!cubeProg) {
        SDL_GL_DestroyContext(ctx);
        SDL_DestroyWindow(win);
        SDL_Quit();
        return 1;
    }

    GLuint vao = 0, vbo = 0;
    pglGenVertexArrays(1, &vao);
    pglBindVertexArray(vao);
    pglGenBuffers(1, &vbo);
    pglBindBuffer(GL_ARRAY_BUFFER, vbo);
    pglBufferData(GL_ARRAY_BUFFER, sizeof(kCube), kCube, GL_STATIC_DRAW);
    pglEnableVertexAttribArray(0);
    pglVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<void*>(offsetof(Vertex, p)));
    pglEnableVertexAttribArray(1);
    pglVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<void*>(offsetof(Vertex, n)));

    glEnable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glEnable(GL_MULTISAMPLE);

    GLint uMVP = pglGetUniformLocation(cubeProg, "uMVP");
    GLint uModel = pglGetUniformLocation(cubeProg, "uModel");
    GLint uColor = pglGetUniformLocation(cubeProg, "uColor");
    GLint uLightDir = pglGetUniformLocation(cubeProg, "uLightDir");
    GLint uAlpha = pglGetUniformLocation(cubeProg, "uAlpha");

    const float eye[3] = { 0.0f, 1.15f, 3.4f };
    const float center[3] = { 0.0f, 0.0f, 0.0f };
    const float up[3] = { 0.0f, 1.0f, 0.0f };
    Mat4 view = lookAt(eye, center, up);

    bool running = true;
    bool dragging = false;
    float dragStartX = 0.0f, dragStartY = 0.0f;
    int winStartX = 0, winStartY = 0;
    Uint64 start = SDL_GetTicks();
    Uint64 lastLog = start;
    int frames = 0;
    float fps = 0.0f;

    while (running) {
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_EVENT_QUIT) {
                running = false;
            } else if (ev.type == SDL_EVENT_KEY_DOWN) {
                if (ev.key.key == SDLK_ESCAPE) running = false;
            } else if (ev.type == SDL_EVENT_MOUSE_BUTTON_DOWN && ev.button.button == SDL_BUTTON_RIGHT) {
                running = false;
            } else if (ev.type == SDL_EVENT_MOUSE_BUTTON_DOWN && ev.button.button == SDL_BUTTON_LEFT) {
                dragging = true;
                SDL_GetGlobalMouseState(&dragStartX, &dragStartY);
                SDL_GetWindowPosition(win, &winStartX, &winStartY);
                SDL_CaptureMouse(true);
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
        if (pw <= 0 || ph <= 0) { SDL_Delay(16); continue; }

        float t = static_cast<float>(SDL_GetTicks() - start) / 1000.0f;
        float bob = std::sin(t * 1.6f) * 0.045f;
        Mat4 model = multiply(translate(0.0f, bob, 0.0f),
                              multiply(rotateY(0.55f + std::sin(t * 0.45f) * 0.40f),
                                       multiply(rotateX(0.28f + std::sin(t * 0.7f) * 0.05f),
                                                scale3(0.88f))));
        Mat4 proj = perspective(38.0f * 3.14159265f / 180.0f, static_cast<float>(pw) / static_cast<float>(ph), 0.1f, 20.0f);
        Mat4 mvp = multiply(proj, multiply(view, model));

        glViewport(0, 0, pw, ph);
        glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        pglUseProgram(cubeProg);
        pglUniformMatrix4fv(uMVP, 1, GL_FALSE, mvp.m);
        pglUniformMatrix4fv(uModel, 1, GL_FALSE, model.m);
        pglUniform3f(uColor, 0.38f, 0.76f, 0.82f);
        pglUniform3f(uLightDir, -0.45f, 0.75f, 0.65f);
        pglUniform1f(uAlpha, 1.0f);
        pglBindVertexArray(vao);
        glDrawArrays(GL_TRIANGLES, 0, 36);

        SDL_GL_SwapWindow(win);
        ++frames;
        Uint64 now = SDL_GetTicks();
        if (now - lastLog >= 1000) {
            fps = static_cast<float>(frames) * 1000.0f / static_cast<float>(now - lastLog);
            SDL_Log("fps=%.1f window=%dx%d", fps, pw, ph);
            frames = 0;
            lastLog = now;
        }

        // Cap at ~30fps: a desktop pet does not need 120fps.
        Uint64 frameEnd = SDL_GetTicks();
        Uint64 target = 33;
        Uint64 elapsed = frameEnd - now;
        if (elapsed < target) SDL_Delay(static_cast<Uint32>(target - elapsed));
    }

    pglDeleteBuffers(1, &vbo);
    pglDeleteVertexArrays(1, &vao);
    pglDeleteProgram(cubeProg);

    SDL_GL_DestroyContext(ctx);
    SDL_DestroyWindow(win);
    SDL_Quit();
    return 0;
}
