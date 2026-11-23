"""The look: black and white with one colour kept (the brand's part, the calipers), crushed blacks,
cool shadows, a vignette and grain. cover.py uses the same function, so the cover and the video match.

Grade a cut's bare picture (HyperFrames hf/assets/picture.mp4, before the type layer), never the
finished render: the labels and captions must stay clean.

    uv run --no-project --with numpy --with scipy python -I grade.py <in.mp4> <out.mp4> \
        [--keep red] [--strength 0.6] [--open-end 3.437]
    uv run --no-project --with numpy --with scipy --with pillow python -I grade.py <in.mp4> <sheet.jpg> \
        --test 1.5,14.5,27.5        (stills: original | full look | blend, one row per time)

--keep       hue to leave in colour: red (default), orange, yellow, green, blue, or none (pure B&W)
--strength   how much of the look after the opening shot (0-1). 0.6 reads as a film, not a gimmick.
--open-end   seconds of full look at the start (the first cut, from cues.json), so the tap lands on
             the cover's look. 0 = the same strength throughout.

The keep mask works on how saturated a pixel is relative to its own brightness, so a caliper in
shadow stays red; it is blurred and smoothed over time so noise and warm light don't flicker.
ffmpeg reads the source at its nominal rate: a file with uneven frame timing comes out with fewer
frames but the same duration, so cuts stay on their beats.
"""
import argparse, json, subprocess
import numpy as np
from scipy.ndimage import gaussian_filter

HUES = {"red": 0, "orange": 25, "yellow": 55, "green": 120, "blue": 220}
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def keep_mask(a, keep="red"):
    """0-1 mask of pixels in the kept hue. a: float32 HxWx3 in 0-1."""
    if keep == "none":
        return np.zeros(a.shape[:2], np.float32)
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / (mx + 0.04)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    hue = np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) % 360
    dist = np.abs((hue - HUES[keep] + 180) % 360 - 180)
    m = np.clip((sat - 0.38) * 3.5, 0, 1) * np.clip((mx - 0.10) * 6, 0, 1) * np.clip((30 - dist) / 12, 0, 1)
    h, w = m.shape
    small = gaussian_filter(m[::4, ::4], 1.5)
    return np.repeat(np.repeat(small, 4, 0), 4, 1)[:h, :w].astype(np.float32)


def vignette(h, w):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h * 0.45) / (h * 0.62)) ** 2)
    return np.clip(1.15 - d ** 2.2, 0.25, 1).astype(np.float32)[..., None]


def look(a, mask, strength=1.0, rng=None, vig=None):
    """The graded frame. strength 1 is the cover; lower blends it over the real colour."""
    lum = (a @ LUMA)[..., None]
    grey = np.clip((lum - 0.05) / 0.85, 0, 1) ** 1.25 * np.array([0.92, 0.95, 1.0], np.float32)
    m = mask[..., None]
    full = grey * (1 - m) + np.clip(a * 1.15, 0, 1) * m
    full = full * (vig if vig is not None else vignette(*a.shape[:2]))
    out = a * (1 - strength) + full * strength
    if rng is not None:
        out = out + rng.normal(0, 0.018 * strength, a.shape[:2])[..., None].astype(np.float32)
    return np.clip(out, 0, 1)


def probe(src):
    s = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate", "-of", "json", src],
                                  capture_output=True, check=True).stdout)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], s["r_frame_rate"], int(n) / int(d)


def still(src, t, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) / 255


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--keep", default="red", choices=[*HUES, "none"])
    ap.add_argument("--strength", type=float, default=0.6)
    ap.add_argument("--open-end", type=float, default=0.0)
    ap.add_argument("--test")
    o = ap.parse_args()
    w, h, rate, fps = probe(o.src)
    rng, vig = np.random.default_rng(3), vignette(h, w)

    if o.test:
        from PIL import Image
        rows = []
        for t in (float(x) for x in o.test.split(",")):
            a = still(o.src, t, w, h)
            m = keep_mask(a, o.keep)
            rows.append(np.concatenate([a, look(a, m, 1.0, rng, vig), look(a, m, o.strength, rng, vig)], 1))
        sheet = Image.fromarray((np.concatenate(rows, 0) * 255).astype(np.uint8))
        sheet.resize((sheet.width // 3, sheet.height // 3)).save(o.dst, quality=90)
        print(o.dst); return

    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", o.src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", rate, "-i", "-", "-c:v", "libx264", "-crf", "15", "-preset", "slow",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", "-movflags", "+faststart", o.dst], stdin=subprocess.PIPE)
    n, prev, size = 0, None, w * h * 3
    while True:
        raw = dec.stdout.read(size)
        if len(raw) < size:
            break
        a = np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
        m, t = keep_mask(a, o.keep), n / fps
        at_cut = o.open_end and abs(t - o.open_end) < 0.5 / fps
        prev = m if prev is None or at_cut else prev * 0.5 + m * 0.5  # smooth over time, reset at the cut
        s = 1.0 if t < o.open_end else o.strength
        enc.stdin.write((look(a, prev, s, rng, vig) * 255 + 0.5).astype(np.uint8).tobytes())
        n += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    print(f"{n} frames -> {o.dst}")


if __name__ == "__main__":
    main()
