#include "inspect_overlay.h"

#include <algorithm>

namespace {

const wchar_t* kClass = L"WhaleGirlInspectOverlay";
InspectOverlay* g_overlay = nullptr;

LRESULT CALLBACK inspectProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_NCHITTEST:
            return HTTRANSPARENT;
        case WM_ERASEBKGND:
            return 1;
        case WM_PAINT: {
            PAINTSTRUCT ps{};
            HDC dc = BeginPaint(hwnd, &ps);
            if (g_overlay) g_overlay->paint(dc);
            EndPaint(hwnd, &ps);
            return 0;
        }
        case WM_DESTROY:
            return 0;
        default:
            return DefWindowProcW(hwnd, msg, wParam, lParam);
    }
}

}  // namespace

InspectOverlay::~InspectOverlay() {
    shutdown();
}

bool InspectOverlay::init(HWND owner) {
    if (hwnd_) return true;
    owner_ = owner;
    static ATOM atom = 0;
    if (!atom) {
        WNDCLASSEXW wc{};
        wc.cbSize = sizeof(wc);
        wc.lpfnWndProc = inspectProc;
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.hCursor = LoadCursorA(nullptr, IDC_ARROW);
        wc.lpszClassName = kClass;
        atom = RegisterClassExW(&wc);
        if (!atom) return false;
    }
    hwnd_ = CreateWindowExW(
        WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
        kClass, L"whale3d inspect", WS_POPUP,
        0, 0, 420, 260, nullptr, nullptr, GetModuleHandleW(nullptr), nullptr);
    if (!hwnd_) return false;
    HDC screen = GetDC(hwnd_);
    memDc_ = CreateCompatibleDC(screen);
    ReleaseDC(hwnd_, screen);
    if (!memDc_) {
        shutdown();
        return false;
    }
    font_ = CreateFontW(-14, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                        DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                        CLEARTYPE_QUALITY, FIXED_PITCH | FF_MODERN, L"Consolas");
    if (!font_) {
        shutdown();
        return false;
    }
    g_overlay = this;
    return true;
}

void InspectOverlay::paint(HDC dc) const {
    if (!dc || !memDc_ || width_ <= 0 || height_ <= 0) return;
    BitBlt(dc, 0, 0, width_, height_, memDc_, 0, 0, SRCCOPY);
}

void InspectOverlay::update(const std::string& text) {
    if (!hwnd_ || !owner_ || !memDc_) return;
    if (!IsWindowVisible(owner_)) {
        ShowWindow(hwnd_, SW_HIDE);
        return;
    }
    RECT client{};
    GetClientRect(owner_, &client);
    const int width = 560;
    const int height = std::max(1L, std::min<LONG>(160, client.bottom - client.top));
    if (width != width_ || height != height_) {
        HDC screen = GetDC(nullptr);
        HBITMAP bitmap = screen ? CreateCompatibleBitmap(screen, width, height) : nullptr;
        if (screen) ReleaseDC(nullptr, screen);
        if (!bitmap) return;
        HBITMAP old = static_cast<HBITMAP>(SelectObject(memDc_, bitmap));
        if (bitmap_) DeleteObject(bitmap_);
        bitmap_ = bitmap;
        if (old && old != HGDI_ERROR) DeleteObject(old);
        width_ = width;
        height_ = height;
    }

    PatBlt(memDc_, 0, 0, width_, height_, BLACKNESS);
    SetBkMode(memDc_, TRANSPARENT);
    SetTextColor(memDc_, RGB(220, 245, 255));
    HGDIOBJ oldFont = SelectObject(memDc_, font_);
    int y = 6;
    size_t start = 0;
    while (start <= text.size()) {
        const size_t end = text.find('\n', start);
        const std::string line = text.substr(start, end == std::string::npos
                                                     ? std::string::npos
                                                     : end - start);
        TextOutA(memDc_, 8, y, line.c_str(), static_cast<int>(line.size()));
        y += 17;
        if (y > height_ - 12) break;
        if (end == std::string::npos) break;
        start = end + 1;
    }
    SelectObject(memDc_, oldFont);

    POINT origin{0, 0};
    ClientToScreen(owner_, &origin);
    int px = origin.x - width_ - 8;
    if (px < 8) px = origin.x + width_ + 8;
    SetWindowPos(hwnd_, HWND_TOPMOST, px, origin.y, width_, height_,
                 SWP_NOACTIVATE | SWP_SHOWWINDOW);
    InvalidateRect(hwnd_, nullptr, FALSE);
    UpdateWindow(hwnd_);
}

void InspectOverlay::shutdown() {
    if (hwnd_) {
        DestroyWindow(hwnd_);
        hwnd_ = nullptr;
    }
    if (font_) {
        DeleteObject(font_);
        font_ = nullptr;
    }
    if (bitmap_) {
        DeleteObject(bitmap_);
        bitmap_ = nullptr;
    }
    if (memDc_) {
        DeleteDC(memDc_);
        memDc_ = nullptr;
    }
    width_ = height_ = 0;
    owner_ = nullptr;
    if (g_overlay == this) g_overlay = nullptr;
}
