import ctypes, time
from ctypes import wintypes
from pathlib import Path
u=ctypes.windll.user32
marker=Path(r"F:\WhaleGirlPet\docs\_native_underlay_marker.txt")
WNDPROC=ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
def proc(hwnd,msg,w,l):
    if msg==0x0201:
        with marker.open("a") as f: f.write("down\n")
    elif msg==0x0202:
        with marker.open("a") as f: f.write("up\n")
    elif msg==0x0001:
        return 1
    elif msg==0x0002:
        u.PostQuitMessage(0); return 0
    return u.DefWindowProcW(hwnd,msg,w,l)
wc=wintypes.WNDCLASSW()
wc.lpfnWndProc=WNDPROC(proc); wc.hInstance=ctypes.windll.kernel32.GetModuleHandleW(None); wc.lpszClassName="NativeUnderlay"; wc.hbrBackground=ctypes.cast(ctypes.c_void_p(0x0000000F),ctypes.c_void_p)
u.RegisterClassW(ctypes.byref(wc))
hwnd=u.CreateWindowExW(0,"NativeUnderlay","NativeUnderlay",0x80000000,1420,430,420,620,None,None,wc.hInstance,None)
u.ShowWindow(hwnd,5); u.UpdateWindow(hwnd)
msg=wintypes.MSG()
while u.GetMessageW(ctypes.byref(msg),None,0,0)>0:
    u.TranslateMessage(ctypes.byref(msg)); u.DispatchMessageW(ctypes.byref(msg))
