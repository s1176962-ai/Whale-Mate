"""Validate the local runtime before opening the desktop application.

Tk is part of the Python installation and cannot be installed with pip, so a
missing Tk gets an actionable, platform-specific message instead. Optional
packages listed in requirements.txt (currently ReportLab, needed only for PDF
exports) are installed on first run when absent; a failed install never blocks
the standard-library core of the app.

A PyInstaller one-file build unpacks into a temporary, disposable directory.
Frozen builds therefore get a writable project root next to the executable and
seed it with the read-only assets on first launch, so accounts and progress
survive restarts while private development data never enters the bundle.
"""

import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_INSTALL_TIMEOUT = 60  # seconds; an offline machine must not block startup
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)")
_MANUAL_INSTALL_HINT = (
    "PDF export stays unavailable until you run: "
    "python -m pip install -r requirements.txt"
)
_FROZEN_RESOURCES = ("assets", "data/questions", "AI-assistant-icon.png")


def is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def writable_data_dir() -> Path:
    """Prefer a portable folder beside the exe; fall back to the user profile."""
    portable = Path(sys.executable).resolve().parent / "WhaleMate_data"
    try:
        portable.mkdir(parents=True, exist_ok=True)
        probe = portable / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return portable
    except OSError:
        fallback = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "WhaleMate"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def portable_project_root(bundle: Path) -> Path:
    """Give a frozen build a writable root seeded with its read-only assets."""
    if not is_frozen():
        return bundle
    target = writable_data_dir()
    for name in _FROZEN_RESOURCES:
        source = bundle / name
        if source.is_file():
            dest = target / name
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
        elif source.is_dir():
            for item in source.rglob("*"):
                if not item.is_file():
                    continue
                dest = target / name / item.relative_to(source)
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
    return target


def required_distributions(folder: Path) -> list[str]:
    """Return distribution names declared in requirements.txt."""
    path = folder / "requirements.txt"
    if not path.is_file():
        return []
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "-")):
            continue
        match = _REQUIREMENT_NAME.match(stripped)
        if match:
            names.append(match.group(1))
    return names


def missing_distributions(folder: Path) -> list[str]:
    """Return declared distributions that are absent from this interpreter."""
    missing: list[str] = []
    for name in required_distributions(folder):
        try:
            importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
    return missing


def install_optional_dependencies(folder: Path) -> bool:
    """Install missing optional packages once; never block the offline core app."""
    if is_frozen():
        return True  # dependencies are already bundled; no pip in a frozen build
    missing = missing_distributions(folder)
    if not missing:
        return True
    print(f"Missing optional dependencies: {', '.join(missing)}")
    print("Installing them with pip; the app will still start if this fails.")
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--timeout",
        "10",
        "--retries",
        "1",
        "-r",
        str(folder / "requirements.txt"),
    ]
    try:
        result = subprocess.run(command, timeout=_INSTALL_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Could not run pip: {exc}")
        print(_MANUAL_INSTALL_HINT)
        return False
    if result.returncode != 0:
        print("Automatic installation failed.")
        print(_MANUAL_INSTALL_HINT)
        return False
    print("Optional dependencies are ready.")
    return True


def tkinter_guidance(platform: str | None = None) -> str:
    """Explain how to restore Tcl/Tk on the given platform."""
    system = platform or sys.platform
    if system == "win32":
        return (
            "Tkinter is missing from this Python installation.\n"
            "Fix: run the python.org installer, choose Modify, enable 'tcl/tk and IDLE',\n"
            "then start WhaleMate again. Microsoft Store Python often lacks Tk."
        )
    if system.startswith("linux"):
        return (
            "Tkinter is missing from this Python installation.\n"
            "Fix: install the system package, e.g. 'sudo apt install python3-tk'\n"
            "(Debian/Ubuntu) or 'sudo dnf install python3-tkinter' (Fedora), then retry."
        )
    if system == "darwin":
        return (
            "Tkinter is missing from this Python installation.\n"
            "Fix: install Python from python.org (it bundles Tcl/Tk), or install\n"
            "tcl-tk with Homebrew and rebuild Python, then retry."
        )
    return "Tkinter is missing. Reinstall Python with Tcl/Tk support and retry."


def display_guidance(exc: Exception, platform: str | None = None) -> str:
    """Explain why Tcl could not open a window."""
    system = platform or sys.platform
    graphical = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if system.startswith("linux") and not graphical:
        return (
            "Tk could not open a window: no graphical display is available.\n"
            "Run WhaleMate in a desktop session, or provide DISPLAY (e.g. via Xvfb)."
        )
    return f"Tk could not open a window ({exc}). Check the Tcl/Tk installation."


def runtime_report(project_root: Path, tk_module) -> str:
    """Exercise Tk and report bundled resources without opening the main window."""
    lines = [
        f"Python {sys.version.split()[0]}",
        f"Frozen: {is_frozen()}",
        f"Project root: {project_root}",
        f"Question bank: {(project_root / 'data' / 'questions').is_dir()}",
        f"Assets: {(project_root / 'assets').is_dir()}",
        f"Icon: {(project_root / 'AI-assistant-icon.png').is_file()}",
    ]
    try:
        import io

        import reportlab
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate

        lines.append(f"ReportLab: {reportlab.Version}")
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        buffer = io.BytesIO()
        SimpleDocTemplate(buffer).build(
            [Paragraph("WhaleMate PDF check", ParagraphStyle(name="check"))]
        )
        lines.append(f"PDF export: OK ({len(buffer.getvalue())} bytes)")
    except Exception as exc:
        lines.append(f"PDF export: FAILED ({exc})")
    try:
        probe = tk_module.Tk()
        probe.withdraw()
        lines.append(f"Tk window: OK (Tk {tk_module.TkVersion})")
        probe.destroy()
    except Exception as exc:
        lines.append(f"Tk window: FAILED ({exc})")
    return "\n".join(lines)


def report_frozen_error(message: str) -> None:
    """Surface startup errors when a windowed build has no console."""
    try:
        (writable_data_dir() / "startup_error.log").write_text(message, encoding="utf-8")
    except OSError:
        pass
    if "--check" in sys.argv[1:] or "--smoke" in sys.argv[1:]:
        return  # unattended diagnostics must never block on a dialog
    try:
        from tkinter import Tk, messagebox

        window = Tk()
        window.withdraw()
        messagebox.showerror("WhaleMate", message)
        window.destroy()
    except Exception:
        pass


def main():
    if sys.version_info < (3, 10):
        raise RuntimeError(
            f"Python 3.10 or later is required (found {sys.version.split()[0]}). "
            "Install Python 3.10+ from python.org and make sure the launcher uses it."
        )
    bundle = Path(__file__).resolve().parent
    project_root = portable_project_root(bundle)
    if not (project_root / "data/questions").is_dir():
        raise RuntimeError("Missing data/questions. Extract the complete project folder.")

    try:
        import tkinter as tk
    except ImportError as exc:
        raise RuntimeError(tkinter_guidance()) from exc

    install_optional_dependencies(bundle)

    if "--check" in sys.argv[1:]:
        report = runtime_report(project_root, tk)
        print(report)
        if is_frozen():
            (writable_data_dir() / "runtime_check.txt").write_text(
                report + "\n", encoding="utf-8"
            )
        return

    if "--smoke" in sys.argv[1:]:
        from learning_platform.gui import Application

        probe = tk.Tk()
        probe.withdraw()
        try:
            Application(probe, project_root=project_root)
            probe.update_idletasks()
            write_probe = project_root / "data" / ".write-test"
            write_probe.parent.mkdir(parents=True, exist_ok=True)
            write_probe.write_text("ok", encoding="utf-8")
            write_probe.unlink()
            report = "\n".join(
                [
                    "GUI smoke: OK (Application constructed)",
                    f"Project root: {project_root}",
                    "Data directory writable: True",
                ]
            )
        finally:
            try:
                probe.destroy()
            except tk.TclError:
                pass
        print(report)
        if is_frozen():
            (writable_data_dir() / "runtime_check.txt").write_text(
                report + "\n", encoding="utf-8"
            )
        return

    from learning_platform.dpi import apply_to, enable
    from learning_platform.gui import Application, maximize_startup

    enable()  # must precede the first Tk window (high-dpi text clarity)
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError(display_guidance(exc)) from exc
    apply_to(root)
    root.withdraw()
    Application(root, project_root=project_root)
    root.deiconify()
    maximize_startup(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        message = f"Startup failed: {exc}"
        print(message)
        if is_frozen():
            report_frozen_error(message)
        sys.exit(1)
