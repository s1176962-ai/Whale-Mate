"""Shared Tk test root.

Creating and destroying a Tk interpreter for every GUI test eventually fails on
Windows with ``invalid command name "tcl_findLibrary"``, ``tk.tcl`` source
errors, or ``image create photo`` TclErrors. Those are Tcl/Tk teardown races,
not application bugs. Reusing one hidden root and clearing it between tests
keeps the suite deterministic without changing production code.
"""

import tkinter as tk

_TK_ROOT = None


def _unbind_tree(widget):
    """Remove Python callbacks that could fire for a doomed widget."""
    try:
        for sequence in widget.bind():
            try:
                widget.unbind(sequence)
            except tk.TclError:
                pass
    except tk.TclError:
        pass
    for child in list(widget.winfo_children()):
        _unbind_tree(child)


def fresh_tk_root():
    """Return the process-wide Tk root, reset to an empty, quiet state."""
    global _TK_ROOT
    try:
        if _TK_ROOT is None or not _TK_ROOT.winfo_exists():
            _TK_ROOT = tk.Tk()
            _TK_ROOT.withdraw()

        root = _TK_ROOT
        # Pending callbacks from the previous test must not fire against widgets
        # that are about to be destroyed.
        try:
            for job in root.tk.call("after", "info"):
                root.after_cancel(job)
        except tk.TclError:
            pass

        # Detach Application's root-level handlers before removing its widgets,
        # otherwise an old app can still react to the next test's events.
        for sequence in (
            "<Destroy>",
            "<Configure>",
            "<MouseWheel>",
            "<Button-4>",
            "<Button-5>",
            "<Key>",
        ):
            try:
                root.unbind(sequence)
            except tk.TclError:
                pass
        for widget_class in ("TCombobox", "TSpinbox"):
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                try:
                    root.unbind_class(widget_class, sequence)
                except tk.TclError:
                    pass

        _unbind_tree(root)
        for child in list(root.winfo_children()):
            try:
                child.destroy()
            except tk.TclError:
                pass
        root.update_idletasks()
        return root
    except tk.TclError:
        _TK_ROOT = None
        raise
