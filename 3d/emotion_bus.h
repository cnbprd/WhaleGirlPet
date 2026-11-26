#pragma once

#include <string>

// v3.2 step 1: a tiny localhost UDP transport for high-level emotion
// parameters. It deliberately carries data only; the Python/LLM side owns
// intent and arbitration, while the 3D process only translates a frame into
// face/pose state.
//
// Datagram example:
// {"emotion":"happy","intensity":0.8,"source":"manual"}
class EmotionBus {
public:
    struct Frame {
        std::string emotion;
        float intensity = 0.0f;
        std::string source;
        std::string raw;
    };

    EmotionBus();
    ~EmotionBus();

    EmotionBus(const EmotionBus&) = delete;
    EmotionBus& operator=(const EmotionBus&) = delete;

    bool start(int port);
    void stop();
    bool running() const;

    // Non-blocking. Returns true when at least one valid datagram arrived;
    // `out` is the last valid frame from this poll.
    bool poll(Frame& out);
    int receivedCount() const;

private:
    unsigned long long socket_ = ~0ULL;
    int port_ = 0;
    int received_ = 0;
    bool wsaStarted_ = false;
};
