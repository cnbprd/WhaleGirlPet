#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>

#include <SDL3/SDL.h>

#include "shell_ui.h"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cwchar>
#include <cwctype>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace {
constexpr UINT kTrayMessage = WM_APP + 42;
constexpr UINT kTrayId = 1;

enum CommandId {
    ID_TRAY_SHOW = 1001,
    ID_TRAY_CLIP = 1002,
    ID_TRAY_SETTINGS = 1003,
    ID_TRAY_EXIT = 1004,
    ID_TRAY_FACE_AUTO = 1010,
    ID_TRAY_FACE_OPEN = 1011,
    ID_TRAY_FACE_BLINK = 1012,
    ID_TRAY_FACE_SMILE = 1013,
};

enum ControlId {
    IDC_SET_MODEL = 2007,
    IDC_SET_CLIP = 2001,
    IDC_SET_FACE = 2002,
    IDC_SET_ANIMATOR = 2003,
    IDC_SET_APPLY = 2004,
    IDC_SET_CLOSE = 2005,
    IDC_SET_STATUS = 2006,
};

const wchar_t* kSettingsClass = L"WhaleGirl3DSettings";

std::wstring toWide(const std::string& text) {
    if (text.empty()) return {};
    int length = MultiByteToWideChar(CP_UTF8, 0, text.c_str(), -1, nullptr, 0);
    if (length <= 0) return {};
    std::wstring result(static_cast<size_t>(length - 1), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, text.c_str(), -1, result.data(), length);
    return result;
}

std::string toUtf8(const std::wstring& text) {
    if (text.empty()) return {};
    int length = WideCharToMultiByte(CP_UTF8, 0, text.c_str(), -1, nullptr, 0, nullptr, nullptr);
    if (length <= 0) return {};
    std::string result(static_cast<size_t>(length - 1), '\0');
    WideCharToMultiByte(CP_UTF8, 0, text.c_str(), -1, result.data(), length, nullptr, nullptr);
    return result;
}

std::wstring comboText(HWND combo) {
    wchar_t buffer[128]{};
    GetWindowTextW(combo, buffer, static_cast<int>(std::size(buffer)));
    return buffer;
}

std::string fileNameOf(const std::string& path) {
    const size_t slash = path.find_last_of("\\/");
    return slash == std::string::npos ? path : path.substr(slash + 1);
}

std::string joinBase(const std::string& base, const std::string& relative) {
    if (base.empty()) return relative;
    const char last = base.back();
    if (last == '\\' || last == '/') return base + relative;
    return base + "\\" + relative;
}

std::string modelDisplayName(const std::string& path) {
    const std::string file = fileNameOf(path);
    if (file == "placeholder.glb") return "方块占位";
    if (file == "whale_girl.vrm") return "鲸鱼娘 v1 (VRM)";
    return "鲸鱼娘 v1";
}

bool forceForeground(HWND hwnd) {
    HWND foreground = GetForegroundWindow();
    const DWORD foregroundThread = foreground
        ? GetWindowThreadProcessId(foreground, nullptr) : 0;
    const DWORD currentThread = GetCurrentThreadId();
    const bool attached = foregroundThread != 0 && foregroundThread != currentThread &&
        AttachThreadInput(foregroundThread, currentThread, TRUE) != FALSE;
    const BOOL ok = SetForegroundWindow(hwnd);
    if (attached) AttachThreadInput(foregroundThread, currentThread, FALSE);
    return ok != FALSE;
}

void setFont(HWND control) {
    SendMessageW(control, WM_SETFONT, reinterpret_cast<WPARAM>(GetStockObject(DEFAULT_GUI_FONT)), TRUE);
}

HWND createChild(HWND parent, const wchar_t* cls, const wchar_t* text, DWORD style,
                 int x, int y, int w, int h, int id = 0) {
    HWND child = CreateWindowExW(0, cls, text, style, x, y, w, h, parent,
                                 reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),
                                 GetModuleHandleW(nullptr), nullptr);
    if (child) setFont(child);
    return child;
}

HWND createCombo(HWND parent, int x, int y, int w, int id) {
    HWND combo = CreateWindowExW(0, L"COMBOBOX", L"",
                                 WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_VSCROLL,
                                 x, y, w, 160, parent,
                                 reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),
                                 GetModuleHandleW(nullptr), nullptr);
    if (combo) setFont(combo);
    return combo;
}
} // namespace

ShellUi* ShellUi::active_ = nullptr;

ShellUi::ShellUi() = default;

ShellUi::~ShellUi() {
    shutdown();
}

bool ShellUi::init(SDL_Window* window, Model* model, const std::string& iconPath,
                  const std::string& assetBase) {
    if (!window || !model || hwnd_) return false;
    window_ = window;
    model_ = model;
    iconPath_ = iconPath;
    assetBase_ = assetBase;

    SDL_PropertiesID properties = SDL_GetWindowProperties(window);
    hwnd_ = static_cast<HWND>(SDL_GetPointerProperty(
        properties, SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr));
    if (!hwnd_) {
        SDL_Log("ShellUi: SDL window has no Win32 HWND");
        return false;
    }

    oldProc_ = reinterpret_cast<WNDPROC>(
        SetWindowLongPtrW(hwnd_, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(&ShellUi::windowProc)));
    if (!oldProc_) {
        SDL_Log("ShellUi: SetWindowLongPtrW failed");
        hwnd_ = nullptr;
        return false;
    }
    active_ = this;

    std::wstring wideIcon = toWide(iconPath);
    if (!wideIcon.empty()) {
        icon_ = static_cast<HICON>(LoadImageW(nullptr, wideIcon.c_str(), IMAGE_ICON,
                                             GetSystemMetrics(SM_CXSMICON),
                                             GetSystemMetrics(SM_CYSMICON),
                                             LR_LOADFROMFILE | LR_DEFAULTSIZE));
        ownsIcon_ = icon_ != nullptr;
    }
    if (!icon_) {
        icon_ = LoadIconW(nullptr, reinterpret_cast<LPCWSTR>(IDI_APPLICATION));
        ownsIcon_ = false;
        SDL_Log("ShellUi: tray icon file missing, using IDI_APPLICATION");
    }

    if (!addTrayIcon()) {
        SDL_Log("ShellUi: Shell_NotifyIcon(NIM_ADD) failed");
        return false;
    }
    promoteTrayIcon();

    NOTIFYICONIDENTIFIER identifier{};
    identifier.cbSize = sizeof(identifier);
    identifier.hWnd = hwnd_;
    identifier.uID = kTrayId;
    RECT rect{};
    HRESULT hr = Shell_NotifyIconGetRect(&identifier, &rect);
    if (SUCCEEDED(hr)) {
        SDL_Log("Tray icon ready: rect=(%ld,%ld)-(%ld,%ld)",
                rect.left, rect.top, rect.right, rect.bottom);
    } else {
        SDL_Log("Tray icon ready: Shell_NotifyIconGetRect hr=0x%08lX",
                static_cast<unsigned long>(hr));
    }
    updateTrayTip();
    return true;
}

void ShellUi::shutdown() {
    if (settings_) {
        DestroyWindow(settings_);
        settings_ = nullptr;
    }
    removeTrayIcon();
    if (hwnd_ && oldProc_) {
        SetWindowLongPtrW(hwnd_, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(oldProc_));
    }
    if (icon_ && ownsIcon_) DestroyIcon(icon_);
    icon_ = nullptr;
    ownsIcon_ = false;
    hwnd_ = nullptr;
    oldProc_ = nullptr;
    window_ = nullptr;
    active_ = nullptr;
    model_ = nullptr;
}

bool ShellUi::quitRequested() const {
    return quit_.load();
}

void ShellUi::setHitTest(HitTestFn fn) {
    hitTest_ = std::move(fn);
}

void ShellUi::updateWindowRegion(const unsigned char* rgba, int width, int height) {
    if (!hwnd_ || !rgba || width <= 0 || height <= 0) return;

    // Build horizontal runs from the alpha mask.  A window region is used
    // instead of only WM_NCHITTEST because HTTRANSPARENT is documented to
    // walk same-thread windows; it does not reliably pass clicks to another
    // process.  The region makes transparent pixels not part of this window.
    std::vector<RECT> runs;
    runs.reserve(1024);
    for (int y = 0; y < height; ++y) {
        const int imageY = height - 1 - y;
        int start = -1;
        for (int x = 0; x < width; ++x) {
            const bool on = rgba[(static_cast<size_t>(imageY) * width + x) * 4 + 3] > 16;
            if (on && start < 0) {
                start = x;
            } else if (!on && start >= 0) {
                runs.push_back(RECT{start, y, x, y + 1});
                start = -1;
            }
        }
        if (start >= 0) runs.push_back(RECT{start, y, width, y + 1});
    }
    if (runs.empty()) return;

    const size_t regionSize = sizeof(RGNDATAHEADER) + runs.size() * sizeof(RECT);
    std::vector<unsigned char> buffer(regionSize);
    RGNDATA* data = reinterpret_cast<RGNDATA*>(buffer.data());
    data->rdh.dwSize = sizeof(RGNDATAHEADER);
    data->rdh.iType = RDH_RECTANGLES;
    data->rdh.nCount = static_cast<DWORD>(runs.size());
    data->rdh.nRgnSize = static_cast<DWORD>(runs.size() * sizeof(RECT));
    RECT bound = runs[0];
    for (const RECT& r : runs) {
        bound.left = std::min(bound.left, r.left);
        bound.top = std::min(bound.top, r.top);
        bound.right = std::max(bound.right, r.right);
        bound.bottom = std::max(bound.bottom, r.bottom);
    }
    data->rdh.rcBound = bound;
    std::memcpy(data->Buffer, runs.data(), runs.size() * sizeof(RECT));

    HRGN region = ExtCreateRegion(nullptr, static_cast<DWORD>(regionSize), data);
    if (!region) return;
    if (!SetWindowRgn(hwnd_, region, TRUE)) {
        DeleteObject(region);
    }
}

bool ShellUi::addTrayIcon() {
    if (!hwnd_ || !icon_) return false;
    NOTIFYICONDATAW data{};
    data.cbSize = sizeof(data);
    data.hWnd = hwnd_;
    data.uID = kTrayId;
    data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP;
    data.uCallbackMessage = kTrayMessage;
    data.hIcon = icon_;
    std::wstring tip = L"鲸鱼娘 · 桌面宠物";
    wcsncpy(data.szTip, tip.c_str(), std::size(data.szTip) - 1);
    if (!Shell_NotifyIconW(NIM_ADD, &data)) return false;
    trayAdded_ = true;
    return true;
}

void ShellUi::removeTrayIcon() {
    if (!hwnd_ || !trayAdded_) return;
    NOTIFYICONDATAW data{};
    data.cbSize = sizeof(data);
    data.hWnd = hwnd_;
    data.uID = kTrayId;
    Shell_NotifyIconW(NIM_DELETE, &data);
    trayAdded_ = false;
}

// Windows 11 keeps per-application tray visibility in
// HKCU\Control Panel\NotifyIconSettings\<hash>. The key name is generated by
// Explorer, so match ExecutablePath rather than guessing the hash. Explorer
// applies the promoted flag on its next start; the current session is already
// fixed manually on this machine, and a fresh install gets the flag written
// here for the next Explorer restart/sign-in.
void ShellUi::promoteTrayIcon() {
    for (int attempt = 0; attempt < 3; ++attempt) {
        if (promoteTrayIconOnce()) return;
        SDL_Delay(250);
    }
    SDL_Log("ShellUi: tray promotion registry key not found");
}

bool ShellUi::promoteTrayIconOnce() {
    wchar_t exePath[32768]{};
    if (!GetModuleFileNameW(nullptr, exePath, static_cast<DWORD>(std::size(exePath)))) {
        return false;
    }

    HKEY root = nullptr;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Control Panel\\NotifyIconSettings",
                      0, KEY_READ, &root) != ERROR_SUCCESS) {
        return false;
    }

    bool found = false;
    for (DWORD index = 0;; ++index) {
        wchar_t keyName[256]{};
        DWORD keyNameLen = static_cast<DWORD>(std::size(keyName));
        const LONG enumResult = RegEnumKeyExW(root, index, keyName, &keyNameLen,
                                              nullptr, nullptr, nullptr, nullptr);
        if (enumResult != ERROR_SUCCESS) break;

        HKEY sub = nullptr;
        if (RegOpenKeyExW(root, keyName, 0, KEY_READ | KEY_SET_VALUE, &sub) != ERROR_SUCCESS) {
            continue;
        }

        wchar_t value[32768]{};
        DWORD type = 0;
        DWORD valueSize = static_cast<DWORD>(sizeof(value));
        const LONG queryResult = RegQueryValueExW(sub, L"ExecutablePath", nullptr, &type,
                                                  reinterpret_cast<LPBYTE>(value), &valueSize);
        if (queryResult == ERROR_SUCCESS && type == REG_SZ &&
            _wcsicmp(value, exePath) == 0) {
            DWORD promoted = 1;
            const LONG setResult = RegSetValueExW(sub, L"IsPromoted", 0, REG_DWORD,
                                                  reinterpret_cast<const BYTE*>(&promoted),
                                                  sizeof(promoted));
            if (setResult == ERROR_SUCCESS) {
                SDL_Log("ShellUi: tray promotion set for key=%ls", keyName);
                found = true;
            } else {
                SDL_Log("ShellUi: tray promotion write failed error=%ld",
                        static_cast<long>(setResult));
            }
            RegCloseKey(sub);
            break;
        }
        RegCloseKey(sub);
    }

    RegCloseKey(root);
    return found;
}

void ShellUi::updateTrayTip() {
    if (!hwnd_ || !trayAdded_ || !model_) return;
    std::wstring tip = L"鲸鱼娘 · ";
    tip += toWide(model_->clipName());
    tip += L" · ";
    tip += toWide(model_->faceName());
    NOTIFYICONDATAW data{};
    data.cbSize = sizeof(data);
    data.hWnd = hwnd_;
    data.uID = kTrayId;
    data.uFlags = NIF_TIP;
    wcsncpy(data.szTip, tip.c_str(), std::size(data.szTip) - 1);
    Shell_NotifyIconW(NIM_MODIFY, &data);
}

void ShellUi::setWindowVisible(bool visible) {
    if (!window_) return;
    if (visible) {
        SDL_ShowWindow(window_);
    } else {
        SDL_HideWindow(window_);
    }
    visible_ = visible;
    updateTrayTip();
}

void ShellUi::handleCommand(int command) {
    switch (command) {
    case ID_TRAY_SHOW:
        setWindowVisible(!visible_);
        break;
    case ID_TRAY_CLIP:
        if (model_) model_->nextClip();
        updateTrayTip();
        break;
    case ID_TRAY_FACE_AUTO:
        if (model_) model_->setFace("auto");
        updateTrayTip();
        break;
    case ID_TRAY_FACE_OPEN:
        if (model_) model_->setFace("open");
        updateTrayTip();
        break;
    case ID_TRAY_FACE_BLINK:
        if (model_) model_->setFace("blink");
        updateTrayTip();
        break;
    case ID_TRAY_FACE_SMILE:
        if (model_) model_->setFace("smile");
        updateTrayTip();
        break;
    case ID_TRAY_SETTINGS:
        showSettings();
        break;
    case ID_TRAY_EXIT:
        quit_.store(true);
        if (settings_) DestroyWindow(settings_);
        break;
    default:
        break;
    }
}

bool ShellUi::handleWindowMessage(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam,
                                  LRESULT& result) {
    static UINT taskbarCreated = RegisterWindowMessageW(L"TaskbarCreated");

    if (msg == WM_NCHITTEST) {
        if (!hitTest_) return false;
        POINT point{};
        point.x = static_cast<int>(static_cast<short>(LOWORD(lParam)));
        point.y = static_cast<int>(static_cast<short>(HIWORD(lParam)));
        ScreenToClient(hwnd, &point);
        const bool hit = hitTest_(point.x, point.y);
        result = hit ? HTCLIENT : HTTRANSPARENT;
        return true;
    }
    if (msg == kTrayMessage) {
        const UINT mouseMessage = LOWORD(lParam);
        if (mouseMessage == WM_LBUTTONUP) {
            setWindowVisible(!visible_);
        } else if (mouseMessage == WM_RBUTTONUP || mouseMessage == WM_CONTEXTMENU) {
            showTrayMenu();
        } else if (mouseMessage == WM_LBUTTONDBLCLK) {
            showSettings();
        }
        result = 0;
        return true;
    }
    if (msg == WM_COMMAND) {
        const int command = LOWORD(wParam);
        if (command >= ID_TRAY_SHOW && command <= ID_TRAY_FACE_SMILE) {
            handleCommand(command);
            result = 0;
            return true;
        }
        return false;
    }
    if (taskbarCreated && msg == taskbarCreated) {
        addTrayIcon();
        result = 0;
        return true;
    }
    if (msg == WM_CLOSE) {
        quit_.store(true);
        result = 0;
        return true;
    }
    return false;
}

LRESULT CALLBACK ShellUi::windowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    ShellUi* self = active_;
    if (self && self->hwnd_ == hwnd) {
        LRESULT result = 0;
        if (self->handleWindowMessage(hwnd, msg, wParam, lParam, result)) {
            return result;
        }
        if (self->oldProc_) {
            return CallWindowProcW(self->oldProc_, hwnd, msg, wParam, lParam);
        }
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

void ShellUi::showTrayMenu() {
    if (!hwnd_) return;
    HMENU menu = CreatePopupMenu();
    if (!menu) return;

    std::string clip = model_ ? model_->clipName() : "idle";
    std::string face = model_ ? model_->faceMode() : "auto";
    const wchar_t* showText = visible_ ? L"隐藏窗口" : L"显示窗口";
    AppendMenuW(menu, MF_STRING, ID_TRAY_SHOW, showText);
    AppendMenuW(menu, MF_STRING, ID_TRAY_CLIP,
                clip == "idle" ? L"动画：切到 Walk" : L"动画：切到 Idle");
    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);

    HMENU faceMenu = CreatePopupMenu();
    AppendMenuW(faceMenu, MF_STRING | (face == "auto" ? MF_CHECKED : 0),
                ID_TRAY_FACE_AUTO, L"Auto");
    AppendMenuW(faceMenu, MF_STRING | (face == "open" ? MF_CHECKED : 0),
                ID_TRAY_FACE_OPEN, L"Open");
    AppendMenuW(faceMenu, MF_STRING | (face == "blink" ? MF_CHECKED : 0),
                ID_TRAY_FACE_BLINK, L"Blink");
    AppendMenuW(faceMenu, MF_STRING | (face == "smile" ? MF_CHECKED : 0),
                ID_TRAY_FACE_SMILE, L"Smile");
    AppendMenuW(menu, MF_POPUP, reinterpret_cast<UINT_PTR>(faceMenu), L"表情");

    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
    AppendMenuW(menu, MF_STRING, ID_TRAY_SETTINGS, L"设置…");
    AppendMenuW(menu, MF_STRING, ID_TRAY_EXIT, L"退出");

    POINT point{};
    GetCursorPos(&point);
    const LONG_PTR exStyle = GetWindowLongPtrW(hwnd_, GWL_EXSTYLE);
    const bool noActivate = (exStyle & WS_EX_NOACTIVATE) != 0;
    if (noActivate) {
        SetWindowLongPtrW(hwnd_, GWL_EXSTYLE, exStyle & ~static_cast<LONG_PTR>(WS_EX_NOACTIVATE));
        SetWindowPos(hwnd_, nullptr, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE |
                     SWP_FRAMECHANGED);
    }
    const BOOL foreground = forceForeground(hwnd_) ? TRUE : FALSE;
    const int command = TrackPopupMenu(menu, TPM_RETURNCMD | TPM_RIGHTBUTTON | TPM_NONOTIFY,
                                       point.x, point.y, 0, hwnd_, nullptr);
    DestroyMenu(menu);
    if (noActivate) {
        SetWindowLongPtrW(hwnd_, GWL_EXSTYLE, exStyle);
        SetWindowPos(hwnd_, nullptr, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE |
                     SWP_FRAMECHANGED);
    }
    PostMessageW(hwnd_, WM_NULL, 0, 0);
    if (command) {
        SDL_Log("Tray menu command=%d foreground=%d", command, foreground ? 1 : 0);
        handleCommand(command);
    }
}

void ShellUi::showSettings() {
    if (!hwnd_) return;
    if (settings_) {
        SetForegroundWindow(settings_);
        return;
    }

    HINSTANCE instance = GetModuleHandleW(nullptr);
    if (!settingsClassRegistered_) {
        WNDCLASSEXW wc{};
        wc.cbSize = sizeof(wc);
        wc.lpfnWndProc = &ShellUi::settingsProc;
        wc.hInstance = instance;
        wc.hCursor = LoadCursorW(nullptr, reinterpret_cast<LPCWSTR>(IDC_ARROW));
        wc.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1);
        wc.lpszClassName = kSettingsClass;
        if (!RegisterClassExW(&wc)) {
            SDL_Log("ShellUi: RegisterClassExW(settings) failed");
            return;
        }
        settingsClassRegistered_ = true;
    }

    RECT desired{0, 0, 420, 360};
    AdjustWindowRectEx(&desired, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU, FALSE,
                       WS_EX_DLGMODALFRAME);
    const int width = desired.right - desired.left;
    const int height = desired.bottom - desired.top;

    RECT petRect{};
    GetWindowRect(hwnd_, &petRect);
    int x = petRect.left + ((petRect.right - petRect.left) - width) / 2;
    int y = petRect.top + ((petRect.bottom - petRect.top) - height) / 2;
    MONITORINFO monitor{};
    monitor.cbSize = sizeof(monitor);
    if (GetMonitorInfoW(MonitorFromWindow(hwnd_, MONITOR_DEFAULTTONEAREST), &monitor)) {
        x = std::max(static_cast<int>(monitor.rcWork.left),
                     std::min(x, static_cast<int>(monitor.rcWork.right) - width));
        y = std::max(static_cast<int>(monitor.rcWork.top),
                     std::min(y, static_cast<int>(monitor.rcWork.bottom) - height));
    }

    settings_ = CreateWindowExW(WS_EX_DLGMODALFRAME, kSettingsClass, L"鲸鱼娘 · 设置",
                               WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU,
                               x, y, width, height, hwnd_, nullptr, instance, this);
    if (!settings_) {
        SDL_Log("ShellUi: CreateWindowExW(settings) failed");
        return;
    }

    EnableWindow(hwnd_, FALSE);
    ShowWindow(settings_, SW_SHOW);
    SetForegroundWindow(settings_);

    MSG msg{};
    while (IsWindow(settings_)) {
        const int got = GetMessageW(&msg, nullptr, 0, 0);
        if (got == 0 || got == -1) {
            quit_.store(true);
            break;
        }
        if (msg.message == WM_QUIT) {
            quit_.store(true);
            break;
        }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    if (settings_) {
        DestroyWindow(settings_);
        settings_ = nullptr;
    }
    EnableWindow(hwnd_, TRUE);
}

void ShellUi::buildSettingsControls(HWND hwnd) {
    createChild(hwnd, L"STATIC", L"鲸鱼娘 · 最小设置",
                WS_CHILD | WS_VISIBLE, 20, 16, 380, 26);
    createChild(hwnd, L"STATIC", L"原生 Win32 控制，不依赖 Qt/PySide6。",
                WS_CHILD | WS_VISIBLE, 20, 44, 380, 20);

    const std::string currentPath = model_ ? model_->sourcePath() : "";
    const std::string currentModel = modelDisplayName(currentPath);
    createChild(hwnd, L"STATIC", L"模型", WS_CHILD | WS_VISIBLE, 20, 90, 60, 22);
    HWND modelCombo = createCombo(hwnd, 100, 86, 280, IDC_SET_MODEL);
    SendMessageW(modelCombo, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"鲸鱼娘 v1 (VRM)"));
    SendMessageW(modelCombo, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"方块占位"));
    SendMessageW(modelCombo, CB_SETCURSEL,
                 fileNameOf(currentPath) == "placeholder.glb" ? 1 : 0, 0);

    createChild(hwnd, L"STATIC", L"动画", WS_CHILD | WS_VISIBLE, 20, 128, 60, 22);
    HWND clip = createCombo(hwnd, 100, 124, 280, IDC_SET_CLIP);
    SendMessageW(clip, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"Idle"));
    SendMessageW(clip, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"Walk"));
    SendMessageW(clip, CB_SETCURSEL,
                 model_ && model_->clipName() == std::string("walk") ? 1 : 0, 0);

    createChild(hwnd, L"STATIC", L"表情", WS_CHILD | WS_VISIBLE, 20, 166, 60, 22);
    HWND face = createCombo(hwnd, 100, 162, 280, IDC_SET_FACE);
    SendMessageW(face, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"Auto"));
    SendMessageW(face, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"Open"));
    SendMessageW(face, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"Blink"));
    SendMessageW(face, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"Smile"));
    const std::string mode = model_ ? model_->faceMode() : "auto";
    int faceIndex = mode == "open" ? 1 : mode == "blink" ? 2 : mode == "smile" ? 3 : 0;
    SendMessageW(face, CB_SETCURSEL, faceIndex, 0);

    createChild(hwnd, L"STATIC", L"采样器", WS_CHILD | WS_VISIBLE, 20, 204, 60, 22);
    HWND animator = createCombo(hwnd, 100, 200, 280, IDC_SET_ANIMATOR);
    SendMessageW(animator, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"ozz"));
    SendMessageW(animator, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(L"self"));
    SendMessageW(animator, CB_SETCURSEL,
                 model_ && model_->animatorName() == std::string("self") ? 1 : 0, 0);

    wchar_t status[512]{};
    swprintf(status, std::size(status), L"当前：%ls · %ls / %ls / %ls　%d 三角形 / %d 关节",
             toWide(currentModel).c_str(),
             model_ ? toWide(model_->clipName()).c_str() : L"idle",
             model_ ? toWide(model_->faceName()).c_str() : L"open",
             model_ ? toWide(model_->animatorName()).c_str() : L"ozz",
             model_ ? model_->triangleCount() : 0,
             model_ ? model_->jointCount() : 0);
    createChild(hwnd, L"STATIC", status, WS_CHILD | WS_VISIBLE, 20, 246, 380, 46,
                IDC_SET_STATUS);

    createChild(hwnd, L"BUTTON", L"应用", WS_CHILD | WS_VISIBLE | BS_DEFPUSHBUTTON,
                215, 300, 82, 30, IDC_SET_APPLY);
    createChild(hwnd, L"BUTTON", L"关闭", WS_CHILD | WS_VISIBLE,
                312, 300, 82, 30, IDC_SET_CLOSE);
}

bool ShellUi::restartWithModel(const std::string& modelPath, const std::string& clip,
                               const std::string& face, const std::string& animator) {
    wchar_t exePath[32768]{};
    if (!GetModuleFileNameW(nullptr, exePath, static_cast<DWORD>(std::size(exePath)))) {
        SDL_Log("Restart failed: cannot locate whale3d.exe");
        return false;
    }
    SetEnvironmentVariableW(L"WHALE3D_CLIP", toWide(clip).c_str());
    SetEnvironmentVariableW(L"WHALE3D_FACE", toWide(face).c_str());
    SetEnvironmentVariableW(L"WHALE3D_ANIMATOR", toWide(animator).c_str());

    std::wstring command = L"\"" + std::wstring(exePath) + L"\" --relaunch " +
                           std::to_wstring(GetCurrentProcessId()) + L" \"" +
                           toWide(modelPath) + L"\"";
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    const BOOL started = CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, 0,
                                        nullptr, nullptr, &startup, &process);
    if (!started) {
        SDL_Log("Restart failed: CreateProcess error=%lu", GetLastError());
        return false;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    SDL_Log("Restart helper requested for model: %s", modelPath.c_str());
    if (window_) SDL_HideWindow(window_);
    quit_.store(true);
    // The tiny --relaunch helper waits for this process to release its GL
    // context, then starts the real child. The new pet therefore does not
    // overlap the old pet's GL/private allocation peak. If the normal loop
    // cannot unwind, this watchdog terminates the old process and lets the
    // helper continue. 2.5 s keeps the blank handoff short without forcing a
    // kill when the normal loop is already exiting.
    std::thread([] {
        Sleep(2500);
        std::fprintf(stderr, "relaunch watchdog: terminating old process\n");
        TerminateProcess(GetCurrentProcess(), 0);
    }).detach();
    return true;
}

void ShellUi::applySettings(HWND hwnd) {
    if (!model_) return;
    const std::wstring modelText = comboText(GetDlgItem(hwnd, IDC_SET_MODEL));
    const std::wstring clipText = comboText(GetDlgItem(hwnd, IDC_SET_CLIP));
    const std::wstring faceText = comboText(GetDlgItem(hwnd, IDC_SET_FACE));
    const std::wstring animatorText = comboText(GetDlgItem(hwnd, IDC_SET_ANIMATOR));

    const std::string modelChoice = toUtf8(modelText);
    const std::string clip = toUtf8(clipText);
    const std::string face = toUtf8(faceText);
    const std::string animator = toUtf8(animatorText);
    const std::string clipKey = (clip == "Walk" || clip == "walk") ? "walk" : "idle";
    const std::string faceKey = (face == "Open" || face == "open") ? "open"
                              : (face == "Blink" || face == "blink") ? "blink"
                              : (face == "Smile" || face == "smile") ? "smile"
                              : "auto";
    const std::string animatorKey = (animator == "self") ? "self" : "ozz";
    const std::string modelFile = modelChoice == "方块占位" ? "placeholder.glb" : "whale_girl.vrm";
    const std::string newModelPath = joinBase(assetBase_, "assets/models/" + modelFile);
    const std::string oldModelPath = model_->sourcePath();

    bool modelOk = true;
    if (newModelPath != oldModelPath) {
        const char* switchMode = std::getenv("WHALE3D_SWITCH");
        const bool useRelaunch = switchMode && std::strcmp(switchMode, "relaunch") == 0;
        if (useRelaunch && restartWithModel(newModelPath, clipKey, faceKey, animatorKey)) {
            PostMessageW(hwnd, WM_CLOSE, 0, 0);
            return;
        }
        if (!useRelaunch) SDL_Log("In-place model switch requested: %s", newModelPath.c_str());
        const Uint64 loadStart = SDL_GetTicks();
        modelOk = model_->load(newModelPath);
        const Uint64 loadMs = SDL_GetTicks() - loadStart;
        if (!useRelaunch) {
            SDL_Log("In-place model load: %s ok=%d ms=%llu",
                    fileNameOf(newModelPath).c_str(), modelOk ? 1 : 0,
                    static_cast<unsigned long long>(loadMs));
        }
        if (!modelOk) {
            SDL_Log("Model '%s' failed: %s; restoring %s",
                    newModelPath.c_str(), model_->error().c_str(), oldModelPath.c_str());
            modelOk = model_->load(oldModelPath);
            if (!modelOk) {
                SDL_Log("Model restore failed: %s", model_->error().c_str());
            }
        }
    }

    bool ok = modelOk;
    if (ok) ok = model_->setAnimator(animatorKey);
    if (ok) ok = model_->setClip(clipKey);
    if (ok) ok = model_->setFace(faceKey);

    HWND status = GetDlgItem(hwnd, IDC_SET_STATUS);
    if (status) {
        std::wstring text;
        if (ok) {
            text = L"已应用：";
            text += toWide(modelDisplayName(model_->sourcePath()));
            text += L" · ";
            text += toWide(model_->clipName());
            text += L" / ";
            text += toWide(model_->faceMode());
            text += L" / ";
            text += toWide(model_->animatorName());
        } else {
            text = L"未应用：所选模型/采样器不支持该组合，已保留 ";
            text += toWide(modelDisplayName(model_->sourcePath()));
            text += L" · ";
            text += toWide(model_->clipName());
            text += L" / ";
            text += toWide(model_->faceMode());
        }
        SetWindowTextW(status, text.c_str());
    }
    updateTrayTip();
    SDL_Log("Settings applied: model=%s model_ok=%d clip=%s face=%s animator=%s ok=%d",
            fileNameOf(model_->sourcePath()).c_str(), modelOk ? 1 : 0,
            model_->clipName(), model_->faceMode(), model_->animatorName(), ok ? 1 : 0);
}

void ShellUi::closeSettings() {
    if (settings_) DestroyWindow(settings_);
    settings_ = nullptr;
}

LRESULT CALLBACK ShellUi::settingsProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    ShellUi* self = reinterpret_cast<ShellUi*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
    if (msg == WM_CREATE) {
        CREATESTRUCTW* create = reinterpret_cast<CREATESTRUCTW*>(lParam);
        self = static_cast<ShellUi*>(create->lpCreateParams);
        SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
        if (self) {
            self->settings_ = hwnd;
            self->buildSettingsControls(hwnd);
        }
        return 0;
    }
    if (!self) return DefWindowProcW(hwnd, msg, wParam, lParam);
    return self->handleSettingsMessage(hwnd, msg, wParam, lParam);
}

LRESULT ShellUi::handleSettingsMessage(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
    case WM_COMMAND: {
        const int id = LOWORD(wParam);
        if (id == IDC_SET_APPLY) {
            applySettings(hwnd);
            return 0;
        }
        if (id == IDC_SET_CLOSE || id == IDCANCEL) {
            closeSettings();
            return 0;
        }
        break;
    }
    case WM_CLOSE:
        closeSettings();
        return 0;
    case WM_DESTROY:
        if (settings_ == hwnd) settings_ = nullptr;
        return 0;
    default:
        break;
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

int runRelaunchHelper(int argc, char** argv) {
    if (argc < 4 || std::strcmp(argv[1], "--relaunch") != 0) {
        std::fprintf(stderr, "relaunch helper: bad arguments\n");
        return 2;
    }

    const DWORD oldPid = static_cast<DWORD>(std::strtoul(argv[2], nullptr, 10));
    const std::string modelPath = argv[3];
    std::fprintf(stderr, "relaunch helper: old_pid=%lu model=%s\n",
                 static_cast<unsigned long>(oldPid), modelPath.c_str());

    if (oldPid != 0) {
        HANDLE oldProcess = OpenProcess(SYNCHRONIZE | PROCESS_TERMINATE, FALSE, oldPid);
        if (oldProcess) {
            const DWORD waitResult = WaitForSingleObject(oldProcess, 12000);
            if (waitResult == WAIT_TIMEOUT) {
                std::fprintf(stderr, "relaunch helper: old process timeout, terminating\n");
                TerminateProcess(oldProcess, 0);
                WaitForSingleObject(oldProcess, 2000);
            }
            CloseHandle(oldProcess);
        } else {
            std::fprintf(stderr, "relaunch helper: old process already gone\n");
        }
    }

    wchar_t exePath[32768]{};
    if (!GetModuleFileNameW(nullptr, exePath, static_cast<DWORD>(std::size(exePath)))) {
        std::fprintf(stderr, "relaunch helper: cannot locate exe\n");
        return 3;
    }

    std::wstring command = L"\"" + std::wstring(exePath) + L"\" \"" + toWide(modelPath) + L"\"";
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    const BOOL started = CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, 0,
                                        nullptr, nullptr, &startup, &process);
    if (!started) {
        std::fprintf(stderr, "relaunch helper: CreateProcess error=%lu\n",
                     static_cast<unsigned long>(GetLastError()));
        return 4;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    std::fprintf(stderr, "relaunch helper: started new pet pid=%lu\n",
                 static_cast<unsigned long>(process.dwProcessId));
    return 0;
}
