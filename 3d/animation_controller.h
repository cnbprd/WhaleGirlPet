#pragma once

// v3.3 stage 2 first cut: logical animation arbitration only.
// No SDL/GL dependency, so this can be unit-tested without a GPU.
// Model still owns sampling/GL; this class only decides which state should
// be active and when it expires.

#include "third_party/json.hpp"

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

class AnimationController {
public:
    struct State {
        std::string id;
        std::string layer;
        std::string clip;
        std::string face;
        int priority = 0;
        bool loop = true;
        bool interruptible = true;
        float ttlMs = 0.0f;
        float fadeInMs = 0.0f;
        float fadeOutMs = 0.0f;
    };

    struct Decision {
        std::string stateId;
        std::string clip;
        std::string face;
        std::string source;
        int priority = 0;
        bool changed = false;
        float fadeInMs = 0.0f;
        float fadeOutMs = 0.0f;
    };

    AnimationController() = default;

    bool loadJson(const std::string& text, std::string& error) {
        try {
            const nlohmann::json root = nlohmann::json::parse(text);
            if (!root.is_object()) {
                error = "state table root must be an object";
                return false;
            }
            if (!root.contains("states") || !root["states"].is_array()) {
                error = "state table missing states array";
                return false;
            }
            const std::string defaultId = root.value("default", "idle");
            std::vector<State> parsed;
            for (const auto& item : root["states"]) {
                if (!item.is_object()) {
                    error = "state entry must be an object";
                    return false;
                }
                State state;
                state.id = item.value("id", "");
                state.layer = item.value("layer", "");
                state.clip = item.value("clip", "");
                state.face = item.value("face", "");
                state.priority = item.value("priority", 0);
                state.loop = item.value("loop", true);
                state.interruptible = item.value("interruptible", true);
                state.ttlMs = item.value("ttlMs", 0.0f);
                state.fadeInMs = item.value("fadeInMs", 0.0f);
                state.fadeOutMs = item.value("fadeOutMs", 0.0f);

                if (state.id.empty() || state.layer.empty() ||
                    state.clip.empty()) {
                    error = "state id/layer/clip must be non-empty";
                    return false;
                }
                if (state.layer != "base" && state.layer != "face" &&
                    state.layer != "action" && state.layer != "overlay") {
                    error = "unknown layer: " + state.layer;
                    return false;
                }
                if (state.priority < 0 || state.priority > 100) {
                    error = "priority out of range: " + state.id;
                    return false;
                }
                if (state.ttlMs < 0.0f || state.fadeInMs < 0.0f ||
                    state.fadeOutMs < 0.0f) {
                    error = "negative timing: " + state.id;
                    return false;
                }
                if (std::any_of(parsed.begin(), parsed.end(),
                                [&](const State& s) { return s.id == state.id; })) {
                    error = "duplicate state id: " + state.id;
                    return false;
                }
                parsed.push_back(std::move(state));
            }
            if (parsed.empty()) {
                error = "state table has no states";
                return false;
            }
            bool hasDefault = false;
            for (const auto& state : parsed) {
                if (state.id == defaultId) hasDefault = true;
            }
            if (!hasDefault) {
                error = "default state not found: " + defaultId;
                return false;
            }

            states_ = std::move(parsed);
            defaultId_ = defaultId;
            activeId_.clear();
            pending_.clear();
            seq_ = 0;
            error.clear();
            return true;
        } catch (const std::exception& e) {
            error = std::string("state table json: ") + e.what();
            return false;
        }
    }

    bool start(const std::string& id, std::string& error) {
        const State* state = find(id);
        if (!state) {
            error = "unknown state: " + id;
            return false;
        }
        activeId_ = id;
        defaultId_ = id;
        activeFromPending_ = false;
        pending_.clear();
        seq_ = 0;
        error.clear();
        return true;
    }

    // priorityOverride/ttlOverride < 0 means "use the state table value".
    bool request(const std::string& id, const std::string& source,
                 int priorityOverride = -1, float ttlOverrideMs = -1.0f,
                 std::string* error = nullptr) {
        const State* state = find(id);
        if (!state) {
            if (error) *error = "unknown state: " + id;
            return false;
        }
        const int priority = priorityOverride >= 0
            ? priorityOverride : state->priority;
        const float ttl = ttlOverrideMs >= 0.0f
            ? ttlOverrideMs : state->ttlMs;
        // A zero/unset TTL means "no expiry", not "expire on the next update".
        const float remainingMs = ttl > 0.0f ? ttl : -1.0f;

        for (auto& pending : pending_) {
            if (pending.id == id && pending.source == source) {
                pending.priority = priority;
                pending.remainingMs = remainingMs;
                pending.seq = ++seq_;
                if (error) error->clear();
                return true;
            }
        }
        // Same state from a different source also replaces the older active
        // instance; otherwise two identical actions can never settle.
        for (auto& pending : pending_) {
            if (pending.id == id) {
                pending.priority = priority;
                pending.remainingMs = remainingMs;
                pending.source = source;
                pending.seq = ++seq_;
                if (error) error->clear();
                return true;
            }
        }
        pending_.push_back(Pending{id, source, priority, remainingMs, ++seq_});
        if (error) error->clear();
        return true;
    }

    Decision update(float dtMs) {
        Decision result;
        const bool wasActive = !activeId_.empty();
        const std::string previous = activeId_;
        expire(dtMs);

        // An expired action must stop blocking lower-priority requests even
        // though its state definition is still in the table. A state passed
        // directly to start() is pinned until an explicit request replaces it.
        if (!activeId_.empty() && activeId_ != defaultId_ && activeFromPending_) {
            const bool stillPending = std::any_of(
                pending_.begin(), pending_.end(),
                [&](const Pending& p) { return p.id == activeId_; });
            if (!stillPending) {
                activeId_.clear();
                activeSource_.clear();
                activeFromPending_ = false;
            }
        }

        const Pending* best = chooseBest();
        const State* active = find(activeId_);
        bool switchToBest = false;
        if (best) {
            if (active && !active->interruptible &&
                best->priority <= active->priority) {
                switchToBest = false;
            } else {
                switchToBest = true;
            }
        }

        if (switchToBest) {
            activeId_ = best->id;
            activeSource_ = best->source;
            activeFromPending_ = true;
        } else if (!best && !activeId_.empty()) {
            activeId_ = defaultId_;
            activeSource_.clear();
            activeFromPending_ = false;
        } else if (activeId_.empty()) {
            activeId_ = defaultId_;
            activeSource_.clear();
            activeFromPending_ = false;
        }

        const State* current = find(activeId_);
        if (current) {
            result.stateId = current->id;
            result.clip = current->clip;
            result.face = current->face;
            result.priority = current->priority;
            result.source = activeSource_;
            result.changed = wasActive ? (previous != activeId_) : true;
            result.fadeInMs = current->fadeInMs;
            result.fadeOutMs = current->fadeOutMs;
            result.fadeOutMs = current->fadeOutMs;
        }
        last_ = result;
        return result;
    }

    // Fixed-step wrapper. dtMs is wall time; logic advances in fixedStepMs
    // chunks, capped at maxSubsteps per call so a long frame cannot explode.
    Decision advance(float dtMs, int maxSubsteps = 4) {
        accumulatorMs_ += std::max(0.0f, dtMs);
        int steps = 0;
        substepsLast_ = 0;
        while (accumulatorMs_ >= fixedStepMs_ && steps < maxSubsteps) {
            accumulatorMs_ -= fixedStepMs_;
            update(fixedStepMs_);
            ++steps;
            ++substepsLast_;
        }
        if (steps == maxSubsteps && accumulatorMs_ > fixedStepMs_) {
            accumulatorMs_ = fixedStepMs_;
        }
        return last_;
    }

    void setFixedStepMs(float ms) {
        if (ms > 0.0f) fixedStepMs_ = ms;
    }

    const Decision& current() const { return last_; }
    bool active() const { return !activeId_.empty(); }
    bool hasState(const std::string& id) const { return find(id) != nullptr; }
    const std::string& activeId() const { return activeId_; }
    const std::string& defaultId() const { return defaultId_; }
    int pendingCount() const { return static_cast<int>(pending_.size()); }
    int lastSubsteps() const { return substepsLast_; }

private:
    struct Pending {
        std::string id;
        std::string source;
        int priority = 0;
        float remainingMs = 0.0f;  // < 0 means no expiry
        uint64_t seq = 0;
    };

    const State* find(const std::string& id) const {
        for (const auto& state : states_) {
            if (state.id == id) return &state;
        }
        return nullptr;
    }

    void expire(float dtMs) {
        for (auto& pending : pending_) {
            if (pending.remainingMs > 0.0f) {
                pending.remainingMs -= std::max(0.0f, dtMs);
                if (pending.remainingMs < 0.0f) pending.remainingMs = 0.0f;
            }
        }
        pending_.erase(
            std::remove_if(pending_.begin(), pending_.end(),
                           [](const Pending& p) { return p.remainingMs == 0.0f; }),
            pending_.end());
    }

    const Pending* chooseBest() const {
        const Pending* best = nullptr;
        for (const auto& pending : pending_) {
            if (!best || pending.priority > best->priority ||
                (pending.priority == best->priority && pending.seq > best->seq)) {
                best = &pending;
            }
        }
        return best;
    }

    std::vector<State> states_;
    std::string defaultId_;
    std::string activeId_;
    std::string activeSource_;
    bool activeFromPending_ = false;
    std::vector<Pending> pending_;
    uint64_t seq_ = 0;
    float fixedStepMs_ = 1000.0f / 60.0f;
    float accumulatorMs_ = 0.0f;
    int substepsLast_ = 0;
    Decision last_{};
};
