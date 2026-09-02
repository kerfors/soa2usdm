"""Turn the recording into the captioned 1920x1080 MP4.

Usage:  python compose.py [REC_DIR] [OUT_MP4]
  REC_DIR  the record.py output dir (default ./rec)
  OUT_MP4  default ./SoA2USDM_review_page_showcase.mp4

Needs ffmpeg, numpy, Pillow and a Liberation Sans (or any sans) TTF.
Scene start times come from the marker square record.py paints, not from the
script clock — Playwright's screencast runs slower than wall time.
"""
import json, subprocess, glob, re, html, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REC = Path(sys.argv[1] if len(sys.argv) > 1 else "rec")
OUT_MP4 = sys.argv[2] if len(sys.argv) > 2 else "SoA2USDM_review_page_showcase.mp4"
V = glob.glob(str(REC / "*.webm"))[0]
M = json.load(open(REC / "marks.json"))
caps = M["caps"]
FPS = 25
W, H_UI, H_BAR = 1920, 960, 120

# ---- 1. scene timeline from the marker square (top-left 14x14, rgb(255,i*25,0))
raw = subprocess.run(["ffmpeg","-v","error","-i",V,"-vf","crop=4:4:5:5,scale=1:1","-f","rawvideo","-pix_fmt","rgb24","-"],
                     capture_output=True).stdout
px = np.frombuffer(raw, dtype=np.uint8).reshape(-1,3)
n = len(px); dur = n/FPS
scene = np.full(n, -1)
cur = 0
for k,(r,g,b) in enumerate(px):
    if r>200 and b<40:
        i = int(round(g/25))
        if i > cur: cur = i
    scene[k] = cur
starts = {}
for k in range(n):
    starts.setdefault(int(scene[k]), k/FPS)
print("frames", n, "duration", round(dur,2))
print("scene starts", {i: round(t,2) for i,t in sorted(starts.items())})

# ---- 2. caption plates (1920x120)
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONTB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
try:
    ImageFont.truetype(FONT, 10)
except OSError:
    FONT = FONTB = subprocess.run(["fc-match","-f","%{file}","sans"],capture_output=True,text=True).stdout
SIZE = 31
f_reg, f_bold = ImageFont.truetype(FONT, SIZE), ImageFont.truetype(FONTB, SIZE)

def tokens(h):
    # split into (text, bold) runs, keep spaces
    out=[]; bold=False
    for part in re.split(r'(<b>|</b>)', h):
        if part=='<b>': bold=True
        elif part=='</b>': bold=False
        elif part:
            for w in re.findall(r'\s*\S+\s*', html.unescape(part)):
                out.append((w,bold))
    return out

def wrap(toks, maxw):
    lines=[[]]; width=0
    for w,b in toks:
        f = f_bold if b else f_reg
        ww = f.getlength(w)
        if width+ww > maxw and lines[-1]:
            lines.append([]); width=0
        if not lines[-1]: w = w.lstrip(); ww = f.getlength(w)
        lines[-1].append((w,b)); width+=ww
    return lines

def plate(h, card=False):
    im = Image.new("RGB",(W,H_BAR),(31,71,136) if card else (16,24,40))
    if not h: return im
    d = ImageDraw.Draw(im)
    lines = wrap(tokens(h), 1760)
    lh = SIZE+10; y = (H_BAR - lh*len(lines))//2 + 2
    for ln in lines:
        tw = sum((f_bold if b else f_reg).getlength(w) for w,b in ln)
        x = (W-tw)/2
        for w,b in ln:
            f = f_bold if b else f_reg
            d.text((x,y), w, font=f, fill=(255,209,102) if b else (255,255,255))
            x += f.getlength(w)
        y += lh
    return im

plates=[]
for i,c in enumerate(caps):
    p = str(REC / f"cap{i}.png")
    plate(c, card=(c=="")).save(p); plates.append(p)

# ---- 3. ffmpeg: pad to 1080, cover marker with header colour, overlay plates by time
order = sorted(starts.items())
inputs = ["-i", V]
for p in plates: inputs += ["-loop","1","-i",p]
fc = f"[0:v]pad={W}:{H_UI+H_BAR}:0:0:color=#101828,drawbox=x=0:y=0:w=16:h=16:color=#1F4788:t=fill[v0]"
prev="v0"
for j,(i,t0) in enumerate(order):
    t1 = order[j+1][1] if j+1 < len(order) else dur+1
    fc += f";[{prev}][{i+1}:v]overlay=0:{H_UI}:enable='between(t,{t0:.3f},{t1:.3f})'[v{i+1}]"
    prev=f"v{i+1}"
# the card scenes: header-colour drawbox must not show on cards -> cards are blue anyway (#1F4788) so it blends.
cmd = ["ffmpeg","-y","-v","error"]+inputs+["-filter_complex",fc,"-map",f"[{prev}]","-r",str(FPS),
       "-c:v","libx264","-preset","slow","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart","-t",f"{dur:.2f}",
       OUT_MP4]
subprocess.run(cmd, check=True)
print("done")
