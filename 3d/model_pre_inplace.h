#pragma once

#include <string>

// Minimal glTF 2.0 (GLB) skinned-mesh model for the WhaleGirl 3D shell.
// Supports: one buffer, bufferViews/accessors, triangles, materials with
// baseColorFactor + baseColorTexture, node hierarchy, skins, and LINEAR
// TRS animation.  It is intentionally not a general glTF implementation.
class Model {
public:
    struct Impl;

    Model();
    ~Model();

    Model(const Model&) = delete;
    Model& operator=(const Model&) = delete;

    bool load(const std::string& path);
    const std::string& sourcePath() const;
    void update(float timeSeconds);
    void draw(const float viewProjection[16]);
    void shutdown();

    bool loaded() const;
    int triangleCount() const;
    int jointCount() const;
    int animationCount() const;
    const std::string& error() const;

    // Selects the runtime sampler. "ozz" uses ozz-animation; "self" keeps
    // the original hand-written sampler as a reference/fallback.
    bool setAnimator(const std::string& name);
    bool usesOzz() const;
    const char* animatorName() const;

    // Clip selection: "idle" or "walk". Returns false if the clip is not
    // available (the self sampler only has the GLB idle clip).
    bool setClip(const std::string& name);
    void nextClip();
    const char* clipName() const;

    // Face frames baked into the atlas: 0 open, 1 blink, 2 smile.
    // "auto" resumes the blink scheduler; "open"/"blink"/"smile" force a frame.
    bool setFace(const std::string& name);
    void toggleSmile();
    void triggerBlink(float timeSeconds);
    const char* faceName() const;
    const char* faceMode() const;

private:
    Impl* impl_;
};
