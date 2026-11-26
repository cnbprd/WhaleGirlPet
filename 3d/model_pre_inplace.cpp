#include "model.h"

#define STB_IMAGE_IMPLEMENTATION
#include "third_party/stb_image.h"
#include "third_party/json.hpp"

#include <SDL3/SDL.h>
#include <GL/gl.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <functional>
#include <limits>
#include <memory>
#include <string>
#include <vector>

#ifdef WHALE3D_USE_OZZ
#include <ozz/animation/offline/animation_builder.h>
#include <ozz/animation/offline/raw_animation.h>
#include <ozz/animation/offline/raw_skeleton.h>
#include <ozz/animation/offline/skeleton_builder.h>
#include <ozz/animation/runtime/animation.h>
#include <ozz/animation/runtime/local_to_model_job.h>
#include <ozz/animation/runtime/sampling_job.h>
#include <ozz/animation/runtime/skeleton.h>
#include <ozz/base/containers/vector.h>
#include <ozz/base/maths/soa_transform.h>
#include <ozz/base/maths/simd_math.h>
#include <ozz/base/memory/unique_ptr.h>
#include <ozz/base/span.h>
#endif

#ifndef GL_ARRAY_BUFFER
#define GL_ARRAY_BUFFER 0x8892
#endif
#ifndef GL_ELEMENT_ARRAY_BUFFER
#define GL_ELEMENT_ARRAY_BUFFER 0x8893
#endif
#ifndef GL_STATIC_DRAW
#define GL_STATIC_DRAW 0x88E4
#endif
#ifndef GL_VERTEX_SHADER
#define GL_VERTEX_SHADER 0x8B31
#endif
#ifndef GL_FRAGMENT_SHADER
#define GL_FRAGMENT_SHADER 0x8B30
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
#ifndef GL_CLAMP_TO_EDGE
#define GL_CLAMP_TO_EDGE 0x812F
#endif
#ifndef GL_TEXTURE0
#define GL_TEXTURE0 0x84C0
#endif

// ---- minimal GL entry points not exported by opengl32 1.1 ----
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
typedef void (APIENTRY* PFNGLUNIFORMMATRIX4FV)(GLint, GLsizei, GLboolean, const GLfloat*);
typedef void (APIENTRY* PFNGLUNIFORM1I)(GLint, GLint);
typedef void (APIENTRY* PFNGLUNIFORM4F)(GLint, GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (APIENTRY* PFNGLUNIFORM3F)(GLint, GLfloat, GLfloat, GLfloat);
typedef void (APIENTRY* PFNGLACTIVETEXTURE)(GLenum);
typedef void (APIENTRY* PFNGLGENERATEMIPMAP)(GLenum);

struct GL {
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
    PFNGLUNIFORMMATRIX4FV uniformMatrix4fv = nullptr;
    PFNGLUNIFORM1I uniform1i = nullptr;
    PFNGLUNIFORM4F uniform4f = nullptr;
    PFNGLUNIFORM3F uniform3f = nullptr;
    PFNGLACTIVETEXTURE activeTexture = nullptr;
    PFNGLGENERATEMIPMAP generateMipmap = nullptr;

    template <typename T>
    bool loadOne(T& fn, const char* name) {
        fn = reinterpret_cast<T>(SDL_GL_GetProcAddress(name));
        if (!fn) {
            SDL_Log("Missing GL entry point: %s", name);
            return false;
        }
        return true;
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
            && loadOne(uniformMatrix4fv, "glUniformMatrix4fv")
            && loadOne(uniform1i, "glUniform1i")
            && loadOne(uniform4f, "glUniform4f")
            && loadOne(uniform3f, "glUniform3f")
            && loadOne(activeTexture, "glActiveTexture")
            && loadOne(generateMipmap, "glGenerateMipmap");
    }
};

// ---- column-major math ----
struct Mat4 {
    GLfloat m[16];
};

static Mat4 matIdentity() {
    Mat4 r{};
    r.m[0] = r.m[5] = r.m[10] = r.m[15] = 1.0f;
    return r;
}

static Mat4 matMultiply(const Mat4& a, const Mat4& b) {
    Mat4 r{};
    for (int c = 0; c < 4; ++c) {
        for (int row = 0; row < 4; ++row) {
            float v = 0.0f;
            for (int k = 0; k < 4; ++k) {
                v += a.m[k * 4 + row] * b.m[c * 4 + k];
            }
            r.m[c * 4 + row] = v;
        }
    }
    return r;
}

static Mat4 matFromArray(const float* src) {
    Mat4 r{};
    std::memcpy(r.m, src, sizeof(r.m));
    return r;
}

static Mat4 matTranslate(float x, float y, float z) {
    Mat4 r = matIdentity();
    r.m[12] = x;
    r.m[13] = y;
    r.m[14] = z;
    return r;
}

static Mat4 matScale(float x, float y, float z) {
    Mat4 r = matIdentity();
    r.m[0] = x;
    r.m[5] = y;
    r.m[10] = z;
    return r;
}

static Mat4 matFromQuat(float x, float y, float z, float w) {
    Mat4 r = matIdentity();
    float xx = x * x, yy = y * y, zz = z * z;
    float xy = x * y, xz = x * z, yz = y * z;
    float wx = w * x, wy = w * y, wz = w * z;
    r.m[0] = 1.0f - 2.0f * (yy + zz);
    r.m[1] = 2.0f * (xy + wz);
    r.m[2] = 2.0f * (xz - wy);
    r.m[4] = 2.0f * (xy - wz);
    r.m[5] = 1.0f - 2.0f * (xx + zz);
    r.m[6] = 2.0f * (yz + wx);
    r.m[8] = 2.0f * (xz + wy);
    r.m[9] = 2.0f * (yz - wx);
    r.m[10] = 1.0f - 2.0f * (xx + yy);
    return r;
}

struct Quat {
    float x, y, z, w;
};

static Quat quatNormalize(Quat q) {
    float len = std::sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
    if (len < 1e-8f) return {0.0f, 0.0f, 0.0f, 1.0f};
    return {q.x / len, q.y / len, q.z / len, q.w / len};
}

static Quat quatSlerp(Quat a, Quat b, float t) {
    a = quatNormalize(a);
    b = quatNormalize(b);
    float dot = a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w;
    if (dot < 0.0f) {
        b.x = -b.x;
        b.y = -b.y;
        b.z = -b.z;
        b.w = -b.w;
        dot = -dot;
    }
    if (dot > 0.9995f) {
        return quatNormalize({a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t,
                              a.z + (b.z - a.z) * t, a.w + (b.w - a.w) * t});
    }
    float theta0 = std::acos(std::min(1.0f, std::max(-1.0f, dot)));
    float theta = theta0 * t;
    float sinTheta = std::sin(theta);
    float sinTheta0 = std::sin(theta0);
    float s0 = std::cos(theta) - dot * sinTheta / sinTheta0;
    float s1 = sinTheta / sinTheta0;
    return {a.x * s0 + b.x * s1, a.y * s0 + b.y * s1,
            a.z * s0 + b.z * s1, a.w * s0 + b.w * s1};
}

// ---- glTF structures ----
struct BufferView {
    size_t byteOffset = 0;
    size_t byteLength = 0;
    size_t byteStride = 0;
};

struct Accessor {
    int bufferView = -1;
    size_t byteOffset = 0;
    int componentType = 0;
    int count = 0;
    std::string type;
    bool normalized = false;

    int components() const {
        if (type == "SCALAR") return 1;
        if (type == "VEC2") return 2;
        if (type == "VEC3") return 3;
        if (type == "VEC4") return 4;
        if (type == "MAT2") return 4;
        if (type == "MAT3") return 9;
        if (type == "MAT4") return 16;
        return 0;
    }

    int componentSize() const {
        switch (componentType) {
            case 5120: case 5121: return 1;
            case 5122: case 5123: return 2;
            case 5125: case 5126: return 4;
            default: return 0;
        }
    }
};

struct Vertex {
    float px, py, pz;
    float nx, ny, nz;
    float u, v;
    float r, g, b, a;
    unsigned char j0, j1, j2, j3;
    float w0, w1, w2, w3;
};

struct Primitive {
    GLuint vao = 0;
    GLuint vbo = 0;
    GLuint ebo = 0;
    GLsizei indexCount = 0;
    GLenum indexType = GL_UNSIGNED_SHORT;
    bool useElements = true;
    int material = -1;
};

struct Mesh {
    std::vector<Primitive> primitives;
};

struct Node {
    std::string name;
    int parent = -1;
    std::vector<int> children;
    int mesh = -1;
    int skin = -1;
    bool hasMatrix = false;

    float baseT[3] = {0, 0, 0};
    float baseR[4] = {0, 0, 0, 1};
    float baseS[3] = {1, 1, 1};

    float t[3] = {0, 0, 0};
    float r[4] = {0, 0, 0, 1};
    float s[3] = {1, 1, 1};

    Mat4 baseLocal = matIdentity();
    Mat4 local = matIdentity();
    Mat4 global = matIdentity();

    void resetLocal() {
        t[0] = baseT[0]; t[1] = baseT[1]; t[2] = baseT[2];
        r[0] = baseR[0]; r[1] = baseR[1]; r[2] = baseR[2]; r[3] = baseR[3];
        s[0] = baseS[0]; s[1] = baseS[1]; s[2] = baseS[2];
        local = baseLocal;
    }

    void recompose() {
        if (hasMatrix) return;
        Mat4 T = matTranslate(t[0], t[1], t[2]);
        Mat4 R = matFromQuat(r[0], r[1], r[2], r[3]);
        Mat4 S = matScale(s[0], s[1], s[2]);
        local = matMultiply(T, matMultiply(R, S));
    }
};

struct Skin {
    std::vector<int> joints;
    std::vector<Mat4> inverseBind;
    std::vector<Mat4> jointMatrices;
};

struct Material {
    float baseColor[4] = {1, 1, 1, 1};
    GLuint texture = 0;
};

struct AnimSampler {
    std::vector<float> times;
    std::vector<float> values;
    int components = 0;
};

struct AnimChannel {
    int node = -1;
    int path = 1; // 0 translation, 1 rotation, 2 scale
    int sampler = -1;
};

struct Animation {
    std::vector<AnimSampler> samplers;
    std::vector<AnimChannel> channels;
    float duration = 0.0f;
};

struct Model::Impl {
    GL gl;
    GLuint program = 0;
    GLuint vao = 0; // unused, kept for symmetry
    std::vector<Mesh> meshes;
    std::vector<Node> nodes;
    std::vector<Skin> skins;
    std::vector<Material> materials;
    std::vector<GLuint> imageTextures;
    std::vector<GLuint> textureIds;
    std::vector<Animation> animations;
    std::vector<uint8_t> bin;
    std::vector<BufferView> bufferViews;
    std::vector<Accessor> accessors;
    std::vector<std::string> imageUris;
    std::string sourcePath;
    int triangleCount = 0;
    bool loaded = false;
    std::string error;

    bool useOzz = true;
    bool ozzReady = false;
    std::string ozzError;
    int activeClip = 0;

#ifdef WHALE3D_USE_OZZ
    ozz::unique_ptr<ozz::animation::Skeleton> ozzSkeleton;
    ozz::unique_ptr<ozz::animation::Animation> ozzIdle;
    ozz::unique_ptr<ozz::animation::Animation> ozzWalk;
    std::unique_ptr<ozz::animation::SamplingJob::Context> ozzContext;
    ozz::vector<ozz::math::SoaTransform> ozzLocals;
    ozz::vector<ozz::math::Float4x4> ozzModels;
    std::vector<int> skinToOzz;
#endif

    GLint uMVP = -1, uModel = -1, uJoints = -1, uSkinned = -1;
    GLint uBaseColor = -1, uTex = -1, uUseTex = -1, uFaceFrame = -1, uLightDir = -1;

    int faceFrame = 0;
    int forcedFace = -1;
    bool smile = false;
    float nextBlink = 2.0f;
    float blinkUntil = -1.0f;

    ~Impl() { shutdown(); }

    void shutdown() {
        if (gl.deleteBuffers) {
            for (auto& mesh : meshes) {
                for (auto& p : mesh.primitives) {
                    if (p.vbo) gl.deleteBuffers(1, &p.vbo);
                    if (p.ebo) gl.deleteBuffers(1, &p.ebo);
                }
            }
        }
        if (gl.deleteVertexArrays) {
            for (auto& mesh : meshes) {
                for (auto& p : mesh.primitives) {
                    if (p.vao) gl.deleteVertexArrays(1, &p.vao);
                }
            }
        }
        if (gl.deleteProgram && program) gl.deleteProgram(program);
        for (GLuint tex : imageTextures) {
            if (tex) glDeleteTextures(1, &tex);
        }
        meshes.clear();
        nodes.clear();
        skins.clear();
        materials.clear();
        imageTextures.clear();
        textureIds.clear();
        animations.clear();
        program = 0;
        loaded = false;
    }
};

// ---- accessor readers ----
static const uint8_t* viewData(const Model::Impl& m, const Accessor& a, size_t index, int comp,
                               size_t& outOffset, size_t& outStride) {
    if (a.bufferView < 0 || a.bufferView >= (int)m.bufferViews.size()) return nullptr;
    const BufferView& v = m.bufferViews[a.bufferView];
    int comps = a.components();
    int csize = a.componentSize();
    if (comps <= 0 || csize <= 0 || a.count <= 0 || index >= (size_t)a.count) return nullptr;
    size_t stride = v.byteStride ? v.byteStride : (size_t)(comps * csize);
    size_t offset = v.byteOffset + a.byteOffset + index * stride + (size_t)(comp * csize);
    if (offset + csize > v.byteOffset + v.byteLength || offset + csize > m.bin.size()) return nullptr;
    outOffset = offset;
    outStride = stride;
    return m.bin.data();
}

static float readAccessorFloat(const Model::Impl& m, const Accessor& a, size_t index, int comp) {
    size_t offset = 0, stride = 0;
    const uint8_t* base = viewData(m, a, index, comp, offset, stride);
    if (!base) return 0.0f;
    switch (a.componentType) {
        case 5126: return *reinterpret_cast<const float*>(base + offset);
        case 5121: {
            float v = (float)*reinterpret_cast<const uint8_t*>(base + offset);
            return a.normalized ? v / 255.0f : v;
        }
        case 5123: {
            float v = (float)*reinterpret_cast<const uint16_t*>(base + offset);
            return a.normalized ? v / 65535.0f : v;
        }
        case 5125: {
            float v = (float)*reinterpret_cast<const uint32_t*>(base + offset);
            return v;
        }
        case 5120: {
            float v = (float)*reinterpret_cast<const int8_t*>(base + offset);
            return a.normalized ? std::max(-1.0f, v / 127.0f) : v;
        }
        case 5122: {
            float v = (float)*reinterpret_cast<const int16_t*>(base + offset);
            return a.normalized ? std::max(-1.0f, v / 32767.0f) : v;
        }
        default: return 0.0f;
    }
}

static int readAccessorInt(const Model::Impl& m, const Accessor& a, size_t index, int comp) {
    size_t offset = 0, stride = 0;
    const uint8_t* base = viewData(m, a, index, comp, offset, stride);
    if (!base) return 0;
    switch (a.componentType) {
        case 5120: return (int)*reinterpret_cast<const int8_t*>(base + offset);
        case 5121: return (int)*reinterpret_cast<const uint8_t*>(base + offset);
        case 5122: return (int)*reinterpret_cast<const int16_t*>(base + offset);
        case 5123: return (int)*reinterpret_cast<const uint16_t*>(base + offset);
        case 5125: return (int)*reinterpret_cast<const uint32_t*>(base + offset);
        case 5126: return (int)*reinterpret_cast<const float*>(base + offset);
        default: return 0;
    }
}

// ---- GL shader helpers ----
static GLuint compileShader(GL& gl, GLenum type, const char* src) {
    GLuint s = gl.createShader(type);
    gl.shaderSource(s, 1, &src, nullptr);
    gl.compileShader(s);
    GLint ok = 0;
    gl.getShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        GLint len = 0;
        gl.getShaderiv(s, GL_INFO_LOG_LENGTH, &len);
        std::vector<char> log(std::max(1, (int)len));
        gl.getShaderInfoLog(s, (GLsizei)log.size(), nullptr, log.data());
        SDL_Log("Model shader compile failed: %s", log.data());
        gl.deleteShader(s);
        return 0;
    }
    return s;
}

static GLuint makeProgram(GL& gl, const char* vs, const char* fs) {
    GLuint v = compileShader(gl, GL_VERTEX_SHADER, vs);
    GLuint f = compileShader(gl, GL_FRAGMENT_SHADER, fs);
    if (!v || !f) return 0;
    GLuint p = gl.createProgram();
    gl.attachShader(p, v);
    gl.attachShader(p, f);
    gl.linkProgram(p);
    gl.deleteShader(v);
    gl.deleteShader(f);
    GLint ok = 0;
    gl.getProgramiv(p, GL_LINK_STATUS, &ok);
    if (!ok) {
        GLint len = 0;
        gl.getProgramiv(p, GL_INFO_LOG_LENGTH, &len);
        std::vector<char> log(std::max(1, (int)len));
        gl.getProgramInfoLog(p, (GLsizei)log.size(), nullptr, log.data());
        SDL_Log("Model program link failed: %s", log.data());
        gl.deleteProgram(p);
        return 0;
    }
    return p;
}

static const char* kModelVS = R"(
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUV;
layout(location = 3) in vec4 aColor;
layout(location = 4) in vec4 aJoints;
layout(location = 5) in vec4 aWeights;
uniform mat4 uMVP;
uniform mat4 uModel;
uniform mat4 uJoints[64];
uniform int uSkinned;
out vec3 vNormal;
out vec2 vUV;
out vec4 vColor;
void main() {
    vec4 p = vec4(aPos, 1.0);
    vec3 n = aNormal;
    if (uSkinned != 0) {
        mat4 skin =
            aWeights.x * uJoints[int(aJoints.x)] +
            aWeights.y * uJoints[int(aJoints.y)] +
            aWeights.z * uJoints[int(aJoints.z)] +
            aWeights.w * uJoints[int(aJoints.w)];
        p = skin * p;
        n = mat3(skin) * n;
    }
    vNormal = mat3(uModel) * n;
    vUV = aUV;
    vColor = aColor;
    gl_Position = uMVP * p;
}
)";

static const char* kModelFS = R"(
#version 330 core
in vec3 vNormal;
in vec2 vUV;
in vec4 vColor;
uniform vec4 uBaseColor;
uniform sampler2D uTex;
uniform int uUseTex;
uniform int uFaceFrame;
uniform vec3 uLightDir;
out vec4 fragColor;
void main() {
    vec4 albedo = uBaseColor * vColor;
    if (uUseTex != 0) {
        vec2 uv = vUV;
        // Face atlas: 2048x512, frames at x=0,512,1024; body uses x=1792.
        if (uv.x < 0.5) {
            uv.x += float(uFaceFrame) * 0.25;
        }
        albedo *= texture(uTex, uv);
    }
    vec3 n = normalize(vNormal);
    float ndl = max(dot(n, normalize(uLightDir)), 0.0);
    float rim = pow(1.0 - max(dot(n, vec3(0.0, 0.0, 1.0)), 0.0), 2.0);
    vec3 lit = albedo.rgb * (0.45 + 0.55 * ndl) + vec3(0.16, 0.30, 0.38) * rim * 0.45;
    fragColor = vec4(lit, albedo.a);
}
)";

// ---- GLB parsing helpers ----
static uint32_t readU32(const std::vector<uint8_t>& data, size_t offset) {
    if (offset + 4 > data.size()) return 0;
    uint32_t v;
    std::memcpy(&v, data.data() + offset, 4);
    return v;
}

static std::vector<uint8_t> readFile(const std::string& path, bool& ok) {
    std::ifstream f(path, std::ios::binary);
    if (!f) {
        ok = false;
        return {};
    }
    std::vector<uint8_t> data((std::istreambuf_iterator<char>(f)),
                              std::istreambuf_iterator<char>());
    ok = true;
    return data;
}

static bool parseGLB(const std::vector<uint8_t>& file, std::string& jsonOut,
                     std::vector<uint8_t>& binOut, std::string& error) {
    if (file.size() < 20 || readU32(file, 0) != 0x46546C67) {
        error = "not a GLB file";
        return false;
    }
    uint32_t version = readU32(file, 4);
    if (version != 2) {
        error = "unsupported GLB version";
        return false;
    }
    size_t offset = 12;
    bool haveJson = false;
    bool haveBin = false;
    while (offset + 8 <= file.size()) {
        uint32_t len = readU32(file, offset);
        uint32_t type = readU32(file, offset + 4);
        offset += 8;
        if (offset + len > file.size()) {
            error = "truncated GLB chunk";
            return false;
        }
        if (type == 0x4E4F534A) {
            jsonOut.assign(reinterpret_cast<const char*>(file.data() + offset), len);
            haveJson = true;
        } else if (type == 0x004E4942) {
            binOut.assign(file.begin() + (ptrdiff_t)offset,
                          file.begin() + (ptrdiff_t)(offset + len));
            haveBin = true;
        }
        offset += len;
    }
    if (!haveJson) {
        error = "GLB has no JSON chunk";
        return false;
    }
    if (!haveBin) error = "GLB has no BIN chunk";
    return true;
}

// ---- optional ozz-animation pipeline ----
#ifdef WHALE3D_USE_OZZ
static ozz::math::Quaternion ozzQuat(const float r[4]) {
    return ozz::math::NormalizeSafe(
        ozz::math::Quaternion(r[0], r[1], r[2], r[3]),
        ozz::math::Quaternion::identity());
}

template <typename KeyVec, typename Value>
static void putKey(KeyVec& keys, float time, const Value& value) {
    for (auto& key : keys) {
        if (std::fabs(key.time - time) < 1e-5f) {
            key.value = value;
            return;
        }
    }
    if (!keys.empty() && time < keys.back().time) return;
    keys.push_back({time, value});
}

static void fillBaseTracks(ozz::animation::offline::RawAnimation& raw,
                           const Model::Impl& m, const std::vector<int>& skinToOzz,
                           float duration) {
    raw.duration = duration;
    raw.tracks.resize((size_t)m.ozzSkeleton->num_joints());
    for (size_t j = 0; j < m.skins[0].joints.size(); ++j) {
        const Node& node = m.nodes[(size_t)m.skins[0].joints[j]];
        int s = skinToOzz[j];
        if (s < 0) continue;
        auto& track = raw.tracks[(size_t)s];
        ozz::math::Float3 t(node.baseT[0], node.baseT[1], node.baseT[2]);
        ozz::math::Float3 sc(node.baseS[0], node.baseS[1], node.baseS[2]);
        ozz::math::Quaternion q = ozzQuat(node.baseR);
        putKey(track.translations, 0.0f, t);
        putKey(track.translations, duration, t);
        putKey(track.rotations, 0.0f, q);
        putKey(track.rotations, duration, q);
        putKey(track.scales, 0.0f, sc);
        putKey(track.scales, duration, sc);
    }
}

static bool buildOzz(Model::Impl& m) {
    m.ozzReady = false;
    m.ozzError.clear();
    if (m.skins.empty() || m.nodes.empty()) {
        m.ozzError = "no skin/nodes for ozz";
        return false;
    }

    const Skin& skin = m.skins[0];
    std::vector<int> nodeToSkin(m.nodes.size(), -1);
    for (size_t j = 0; j < skin.joints.size(); ++j) {
        int ni = skin.joints[j];
        if (ni >= 0 && ni < (int)m.nodes.size()) nodeToSkin[(size_t)ni] = (int)j;
    }

    using RawJoint = ozz::animation::offline::RawSkeleton::Joint;
    std::function<RawJoint(int)> makeJoint = [&](int ni) -> RawJoint {
        const Node& n = m.nodes[(size_t)ni];
        RawJoint j;
        j.name = n.name.c_str();
        j.transform.translation = ozz::math::Float3(n.baseT[0], n.baseT[1], n.baseT[2]);
        j.transform.rotation = ozzQuat(n.baseR);
        j.transform.scale = ozz::math::Float3(n.baseS[0], n.baseS[1], n.baseS[2]);
        for (int c : n.children) {
            if (c >= 0 && c < (int)m.nodes.size() && nodeToSkin[(size_t)c] >= 0) {
                j.children.push_back(makeJoint(c));
            }
        }
        return j;
    };

    ozz::animation::offline::RawSkeleton rawSkeleton;
    for (size_t j = 0; j < skin.joints.size(); ++j) {
        int ni = skin.joints[j];
        if (ni < 0 || ni >= (int)m.nodes.size()) continue;
        int parent = m.nodes[(size_t)ni].parent;
        if (parent < 0 || parent >= (int)m.nodes.size() || nodeToSkin[(size_t)parent] < 0) {
            rawSkeleton.roots.push_back(makeJoint(ni));
        }
    }
    if (!rawSkeleton.Validate() || rawSkeleton.roots.empty()) {
        m.ozzError = "invalid raw skeleton";
        return false;
    }

    m.ozzSkeleton = ozz::animation::offline::SkeletonBuilder()(rawSkeleton);
    if (!m.ozzSkeleton) {
        m.ozzError = "SkeletonBuilder failed";
        return false;
    }

    std::vector<int> skinToOzz(skin.joints.size(), -1);
    auto names = m.ozzSkeleton->joint_names();
    for (int s = 0; s < (int)names.size(); ++s) {
        std::string name = names[s] ? names[s] : "";
        for (size_t j = 0; j < skin.joints.size(); ++j) {
            int ni = skin.joints[j];
            if (ni >= 0 && ni < (int)m.nodes.size() && m.nodes[(size_t)ni].name == name) {
                skinToOzz[j] = s;
                break;
            }
        }
    }
    for (int s : skinToOzz) {
        if (s < 0) {
            m.ozzError = "ozz joint mapping incomplete";
            return false;
        }
    }

    float idleDuration = m.animations.empty() ? 4.0f : m.animations.front().duration;
    if (idleDuration <= 0.0f) idleDuration = 4.0f;

    ozz::animation::offline::RawAnimation rawIdle;
    fillBaseTracks(rawIdle, m, skinToOzz, idleDuration);

    if (!m.animations.empty()) {
        const Animation& src = m.animations.front();
        for (const AnimChannel& ch : src.channels) {
            if (ch.node < 0 || ch.node >= (int)m.nodes.size()) continue;
            int sj = nodeToSkin[(size_t)ch.node];
            if (sj < 0 || ch.sampler < 0 || ch.sampler >= (int)src.samplers.size()) continue;
            int s = skinToOzz[(size_t)sj];
            const AnimSampler& sampler = src.samplers[(size_t)ch.sampler];
            if (sampler.times.empty() || sampler.components <= 0) continue;
            auto& track = rawIdle.tracks[(size_t)s];
            for (size_t i = 0; i < sampler.times.size(); ++i) {
                float t = sampler.times[i];
                if (t < 0.0f || t > idleDuration) continue;
                const float* v = &sampler.values[i * (size_t)sampler.components];
                if (ch.path == 1 && sampler.components == 4) {
                    ozz::math::Quaternion q = ozzQuat(v);
                    putKey(track.rotations, t, q);
                } else if (ch.path == 0 && sampler.components >= 3) {
                    putKey(track.translations, t,
                           ozz::math::Float3(v[0], v[1], v[2]));
                } else if (ch.path == 2 && sampler.components >= 3) {
                    putKey(track.scales, t, ozz::math::Float3(v[0], v[1], v[2]));
                }
            }
        }
    }
    if (!rawIdle.Validate()) {
        m.ozzError = "idle RawAnimation invalid";
        return false;
    }
    m.ozzIdle = ozz::animation::offline::AnimationBuilder()(rawIdle);
    if (!m.ozzIdle) {
        m.ozzError = "idle AnimationBuilder failed";
        return false;
    }

    // Walk is a procedural clip built from the same rest pose. It is deliberately
    // small: legs, arms and a little head/chest counter-motion.
    const float walkDuration = 2.0f;
    ozz::animation::offline::RawAnimation rawWalk;
    fillBaseTracks(rawWalk, m, skinToOzz, walkDuration);
    auto jointByName = [&](const char* name) {
        for (size_t ni = 0; ni < m.nodes.size(); ++ni) {
            if (m.nodes[ni].name == name) return (int)ni;
        }
        return -1;
    };
    auto cycle = [&](const char* name, const ozz::math::Float3& axis, float amplitude,
                     float phase) {
        int ni = jointByName(name);
        if (ni < 0 || nodeToSkin[(size_t)ni] < 0) return;
        int s = skinToOzz[(size_t)nodeToSkin[(size_t)ni]];
        const Node& node = m.nodes[(size_t)ni];
        auto& track = rawWalk.tracks[(size_t)s];
        ozz::math::Quaternion base = ozzQuat(node.baseR);
        for (int k = 0; k <= 8; ++k) {
            float t = walkDuration * (float)k / 8.0f;
            float angle = amplitude * std::sin(2.0f * 3.14159265f * t / walkDuration + phase);
            putKey(track.rotations, t,
                   ozz::math::NormalizeSafe(
                       base * ozz::math::Quaternion::FromAxisAngle(axis, angle), base));
        }
    };
    cycle("thigh.L", ozz::math::Float3(1, 0, 0), 0.40f, 0.0f);
    cycle("thigh.R", ozz::math::Float3(1, 0, 0), -0.40f, 0.0f);
    cycle("shin.L", ozz::math::Float3(1, 0, 0), 0.18f, 0.6f);
    cycle("shin.R", ozz::math::Float3(1, 0, 0), -0.18f, 0.6f);
    cycle("upper_arm.L", ozz::math::Float3(1, 0, 0), -0.28f, 0.0f);
    cycle("upper_arm.R", ozz::math::Float3(1, 0, 0), 0.28f, 0.0f);
    cycle("head", ozz::math::Float3(0, 1, 0), 0.06f, 0.0f);
    cycle("chest", ozz::math::Float3(1, 0, 0), 0.03f, 0.0f);
    if (!rawWalk.Validate()) {
        m.ozzError = "walk RawAnimation invalid";
        return false;
    }
    m.ozzWalk = ozz::animation::offline::AnimationBuilder()(rawWalk);
    if (!m.ozzWalk) {
        m.ozzError = "walk AnimationBuilder failed";
        return false;
    }

    m.skinToOzz = std::move(skinToOzz);
    m.ozzLocals.resize((size_t)m.ozzSkeleton->num_soa_joints());
    m.ozzModels.resize((size_t)m.ozzSkeleton->num_joints());
    m.ozzContext = std::make_unique<ozz::animation::SamplingJob::Context>(
        m.ozzIdle->num_tracks());
    m.ozzReady = true;
    return true;
}
#endif
Model::Model() : impl_(new Impl()) {}
Model::~Model() { delete impl_; }

bool Model::loaded() const { return impl_ && impl_->loaded; }
const std::string& Model::sourcePath() const {
    static const std::string empty;
    return impl_ ? impl_->sourcePath : empty;
}
int Model::triangleCount() const { return impl_ ? impl_->triangleCount : 0; }
int Model::jointCount() const {
    return (impl_ && !impl_->skins.empty()) ? (int)impl_->skins[0].joints.size() : 0;
}
int Model::animationCount() const {
    return impl_ ? (int)impl_->animations.size() : 0;
}
const std::string& Model::error() const {
    static const std::string empty;
    return impl_ ? impl_->error : empty;
}

bool Model::setAnimator(const std::string& name) {
    if (!impl_) return false;
    if (name == "self") {
        impl_->useOzz = false;
        impl_->activeClip = 0;
        return true;
    }
    if (name == "ozz") {
#ifdef WHALE3D_USE_OZZ
        impl_->useOzz = true;
        return impl_->ozzReady;
#else
        impl_->ozzError = "ozz support was not compiled in";
        return false;
#endif
    }
    return false;
}

bool Model::usesOzz() const {
#ifdef WHALE3D_USE_OZZ
    return impl_ && impl_->useOzz && impl_->ozzReady;
#else
    return false;
#endif
}

const char* Model::animatorName() const {
    return usesOzz() ? "ozz" : "self";
}

bool Model::setClip(const std::string& name) {
    if (!impl_) return false;
    if (name == "idle") {
        impl_->activeClip = 0;
        return true;
    }
#ifdef WHALE3D_USE_OZZ
    if (name == "walk" && impl_->useOzz && impl_->ozzWalk) {
        impl_->activeClip = 1;
        return true;
    }
#endif
    return false;
}

void Model::nextClip() {
    if (!impl_) return;
#ifdef WHALE3D_USE_OZZ
    if (impl_->useOzz && impl_->ozzWalk) impl_->activeClip = (impl_->activeClip + 1) % 2;
#endif
}

const char* Model::clipName() const {
#ifdef WHALE3D_USE_OZZ
    if (impl_ && impl_->useOzz && impl_->activeClip == 1 && impl_->ozzWalk) return "walk";
#endif
    return "idle";
}

bool Model::setFace(const std::string& name) {
    if (!impl_) return false;
    if (name == "auto") {
        impl_->forcedFace = -1;
        impl_->smile = false;
        impl_->nextBlink = 2.0f;
        impl_->blinkUntil = -1.0f;
        impl_->faceFrame = 0;
        return true;
    }
    if (name == "open") { impl_->forcedFace = 0; impl_->faceFrame = 0; return true; }
    if (name == "blink") { impl_->forcedFace = 1; impl_->faceFrame = 1; return true; }
    if (name == "smile") { impl_->forcedFace = 2; impl_->faceFrame = 2; return true; }
    return false;
}

void Model::toggleSmile() {
    if (!impl_) return;
    impl_->forcedFace = -1;
    impl_->smile = !impl_->smile;
    impl_->faceFrame = impl_->smile ? 2 : 0;
}

void Model::triggerBlink(float timeSeconds) {
    if (!impl_) return;
    impl_->forcedFace = -1;
    impl_->blinkUntil = timeSeconds + 0.18f;
    impl_->faceFrame = 1;
}

const char* Model::faceName() const {
    if (!impl_) return "open";
    if (impl_->faceFrame == 1) return "blink";
    if (impl_->faceFrame == 2) return "smile";
    return "open";
}

const char* Model::faceMode() const {
    if (!impl_) return "auto";
    if (impl_->forcedFace == 0) return "open";
    if (impl_->forcedFace == 1) return "blink";
    if (impl_->forcedFace == 2) return "smile";
    return "auto";
}

void Model::shutdown() { if (impl_) impl_->shutdown(); }

bool Model::load(const std::string& path) {
    Impl& m = *impl_;
    m.shutdown();
    m.bufferViews.clear();
    m.accessors.clear();
    m.bin.clear();
    m.imageUris.clear();
    m.sourcePath = path;
    m.triangleCount = 0;
    m.activeClip = 0;
#ifdef WHALE3D_USE_OZZ
    m.ozzReady = false;
    m.ozzError.clear();
    m.ozzSkeleton.reset();
    m.ozzIdle.reset();
    m.ozzWalk.reset();
    m.ozzContext.reset();
    m.ozzLocals.clear();
    m.ozzModels.clear();
    m.skinToOzz.clear();
#endif
    m.error.clear();
    m.faceFrame = 0;
    m.forcedFace = -1;
    m.smile = false;
    m.nextBlink = 2.0f;
    m.blinkUntil = -1.0f;

    if (!m.gl.load()) {
        m.error = "failed to load OpenGL entry points";
        return false;
    }

    bool ok = false;
    std::vector<uint8_t> file = readFile(path, ok);
    if (!ok) {
        m.error = "cannot open " + path;
        return false;
    }

    std::string jsonText;
    std::vector<uint8_t> bin;
    if (!parseGLB(file, jsonText, bin, m.error)) return false;
    m.bin = std::move(bin);

    nlohmann::json j;
    try {
        j = nlohmann::json::parse(jsonText);
    } catch (const std::exception& e) {
        m.error = std::string("JSON parse: ") + e.what();
        return false;
    }

    // bufferViews / accessors
    if (j.contains("bufferViews")) {
        for (const auto& v : j["bufferViews"]) {
            BufferView bv;
            bv.byteOffset = v.value("byteOffset", 0);
            bv.byteLength = v.value("byteLength", 0);
            bv.byteStride = v.value("byteStride", 0);
            m.bufferViews.push_back(bv);
        }
    }
    if (j.contains("accessors")) {
        for (const auto& a : j["accessors"]) {
            Accessor ac;
            ac.bufferView = a.value("bufferView", -1);
            ac.byteOffset = a.value("byteOffset", 0);
            ac.componentType = a.value("componentType", 0);
            ac.count = a.value("count", 0);
            ac.type = a.value("type", "");
            ac.normalized = a.value("normalized", false);
            m.accessors.push_back(ac);
        }
    }

    // program
    m.program = makeProgram(m.gl, kModelVS, kModelFS);
    if (!m.program) {
        m.error = "model shader program failed";
        return false;
    }
    m.uMVP = m.gl.getUniformLocation(m.program, "uMVP");
    m.uModel = m.gl.getUniformLocation(m.program, "uModel");
    m.uJoints = m.gl.getUniformLocation(m.program, "uJoints");
    m.uSkinned = m.gl.getUniformLocation(m.program, "uSkinned");
    m.uBaseColor = m.gl.getUniformLocation(m.program, "uBaseColor");
    m.uTex = m.gl.getUniformLocation(m.program, "uTex");
    m.uUseTex = m.gl.getUniformLocation(m.program, "uUseTex");
    m.uFaceFrame = m.gl.getUniformLocation(m.program, "uFaceFrame");
    m.uLightDir = m.gl.getUniformLocation(m.program, "uLightDir");

    // images -> GL textures
    if (j.contains("images")) {
        for (size_t i = 0; i < j["images"].size(); ++i) {
            const auto& img = j["images"][i];
            std::vector<uint8_t> bytes;
            if (img.contains("bufferView")) {
                int vi = img["bufferView"];
                if (vi < 0 || vi >= (int)m.bufferViews.size()) {
                    m.error = "image bufferView out of range";
                    return false;
                }
                const BufferView& bv = m.bufferViews[vi];
                if (bv.byteOffset + bv.byteLength > m.bin.size()) {
                    m.error = "image bufferView out of range";
                    return false;
                }
                bytes.assign(m.bin.begin() + (ptrdiff_t)bv.byteOffset,
                             m.bin.begin() + (ptrdiff_t)(bv.byteOffset + bv.byteLength));
            } else if (img.contains("uri")) {
                m.error = "external/data-URI images are not supported yet";
                return false;
            } else {
                m.error = "image has no bufferView or uri";
                return false;
            }

            int w = 0, h = 0, comps = 0;
            stbi_set_flip_vertically_on_load(0);
            unsigned char* pixels = stbi_load_from_memory(
                bytes.data(), (int)bytes.size(), &w, &h, &comps, 4);
            if (!pixels) {
                m.error = "stb_image failed to decode embedded image";
                return false;
            }
            GLuint tex = 0;
            glGenTextures(1, &tex);
            glBindTexture(GL_TEXTURE_2D, tex);
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA,
                         GL_UNSIGNED_BYTE, pixels);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
            // No mip chain: a desktop pet stays close to the camera, and this
            // saves GPU memory on driver heaps that keep private bytes high.
            glBindTexture(GL_TEXTURE_2D, 0);
            stbi_image_free(pixels);
            m.imageTextures.push_back(tex);
        }
    }

    // textures -> GLuint
    if (j.contains("textures")) {
        for (size_t i = 0; i < j["textures"].size(); ++i) {
            int source = j["textures"][i].value("source", -1);
            GLuint tex = 0;
            if (source >= 0 && source < (int)m.imageTextures.size()) {
                tex = m.imageTextures[source];
            }
            m.textureIds.push_back(tex);
        }
    }

    // materials
    if (j.contains("materials")) {
        for (const auto& mat : j["materials"]) {
            Material mmat;
            if (mat.contains("pbrMetallicRoughness")) {
                const auto& pbr = mat["pbrMetallicRoughness"];
                if (pbr.contains("baseColorFactor")) {
                    const auto& c = pbr["baseColorFactor"];
                    for (int k = 0; k < 4 && k < (int)c.size(); ++k) mmat.baseColor[k] = c[k];
                }
                if (pbr.contains("baseColorTexture")) {
                    int ti = pbr["baseColorTexture"].value("index", -1);
                    if (ti >= 0 && ti < (int)m.textureIds.size()) mmat.texture = m.textureIds[ti];
                }
            }
            m.materials.push_back(mmat);
        }
    }

    // meshes
    if (j.contains("meshes")) {
        for (const auto& meshJson : j["meshes"]) {
            Mesh mesh;
            if (!meshJson.contains("primitives")) continue;
            for (const auto& prim : meshJson["primitives"]) {
                if (prim.value("mode", 4) != 4) {
                    m.error = "only triangle primitives are supported";
                    return false;
                }
                if (!prim.contains("attributes") || !prim["attributes"].contains("POSITION")) {
                    m.error = "primitive has no POSITION";
                    return false;
                }
                int posAcc = prim["attributes"]["POSITION"];
                if (posAcc < 0 || posAcc >= (int)m.accessors.size()) {
                    m.error = "POSITION accessor out of range";
                    return false;
                }
                const Accessor& pos = m.accessors[posAcc];
                int count = pos.count;
                if (count <= 0) continue;

                std::vector<Vertex> verts((size_t)count);
                for (int i = 0; i < count; ++i) {
                    Vertex v{};
                    v.px = readAccessorFloat(m, pos, i, 0);
                    v.py = readAccessorFloat(m, pos, i, 1);
                    v.pz = readAccessorFloat(m, pos, i, 2);
                    v.nx = 0.0f; v.ny = 1.0f; v.nz = 0.0f;
                    v.u = 0.0f; v.v = 0.0f;
                    v.r = v.g = v.b = v.a = 1.0f;
                    v.w0 = 1.0f; v.w1 = v.w2 = v.w3 = 0.0f;

                    auto attr = [&](const char* name, int& out) {
                        out = -1;
                        if (prim["attributes"].contains(name)) out = prim["attributes"][name];
                    };
                    int nAcc = -1, uvAcc = -1, colAcc = -1, jAcc = -1, wAcc = -1;
                    attr("NORMAL", nAcc);
                    attr("TEXCOORD_0", uvAcc);
                    attr("COLOR_0", colAcc);
                    attr("JOINTS_0", jAcc);
                    attr("WEIGHTS_0", wAcc);

                    if (nAcc >= 0 && nAcc < (int)m.accessors.size()) {
                        const Accessor& a = m.accessors[nAcc];
                        v.nx = readAccessorFloat(m, a, i, 0);
                        v.ny = readAccessorFloat(m, a, i, 1);
                        v.nz = readAccessorFloat(m, a, i, 2);
                    }
                    if (uvAcc >= 0 && uvAcc < (int)m.accessors.size()) {
                        const Accessor& a = m.accessors[uvAcc];
                        v.u = readAccessorFloat(m, a, i, 0);
                        v.v = readAccessorFloat(m, a, i, 1);
                    }
                    if (colAcc >= 0 && colAcc < (int)m.accessors.size()) {
                        const Accessor& a = m.accessors[colAcc];
                        int comps = a.components();
                        v.r = readAccessorFloat(m, a, i, 0);
                        v.g = readAccessorFloat(m, a, i, 1);
                        v.b = readAccessorFloat(m, a, i, 2);
                        v.a = comps >= 4 ? readAccessorFloat(m, a, i, 3) : 1.0f;
                    }
                    if (jAcc >= 0 && jAcc < (int)m.accessors.size()) {
                        const Accessor& a = m.accessors[jAcc];
                        v.j0 = (unsigned char)readAccessorInt(m, a, i, 0);
                        v.j1 = (unsigned char)readAccessorInt(m, a, i, 1);
                        v.j2 = (unsigned char)readAccessorInt(m, a, i, 2);
                        v.j3 = (unsigned char)readAccessorInt(m, a, i, 3);
                    }
                    if (wAcc >= 0 && wAcc < (int)m.accessors.size()) {
                        const Accessor& a = m.accessors[wAcc];
                        v.w0 = readAccessorFloat(m, a, i, 0);
                        v.w1 = readAccessorFloat(m, a, i, 1);
                        v.w2 = readAccessorFloat(m, a, i, 2);
                        v.w3 = readAccessorFloat(m, a, i, 3);
                    }
                    verts[(size_t)i] = v;
                }

                Primitive p;
                p.material = prim.value("material", -1);
                p.useElements = prim.contains("indices");
                std::vector<uint32_t> idx32;
                if (p.useElements) {
                    int idxAcc = prim["indices"];
                    if (idxAcc < 0 || idxAcc >= (int)m.accessors.size()) {
                        m.error = "indices accessor out of range";
                        return false;
                    }
                    const Accessor& ia = m.accessors[idxAcc];
                    idx32.resize((size_t)ia.count);
                    for (int i = 0; i < ia.count; ++i) idx32[(size_t)i] = (uint32_t)readAccessorInt(m, ia, i, 0);
                    p.indexCount = ia.count;
                    p.indexType = (ia.componentType == 5125) ? GL_UNSIGNED_INT
                               : (ia.componentType == 5121) ? GL_UNSIGNED_BYTE
                               : GL_UNSIGNED_SHORT;
                } else {
                    p.indexCount = count;
                }

                m.gl.genVertexArrays(1, &p.vao);
                m.gl.bindVertexArray(p.vao);
                m.gl.genBuffers(1, &p.vbo);
                m.gl.bindBuffer(GL_ARRAY_BUFFER, p.vbo);
                m.gl.bufferData(GL_ARRAY_BUFFER, (GLsizeiptr)(verts.size() * sizeof(Vertex)),
                                verts.data(), GL_STATIC_DRAW);

                auto attrib = [&](GLuint index, GLint size, GLenum type, GLsizei stride,
                                  size_t offset) {
                    m.gl.enableVertexAttribArray(index);
                    m.gl.vertexAttribPointer(index, size, type, GL_FALSE, stride,
                                             reinterpret_cast<const void*>(offset));
                };
                attrib(0, 3, GL_FLOAT, sizeof(Vertex), offsetof(Vertex, px));
                attrib(1, 3, GL_FLOAT, sizeof(Vertex), offsetof(Vertex, nx));
                attrib(2, 2, GL_FLOAT, sizeof(Vertex), offsetof(Vertex, u));
                attrib(3, 4, GL_FLOAT, sizeof(Vertex), offsetof(Vertex, r));
                attrib(4, 4, GL_UNSIGNED_BYTE, sizeof(Vertex), offsetof(Vertex, j0));
                attrib(5, 4, GL_FLOAT, sizeof(Vertex), offsetof(Vertex, w0));

                if (p.useElements) {
                    m.gl.genBuffers(1, &p.ebo);
                    m.gl.bindBuffer(GL_ELEMENT_ARRAY_BUFFER, p.ebo);
                    GLsizeiptr bytes = (GLsizeiptr)(idx32.size() * (p.indexType == GL_UNSIGNED_INT ? 4 : p.indexType == GL_UNSIGNED_BYTE ? 1 : 2));
                    if (p.indexType == GL_UNSIGNED_INT) {
                        m.gl.bufferData(GL_ELEMENT_ARRAY_BUFFER, bytes, idx32.data(), GL_STATIC_DRAW);
                    } else if (p.indexType == GL_UNSIGNED_BYTE) {
                        std::vector<uint8_t> tmp(idx32.begin(), idx32.end());
                        m.gl.bufferData(GL_ELEMENT_ARRAY_BUFFER, bytes, tmp.data(), GL_STATIC_DRAW);
                    } else {
                        std::vector<uint16_t> tmp(idx32.begin(), idx32.end());
                        m.gl.bufferData(GL_ELEMENT_ARRAY_BUFFER, bytes, tmp.data(), GL_STATIC_DRAW);
                    }
                }
                m.gl.bindVertexArray(0);
                m.triangleCount += p.indexCount / 3;
                mesh.primitives.push_back(p);
            }
            m.meshes.push_back(std::move(mesh));
        }
    }

    // skins (needs accessors)
    if (j.contains("skins")) {
        for (const auto& sk : j["skins"]) {
            Skin skin;
            if (sk.contains("joints")) {
                for (const auto& jn : sk["joints"]) skin.joints.push_back(jn.get<int>());
            }
            int ibmAcc = sk.value("inverseBindMatrices", -1);
            if (ibmAcc >= 0 && ibmAcc < (int)m.accessors.size()) {
                const Accessor& a = m.accessors[ibmAcc];
                for (int i = 0; i < (int)skin.joints.size(); ++i) {
                    Mat4 mat = matIdentity();
                    for (int k = 0; k < 16; ++k) mat.m[k] = readAccessorFloat(m, a, (size_t)i, k);
                    skin.inverseBind.push_back(mat);
                }
            } else {
                for (size_t i = 0; i < skin.joints.size(); ++i) skin.inverseBind.push_back(matIdentity());
            }
            skin.jointMatrices.resize(skin.joints.size(), matIdentity());
            m.skins.push_back(std::move(skin));
        }
    }

    // nodes
    if (j.contains("nodes")) {
        for (const auto& nj : j["nodes"]) {
            Node n;
            n.name = nj.value("name", "");
            n.mesh = nj.value("mesh", -1);
            n.skin = nj.value("skin", -1);
            if (nj.contains("children")) {
                for (const auto& c : nj["children"]) n.children.push_back(c.get<int>());
            }
            if (nj.contains("matrix")) {
                n.hasMatrix = true;
                for (int k = 0; k < 16; ++k) n.baseLocal.m[k] = nj["matrix"][k].get<float>();
                n.local = n.baseLocal;
            } else {
                if (nj.contains("translation")) {
                    for (int k = 0; k < 3; ++k) n.baseT[k] = nj["translation"][k].get<float>();
                }
                if (nj.contains("rotation")) {
                    for (int k = 0; k < 4; ++k) n.baseR[k] = nj["rotation"][k].get<float>();
                    Quat q = quatNormalize({n.baseR[0], n.baseR[1], n.baseR[2], n.baseR[3]});
                    n.baseR[0] = q.x; n.baseR[1] = q.y; n.baseR[2] = q.z; n.baseR[3] = q.w;
                }
                if (nj.contains("scale")) {
                    for (int k = 0; k < 3; ++k) n.baseS[k] = nj["scale"][k].get<float>();
                }
                n.baseLocal = matMultiply(matTranslate(n.baseT[0], n.baseT[1], n.baseT[2]),
                                          matMultiply(matFromQuat(n.baseR[0], n.baseR[1], n.baseR[2], n.baseR[3]),
                                                      matScale(n.baseS[0], n.baseS[1], n.baseS[2])));
                n.local = n.baseLocal;
            }
            m.nodes.push_back(std::move(n));
        }
        for (size_t i = 0; i < m.nodes.size(); ++i) {
            for (int c : m.nodes[i].children) {
                if (c >= 0 && c < (int)m.nodes.size()) m.nodes[(size_t)c].parent = (int)i;
            }
        }
    }

    // animations (first one)
    if (j.contains("animations")) {
        for (const auto& aj : j["animations"]) {
            Animation anim;
            if (aj.contains("samplers")) {
                for (const auto& sj : aj["samplers"]) {
                    AnimSampler s;
                    int in = sj.value("input", -1);
                    int out = sj.value("output", -1);
                    if (in < 0 || in >= (int)m.accessors.size() || out < 0 || out >= (int)m.accessors.size()) {
                        continue;
                    }
                    const Accessor& ia = m.accessors[in];
                    const Accessor& oa = m.accessors[out];
                    s.components = oa.components();
                    s.times.resize((size_t)ia.count);
                    for (int i = 0; i < ia.count; ++i) s.times[(size_t)i] = readAccessorFloat(m, ia, (size_t)i, 0);
                    s.values.resize((size_t)oa.count * (size_t)s.components);
                    for (int i = 0; i < oa.count; ++i) {
                        for (int k = 0; k < s.components; ++k) {
                            s.values[(size_t)i * s.components + k] = readAccessorFloat(m, oa, (size_t)i, k);
                        }
                    }
                    if (!s.times.empty()) anim.duration = std::max(anim.duration, s.times.back());
                    anim.samplers.push_back(std::move(s));
                }
            }
            if (aj.contains("channels")) {
                for (const auto& cj : aj["channels"]) {
                    AnimChannel c;
                    c.node = cj["target"].value("node", -1);
                    std::string path = cj["target"].value("path", "");
                    c.path = path == "translation" ? 0 : path == "scale" ? 2 : 1;
                    c.sampler = cj.value("sampler", -1);
                    if (c.node >= 0 && c.sampler >= 0) anim.channels.push_back(c);
                }
            }
            m.animations.push_back(std::move(anim));
        }
    }

#ifdef WHALE3D_USE_OZZ
    if (!buildOzz(m)) {
        SDL_Log("ozz init failed: %s", m.ozzError.c_str());
    } else {
        SDL_Log("ozz ready: %d joints, clips=idle/walk",
                m.ozzSkeleton->num_joints());
    }
#endif

    m.loaded = true;
    update(0.0f);
    return true;
}

// ---- animation/global transform update ----
static void computeGlobals(Model::Impl& m) {
    std::function<void(int, const Mat4&)> walk = [&](int idx, const Mat4& parent) {
        if (idx < 0 || idx >= (int)m.nodes.size()) return;
        Node& n = m.nodes[(size_t)idx];
        n.global = matMultiply(parent, n.local);
        for (int c : n.children) walk(c, n.global);
    };
    for (size_t i = 0; i < m.nodes.size(); ++i) {
        if (m.nodes[i].parent < 0) walk((int)i, matIdentity());
    }
}

static void sampleAnimation(Model::Impl& m, Animation& anim, float time) {
    for (auto& n : m.nodes) n.resetLocal();
    if (anim.samplers.empty() || anim.channels.empty()) return;

    float t = anim.duration > 0.0f ? std::fmod(time, anim.duration) : 0.0f;
    for (const auto& ch : anim.channels) {
        if (ch.sampler < 0 || ch.sampler >= (int)anim.samplers.size()) continue;
        if (ch.node < 0 || ch.node >= (int)m.nodes.size()) continue;
        const AnimSampler& s = anim.samplers[(size_t)ch.sampler];
        if (s.times.empty() || s.components <= 0) continue;

        size_t i0 = 0;
        if (t <= s.times.front()) {
            i0 = 0;
        } else if (t >= s.times.back()) {
            i0 = s.times.size() - 1;
        } else {
            while (i0 + 1 < s.times.size() && s.times[i0 + 1] <= t) ++i0;
        }
        size_t i1 = std::min(i0 + 1, s.times.size() - 1);
        float u = (i1 == i0) ? 0.0f : (t - s.times[i0]) / (s.times[i1] - s.times[i0]);
        Node& n = m.nodes[(size_t)ch.node];

        if (ch.path == 1 && s.components == 4) {
            size_t o0 = i0 * 4, o1 = i1 * 4;
            Quat q0{s.values[o0], s.values[o0 + 1], s.values[o0 + 2], s.values[o0 + 3]};
            Quat q1{s.values[o1], s.values[o1 + 1], s.values[o1 + 2], s.values[o1 + 3]};
            Quat q = quatSlerp(q0, q1, u);
            n.r[0] = q.x; n.r[1] = q.y; n.r[2] = q.z; n.r[3] = q.w;
        } else if (s.components >= 3) {
            for (int k = 0; k < 3; ++k) {
                float v = s.values[i0 * s.components + k] * (1.0f - u) +
                          s.values[i1 * s.components + k] * u;
                if (ch.path == 0) n.t[k] = v;
                else if (ch.path == 2) n.s[k] = v;
            }
        }
        n.recompose();
    }
}

#ifdef WHALE3D_USE_OZZ
static Mat4 matFromOzz(const ozz::math::Float4x4& src) {
    Mat4 r{};
    std::memcpy(r.m, &src.cols[0], sizeof(r.m));
    return r;
}

static bool updateOzz(Model::Impl& m, float timeSeconds) {
    const ozz::animation::Animation* clip =
        (m.activeClip == 1 && m.ozzWalk) ? m.ozzWalk.get() : m.ozzIdle.get();
    if (!clip || !m.ozzContext || m.ozzModels.empty() || m.ozzLocals.empty()) return false;
    float duration = clip->duration();
    if (duration <= 0.0f) return false;
    float ratio = std::fmod(timeSeconds, duration) / duration;
    if (ratio < 0.0f) ratio += 1.0f;

    ozz::animation::SamplingJob sampling;
    sampling.animation = clip;
    sampling.context = m.ozzContext.get();
    sampling.ratio = ratio;
    sampling.output = ozz::make_span(m.ozzLocals);
    if (!sampling.Run()) return false;

    ozz::animation::LocalToModelJob localToModel;
    localToModel.skeleton = m.ozzSkeleton.get();
    localToModel.input = ozz::make_span(m.ozzLocals);
    localToModel.output = ozz::make_span(m.ozzModels);
    if (!localToModel.Run()) return false;

    for (auto& skin : m.skins) {
        for (size_t j = 0; j < skin.joints.size() && j < m.skinToOzz.size(); ++j) {
            int s = m.skinToOzz[j];
            if (s < 0 || s >= (int)m.ozzModels.size() || j >= skin.inverseBind.size()) continue;
            Mat4 model = matFromOzz(m.ozzModels[(size_t)s]);
            skin.jointMatrices[j] = matMultiply(model, skin.inverseBind[j]);
        }
    }
    return true;
}
#endif

static void updateFace(Model::Impl& m, float timeSeconds) {
    if (m.forcedFace >= 0) {
        m.faceFrame = m.forcedFace;
        return;
    }
    if (timeSeconds >= m.nextBlink && timeSeconds > m.blinkUntil) {
        m.blinkUntil = timeSeconds + 0.18f;
        m.nextBlink = timeSeconds + 3.2f;
    }
    m.faceFrame = (timeSeconds < m.blinkUntil) ? 1 : (m.smile ? 2 : 0);
}

void Model::update(float timeSeconds) {
    Impl& m = *impl_;
    if (!m.loaded) return;
    updateFace(m, timeSeconds);
#ifdef WHALE3D_USE_OZZ
    if (m.useOzz && m.ozzReady && updateOzz(m, timeSeconds)) return;
#endif
    if (!m.animations.empty()) {
        sampleAnimation(m, m.animations.front(), timeSeconds);
    } else {
        for (auto& n : m.nodes) n.resetLocal();
    }
    computeGlobals(m);

    for (auto& skin : m.skins) {
        for (size_t j = 0; j < skin.joints.size(); ++j) {
            int ni = skin.joints[j];
            if (ni >= 0 && ni < (int)m.nodes.size() && j < skin.inverseBind.size()) {
                skin.jointMatrices[j] = matMultiply(m.nodes[(size_t)ni].global, skin.inverseBind[j]);
            }
        }
    }
}

void Model::draw(const float viewProjection[16]) {
    Impl& m = *impl_;
    if (!m.loaded || !m.program) return;

    Mat4 viewProj = matFromArray(viewProjection);
    m.gl.useProgram(m.program);
    m.gl.uniform3f(m.uLightDir, -0.45f, 0.75f, 0.65f);
    m.gl.uniform1i(m.uTex, 0);
    m.gl.uniform1i(m.uFaceFrame, m.faceFrame);

    for (const auto& node : m.nodes) {
        if (node.mesh < 0 || node.mesh >= (int)m.meshes.size()) continue;
        bool skinned = node.skin >= 0 && node.skin < (int)m.skins.size();
        Mat4 model = skinned ? matIdentity() : node.global;
        Mat4 mvp = matMultiply(viewProj, model);
        m.gl.uniformMatrix4fv(m.uMVP, 1, GL_FALSE, mvp.m);
        m.gl.uniformMatrix4fv(m.uModel, 1, GL_FALSE, model.m);
        m.gl.uniform1i(m.uSkinned, skinned ? 1 : 0);
        if (skinned) {
            const Skin& skin = m.skins[(size_t)node.skin];
            if (!skin.jointMatrices.empty()) {
                m.gl.uniformMatrix4fv(m.uJoints, (GLsizei)skin.jointMatrices.size(),
                                      GL_FALSE, skin.jointMatrices[0].m);
            }
        }

        const Mesh& mesh = m.meshes[(size_t)node.mesh];
        for (const auto& p : mesh.primitives) {
            if (p.material >= 0 && p.material < (int)m.materials.size()) {
                const Material& mm = m.materials[(size_t)p.material];
                m.gl.uniform4f(m.uBaseColor, mm.baseColor[0], mm.baseColor[1],
                               mm.baseColor[2], mm.baseColor[3]);
                m.gl.uniform1i(m.uUseTex, mm.texture ? 1 : 0);
                if (mm.texture) {
                    m.gl.activeTexture(GL_TEXTURE0);
                    glBindTexture(GL_TEXTURE_2D, mm.texture);
                }
            } else {
                m.gl.uniform4f(m.uBaseColor, 1, 1, 1, 1);
                m.gl.uniform1i(m.uUseTex, 0);
            }
            m.gl.bindVertexArray(p.vao);
            if (p.useElements) {
                glDrawElements(GL_TRIANGLES, p.indexCount, p.indexType, nullptr);
            } else {
                glDrawArrays(GL_TRIANGLES, 0, p.indexCount);
            }
        }
    }
    m.gl.bindVertexArray(0);
}
