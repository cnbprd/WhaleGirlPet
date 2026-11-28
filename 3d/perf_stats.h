#pragma once

// v3.3 stage 1: lightweight frame/pass statistics for the 3D shell.
// Header-only so the existing build.ps1 source list does not need a new .cpp.
// Enabled by WHALE3D_STAT=1 or WHALE3D_TRACE=<path>.

#include <SDL3/SDL.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

class PerfStats {
public:
    struct FrameSample {
        uint64_t intervalUs = 0;
        uint64_t workUs = 0;
        uint64_t updateUs = 0;
        uint64_t renderUs = 0;
        uint64_t readbackUs = 0;
        uint64_t regionUs = 0;
        uint64_t overlayUs = 0;
        uint64_t swapUs = 0;
    };

    class Timer {
    public:
        Timer(PerfStats& owner, uint64_t& target)
            : owner_(owner),
              target_(target),
              active_(owner.enabled()),
              start_(active_ ? owner.now() : 0) {}
        ~Timer() {
            if (active_) target_ += owner_.toUs(owner_.now() - start_);
        }

        Timer(const Timer&) = delete;
        Timer& operator=(const Timer&) = delete;

    private:
        PerfStats& owner_;
        uint64_t& target_;
        bool active_ = false;
        uint64_t start_ = 0;
    };

    PerfStats()
        : enabled_(std::getenv("WHALE3D_STAT") != nullptr ||
                   std::getenv("WHALE3D_TRACE") != nullptr),
          freq_(SDL_GetPerformanceFrequency()),
          lastLog_(now()),
          lastFrameStart_(now()) {
        const char* tracePath = std::getenv("WHALE3D_TRACE");
        if (tracePath && *tracePath) {
            trace_ = std::fopen(tracePath, "a");
        }
    }

    ~PerfStats() {
        if (trace_) {
            std::fclose(trace_);
            trace_ = nullptr;
        }
    }

    PerfStats(const PerfStats&) = delete;
    PerfStats& operator=(const PerfStats&) = delete;

    bool enabled() const { return enabled_; }

    uint64_t now() const {
        return SDL_GetPerformanceCounter();
    }

    uint64_t toUs(uint64_t ticks) const {
        return freq_ ? (ticks * 1000000ULL / freq_) : 0;
    }

    void beginFrame() {
        if (!enabled_) return;
        const uint64_t t = now();
        current_ = FrameSample{};
        current_.intervalUs = lastFrameStart_ ? toUs(t - lastFrameStart_) : 0;
        lastFrameStart_ = t;
        frameStart_ = t;
    }

    // Drop startup/warm-up samples without touching the log cadence.
    void resetSamples() {
        if (!enabled_) return;
        sampleHead_ = 0;
        sampleCount_ = 0;
        frames_ = 0;
        hitches_ = 0;
        sumWorkUs_ = sumUpdateUs_ = sumRenderUs_ = 0;
        sumReadbackUs_ = sumRegionUs_ = sumOverlayUs_ = sumSwapUs_ = 0;
        lastLog_ = now();
        lastFrameStart_ = lastLog_;
    }

    void endFrame() {
        if (!enabled_) return;
        current_.workUs = toUs(now() - frameStart_);
        samples_[sampleHead_] = current_;
        sampleHead_ = (sampleHead_ + 1) % kCapacity;
        sampleCount_ = std::min(sampleCount_ + 1, kCapacity);
        ++frames_;
        sumWorkUs_ += current_.workUs;
        sumUpdateUs_ += current_.updateUs;
        sumRenderUs_ += current_.renderUs;
        sumReadbackUs_ += current_.readbackUs;
        sumRegionUs_ += current_.regionUs;
        sumOverlayUs_ += current_.overlayUs;
        sumSwapUs_ += current_.swapUs;
        if (current_.intervalUs > 50000) ++hitches_;
    }

    // Intended to be called once per frame after endFrame().  Emits a compact
    // one-line summary every second and, when WHALE3D_TRACE is set, one JSONL
    // record with the same window.
    void maybeLog() {
        if (!enabled_ || frames_ == 0 || freq_ == 0) return;
        const uint64_t t = now();
        const uint64_t elapsedUs = (t - lastLog_) * 1000000ULL / freq_;
        if (elapsedUs < 1000000ULL) return;

        const double fps = static_cast<double>(frames_) * 1000000.0 /
                           static_cast<double>(std::max<uint64_t>(elapsedUs, 1));
        const double intervalP50 = percentileMs(0.50, true);
        const double intervalP95 = percentileMs(0.95, true);
        const double intervalP99 = percentileMs(0.99, true);
        const double updateAvg = avgMs(sumUpdateUs_);
        const double renderAvg = avgMs(sumRenderUs_);
        const double readbackAvg = avgMs(sumReadbackUs_);
        const double regionAvg = avgMs(sumRegionUs_);
        const double overlayAvg = avgMs(sumOverlayUs_);
        const double swapAvg = avgMs(sumSwapUs_);

        SDL_Log("stat fps=%.1f interval_p50=%.2fms p95=%.2fms p99=%.2fms "
                "work=%.2fms hitch=%u update=%.2fms render=%.2fms "
                "readback=%.2fms region=%.2fms overlay=%.2fms swap=%.2fms",
                fps, intervalP50, intervalP95, intervalP99,
                avgMs(sumWorkUs_), hitches_,
                updateAvg, renderAvg, readbackAvg, regionAvg, overlayAvg, swapAvg);

        if (trace_) {
            std::fprintf(trace_,
                         "{\"t_ms\":%llu,\"fps\":%.2f,\"frames\":%u,"
                         "\"p50_ms\":%.2f,\"p95_ms\":%.2f,\"p99_ms\":%.2f,"
                         "\"hitch\":%u,\"update_ms\":%.2f,\"render_ms\":%.2f,"
                         "\"readback_ms\":%.2f,\"region_ms\":%.2f,"
                         "\"overlay_ms\":%.2f,\"swap_ms\":%.2f}\n",
                         static_cast<unsigned long long>(SDL_GetTicks()),
                         fps, frames_, intervalP50, intervalP95, intervalP99,
                         hitches_, updateAvg, renderAvg, readbackAvg,
                         regionAvg, overlayAvg, swapAvg);
            std::fflush(trace_);
        }

        frames_ = 0;
        hitches_ = 0;
        sumUpdateUs_ = sumRenderUs_ = sumReadbackUs_ = 0;
        sumRegionUs_ = sumOverlayUs_ = sumSwapUs_ = sumWorkUs_ = 0;
        lastLog_ = t;
    }

    FrameSample& current() { return current_; }

private:
    static constexpr size_t kCapacity = 600;

    double avgMs(uint64_t sumUs) const {
        return frames_ > 0
            ? static_cast<double>(sumUs) / static_cast<double>(frames_) / 1000.0
            : 0.0;
    }

    double percentileMs(double p, bool interval) const {
        if (sampleCount_ == 0) return 0.0;
        std::array<uint64_t, kCapacity> tmp{};
        for (size_t i = 0; i < sampleCount_; ++i) {
            const size_t src = (sampleHead_ + kCapacity - sampleCount_ + i) % kCapacity;
            tmp[i] = interval ? samples_[src].intervalUs : samples_[src].workUs;
        }
        std::sort(tmp.begin(), tmp.begin() + static_cast<std::ptrdiff_t>(sampleCount_));
        size_t index = static_cast<size_t>(p * static_cast<double>(sampleCount_ - 1));
        if (index >= sampleCount_) index = sampleCount_ - 1;
        return static_cast<double>(tmp[index]) / 1000.0;
    }

    bool enabled_ = false;
    uint64_t freq_ = 0;
    uint64_t lastLog_ = 0;
    uint64_t lastFrameStart_ = 0;
    uint64_t frameStart_ = 0;
    uint64_t sumWorkUs_ = 0;
    uint64_t sumUpdateUs_ = 0;
    uint64_t sumRenderUs_ = 0;
    uint64_t sumReadbackUs_ = 0;
    uint64_t sumRegionUs_ = 0;
    uint64_t sumOverlayUs_ = 0;
    uint64_t sumSwapUs_ = 0;
    uint32_t frames_ = 0;
    uint32_t hitches_ = 0;
    std::array<FrameSample, kCapacity> samples_{};
    size_t sampleHead_ = 0;
    size_t sampleCount_ = 0;
    FrameSample current_{};
    FILE* trace_ = nullptr;
};
