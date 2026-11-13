"""Build RATT's two native helpers into assets\\ with MinGW-w64 gcc.

    python build_native.py

  assets\\ratt_daemon.dll   hotkeys, key injection, event pipe   (daemon\\ratt_daemon.c)
  assets\\ratt_menu.dll     right-click menu shell extension     (shellext\\ratt_menu.c)

gcc is taken from PATH or from C:\\msys64\\mingw64\\bin. Environment variable GCC_B can
point at an extra directory holding the binutils (as.exe, ld.exe) if gcc cannot find them.
SEC-R002-08: When `signtool.exe` and a code-signing certificate (`RATT_SIGN_PFX` or
`RATT_SIGN_THUMBPRINT`) are configured, the built DLLs are automatically Authenticode-signed.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

TARGETS = [
    ("assets/ratt_daemon.dll", "daemon/ratt_daemon.c", ["-s", "-luser32", "-ladvapi32"]),
    ("assets/ratt_menu.dll", "shellext/ratt_menu.c",
     ["-lole32", "-luuid", "-lshell32", "-lgdi32", "-luser32"]),
]


def find_gcc():
    gcc = shutil.which("gcc") or r"C:\msys64\mingw64\bin\gcc.exe"
    if not os.path.exists(gcc):
        sys.exit("gcc not found. Install MSYS2 MinGW-w64 or add gcc to PATH.")
    return gcc


def sign_binary(path: str):
    """SEC-R002-08: Sign binary with signtool.exe when a certificate is configured."""
    signtool = shutil.which("signtool") or shutil.which("signtool.exe")
    pfx = os.environ.get("RATT_SIGN_PFX", "")
    thumbprint = os.environ.get("RATT_SIGN_THUMBPRINT", "")
    if not signtool or not (pfx or thumbprint):
        return
    cmd = [signtool, "sign", "/fd", "SHA256", "/tr", "http://timestamp.digicert.com", "/td", "SHA256"]
    if pfx:
        cmd.extend(["/f", pfx])
        pw = os.environ.get("RATT_SIGN_PASSWORD", "")
        if pw:
            cmd.extend(["/p", pw])
    else:
        cmd.extend(["/sha1", thumbprint])
    cmd.append(path)
    print("signing", path)
    subprocess.run(cmd, check=False, cwd=ROOT)


def main():
    gcc = find_gcc()
    extra = ["-B", os.environ["GCC_B"]] if os.environ.get("GCC_B") else []
    dist_dir = os.path.join(ROOT, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    for output, source, libs in TARGETS:
        out_path = os.path.join(ROOT, output)
        command = [gcc, "-shared", "-O2", "-Wall", "-static", *extra,
                   "-o", out_path, os.path.join(ROOT, source), *libs]
        print("building", output)
        subprocess.run(command, check=True, cwd=ROOT)
        sign_binary(out_path)
        shutil.copyfile(out_path, os.path.join(dist_dir, os.path.basename(out_path)))
    print("done")


if __name__ == "__main__":
    main()
