#include "sprite_manifest.h"

#include "third_party/json.hpp"

#include <exception>
#include <utility>

namespace sprite_manifest {

bool parseJson(const std::string& text, Data& out, std::string& err) {
    out = Data{};
    err.clear();
    try {
        const nlohmann::json j = nlohmann::json::parse(text);
        Data parsed;

        const auto& size = j.at("sheet_size");
        if (!size.is_array() || size.size() != 2) {
            err = "sheet_size must be two integers";
            return false;
        }
        parsed.sheet_w = size[0].get<int>();
        parsed.sheet_h = size[1].get<int>();
        if (parsed.sheet_w <= 0 || parsed.sheet_h <= 0) {
            err = "sheet_size must be positive";
            return false;
        }

        const auto& cardEntries = j.at("cards");
        if (!cardEntries.is_array() || cardEntries.empty()) {
            err = "cards must be a non-empty array";
            return false;
        }

        for (const auto& entry : cardEntries) {
            const std::string id = entry.at("id").get<std::string>();
            if (id.empty()) {
                err = "empty card id";
                return false;
            }
            if (parsed.cards.find(id) != parsed.cards.end()) {
                err = "duplicate card id: " + id;
                return false;
            }

            const auto& r = entry.at("rect");
            if (!r.is_array() || r.size() != 4) {
                err = "card rect must be four integers: " + id;
                return false;
            }
            const int x = r[0].get<int>();
            const int y = r[1].get<int>();
            const int w = r[2].get<int>();
            const int h = r[3].get<int>();
            if (w <= 0 || h <= 0 || x < 0 || y < 0 ||
                x + w > parsed.sheet_w || y + h > parsed.sheet_h) {
                err = "card outside atlas: " + id;
                return false;
            }

            CardRect rect;
            rect.u0 = static_cast<float>(x) / parsed.sheet_w;
            rect.u1 = static_cast<float>(x + w) / parsed.sheet_w;
            // stb rows are top-down and the first uploaded row lands at GL
            // texture v=0; keep v0 as the image top and v1 as the image bottom.
            rect.v0 = static_cast<float>(y) / parsed.sheet_h;
            rect.v1 = static_cast<float>(y + h) / parsed.sheet_h;
            rect.w = w;
            rect.h = h;
            parsed.cards[id] = rect;
        }

        parsed.sheet_rel = j.at("sheet").get<std::string>();
        if (parsed.sheet_rel.empty()) {
            err = "sheet path missing";
            return false;
        }

        out = std::move(parsed);
        return true;
    } catch (const std::exception& e) {
        err = std::string("manifest parse: ") + e.what();
        return false;
    }
}

bool validateAtlasSize(const Data& data, int actual_w, int actual_h,
                       std::string& err) {
    err.clear();
    if (actual_w != data.sheet_w || actual_h != data.sheet_h) {
        err = "atlas size mismatch: actual " + std::to_string(actual_w) + "x"
            + std::to_string(actual_h) + ", manifest "
            + std::to_string(data.sheet_w) + "x" + std::to_string(data.sheet_h);
        return false;
    }
    return true;
}

}  // namespace sprite_manifest
