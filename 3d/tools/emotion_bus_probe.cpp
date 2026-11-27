#include "emotion_bus.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>

int main(int argc, char** argv) {
    int port = 47837;
    double seconds = 3.0;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--port" && i + 1 < argc) {
            port = std::atoi(argv[++i]);
        } else if (arg == "--seconds" && i + 1 < argc) {
            seconds = std::atof(argv[++i]);
        }
    }
    EmotionBus bus;
    if (!bus.start(port)) {
        std::printf("start failed port=%d\n", port);
        std::fflush(stdout);
        return 1;
    }
    std::printf("ready port=%d\n", port);
    std::fflush(stdout);

    const auto start = std::chrono::steady_clock::now();
    while (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count()
           < seconds) {
        EmotionBus::Frame frame;
        if (bus.poll(frame)) {
            std::printf("valid emotion=%s card=%s ttl=%.0f source=%s\n",
                        frame.emotion.c_str(),
                        frame.card.empty() ? "-" : frame.card.c_str(),
                        frame.cardTtlMs, frame.source.c_str());
            std::fflush(stdout);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    std::printf("done received=%d\n", bus.receivedCount());
    std::fflush(stdout);
    bus.stop();
    return 0;
}
