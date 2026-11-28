#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <winsock2.h>
#include <ws2tcpip.h>

#include "emotion_bus.h"

#include <cctype>
#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <utility>

namespace {
constexpr int kMaxPacket = 512;

bool jsonString(const std::string& raw, const char* key, std::string& out) {
    const std::string needle = std::string("\"") + key + "\"";
    size_t p = raw.find(needle);
    if (p == std::string::npos) return false;
    p = raw.find(':', p + needle.size());
    if (p == std::string::npos) return false;
    p = raw.find('"', p + 1);
    if (p == std::string::npos) return false;
    const size_t end = raw.find('"', p + 1);
    if (end == std::string::npos) return false;
    out = raw.substr(p + 1, end - p - 1);
    return !out.empty();
}

bool jsonNumber(const std::string& raw, const char* key, float& out) {
    const std::string needle = std::string("\"") + key + "\"";
    size_t p = raw.find(needle);
    if (p == std::string::npos) return false;
    p = raw.find(':', p + needle.size());
    if (p == std::string::npos) return false;
    p += 1;
    while (p < raw.size() && std::isspace(static_cast<unsigned char>(raw[p]))) ++p;
    char* end = nullptr;
    errno = 0;
    const float value = std::strtof(raw.c_str() + p, &end);
    if (errno != 0 || end == raw.c_str() + p) return false;
    out = value;
    return true;
}

bool jsonObject(const std::string& raw, const char* key, std::string& out) {
    const std::string needle = std::string("\"") + key + "\"";
    size_t p = raw.find(needle);
    if (p == std::string::npos) return false;
    p = raw.find('{', p + needle.size());
    if (p == std::string::npos) return false;
    int depth = 0;
    for (size_t i = p; i < raw.size(); ++i) {
        if (raw[i] == '{') {
            ++depth;
        } else if (raw[i] == '}') {
            if (--depth == 0) {
                out = raw.substr(p, i - p + 1);
                return true;
            }
        }
    }
    return false;
}

void readPose(const std::string& raw, const char* key,
              float& x, float& y, float& weight) {
    x = 0.0f;
    y = 0.0f;
    weight = 0.0f;
    std::string body;
    if (!jsonObject(raw, key, body)) return;
    jsonNumber(body, "x", x);
    jsonNumber(body, "y", y);
    weight = 1.0f;
    jsonNumber(body, "weight", weight);
    if (!std::isfinite(x)) x = 0.0f;
    if (!std::isfinite(y)) y = 0.0f;
    if (!std::isfinite(weight)) weight = 0.0f;
    x = std::clamp(x, -1.0f, 1.0f);
    y = std::clamp(y, -1.0f, 1.0f);
    weight = std::clamp(weight, 0.0f, 1.0f);
}

bool parseFrame(const std::string& raw, EmotionBus::Frame& out) {
    std::string emotion;
    if (!jsonString(raw, "emotion", emotion)) return false;

    float intensity = 1.0f;
    jsonNumber(raw, "intensity", intensity);
    if (!std::isfinite(intensity)) intensity = 1.0f;
    intensity = std::clamp(intensity, 0.0f, 1.0f);

    float attackMs = 180.0f;
    float releaseMs = 420.0f;
    jsonNumber(raw, "attack_ms", attackMs);
    jsonNumber(raw, "release_ms", releaseMs);
    if (!std::isfinite(attackMs) || attackMs < 40.0f) attackMs = 40.0f;
    if (attackMs > 2000.0f) attackMs = 2000.0f;
    if (!std::isfinite(releaseMs) || releaseMs < 40.0f) releaseMs = 40.0f;
    if (releaseMs > 2000.0f) releaseMs = 2000.0f;

    float gazeX = 0.0f, gazeY = 0.0f, gazeWeight = 0.0f;
    float leanX = 0.0f, leanY = 0.0f, leanWeight = 0.0f;
    readPose(raw, "gaze", gazeX, gazeY, gazeWeight);
    readPose(raw, "lean", leanX, leanY, leanWeight);

    std::string card;
    jsonString(raw, "card", card);
    float cardTtlMs = 0.0f;
    jsonNumber(raw, "card_ttl_ms", cardTtlMs);
    if (!std::isfinite(cardTtlMs) || cardTtlMs < 0.0f) cardTtlMs = 0.0f;
    if (cardTtlMs > 10000.0f) cardTtlMs = 10000.0f;

    out.emotion = emotion;
    out.intensity = intensity;
    out.attackMs = attackMs;
    out.releaseMs = releaseMs;
    out.gazeX = gazeX;
    out.gazeY = gazeY;
    out.gazeWeight = gazeWeight;
    out.leanX = leanX;
    out.leanY = leanY;
    out.leanWeight = leanWeight;
    out.card = card;
    out.cardTtlMs = cardTtlMs;
    out.raw = raw;
    out.source.clear();
    jsonString(raw, "source", out.source);
    return true;
}
}  // namespace

EmotionBus::EmotionBus() = default;

EmotionBus::~EmotionBus() {
    stop();
}

bool EmotionBus::start(int port) {
    stop();
    if (port <= 0 || port > 65535) return false;

    WSADATA data{};
    if (WSAStartup(MAKEWORD(2, 2), &data) != 0) return false;
    wsaStarted_ = true;

    SOCKET sock = ::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) {
        stop();
        return false;
    }
    socket_ = static_cast<unsigned long long>(sock);
    port_ = port;

    BOOL yes = TRUE;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR,
               reinterpret_cast<const char*>(&yes), sizeof(yes));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<unsigned short>(port));
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(sock, reinterpret_cast<const sockaddr*>(&addr), sizeof(addr)) == SOCKET_ERROR) {
        std::fprintf(stderr, "emotion bus: bind 127.0.0.1:%d failed (%d)\n",
                     port, WSAGetLastError());
        stop();
        return false;
    }

    u_long nonBlocking = 1;
    if (ioctlsocket(sock, FIONBIO, &nonBlocking) == SOCKET_ERROR) {
        stop();
        return false;
    }
    return true;
}

void EmotionBus::stop() {
    if (socket_ != ~0ULL) {
        SOCKET sock = static_cast<SOCKET>(socket_);
        closesocket(sock);
        socket_ = ~0ULL;
    }
    if (wsaStarted_) {
        WSACleanup();
        wsaStarted_ = false;
    }
    port_ = 0;
}

bool EmotionBus::running() const {
    return socket_ != ~0ULL;
}

int EmotionBus::receivedCount() const {
    return received_;
}

bool EmotionBus::pollAll(std::vector<Frame>& out) {
    out.clear();
    if (!running()) return false;

    SOCKET sock = static_cast<SOCKET>(socket_);
    for (;;) {
        char buffer[kMaxPacket + 1]{};
        sockaddr_in from{};
        int fromLen = sizeof(from);
        const int n = recvfrom(sock, buffer, kMaxPacket, 0,
                               reinterpret_cast<sockaddr*>(&from), &fromLen);
        if (n == SOCKET_ERROR) {
            const int err = WSAGetLastError();
            if (err == WSAEWOULDBLOCK) break;
            break;
        }
        if (n <= 0) continue;

        Frame frame;
        if (!parseFrame(std::string(buffer, static_cast<size_t>(n)), frame)) {
            continue;
        }
        ++received_;
        out.push_back(std::move(frame));
    }
    return !out.empty();
}

bool EmotionBus::poll(Frame& out) {
    std::vector<Frame> frames;
    if (!pollAll(frames)) return false;
    out = std::move(frames.back());
    return true;
}
