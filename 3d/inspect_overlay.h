#pragma once

#include <windows.h>
#include <string>

// v3.3 stage 4: optional click-through Win32 text overlay for developer
// inspection. It is independent from the OpenGL window and only used by
// --inspect; it never owns model/sprite state.
class InspectOverlay {
public:
    InspectOverlay() = default;
    ~InspectOverlay();

    InspectOverlay(const InspectOverlay&) = delete;
    InspectOverlay& operator=(const InspectOverlay&) = delete;

    bool init(HWND owner);
    void update(const std::string& text);
    void shutdown();
    void paint(HDC dc) const;

private:
    HWND hwnd_ = nullptr;
    HWND owner_ = nullptr;
    HDC memDc_ = nullptr;
    HBITMAP bitmap_ = nullptr;
    HFONT font_ = nullptr;
    int width_ = 0;
    int height_ = 0;
};
