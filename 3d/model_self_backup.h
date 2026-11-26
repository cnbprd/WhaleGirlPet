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
    void update(float timeSeconds);
    void draw(const float viewProjection[16]);
    void shutdown();

    bool loaded() const;
    int triangleCount() const;
    int jointCount() const;
    int animationCount() const;
    const std::string& error() const;

private:
    Impl* impl_;
};
