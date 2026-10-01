"""
Manual verification script for the pixel <-> (time, frequency) geometry exposed
by `Spectrogram.axis_bounds()` / the `X-Axis-*` headers of
`GET /api/records/<id>/spectrogram` (Phase 3 of the redesign, see
docs/redesign/ROADMAP.md).

It checks that the simple linear formula documented in
`Spectrogram.axis_bounds()`:

    px = pixel_x + (t - time_start) / (time_end - time_start) * pixel_width
    py = pixel_y + (freq_max - f) / (freq_max - freq_min) * pixel_height

(computed purely from the numbers a client receives, no matplotlib involved)
reproduces exactly what `Spectrogram.get_coordinates()` computes from the live
matplotlib `transData` transform, for a real detection box.

Usage (inside the `osadec` container, which has matplotlib/scipy/librosa):

    docker exec -i osadec python3 src/utils/verify_pixel_calibration.py

It is a standalone script rather than a pytest test because the project has no
test runner configured yet (see CLAUDE.md: "Pas de suite de tests
actuellement."); it can be adapted into a real test once one exists.
"""

import sys

import numpy as np

sys.path.insert(0, "src/utils")

from pixlabel import Spectrogram  # noqa: E402


def predict_pixel_bbox(bounds, t0, f0, t1, f1):
    """Reimplements the client-side formula documented in axis_bounds()."""

    def to_px(t, f):
        px = bounds["pixel_x"] + (t - bounds["time_start"]) / (
            bounds["time_end"] - bounds["time_start"]
        ) * bounds["pixel_width"]
        py = bounds["pixel_y"] + (bounds["freq_max"] - f) / (
            bounds["freq_max"] - bounds["freq_min"]
        ) * bounds["pixel_height"]
        return px, py

    x1, y1 = to_px(t0, f1)  # top-left corresponds to (t_start, f_max)
    x2, y2 = to_px(t1, f0)  # bottom-right corresponds to (t_end, f_min)
    return x1, y1, x2 - x1, y2 - y1


def main():
    fs = 2000
    duration = 300

    rng = np.random.default_rng(0)
    t = np.arange(0, duration, 1 / fs)
    s = rng.standard_normal(len(t)) * 0.001

    # Known "detection": a tone at 55Hz between t=100s and t=110s, i.e. a box
    # [t_start=100, t_end=110] x [f_min=50, f_max=60] -- matching the synthetic
    # detection (id=5213 on the QA test record) used to exercise the live API
    # during this phase's verification.
    tone_mask = (t >= 100) & (t < 110)
    s[tone_mask] += 0.5 * np.sin(2 * np.pi * 55 * t[tone_mask])

    spectro = Spectrogram(s=s, fs=fs, img_name="calibration_check.png")
    try:
        bounds = spectro.axis_bounds()

        t_start, t_end, f_min, f_max = 100.0, 110.0, 50.0, 60.0

        # Ground truth: matplotlib's own transData, used directly.
        gx, gy, gw, gh = spectro.get_coordinates(t_start, f_min, t_end, f_max)

        # Client-side reimplementation, using only the numbers served in the
        # `X-Axis-*` headers (here taken straight from axis_bounds()).
        px, py, pw, ph = predict_pixel_bbox(bounds, t_start, f_min, t_end, f_max)

        print("axis_bounds():", bounds)
        print(f"ground truth (matplotlib transData): x={gx:.3f} y={gy:.3f} w={gw:.3f} h={gh:.3f}")
        print(f"client formula (headers only):        x={px:.3f} y={py:.3f} w={pw:.3f} h={ph:.3f}")

        for name, g, p in (("x", gx, px), ("y", gy, py), ("w", gw, pw), ("h", gh, ph)):
            assert abs(g - p) < 0.5, f"{name}: ground truth {g} vs predicted {p} (pixel drift > 0.5px)"

        print("OK: client-side formula matches matplotlib's transData within 0.5px.")
    finally:
        spectro.close()


if __name__ == "__main__":
    main()
