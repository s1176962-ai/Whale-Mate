#!/bin/zsh

# macOS launcher: keep the project and Windows start_windows.bat unchanged.
PROJECT_DIR="${0:A:h}"
PYTHON_BIN="/usr/local/bin/python3"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python 3.13 is required at $PYTHON_BIN."
  echo "Install it from https://www.python.org/downloads/macos/ (Tcl/Tk included)."
  read "?Press Return to close..."
  exit 1
fi

cd "$PROJECT_DIR" || exit 1
"$PYTHON_BIN" "$PROJECT_DIR/launcher.py"
STATUS=$?
if [[ $STATUS -ne 0 ]]; then
  echo "WhaleMate did not start (exit $STATUS)."
  echo "Follow the instruction printed above, then try again."
  read "?Press Return to close..."
fi
exit $STATUS
