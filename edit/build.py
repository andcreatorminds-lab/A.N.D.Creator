#!/usr/bin/env python3
"""Builds the setting-spray review edit (1080x1920, 30fps) in the style of the
skincare review template: jump cuts + alternating punch-ins, big lowercase serif
on-screen text, small sans captions, soft warm grade, white flash on scene change.
Edit edit/edit.json (segments, headlines, captions) and re-run."""
import json, subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(here, "edit.json")))
SERIF = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
W, H, FPS = 1080, 1920, 30

def esc(t): return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")

inputs, parts, t0, draw = [], [], 0.0, []
for i, s in enumerate(cfg["segments"]):
    if s["src"] not in inputs: inputs.append(s["src"])
    idx = inputs.index(s["src"]); dur = s["end"] - s["start"]; z = s.get("zoom", 1.0)
    # punch-in: crop toward upper-centre (face), then scale to 1080x1920, fps normalised (iPhone VFR)
    f = (f"[{idx}:v]trim=start={s['start']}:end={s['end']},setpts=PTS-STARTPTS,fps={FPS},"
         f"crop=iw/{z}:ih/{z}:(iw-iw/{z})/2:(ih-ih/{z})*0.25,scale={W}:{H}:flags=lanczos,"
         f"eq=brightness=0.03:saturation=1.08:contrast=1.04,setsar=1")
    if s.get("flash"): f += f",fade=t=in:st=0:d=0.12:color=white"
    f += f"[v{i}]"; parts.append(f)
    parts.append(f"[{idx}:a]atrim=start={s['start']}:end={s['end']},asetpts=PTS-STARTPTS,"
                 f"aresample=48000,afade=t=in:d=0.02,afade=t=out:st={dur-0.04}:d=0.04[a{i}]")
    s["_t0"] = t0; t0 += dur
n = len(cfg["segments"])
parts.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")

def alpha(a, b, fi=0.15, fo=0.15):
    return f"if(lt(t,{a}),0,if(lt(t,{a+fi}),(t-{a})/{fi},if(lt(t,{b-fo}),1,if(lt(t,{b}),({b}-t)/{fo},0))))"

for h in cfg["headlines"]:   # big lowercase serif, template style
    a = h["t"]; b = a + h["dur"]
    for k, line in enumerate(h["lines"]):
        draw.append(f"drawtext=fontfile={SERIF}:text='{esc(line)}':fontsize=118:fontcolor=white:"
                    f"shadowcolor=black@0.55:shadowx=2:shadowy=5:x=(w-text_w)/2:y={h.get('y',1180)+k*125}:"
                    f"alpha='{alpha(a,b)}'")
for c in cfg["captions"]:    # small sans captions, bottom
    a, b = c["t"], c["t"] + c["dur"]
    draw.append(f"drawtext=fontfile={SANS}:text='{esc(c['text'])}':fontsize=52:fontcolor=white:"
                f"box=1:boxcolor=black@0.28:boxborderw=18:x=(w-text_w)/2:y=1560:"
                f"enable='between(t,{a},{b})'")
for tg in cfg.get("tags", []):
    draw.append(f"drawtext=fontfile={SANS}:text='{esc(tg['text'])}':fontsize=34:fontcolor=white@0.9:"
                f"x=(w-text_w)/2:y={tg['y']}:enable='between(t,{tg['t']},{tg['t']+tg['dur']})'")
parts.append(f"[vc]{','.join(draw)}[vout]")

cmd = ["ffmpeg", "-v", "error", "-y"]
for p in inputs: cmd += ["-i", p]
cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[ac]",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cfg["out"]]
subprocess.run(cmd, check=True); print("wrote", cfg["out"], "length", round(t0, 2), "s")
