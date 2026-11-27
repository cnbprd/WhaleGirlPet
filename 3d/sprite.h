#pragma once

#include <string>

// v3.2 sprite skeleton: a single screen-space textured quad fed by the 2D
// atlas manifest.  It deliberately does not own the render loop yet; the
// main.cpp hookup comes after the 24h soak.
class SpriteLayer {
public:
    SpriteLayer();
    ~SpriteLayer();

    SpriteLayer(const SpriteLayer&) = delete;
    SpriteLayer& operator=(const SpriteLayer&) = delete;

    // `assetBase` is the directory that contains `assets/` (same convention as
    // main.cpp's SDL_GetBasePath()).  Must be called after the GL context is
    // current.
    bool init(const std::string& assetBase);
    void shutdown();

    // Card ids come from `assets/2d_bridge/manifest.json`; unknown ids fail.
    bool showCard(const std::string& cardId, float ttlMs = 1800.0f);
    void update(float dtSeconds);

    // Draw in the bottom-right corner.  Call after the hit-mask glReadPixels
    // and before SDL_GL_SwapWindow so the decoration is not clickable.
    void draw(int pixelWidth, int pixelHeight);

    bool visible() const;
    const std::string& card() const;
    const std::string& error() const;

private:
    struct Impl;
    Impl* impl_;
};
