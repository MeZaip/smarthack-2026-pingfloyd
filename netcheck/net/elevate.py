"""Run ONE command (nmap) with admin rights through the operating system's own permission dialog.

Least privilege (NFR-04): the app itself never runs as admin. Only the nmap process gets elevated,
and the user sees the familiar system prompt:
  * Windows: the UAC dialog ("Do you want to allow this app to make changes?") via Start-Process -Verb RunAs
  * Linux:   pkexec (graphical password prompt); without a desktop, `sudo -n` (works only if already allowed)
  * macOS:   the standard administrator password dialog via osascript
If the app already runs with admin rights (e.g. started from an admin terminal), the command runs directly.
"""
from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
from typing import Callable, Optional

Run = Callable[..., subprocess.CompletedProcess]

WINDOWS_CANCELLED = 1223   # ERROR_CANCELLED: the user clicked "No" in the UAC dialog
PKEXEC_DISMISSED = 126     # pkexec: authorisation dialog dismissed
NO_WINDOW = 0x08000000     # CREATE_NO_WINDOW: no console flashes when started from the app


class ElevationDenied(Exception):
    """The user said no in the permission dialog."""


class ElevationUnavailable(Exception):
    """This computer offers no way to ask for admin rights from the app."""


def is_admin() -> bool:
    if os.name == "nt":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return False
    return os.geteuid() == 0


def _ps_quote(s: str) -> str:
    """PowerShell single-quoted literal."""
    return "'" + s.replace("'", "''") + "'"


def windows_command(cmd: list[str]) -> list[str]:
    """powershell command that runs `cmd` elevated, waits, and exits with its exit code (1223 if refused)."""
    exe, args = cmd[0], subprocess.list2cmdline(cmd[1:])
    script = (
        "$ErrorActionPreference='Stop'; "
        f"try {{ $p = Start-Process -FilePath {_ps_quote(exe)} -ArgumentList {_ps_quote(args)} "
        "-Verb RunAs -WindowStyle Hidden -Wait -PassThru; exit $p.ExitCode } "
        # language-independent: the Win32 error code (1223 = cancelled by the user), not the localized message
        "catch { $e = $_.Exception; "
        "while ($e -and -not ($e -is [System.ComponentModel.Win32Exception])) { $e = $e.InnerException }; "
        "if ($e) { exit $e.NativeErrorCode } else { exit 1 } }"
    )
    return ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]


def macos_command(cmd: list[str]) -> list[str]:
    shell = shlex.join(cmd).replace("\\", "\\\\").replace('"', '\\"')
    return ["osascript", "-e", f'do shell script "{shell}" with administrator privileges']


def linux_command(cmd: list[str]) -> list[str]:
    if shutil.which("pkexec") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return ["pkexec"] + cmd
    return ["sudo", "-n"] + cmd


def elevated_command(cmd: list[str], system: Optional[str] = None, admin: Optional[bool] = None) -> list[str]:
    system = system or platform.system()
    if admin if admin is not None else is_admin():
        return list(cmd)
    if system == "Windows":
        return windows_command(cmd)
    if system == "Darwin":
        return macos_command(cmd)
    return linux_command(cmd)


def run_elevated(cmd: list[str], timeout: float = 900, run: Run = subprocess.run,
                 system: Optional[str] = None, admin: Optional[bool] = None) -> subprocess.CompletedProcess:
    """Run `cmd` with admin rights. Raises ElevationDenied / ElevationUnavailable; returns the finished process."""
    system = system or platform.system()
    full = elevated_command(cmd, system, admin)
    kwargs = {"capture_output": True, "text": True, "timeout": timeout}
    if system == "Windows":
        kwargs["creationflags"] = NO_WINDOW
    proc = run(full, **kwargs)
    via = full[0]
    if via == "powershell" and proc.returncode == WINDOWS_CANCELLED:
        raise ElevationDenied("permission refused in the Windows dialog")
    if via == "pkexec" and proc.returncode == PKEXEC_DISMISSED:
        raise ElevationDenied("permission refused in the password dialog")
    if via == "osascript" and proc.returncode != 0 and "-128" in (proc.stderr or ""):
        raise ElevationDenied("permission refused in the password dialog")
    if via == "sudo" and proc.returncode != 0 and "password" in (proc.stderr or "").lower():
        raise ElevationUnavailable("admin rights are needed: start SafeHouse from an administrator terminal")
    return proc
