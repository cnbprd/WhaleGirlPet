#include "sprite.h"

#include <SDL3/SDL.h>
#include <GL/gl.h>

#include "third_party/json.hpp"
#include "third_party/stb_image.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#ifndef GL_ARRAY_BUFFER
#define GL_ARRAY_BUFFER 0x8892
#endif
#ifndef GL_STATIC_DRAW
#define GL_STATIC_DRAW 0x88E4
#endif
#ifndef GL_FRAGMENT_SHADER
#define GL_FRAGMENT_SHADER 0x8B30
#endif
#ifndef GL_VERTEX_SHADER
#define GL_VERTEX_SHADER 0x8B31
#endif
#ifndef GL_COMPILE_STATUS
#define GL_COMPILE_STATUS 0x8B81
#endif
#ifndef GL_LINK_STATUS
#define GL_LINK_STATUS 0x8B82
#endif
#ifndef GL_INFO_LOG_LENGTH
#define GL_INFO_LOG_LENGTH 0x8B84
#endif
#ifndef GL_TEXTURE0
#define GL_TEXTURE0 0x84C0
#endif
#ifndef GL_CLAMP_TO_EDGE
#define GL_CLAMP_TO_EDGE 0x812F
#endif
#ifndef GL_TRIANGLE_STRIP
#define GL_TRIANGLE_STRIP 0x0005
#endif

typedef ptrdiff_t GLsizeiptr;
typedef char GLchar;
typedef void (APIENTRY* PFNGLGENVERTEXARRAYS)(GLsizei, GLuint*);
typedef void (APIENTRY* PFNGLBINDVERTEXARRAY)(GLuint);
typedef void (APIENTRY* PFNGLDELETEVERTEXARRAYS)(GLsizei, const GLuint*);
typedef void (APIENTRY* PFNGLGENBUFFERS)(GLsizei, GLuint*);
typedef void (APIENTRY* PFNGLBINDBUFFER)(GLenum, GLuint);
typedef void (APIENTRY* PFNGLBUFFERDATA)(GLenum, GLsizeiptr, const void*, GLenum);
typedef void (APIENTRY* PFNGLDELETEBUFFERS)(GLsizei, const GLuint*);
typedef void (APIENTRY* PFNGLVERTEXATTRIBPOINTER)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void*);
typedef void (APIENTRY* PFNGLENABLEVERTEXATTRIBARRAY)(GLuint);
typedef GLuint (APIENTRY* PFNGLCREATESHADER)(GLenum);
typedef void (APIENTRY* PFNGLSHADERSOURCE)(GLuint, GLsizei, const GLchar* const*, const GLint*);
typedef void (APIENTRY* PFNGLCOMPILESHADER)(GLuint);
typedef void (APIENTRY* PFNGLGETSHADERIV)(GLuint, GLenum, GLint*);
typedef void (APIENTRY* PFNGLGETSHADERINFOLOG)(GLuint, GLsizei, GLsizei*, GLchar*);
typedef void (APIENTRY* PFNGLDELETESHADER)(GLuint);
typedef GLuint (APIENTRY* PFNGLCREATEPROGRAM)(void);
typedef void (APIENTRY* PFNGLATTACHSHADER)(GLuint, GLuint);
typedef void (APIENTRY* PFNGLLINKPROGRAM)(GLuint);
typedef void (APIENTRY* PFNGLGETPROGRAMIV)(GLuint, GLenum, GLint*);
typedef void (APIENTRY* PFNGLGETPROGRAMINFOLOG)(GLuint, GLsizei, GLsizei*, GLchar*);
typedef void (APIENTRY* PFNGLDELETEPROGRAM)(GLuint);
typedef void (APIENTRY* PFNGLUSEPROGRAM)(GLuint);
typedef GLint (APIENTRY* PFNGLGETUNIFORMLOCATION)(GLuint, const GLchar*);
typedef void (APIENTRY* PFNGLUNIFORM1I)(GLint, GLint);
typedef void (APIENTRY* PFNGLUNIFORM1F)(GLint, GLfloat);
typedef void (APIENTRY* PFNGLUNIFORM4F)(GLint, GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (APIENTRY* PFNGLACTIVETEXTURE)(GLenum);
typedef void (APIENTRY* PFNGLGENERATEMIPMAP)(GLenum);

namespace {
struct Gl {
    PFNGLGENVERTEXARRAYS genVertexArrays = nullptr;
    PFNGLBINDVERTEXARRAY bindVertexArray = nullptr;
    PFNGLDELETEVERTEXARRAYS deleteVertexArrays = nullptr;
    PFNGLGENBUFFERS genBuffers = nullptr;
    PFNGLBINDBUFFER bindBuffer = nullptr;
    PFNGLBUFFERDATA bufferData = nullptr;
    PFNGLDELETEBUFFERS deleteBuffers = nullptr;
    PFNGLVERTEXATTRIBPOINTER vertexAttribPointer = nullptr;
    PFNGLENABLEVERTEXATTRIBARRAY enableVertexAttribArray = nullptr;
    PFNGLCREATESHADER createShader = nullptr;
    PFNGLSHADERSOURCE shaderSource = nullptr;
    PFNGLCOMPILESHADER compileShader = nullptr;
    PFNGLGETSHADERIV getShaderiv = nullptr;
    PFNGLGETSHADERINFOLOG getShaderInfoLog = nullptr;
    PFNGLDELETESHADER deleteShader = nullptr;
    PFNGLCREATEPROGRAM createProgram = nullptr;
    PFNGLATTACHSHADER attachShader = nullptr;
    PFNGLLINKPROGRAM linkProgram = nullptr;
    PFNGLGETPROGRAMIV getProgramiv = nullptr;
    PFNGLGETPROGRAMINFOLOG getProgramInfoLog = nullptr;
    PFNGLDELETEPROGRAM deleteProgram = nullptr;
    PFNGLUSEPROGRAM useProgram = nullptr;
    PFNGLGETUNIFORMLOCATION getUniformLocation = nullptr;
    PFNGLUNIFORM1I uniform1i = nullptr;
    PFNGLUNIFORM1F uniform1f = nullptr;
    PFNGLUNIFORM4F uniform4f = nullptr;
    PFNGLACTIVETEXTURE activeTexture = nullptr;
    PFNGLGENERATEMIPMAP generateMipmap = nullptr;

    template <typename T>
    bool loadOne(T& fn, const char* name) {
        fn = reinterpret_cast<T>(SDL_GL_GetProcAddress(name));
        return fn != nullptr;
    }

    bool load() {
        return loadOne(genVertexArrays, "glGenVertexArrays")
            && loadOne(bindVertexArray, "glBindVertexArray")
            && loadOne(deleteVertexArrays, "glDeleteVertexArrays")
            && loadOne(genBuffers, "glGenBuffers")
            && loadOne(bindBuffer, "glBindBuffer")
            && loadOne(bufferData, "glBufferData")
            && loadOne(deleteBuffers, "glDeleteBuffers")
            && loadOne(vertexAttribPointer, "glVertexAttribPointer")
            && loadOne(enableVertexAttribArray, "glEnableVertexAttribArray")
            && loadOne(createShader, "glCreateShader")
            && loadOne(shaderSource, "glShaderSource")
            && loadOne(compileShader, "glCompileShader")
            && loadOne(getShaderiv, "glGetShaderiv")
            && loadOne(getShaderInfoLog, "glGetShaderInfoLog")
            && loadOne(deleteShader, "glDeleteShader")
            && loadOne(createProgram, "glCreateProgram")
            && loadOne(attachShader, "glAttachShader")
            && loadOne(linkProgram, "glLinkProgram")
            && loadOne(getProgramiv, "glGetProgramiv")
            && loadOne(getProgramInfoLog, "glGetProgramInfoLog")
            && loadOne(deleteProgram, "glDeleteProgram")
            && loadOne(useProgram, "glUseProgram")
            && loadOne(getUniformLocation, "glGetUniformLocation")
            && loadOne(uniform1i, "glUniform1i")
            && loadOne(uniform1f, "glUniform1f")
            && loadOne(uniform4f, "glUniform4f")
            && loadOne(activeTexture, "glActiveTexture")
            && loadOne(generateMipmap, "glGenerateMipmap");
    }
};

const char* kVert = R"(
#version 330 core
layout(location = 0) in vec2 aPos;
layout(location = 1) in vec2 aUv;
uniform vec4 uRect;
uniform vec4 uUvRect;
out vec2 vUv;
void main() {
    gl_Position = vec4(uRect.xy + aPos * uRect.zw, 0.0, 1.0);
    vUv = uUvRect.xy + aUv * uUvRect.zw;
}
)";

const char* kFrag = R"(
#version 330 core
uniform sampler2D uTex;
uniform float uAlpha;
in vec2 vUv;
out vec4 FragColor;
void main() {
    vec4 c = texture(uTex, vUv);
    FragColor = vec4(c.rgb, c.a * uAlpha);
}
)";
}  // namespace

struct SpriteLayer::Impl {
    Gl gl;
    struct Rect {
        float u0 = 0.0f;
        float v0 = 0.0f;
        float u1 = 0.0f;
        float v1 = 0.0f;
        int w = 0;
        int h = 0;
    };
    std::unordered_map<std::string, Rect> cards;
    GLuint program = 0;
    GLuint vao = 0;
    GLuint vbo = 0;
    GLuint texture = 0;
    GLint uRect = -1;
    GLint uUvRect = -1;
    GLint uTex = -1;
    GLint uAlpha = -1;
    std::string current;
    std::string error;
    float ttl = 0.0f;
    float age = 0.0f;
    PixelRect lastRect;

    bool active() const { return !current.empty() && age < ttl; }

    void clearGl() {
        if (vbo && gl.deleteBuffers) gl.deleteBuffers(1, &vbo);
        if (vao && gl.deleteVertexArrays) gl.deleteVertexArrays(1, &vao);
        if (program && gl.deleteProgram) gl.deleteProgram(program);
        if (texture) glDeleteTextures(1, &texture);
        vbo = vao = program = texture = 0;
    }

    GLuint compile(GLenum type, const char* src, std::string& err) {
        GLuint shader = gl.createShader(type);
        gl.shaderSource(shader, 1, &src, nullptr);
        gl.compileShader(shader);
        GLint ok = 0;
        gl.getShaderiv(shader, GL_COMPILE_STATUS, &ok);
        if (!ok) {
            GLint logLen = 0;
            gl.getShaderiv(shader, GL_INFO_LOG_LENGTH, &logLen);
            std::string log(static_cast<size_t>(std::max(0, logLen)), '\0');
            if (logLen > 0) gl.getShaderInfoLog(shader, logLen, nullptr, log.data());
            err = "shader compile: " + log;
            gl.deleteShader(shader);
            return 0;
        }
        return shader;
    }

    bool buildProgram(std::string& err) {
        GLuint vs = compile(GL_VERTEX_SHADER, kVert, err);
        if (!vs) return false;
        GLuint fs = compile(GL_FRAGMENT_SHADER, kFrag, err);
        if (!fs) {
            gl.deleteShader(vs);
            return false;
        }
        program = gl.createProgram();
        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);
        gl.deleteShader(vs);
        gl.deleteShader(fs);
        GLint ok = 0;
        gl.getProgramiv(program, GL_LINK_STATUS, &ok);
        if (!ok) {
            GLint logLen = 0;
            gl.getProgramiv(program, GL_INFO_LOG_LENGTH, &logLen);
            std::string log(static_cast<size_t>(std::max(0, logLen)), '\0');
            if (logLen > 0) gl.getProgramInfoLog(program, logLen, nullptr, log.data());
            err = "program link: " + log;
            gl.deleteProgram(program);
            program = 0;
            return false;
        }
        uRect = gl.getUniformLocation(program, "uRect");
        uUvRect = gl.getUniformLocation(program, "uUvRect");
        uTex = gl.getUniformLocation(program, "uTex");
        uAlpha = gl.getUniformLocation(program, "uAlpha");
        return true;
    }

    bool buildGeometry() {
        gl.genVertexArrays(1, &vao);
        gl.bindVertexArray(vao);
        gl.genBuffers(1, &vbo);
        gl.bindBuffer(GL_ARRAY_BUFFER, vbo);
        // unit quad: x,y,u,v
        const float verts[] = {
            0.0f, 0.0f, 0.0f, 0.0f,
            1.0f, 0.0f, 1.0f, 0.0f,
            1.0f, 1.0f, 1.0f, 1.0f,
            0.0f, 1.0f, 0.0f, 1.0f,
        };
        gl.bufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STATIC_DRAW);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), nullptr);
        gl.enableVertexAttribArray(1);
        gl.vertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float),
                               reinterpret_cast<const void*>(2 * sizeof(float)));
        gl.bindVertexArray(0);
        return true;
    }

    bool loadAtlas(const std::string& assetBase, std::string& err) {
        const std::string manifestPath = assetBase + "assets/2d_bridge/manifest.json";
        std::ifstream file(manifestPath);
        if (!file) {
            err = "manifest missing: " + manifestPath;
            return false;
        }
        nlohmann::json j;
        try {
            file >> j;
        } catch (const std::exception& e) {
            err = std::string("manifest JSON: ") + e.what();
            return false;
        }
        const int sheetW = j.at("sheet_size")[0].get<int>();
        const int sheetH = j.at("sheet_size")[1].get<int>();
        for (const auto& entry : j.at("cards")) {
            const std::string id = entry.at("id").get<std::string>();
            const auto& r = entry.at("rect");
            const int x = r[0].get<int>();
            const int y = r[1].get<int>();
            const int w = r[2].get<int>();
            const int h = r[3].get<int>();
            if (w <= 0 || h <= 0 || x < 0 || y < 0 || x + w > sheetW || y + h > sheetH) {
                err = "card outside atlas: " + id;
                return false;
            }
            Rect rect;
            rect.u0 = static_cast<float>(x) / sheetW;
            rect.u1 = static_cast<float>(x + w) / sheetW;
            // stb rows are top-down and the first uploaded row lands at GL
            // texture v=0; keep v0 as the image top and v1 as the image bottom.
            rect.v0 = static_cast<float>(y) / sheetH;
            rect.v1 = static_cast<float>(y + h) / sheetH;
            rect.w = w;
            rect.h = h;
            cards[id] = rect;
        }

        const std::string atlasPath = assetBase + j.at("sheet").get<std::string>();
        int w = 0, h = 0, n = 0;
        stbi_set_flip_vertically_on_load(0);
        unsigned char* pixels = stbi_load(atlasPath.c_str(), &w, &h, &n, 4);
        if (!pixels) {
            err = "atlas decode failed: " + atlasPath;
            return false;
        }
        glGenTextures(1, &texture);
        glBindTexture(GL_TEXTURE_2D, texture);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA,
                     GL_UNSIGNED_BYTE, pixels);
        glBindTexture(GL_TEXTURE_2D, 0);
        stbi_image_free(pixels);
        if (w != sheetW || h != sheetH) {
            err = "atlas size mismatch";
            return false;
        }
        return true;
    }
};

SpriteLayer::SpriteLayer() : impl_(new Impl()) {}

SpriteLayer::~SpriteLayer() {
    shutdown();
    delete impl_;
}

bool SpriteLayer::init(const std::string& assetBase) {
    if (!impl_) return false;
    impl_->error.clear();
    if (!impl_->gl.load()) {
        impl_->error = "missing GL entry point";
        return false;
    }
    if (!impl_->buildProgram(impl_->error)) return false;
    if (!impl_->buildGeometry()) {
        impl_->error = "geometry setup failed";
        return false;
    }
    if (!impl_->loadAtlas(assetBase, impl_->error)) {
        impl_->clearGl();
        return false;
    }
    return true;
}

void SpriteLayer::shutdown() {
    if (!impl_) return;
    impl_->clearGl();
    impl_->cards.clear();
    impl_->current.clear();
    impl_->ttl = 0.0f;
    impl_->age = 0.0f;
}

bool SpriteLayer::showCard(const std::string& cardId, float ttlMs) {
    if (!impl_ || cardId.empty()) return false;
    auto it = impl_->cards.find(cardId);
    if (it == impl_->cards.end()) return false;
    impl_->current = cardId;
    impl_->ttl = std::clamp(ttlMs / 1000.0f, 0.2f, 10.0f);
    impl_->age = 0.0f;
    return true;
}

void SpriteLayer::update(float dtSeconds) {
    if (!impl_ || !impl_->active()) return;
    impl_->age += std::max(0.0f, dtSeconds);
}

void SpriteLayer::draw(int pixelWidth, int pixelHeight) {
    if (!impl_ || pixelWidth <= 0 || pixelHeight <= 0 || !impl_->active()) return;
    const auto& rect = impl_->cards[impl_->current];
    const float cardH = std::min(220.0f, pixelHeight * 0.36f);
    const float cardW = cardH * static_cast<float>(rect.w) / static_cast<float>(rect.h);
    const float margin = 12.0f;
    const float px = static_cast<float>(pixelWidth) - cardW - margin;
    const float py = margin;
    const float ndcX = 2.0f * px / pixelWidth - 1.0f;
    const float ndcY = 2.0f * py / pixelHeight - 1.0f;
    const float ndcW = 2.0f * cardW / pixelWidth;
    const float ndcH = 2.0f * cardH / pixelHeight;
    impl_->lastRect.x = static_cast<int>(px);
    impl_->lastRect.y = static_cast<int>(pixelHeight - py - cardH);
    impl_->lastRect.width = static_cast<int>(cardW);
    impl_->lastRect.height = static_cast<int>(cardH);
    const float fadeIn = 0.12f;
    const float fadeOut = 0.12f;
    const float alpha = std::min({1.0f, impl_->age / fadeIn,
                                  (impl_->ttl - impl_->age) / fadeOut});

    impl_->gl.useProgram(impl_->program);
    impl_->gl.uniform4f(impl_->uRect, ndcX, ndcY, ndcW, ndcH);
    impl_->gl.uniform4f(impl_->uUvRect, rect.u0, rect.v1,
                        rect.u1 - rect.u0, rect.v0 - rect.v1);
    impl_->gl.uniform1f(impl_->uAlpha, std::max(0.0f, alpha));
    impl_->gl.activeTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, impl_->texture);
    impl_->gl.uniform1i(impl_->uTex, 0);
    static bool traced = false;
    if (!traced && std::getenv("WHALE3D_SPRITE_TRACE")) {
        SDL_Log("Sprite draw card=%s active=%d ttl=%.2f age=%.2f "
                "rect=(%d,%d %dx%d) alpha=%.2f tex=%u prog=%u "
                "uRect=%d uTex=%d uAlpha=%d",
                impl_->current.c_str(), impl_->active() ? 1 : 0,
                impl_->ttl, impl_->age, impl_->lastRect.x, impl_->lastRect.y,
                impl_->lastRect.width, impl_->lastRect.height, alpha,
                impl_->texture, impl_->program, impl_->uRect, impl_->uTex,
                impl_->uAlpha);
        traced = true;
    }
    glDisable(GL_DEPTH_TEST);
    const GLboolean cullFace = glIsEnabled(GL_CULL_FACE);
    glDisable(GL_CULL_FACE);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    impl_->gl.bindVertexArray(impl_->vao);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    impl_->gl.bindVertexArray(0);
    if (cullFace) glEnable(GL_CULL_FACE);
    else glDisable(GL_CULL_FACE);
    glEnable(GL_DEPTH_TEST);
    impl_->gl.useProgram(0);
    if (std::getenv("WHALE3D_SPRITE_TRACE")) {
        const GLenum err = glGetError();
        if (err != GL_NO_ERROR) SDL_Log("Sprite draw GL error: 0x%x", err);
    }
}

bool SpriteLayer::visible() const {
    return impl_ && impl_->active();
}

const SpriteLayer::PixelRect& SpriteLayer::lastRect() const {
    static const PixelRect empty;
    return impl_ ? impl_->lastRect : empty;
}

const std::string& SpriteLayer::card() const {
    static const std::string empty;
    return impl_ ? impl_->current : empty;
}

const std::string& SpriteLayer::error() const {
    static const std::string empty;
    return impl_ ? impl_->error : empty;
}
