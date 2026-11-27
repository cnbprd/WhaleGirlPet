#pragma once

// Pure, GL-free manifest parsing for the sprite layer. This is split out so
// the 17 bad-manifest fixtures can run without creating an SDL/OpenGL context.
// It deliberately has no dependency on sprite.h, SDL3, stb_image or GL.

#include <string>
#include <unordered_map>

namespace sprite_manifest {

struct CardRect {
    float u0 = 0.0f;
    float v0 = 0.0f;
    float u1 = 0.0f;
    float v1 = 0.0f;
    int w = 0;
    int h = 0;
};

struct Data {
    int sheet_w = 0;
    int sheet_h = 0;
    std::string sheet_rel;
    std::unordered_map<std::string, CardRect> cards;
};

// Parses a manifest JSON string and fills `out`. On failure returns false and
// keeps the same error strings/order as SpriteLayer::Impl::loadAtlas.
bool parseJson(const std::string& text, Data& out, std::string& err);

// Compares the manifest sheet size with the decoded atlas size. The atlas
// decoding itself stays in sprite.cpp; this only owns the dimension check.
bool validateAtlasSize(const Data& data, int actual_w, int actual_h,
                       std::string& err);

}  // namespace sprite_manifest
