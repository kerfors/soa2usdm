"""Shared pieces for the two videos: square frames, moving crops of stills, caption bar, cards, encoding."""
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H, BAR, FPS = 1080, 1080, 170, 30
VIEW_H = H - BAR
ASPECT = W / VIEW_H
BLUE, BG, WHITE, INK, MUTED = (31, 71, 136), (245, 247, 250), (255, 255, 255), (31, 41, 51), (95, 107, 122)
INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(size, weight="SemiBold"):
    return ImageFont.truetype(INTER.format(weight), size)


def mono(size):
    return ImageFont.truetype(MONO, size)


def ease(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


class Stills:
    """Named still images with padding, cropped in source units (CSS px or PDF points)."""

    def __init__(self, scale, pad=900, bg=BG):
        self.scale, self.pad, self.bg, self.images = scale, pad, bg, {}

    def add(self, key, img):
        img = img.convert("RGB")
        padded = Image.new("RGB", (img.width + 2 * self.pad, img.height + 2 * self.pad), self.bg)
        padded.paste(img, (self.pad, self.pad))
        self.images[key] = padded

    def view(self, key, crop, size=(W, VIEW_H)):
        cx, cy, w = crop
        h = w * size[1] / size[0]
        box = tuple(v * self.scale + self.pad for v in (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
        return self.images[key].resize(size, Image.LANCZOS, box=box)


def rect(box, margin=24, width=None):
    x, y, w, h = box
    w2 = max(w + 2 * margin, (h + 2 * margin) * ASPECT) if width is None else width
    return (x + w / 2, y + h / 2, w2)


def rect_top(left, top, width, margin=0):
    w = width + 2 * margin
    return (left + width / 2, top - margin + (w / ASPECT) / 2, w)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


_bars = {}


def bar(caption):
    if caption not in _bars:
        img = Image.new("RGB", (W, BAR), BLUE)
        draw = ImageDraw.Draw(img)
        fnt = font(38)
        lines = wrap(draw, caption, fnt, W - 110)
        y = (BAR - 50 * len(lines)) / 2 + 2
        for line in lines:
            draw.text(((W - draw.textlength(line, font=fnt)) / 2, y), line, font=fnt, fill=WHITE)
            y += 50
        _bars[caption] = img
    return _bars[caption]


def frame(content, caption):
    out = Image.new("RGB", (W, H), BG)
    out.paste(content, (0, 0))
    out.paste(bar(caption), (0, VIEW_H))
    return out


def card(title, lines, footer=()):
    img = Image.new("RGB", (W, H), BLUE)
    draw = ImageDraw.Draw(img)
    draw.text((90, 320), title, font=font(84, "Bold"), fill=WHITE)
    y = 460
    for line in lines:
        draw.text((90, y), line, font=font(44), fill=(214, 226, 245))
        y += 62
    y = 900 - 48 * (len(footer) - 1)
    for line in footer:
        draw.text((90, y), line, font=font(31, "Regular"), fill=WHITE)
        y += 48
    return img


def ring(img, x, y, t):
    """A click marker: a ring that grows and fades, t in 0..1."""
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(over)
    r = 14 + 34 * t
    alpha = int(230 * (1 - t))
    draw.ellipse((x - r, y - r, x + r, y + r), outline=(255, 179, 0, alpha), width=7)
    draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(255, 179, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


def shot(stills, seconds, key, start, end=None, caption="", key_to=None, click=None):
    """Frames of one shot: a crop moving from start to end; optional cross-fade to another still; optional click ring."""
    n = round(seconds * FPS)
    for i in range(n):
        t = ease(i / max(n - 1, 1))
        crop = lerp(start, end, t) if end else start
        content = stills.view(key, crop)
        if key_to:
            content = Image.blend(content, stills.view(key_to, crop), t)
        if click and i < round(0.9 * FPS):
            cx, cy, w = crop
            fx = (click[0] - (cx - w / 2)) * W / w
            fy = (click[1] - (cy - (w / ASPECT) / 2)) * W / w
            content = ring(content, fx, fy, i / (0.9 * FPS))
        yield frame(content, caption)


def still(seconds, img):
    for _ in range(round(seconds * FPS)):
        yield img


def frames(timeline, fade_seconds=0.4):
    last, fade = None, round(fade_seconds * FPS)
    for mode, gen in timeline:
        previous = last
        for i, img in enumerate(gen):
            if mode == "fade" and previous is not None and i < fade:
                img = Image.blend(previous, img, (i + 1) / (fade + 1))
            yield img
            last = img


def encode(timeline, out):
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    count = 0
    for img in frames(timeline):
        ff.stdin.write(img.tobytes())
        count += 1
    ff.stdin.close()
    ff.wait()
    print(f"{count} frames, {count / FPS:.1f} s -> {out}")
