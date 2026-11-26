import ctypes, time
from ctypes import wintypes
from pathlib import Path
u=ctypes.windll.user32
marker=Path(r"F:\WhaleGirlPet\docs\_native_underlay_marker.txt")
LRESULT=ctypes.c_ssize_t
WNDPROC=ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
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
class WNDCLASSW(ctypes.Structure):
    _fields_=[("style",wintypes.UINT),("lpfnWndProc",WNDPROC),("cbClsExtra",ctypes.c_int),("cbWndExtra",ctypes.c_int),("hInstance",wintypes.HINSTANCE),("hIcon",wintypes.HICON),("hCursor",wintypes.HANDLE),("hbrBackground",wintypes.HBRUSH),("lpszMenuName",wintypes.LPCWSTR),("lpszClassName",wintypes.LPCWSTR)]
wc=WNDCLASSW(); wc.lpfnWndProc=WNDPROC(proc); wc.hInstance=ctypes.windll.kernel32.GetModuleHandleW(None); wc.lpszClassName="NativeUnderlay"; wc.hbrBackground=ctypes.cast(ctypes.c_void_p(6),wintypes.HBRUSH)
u.RegisterClassW(ctypes.byref(wc))
hinst=ctypes.c_void_p(ctypes.windll.kernel32.GetModuleHandleW(None))
hwnd=u.CreateWindowExW(0,"NativeUnderlay","NativeUnderlay",0x80000000,1420,430,420,620,None,None,hinst,None)
print("hwnd",hwnd,flush=True)
if hwnd:
 u.ShowWindow(hwnd,5); u.UpdateWindow(hwnd)
msg=wintypes.MSG()
while u.GetMessageW(ctypes.byref(msg),None,0,0)>0:
    u.TranslateMessage(ctypes.byref(msg)); u.DispatchMessageW(ctypes.byref(msg))
