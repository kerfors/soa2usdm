"""Animate the captured stills into a 1080x1080 MP4 (camera moves, cursor, captions, fades).

All motion is computed per frame from keyframes, so playback is perfectly smooth.
Coordinates are CSS px of the 1920x1080 stills; the stills themselves are 2x (3840x2160).
Usage: python render.py [OUT.mp4]
       python render.py --preview          every 15th frame as JPEG into prev/
       python render.py --at 12.5,40       the frames at those times into prev/
"""
import json, math, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "SoA2USDM_review_showcase_v2.mp4"
PREVIEW = "--preview" in sys.argv
FPS, S = 30, 1080
R = json.load(open("stills/rects.json"))

# ---------------------------------------------------------------- assets
HI = {n: Image.open(f"stills/{n}.png").convert("RGB") for n in R}
LO = {n: im.resize((1920, 1080), Image.LANCZOS) for n, im in HI.items()}
CARD = {n: Image.open(f"gfx/{n}.png").convert("RGB") for n in ("title", "end")}
CAP = {p.stem[4:]: Image.open(p).convert("RGBA") for p in Path("gfx").glob("cap_*.png")}

def gradient():
    g = Image.new("RGB", (S, S))
    px = g.load()
    for y in range(S):
        for x in range(0, S):
            d = math.hypot(x - 160, y) / 1500
            t = min(1, d)
            c0, c1 = (36, 73, 127), (11, 26, 49)
            px[x, y] = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
    return g
BG = gradient()

def cursor_sprite():
    k = 4
    im = Image.new("RGBA", (40 * k, 48 * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(4, 3), (4, 33), (12, 25), (18, 38), (23, 36), (17, 23), (28, 23)]
    sh = [(x * k + 2 * k, y * k + 3 * k) for x, y in pts]
    d.polygon(sh, fill=(0, 0, 0, 90))
    im = im.filter(ImageFilter.GaussianBlur(3 * k))
    d = ImageDraw.Draw(im)
    d.polygon([(x * k, y * k) for x, y in pts], fill=(255, 255, 255, 255), outline=(17, 17, 17, 255), width=int(1.8 * k))
    return im.resize((40, 48), Image.LANCZOS)
CUR = cursor_sprite()

# ---------------------------------------------------------------- easing / keyframes
def ease(u):
    u = max(0.0, min(1.0, u))
    return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2

def interp(keys, t):
    """keys: [(t, v...)] -> eased piecewise interpolation of the tuple values."""
    if t <= keys[0][0]: return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            u = ease((t - a[0]) / (b[0] - a[0])) if b[0] > a[0] else 1
            return tuple(x + (y - x) * u for x, y in zip(a[1:], b[1:]))
    return keys[-1][1:]

def ramp(t, t0, t1, fade=.35):
    if t < t0 or t > t1: return 0.0
    return ease(min((t - t0) / fade, (t1 - t) / fade, 1.0))

# ---------------------------------------------------------------- drawing
AY = 470   # output row where the camera centre lands (focal point sits above the captions)

def clamp(cx, cy, size):
    s = S / size
    # keep the page filling the frame; once the frame is larger than the page the same bounds,
    # swapped, keep the page inside the frame -- continuous in both regimes (no jump at the crossover)
    lo, hi = (S / 2) / s, 1920 - (S / 2) / s
    cx = min(max(cx, min(lo, hi)), max(lo, hi))
    lo, hi = AY / s, 1080 - (S - AY) / s
    cy = min(max(cy, min(lo, hi)), max(lo, hi))
    return cx, cy, size

def still(name, cx, cy, size):
    cx, cy, size = clamp(cx, cy, size)
    s = S / size
    x0, y0 = S / 2 - cx * s, AY - cy * s
    w, h = 1920 * s, 1080 * s
    ox0, oy0, ox1, oy1 = max(0, x0), max(0, y0), min(S, x0 + w), min(S, y0 + h)
    ix0, iy0, ix1, iy1 = round(ox0), round(oy0), round(ox1), round(oy1)
    tw, th = ix1 - ix0, iy1 - iy0
    src, k = (HI[name], 2) if s > .55 else (LO[name], 1)
    bx0, by0, bx1, by1 = (v * k for v in ((ix0 - x0) / s, (iy0 - y0) / s, (ix1 - x0) / s, (iy1 - y0) / s))
    box = (max(0, bx0), max(0, by0), min(src.width, bx1), min(src.height, by1))
    part = src.resize((tw, th), Image.LANCZOS, box=box, reducing_gap=3.0)
    if tw == S and th == S:
        return part
    frame = BG.copy()
    # soft shadow + rounded corners when the page does not fill the frame
    sh = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sh).rounded_rectangle([ix0 + 6, iy0 + 16, ix1 - 6, iy1 + 22], radius=22, fill=150)
    frame.paste((3, 8, 18), (0, 0), sh.filter(ImageFilter.BoxBlur(18)))
    m = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, tw - 1, th - 1], radius=max(6, int(14 * s * 1.6)), fill=255)
    frame.paste(part, (ix0, iy0), m)
    return frame

def to_out(cam, x, y):
    cx, cy, size = clamp(*cam)
    s = S / size
    return S / 2 + (x - cx) * s, AY + (y - cy) * s

def spotlight(frame, cam, rects, a):
    if a <= 0: return frame
    m = Image.new("L", (S, S), int(150 * a))
    d = ImageDraw.Draw(m)
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ring)
    for (x, y, w, h) in rects:
        p0 = to_out(cam, x - 6, y - 6); p1 = to_out(cam, x + w + 6, y + h + 6)
        d.rounded_rectangle([p0, p1], radius=14, fill=0)
        dr.rounded_rectangle([p0, p1], radius=14, outline=(243, 201, 105, int(255 * a)), width=4)
    frame = Image.composite(Image.new("RGB", (S, S), (8, 16, 32)), frame, m.filter(ImageFilter.BoxBlur(6)))
    frame.paste(ring, (0, 0), ring)
    return frame

def draw_cursor(frame, pos, alpha, click_age):
    if alpha <= 0 or pos is None: return frame
    x, y = pos
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if click_age is not None and 0 <= click_age < .6:
        u = click_age / .6
        r = 10 + 34 * ease(u)
        ImageDraw.Draw(lay).ellipse([x - r, y - r, x + r, y + r], outline=(243, 201, 105, int(230 * (1 - u) * alpha)), width=5)
    sc = .82 if click_age is not None and 0 <= click_age < .14 else 1.0
    c = CUR if sc == 1 else CUR.resize((int(40 * sc), int(48 * sc)), Image.LANCZOS)
    if alpha < 1:
        c = c.copy(); c.putalpha(c.getchannel("A").point(lambda v: int(v * alpha)))
    lay.alpha_composite(c, (int(x - 4 * sc), int(y - 3 * sc)))
    frame = frame.convert("RGBA"); frame.alpha_composite(lay)
    return frame.convert("RGB")

def draw_caption(frame, key, a):
    if a <= 0: return frame
    p = CAP[key]
    if a < 1:
        p = p.copy(); p.putalpha(p.getchannel("A").point(lambda v: int(v * a)))
    y = S - p.height - 22 + int(16 * (1 - a))
    frame = frame.convert("RGBA"); frame.alpha_composite(p, (0, y))
    return frame.convert("RGB")

# ---------------------------------------------------------------- the shots
PAGE_GRID18 = (512, 725, 700)
TABLE_TOP = (1262, 850, 500)
OVERVIEW = (960, 540, 1880)
TILES = (960, 520, 1150)
TABLE_R32 = (1260, 820, 520)
WIDE = (755, 540, 1080)
BAND_R32 = (512, 580, 720)
BAND_HDR = (512, 470, 700)
TABLE_SUP = (1250, 800, 560)
RIGHT = (1455, 630, 900)
BAND_R25 = (515, 700, 720)
IDX_ALL = (960, 540, 1900)
IDX_REV = (1480, 560, 740)

def c(r):  # centre of a rect
    return (r[0] + r[2] / 2, r[1] + r[3] / 2)

r32 = R["pre_row"]["row32"]; hdr2 = R["hdr"]["hdr2"]; sup = R["note"]["sup"]
dtab = R["dec"]["tab"]; d2 = R["dec"]["d2"]; rc = R["index"]["review_cells"]

SHOTS = [
    dict(dur=3.6, card="title", zoom=(1.0, 1.035)),
    dict(dur=5.0, imgs=[(0, "start")], cam=[(0, 512, 735, 780), (5.0, *PAGE_GRID18)],
         caps=[("printed", .5, 4.9)]),
    dict(dur=4.6, imgs=[(0, "json")], cam=[(0, 460, 380, 900), (4.6, 430, 420, 830)],
         caps=[("json", .4, 4.5)]),
    dict(dur=4.2, imgs=[(0, "start")], cam=[(0, 1262, 850, 520), (4.2, 1262, 850, 470)],
         caps=[("extracted", .4, 4.1)]),
    dict(dur=8.6, imgs=[(0, "start")], cam=[(0, *TABLE_TOP), (1.9, *OVERVIEW), (4.0, 960, 540, 1800), (5.0, *TILES), (8.6, 960, 520, 1110)],
         caps=[("overview", 1.0, 4.7), ("checks", 5.1, 8.5)],
         spot=[(5.3, 8.6, [R["start"]["tile_rows"], R["start"]["tile_marks"]])]),
    dict(dur=8.2, imgs=[(0, "pre_row"), (1.95, "row")],
         cam=[(0, *TABLE_R32), (2.8, *TABLE_R32), (4.0, *WIDE), (5.0, *WIDE), (6.3, *BAND_R32), (8.2, 512, 580, 680)],
         cur=[(0, 1420, 700), (1.7, r32[0] + 60, r32[1] + 16), (2.9, r32[0] + 60, r32[1] + 16)], cur_hide=3.0,
         clicks=[1.8], caps=[("row", .4, 8.1)]),
    dict(dur=6.8, imgs=[(0, "row"), (2.45, "hdr")],
         cam=[(0, 512, 580, 680), (1.2, *WIDE), (3.5, *WIDE), (4.7, *BAND_HDR), (6.8, 512, 470, 660)],
         cur=[(.6, 760, 700), (2.2, hdr2[0] + 70, hdr2[1] + 11), (3.4, hdr2[0] + 70, hdr2[1] + 11)], cur_show=.8, cur_hide=3.5,
         clicks=[2.3], caps=[("header", .4, 6.7)]),
    dict(dur=6.6, imgs=[(0, "hdr"), (2.15, "note")],
         cam=[(0, 512, 470, 660), (1.2, *TABLE_SUP), (2.6, *TABLE_SUP), (3.8, *RIGHT), (6.6, 1455, 630, 870)],
         cur=[(.7, 1160, 700), (1.9, sup[0] + 7, sup[1] + 5), (6.6, sup[0] + 7, sup[1] + 5)], cur_show=.9,
         clicks=[2.0], caps=[("note", .4, 6.5)]),
    dict(dur=10.6, imgs=[(0, "note"), (1.25, "dec"), (2.55, "dec_d2")],
         cam=[(0, 1455, 630, 870), (3.6, 1455, 630, 870), (4.4, 1455, 600, 900), (7.2, 1455, 600, 900), (8.4, *BAND_R25), (10.6, 515, 700, 690)],
         cur=[(0, sup[0] + 7, sup[1] + 5), (1.0, *c(dtab)), (1.3, *c(dtab)), (2.3, d2[0] + 330, d2[1] + 90), (3.2, d2[0] + 330, d2[1] + 90)],
         cur_hide=3.3, clicks=[1.1, 2.4],
         caps=[("flags", .3, 3.9), ("decide", 4.2, 7.4), ("raw", 7.7, 10.5)],
         spot=[(4.4, 7.4, [d2])]),
    dict(dur=6.6, imgs=[(0, "consol")], cam=[(0, 545, 400, 1000), (1.2, 545, 400, 1000), (6.6, 530, 800, 900)],
         caps=[("consol", .4, 6.5)]),
    dict(dur=8.4, imgs=[(0, "index")], cam=[(0, *IDX_ALL), (2.2, 960, 540, 1840), (3.6, *IDX_REV), (8.4, 1480, 555, 710)],
         caps=[("index", .5, 5.0), ("ready", 5.3, 8.3)],
         spot=[(3.7, 8.4, [rc[:4]])]),
    dict(dur=5.6, card="end", zoom=(1.0, 1.03)),
]
XF = .45   # cross-fade between shots

def render_shot(sh, t):
    if "card" in sh:
        z = interp([(0, sh["zoom"][0]), (sh["dur"], sh["zoom"][1])], t)[0]
        im = CARD[sh["card"]]
        w = int(S * z)
        big = im.resize((w, w), Image.LANCZOS)
        o = (w - S) // 2
        return big.crop((o, o, o + S, o + S))
    cam = interp(sh["cam"], t)
    def at(name): return still(name, *cam)
    imgs = sh["imgs"]
    cur_i = max(i for i, (ti, _) in enumerate(imgs) if ti <= t)
    fr = at(imgs[cur_i][1])
    ti = imgs[cur_i][0]
    if cur_i > 0 and t - ti < .28:
        fr = Image.blend(at(imgs[cur_i - 1][1]), fr, ease((t - ti) / .28))
    for (t0, t1, rects) in sh.get("spot", []):
        fr = spotlight(fr, cam, rects, ramp(t, t0, t1, .5))
    if "cur" in sh:
        ck = sh["cur"]
        show, hide = sh.get("cur_show", ck[0][0]), sh.get("cur_hide", sh["dur"] + 1)
        a = ramp(t, show - .2, hide, .25) if t >= show - .2 else 0
        x, y = interp(ck, t)
        ages = [t - tc for tc in sh.get("clicks", []) if t >= tc]
        fr = draw_cursor(fr, to_out(cam, x, y), a, min(ages) if ages else None)
    for (k, t0, t1) in sh.get("caps", []):
        fr = draw_caption(fr, k, ramp(t, t0, t1))
    return fr

def frames():
    starts, T = [], 0.0
    for sh in SHOTS:
        starts.append(T); T += sh["dur"]
    n = int(round(T * FPS))
    for f in range(n):
        t = f / FPS
        i = max(j for j, s0 in enumerate(starts) if s0 <= t)
        lt = t - starts[i]
        fr = render_shot(SHOTS[i], lt)
        if i + 1 < len(SHOTS) and SHOTS[i]["dur"] - lt < XF:
            u = ease(1 - (SHOTS[i]["dur"] - lt) / XF)
            fr = Image.blend(fr, render_shot(SHOTS[i + 1], 0), u)
        if f < 8:       # fade in from black
            fr = Image.blend(Image.new("RGB", (S, S)), fr, f / 8)
        yield f, n, fr

AT = [float(a) for a in sys.argv[sys.argv.index("--at") + 1].split(",")] if "--at" in sys.argv else None
if AT:
    Path("prev").mkdir(exist_ok=True)
    want = {int(round(t * FPS)) for t in AT}
    for f, n, fr in frames():
        if f in want: fr.save(f"prev/t{f/FPS:05.1f}.jpg", quality=88)
        if f > max(want): break
    print("frames at", sorted(want))
elif PREVIEW:
    Path("prev").mkdir(exist_ok=True)
    for f, n, fr in frames():
        if f % 15 == 0: fr.save(f"prev/f{f:05d}.jpg", quality=85)
    print("preview frames written")
else:
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S}x{S}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
                          "-profile:v", "high", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    for f, n, fr in frames():
        p.stdin.write(fr.tobytes())
        if f % 300 == 0: print(f, "/", n, flush=True)
    p.stdin.close(); p.wait()
    print("written", OUT)
