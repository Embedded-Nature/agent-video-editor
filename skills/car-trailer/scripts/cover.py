"""A Short's cover (or a 16:9 thumbnail) in the same look as grade.py: one strong frame, the brand's
logo, the car as the headline, a small tag line. Lettered in Michroma (assets/fonts, OFL), the wide
flat caps of a car badge.

    uv run --no-project --with numpy --with scipy --with pillow python -I cover.py \
        --frame "<export.mov>@503" --cx 0.36 --out cover.jpg \
        --logo logo-reversed.png --kicker PORSCHE --title "PANAMERA TURBO" \
        --tag "971 · AIR FILTER UPGRADE" --accent 971 [--keep red] [--top 1275] [--size 1080x1920]

    python3 -I cover.py --reverse-logo <logo on white.png> <logo-reversed.png> [--keep red]
        (a dark-ground version of a logo: the kept colour stays, black ink turns white, white goes clear)

--frame    a still image, or <video>@<seconds>. Pick a frame where the part and the car are both in shot.
--cx       horizontal centre of the crop, 0-1 of the source width (9:16 from 16:9 keeps a narrow slice).
--top      y of the logo's top edge. Put the type below the subject: if the logo covers the part, lower it.
--accent   the word of the tag line printed in the kept colour.
"""
import argparse, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grade import HUES, keep_mask, look  # noqa: E402

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MICHROMA = os.path.join(SKILL, "assets", "fonts", "Michroma-Regular.ttf")
ACCENT = {"red": (214, 32, 39), "orange": (236, 120, 30), "yellow": (240, 196, 40),
          "green": (60, 180, 90), "blue": (40, 120, 230), "none": (245, 245, 245)}


def load_frame(spec):
    if "@" in spec and not os.path.exists(spec):
        path, t = spec.rsplit("@", 1)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", t, "-i", path, "-frames:v", "1", "-f", "image2pipe",
                              "-vcodec", "png", "-"], capture_output=True, check=True).stdout
        import io
        return Image.open(io.BytesIO(raw)).convert("RGB")
    return Image.open(spec).convert("RGB")


def reverse_logo(src, dst, keep="red"):
    a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
    k = max(1, round(1800 / max(a.shape[:2])))
    if k > 1:
        a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize(
            (a.shape[1] * k, a.shape[0] * k), Image.Resampling.LANCZOS)).astype(np.float32) / 255
    kept = keep_mask(a, keep) > 0.3
    alpha = 1 - np.clip((a.min(-1) - 0.85) / 0.15, 0, 1)  # white ground goes clear
    out = np.zeros(a.shape[:2] + (4,), np.float32)
    out[..., :3] = np.where(kept[..., None], a, 1.0)  # black ink -> white
    out[..., 3] = alpha
    im = Image.fromarray((out * 255).astype(np.uint8), "RGBA")
    im.crop(im.getbbox()).save(dst)
    print(dst)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--reverse-logo":
        keep = sys.argv[sys.argv.index("--keep") + 1] if "--keep" in sys.argv else "red"
        return reverse_logo(sys.argv[2], sys.argv[3], keep)
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--cx", type=float, default=0.5)
    ap.add_argument("--keep", default="red", choices=[*HUES, "none"])
    ap.add_argument("--logo"); ap.add_argument("--logo-width", type=int, default=400)
    ap.add_argument("--kicker", default=""); ap.add_argument("--title", required=True)
    ap.add_argument("--tag", default=""); ap.add_argument("--accent", default="")
    ap.add_argument("--top", type=int); ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--font", default=MICHROMA)
    o = ap.parse_args()
    W, H = map(int, o.size.split("x"))

    im = load_frame(o.frame)
    k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.Resampling.LANCZOS)
    x = min(max(round(im.width * o.cx - W / 2), 0), im.width - W)
    y = (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H)).filter(ImageFilter.UnsharpMask(2.5, 70, 2))

    a = np.asarray(im).astype(np.float32) / 255
    a = look(a, keep_mask(a, o.keep), 1.0, np.random.default_rng(7))
    top = o.top if o.top is not None else int(H * 0.66)
    yy, xx = np.mgrid[0:H, 0:W]
    t = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - (top + H * 0.15)) / (H * 0.16)) ** 2)
    a *= (1 - 0.72 * np.clip(1.25 - t, 0, 1) ** 1.2)[..., None]  # a soft dark pool under the type
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    accent, white, grey = ACCENT[o.keep], (245, 245, 245), (215, 215, 215)

    def fitted(text, size, track, maxw):
        while size > 16:
            f = ImageFont.truetype(o.font, size)
            if sum(dr.textlength(c, font=f) for c in text) + track * (len(text) - 1) <= maxw:
                return f
            size -= 2
        return ImageFont.truetype(o.font, size)

    def line(y, runs, f, track, bold):
        chars = [(c, col) for txt, col in runs for c in txt]
        x0 = (W - sum(dr.textlength(c, font=f) for c, _ in chars) - track * (len(chars) - 1)) / 2
        for c, col in chars:
            dr.text((x0 + 3, y + 4), c, font=f, fill=(0, 0, 0), stroke_width=bold, stroke_fill=(0, 0, 0))
            dr.text((x0, y), c, font=f, fill=col, stroke_width=bold, stroke_fill=col)  # faux bold: one weight
            x0 += dr.textlength(c, font=f) + track

    y, s = top, W / 1080
    if o.logo:
        logo = Image.open(o.logo).convert("RGBA")
        lw = round(o.logo_width * s)
        logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.Resampling.LANCZOS)
        im.paste(logo, ((W - lw) // 2, y), logo)
        y += logo.height + round(40 * s)
    if o.kicker:
        line(y, [(o.kicker, grey)], fitted(o.kicker, round(40 * s), round(22 * s), W * 0.8), round(22 * s), 1)
        y += round(66 * s)
    hero = fitted(o.title, round(110 * s), round(6 * s), W * 0.89)
    line(y, [(o.title, white)], hero, round(6 * s), max(1, round(3 * s)))
    y += int(hero.size * 1.45)
    if o.tag:
        tag = o.tag
        runs = [(tag[:len(o.accent)], accent), (tag[len(o.accent):], grey)] if o.accent and tag.startswith(o.accent) \
            else [(tag, grey)]
        line(y, runs, fitted(tag, round(30 * s), round(12 * s), W * 0.86), round(12 * s), 1)
    im.save(o.out, quality=94)
    print(o.out)


if __name__ == "__main__":
    main()
