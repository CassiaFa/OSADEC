"""
Formalizes `src/utils/verify_pixel_calibration.py` (manual verification
script, see its own docstring and docs/testing.md) as a pytest test: runs it
exactly as documented (`python3 src/utils/verify_pixel_calibration.py` from
the app root) and asserts it reports that the client-side pixel<->(time,
frequency) formula matches matplotlib's own transData within 0.5px.

Kept as a subprocess invocation rather than importing its `main()` directly:
the script is explicitly out of scope to modify for this task (osadec-viewer
territory this round) and its own `sys.path.insert(0, "src/utils")` assumes
it is run as a script with the app root as the working directory, not
imported as a module from `tests/`.
"""

import os
import subprocess
import sys

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_pixel_to_time_frequency_calibration():
    result = subprocess.run(
        [sys.executable, os.path.join("src", "utils", "verify_pixel_calibration.py")],
        cwd=APP_ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: client-side formula matches matplotlib's transData within 0.5px." in result.stdout
