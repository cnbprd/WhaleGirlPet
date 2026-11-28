#pragma once

#include <SDL3/SDL.h>

#include <array>
#include <cstdint>
#include <cstdio>
#include <string>

// v3.3 stage 4: explicit pass boundaries around the existing OpenGL calls.
// This is deliberately not a second rendering backend: GLRenderer owns the
// frame/pass clock and stats, while Model/SpriteLayer still issue their GL.
enum class RenderPass : uint8_t {
    Model = 0,
    HitMask,
    Sprite,
    Region,
    Count,
};

inline const char* renderPassName(RenderPass pass) {
    switch (pass) {
        case RenderPass::Model: return "model";
        case RenderPass::HitMask: return "hitmask";
        case RenderPass::Sprite: return "sprite";
        case RenderPass::Region: return "region";
        default: return "?";
    }
}

inline const char* renderPassInputs(RenderPass pass) {
    switch (pass) {
        case RenderPass::Model: return "view_proj + skinned pose";
        case RenderPass::HitMask: return "model color back buffer";
        case RenderPass::Sprite: return "atlas + card rect";
        case RenderPass::Region: return "hit mask alpha + card rect";
        default: return "";
    }
}

inline const char* renderPassOutputs(RenderPass pass) {
    switch (pass) {
        case RenderPass::Model: return "color/depth back buffer";
        case RenderPass::HitMask: return "RGBA hit mask";
        case RenderPass::Sprite: return "card overlay pixels";
        case RenderPass::Region: return "window/overlay input region";
        default: return "";
    }
}

struct PassSample {
    uint64_t lastUs = 0;
    uint64_t totalUs = 0;
    uint32_t count = 0;

    double lastMs() const { return static_cast<double>(lastUs) / 1000.0; }
    double avgMs() const {
        return count ? static_cast<double>(totalUs) / static_cast<double>(count) / 1000.0 : 0.0;
    }
};

class IRenderer {
public:
    virtual ~IRenderer() = default;
    virtual void beginFrame() = 0;
    virtual void beginPass(RenderPass pass) = 0;
    virtual void endPass() = 0;
    virtual void endFrame() = 0;
    virtual std::string describe() const = 0;
};

class GLRenderer final : public IRenderer {
public:
    GLRenderer() : freq_(SDL_GetPerformanceFrequency()) {}

    void beginFrame() override {
        frameStart_ = now();
        active_ = RenderPass::Count;
        passStart_ = 0;
        frameUs_ = 0;
    }

    void beginPass(RenderPass pass) override {
        if (active_ != RenderPass::Count) endPass();
        active_ = pass;
        passStart_ = now();
    }

    void endPass() override {
        if (active_ == RenderPass::Count || !passStart_) return;
        const uint64_t elapsed = toUs(now() - passStart_);
        PassSample& sample = samples_[static_cast<size_t>(active_)];
        sample.lastUs = elapsed;
        sample.totalUs += elapsed;
        ++sample.count;
        active_ = RenderPass::Count;
        passStart_ = 0;
    }

    void endFrame() override {
        if (active_ != RenderPass::Count) endPass();
        frameUs_ = toUs(now() - frameStart_);
    }

    std::string describe() const override {
        char text[256];
        std::snprintf(text, sizeof(text),
                      "passes model=%.2fms hitmask=%.2fms sprite=%.2fms "
                      "region=%.2fms frame_last=%.2fms",
                      samples_[static_cast<size_t>(RenderPass::Model)].avgMs(),
                      samples_[static_cast<size_t>(RenderPass::HitMask)].avgMs(),
                      samples_[static_cast<size_t>(RenderPass::Sprite)].avgMs(),
                      samples_[static_cast<size_t>(RenderPass::Region)].avgMs(),
                      frameUs_ ? static_cast<double>(frameUs_) / 1000.0 : 0.0);
        return text;
    }

    std::string describeCompact() const {
        char text[192];
        std::snprintf(text, sizeof(text),
                      "model=%.2f hitmask=%.2f\nsprite=%.2f region=%.2f frame=%.2f",
                      samples_[static_cast<size_t>(RenderPass::Model)].lastMs(),
                      samples_[static_cast<size_t>(RenderPass::HitMask)].lastMs(),
                      samples_[static_cast<size_t>(RenderPass::Sprite)].lastMs(),
                      samples_[static_cast<size_t>(RenderPass::Region)].lastMs(),
                      frameUs_ ? static_cast<double>(frameUs_) / 1000.0 : 0.0);
        return text;
    }

    const PassSample& sample(RenderPass pass) const {
        return samples_[static_cast<size_t>(pass)];
    }

private:
    uint64_t now() const { return SDL_GetPerformanceCounter(); }
    uint64_t toUs(uint64_t ticks) const {
        return freq_ ? ticks * 1000000ULL / freq_ : 0;
    }

    uint64_t freq_ = 0;
    uint64_t frameStart_ = 0;
    uint64_t passStart_ = 0;
    uint64_t frameUs_ = 0;
    RenderPass active_ = RenderPass::Count;
    std::array<PassSample, static_cast<size_t>(RenderPass::Count)> samples_{};
};

class NullRenderer final : public IRenderer {
public:
    void beginFrame() override {}
    void beginPass(RenderPass) override {}
    void endPass() override {}
    void endFrame() override {}
    std::string describe() const override { return "passes disabled"; }
};
