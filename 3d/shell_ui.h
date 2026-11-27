#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <atomic>
#include <functional>
#include <string>

#include "model.h"

class SDL_Window;
class Model;

// Native Win32 tray + a small modal settings window.  It deliberately uses
// only user32/shell32 controls, so the 3D core does not pull in Qt.
class ShellUi {
public:
    using HitTestFn = std::function<bool(int clientX, int clientY)>;

    ShellUi();
    ~ShellUi();

    ShellUi(const ShellUi&) = delete;
    ShellUi& operator=(const ShellUi&) = delete;

    bool init(SDL_Window* window, Model* model, const std::string& iconPath,
              const std::string& assetBase);
    void shutdown();

    bool quitRequested() const;
    void showTrayMenu();
    void setHitTest(HitTestFn fn);
    void updateWindowRegion(const unsigned char* rgba, int width, int height,
                            int extraLeft = 0, int extraTop = 0,
                            int extraRight = 0, int extraBottom = 0);

private:
    static LRESULT CALLBACK windowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
    static LRESULT CALLBACK settingsProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);

    bool handleWindowMessage(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam, LRESULT& result);
    LRESULT handleSettingsMessage(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);

    bool addTrayIcon();
    void removeTrayIcon();
    void promoteTrayIcon();
    bool promoteTrayIconOnce();
    void updateTrayTip();
    void setWindowVisible(bool visible);
    void handleCommand(int command);
    void showSettings();
    bool restartWithModel(const std::string& modelPath, const std::string& clip,
                          const std::string& face, const std::string& animator);
    void buildSettingsControls(HWND hwnd);
    void applySettings(HWND hwnd);
    void closeSettings();

    static ShellUi* active_;

    SDL_Window* window_ = nullptr;
    HWND hwnd_ = nullptr;
    WNDPROC oldProc_ = nullptr;
    HICON icon_ = nullptr;
    bool ownsIcon_ = false;
    bool trayAdded_ = false;
    bool visible_ = true;
    bool settingsClassRegistered_ = false;
    HWND settings_ = nullptr;
    Model* model_ = nullptr;
    std::atomic<bool> quit_{false};
    HitTestFn hitTest_;
    std::string iconPath_;
    std::string assetBase_;
};

// Minimal same-exe relaunch helper. It is dispatched before SDL init, waits
// for the old process to release its GL context, then starts the real pet.
int runRelaunchHelper(int argc, char** argv);
