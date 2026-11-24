"""Windows CI bootstrap: explicitly load verified Mesa before Qt/OCP/VTK.

The CI installer verifies the distribution archive; this module is not a
production installer and never alters System32 or global driver settings.
"""
import ctypes
import os
from pathlib import Path
import runpy
import sys


def main():
    if sys.platform != "win32" or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise RuntimeError("Windows x64 CI only")
    folder = Path(os.environ["GOOSECAD_MESA_DLL_DIR"]).resolve(strict=True)
    gl_path = folder / "opengl32.dll"
    if not gl_path.is_file() or not (folder / "libgallium_wgl.dll").is_file():
        raise RuntimeError("Mesa WGL DLLs missing")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    if kernel.GetModuleHandleW("opengl32.dll"):
        raise RuntimeError("OpenGL already loaded before Mesa bootstrap")
    os.environ["GALLIUM_DRIVER"] = "llvmpipe"
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    os.environ["VTK_DEFAULT_OPENGL_WINDOW"] = "vtkWin32OpenGLRenderWindow"
    with os.add_dll_directory(str(folder)):
        gl = ctypes.WinDLL(str(gl_path), winmode=0x1100)
        if kernel.GetModuleHandleW("opengl32.dll") != gl._handle:
            raise RuntimeError("Mesa WGL module was not selected")
        print(f"Loaded process-local Mesa WGL: {gl_path}", flush=True)
        args = sys.argv[1:]
        if not args:
            raise SystemExit("Expected script path or -m module")
        if args[0] == "-m":
            sys.argv = args[1:]
            runpy.run_module(args[1], run_name="__main__", alter_sys=True)
        else:
            sys.argv = args
            runpy.run_path(args[0], run_name="__main__")


if __name__ == "__main__":
    main()
