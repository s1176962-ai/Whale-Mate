"""Startup checks: optional dependency bootstrap and platform-specific Tk help."""

import subprocess
import sys
import tempfile
import unittest
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import launcher


def _requirements(folder: Path, text: str = "reportlab>=4.0,<5\n") -> Path:
    (folder / "requirements.txt").write_text(text, encoding="utf-8")
    return folder


class RequirementParsingTests(unittest.TestCase):
    def test_comments_extras_and_specifiers_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _requirements(
                Path(tmp),
                "# PDF export dependency; core application uses the standard library.\n"
                "reportlab>=4.0,<5\n"
                "\n"
                "custom-widget~=2.1 ; python_version >= '3.10'\n"
                "-r other.txt\n",
            )
            self.assertEqual(
                launcher.required_distributions(folder), ["reportlab", "custom-widget"]
            )

    def test_missing_requirements_file_means_no_optional_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(launcher.required_distributions(Path(tmp)), [])

    def test_only_absent_distributions_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _requirements(Path(tmp), "reportlab>=4.0,<5\nother-pkg==1.0\n")
            with patch(
                "launcher.importlib.metadata.version",
                side_effect=[PackageNotFoundError("reportlab"), "1.0"],
            ):
                self.assertEqual(launcher.missing_distributions(folder), ["reportlab"])


class OptionalDependencyTests(unittest.TestCase):
    def setUp(self):
        printer = patch("builtins.print")
        printer.start()
        self.addCleanup(printer.stop)

    def test_installed_dependencies_do_not_invoke_pip(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _requirements(Path(tmp))
            with patch("launcher.importlib.metadata.version", return_value="4.5.1"), patch(
                "launcher.subprocess.run"
            ) as run:
                self.assertTrue(launcher.install_optional_dependencies(folder))
                run.assert_not_called()

    def test_missing_dependency_is_installed_into_the_running_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _requirements(Path(tmp))
            done = subprocess.CompletedProcess(args=[], returncode=0)
            with patch(
                "launcher.importlib.metadata.version",
                side_effect=PackageNotFoundError("reportlab"),
            ), patch("launcher.subprocess.run", return_value=done) as run:
                self.assertTrue(launcher.install_optional_dependencies(folder))
            command = run.call_args.args[0]
            self.assertEqual(command[0], sys.executable)
            self.assertEqual(command[1:4], ["-m", "pip", "install"])
            self.assertIn("--no-input", command)
            self.assertIn(str(folder / "requirements.txt"), command)
            self.assertEqual(run.call_args.kwargs["timeout"], launcher._INSTALL_TIMEOUT)

    def test_failed_install_does_not_raise_or_block_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _requirements(Path(tmp))
            failed = subprocess.CompletedProcess(args=[], returncode=1)
            with patch(
                "launcher.importlib.metadata.version",
                side_effect=PackageNotFoundError("reportlab"),
            ), patch("launcher.subprocess.run", return_value=failed):
                self.assertFalse(launcher.install_optional_dependencies(folder))

    def test_pip_timeout_does_not_raise_or_block_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = _requirements(Path(tmp))
            with patch(
                "launcher.importlib.metadata.version",
                side_effect=PackageNotFoundError("reportlab"),
            ), patch(
                "launcher.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="pip", timeout=60),
            ):
                self.assertFalse(launcher.install_optional_dependencies(folder))


class TkGuidanceTests(unittest.TestCase):
    def test_windows_points_at_the_installer_option(self):
        self.assertIn("tcl/tk and IDLE", launcher.tkinter_guidance("win32"))

    def test_linux_points_at_the_system_package(self):
        self.assertIn("python3-tk", launcher.tkinter_guidance("linux"))

    def test_macos_points_at_the_python_org_installer(self):
        self.assertIn("python.org", launcher.tkinter_guidance("darwin"))

    def test_unknown_platform_still_explains_the_problem(self):
        self.assertIn("Tcl/Tk", launcher.tkinter_guidance("freebsd"))

    def test_linux_without_display_explains_the_graphical_session(self):
        with patch.dict("os.environ", {"DISPLAY": "", "WAYLAND_DISPLAY": ""}):
            message = launcher.display_guidance(RuntimeError("no display"), platform="linux")
        self.assertIn("DISPLAY", message)

    def test_tcl_failure_on_windows_mentions_the_installation(self):
        message = launcher.display_guidance(RuntimeError("bad Tcl version"), platform="win32")
        self.assertIn("Tcl/Tk", message)


class FrozenBuildTests(unittest.TestCase):
    def test_frozen_build_never_invokes_pip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("launcher.is_frozen", return_value=True), patch(
                "launcher.subprocess.run"
            ) as run:
                self.assertTrue(launcher.install_optional_dependencies(Path(tmp)))
                run.assert_not_called()

    def test_only_distributable_resources_are_seeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            (bundle / "assets" / "images").mkdir(parents=True)
            (bundle / "assets" / "images" / "art.png").write_bytes(b"png")
            (bundle / "data" / "questions").mkdir(parents=True)
            (bundle / "data" / "questions" / "english.json").write_text(
                "[]", encoding="utf-8"
            )
            (bundle / "data" / "users.json").write_text("private", encoding="utf-8")
            (bundle / "AI-assistant-icon.png").write_bytes(b"icon")
            target = Path(tmp) / "portable"
            with patch("launcher.is_frozen", return_value=True), patch(
                "launcher.writable_data_dir", return_value=target
            ):
                root = launcher.portable_project_root(bundle)
            self.assertEqual(root, target)
            self.assertTrue((target / "assets/images/art.png").is_file())
            self.assertTrue((target / "data/questions/english.json").is_file())
            self.assertTrue((target / "AI-assistant-icon.png").is_file())
            self.assertFalse((target / "data/users.json").exists())

    def test_existing_user_files_are_not_overwritten_on_relaunch(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            (bundle / "data" / "questions").mkdir(parents=True)
            (bundle / "data" / "questions" / "english.json").write_text(
                "[]", encoding="utf-8"
            )
            target = Path(tmp) / "portable"
            (target / "data" / "questions").mkdir(parents=True)
            kept = target / "data" / "questions" / "english.json"
            kept.write_text("user-edited", encoding="utf-8")
            with patch("launcher.is_frozen", return_value=True), patch(
                "launcher.writable_data_dir", return_value=target
            ):
                launcher.portable_project_root(bundle)
            self.assertEqual(kept.read_text(encoding="utf-8"), "user-edited")

    def test_runtime_report_probes_tk_without_a_visible_window(self):
        class Probe:
            def withdraw(self):
                pass

            def destroy(self):
                pass

        fake_tk = SimpleNamespace(Tk=Probe, TkVersion=8.6)
        with tempfile.TemporaryDirectory() as tmp:
            report = launcher.runtime_report(Path(tmp), fake_tk)
        self.assertIn("Tk window: OK (Tk 8.6)", report)
        self.assertIn("ReportLab:", report)
        self.assertIn("PDF export: OK", report)


if __name__ == "__main__":
    unittest.main()
