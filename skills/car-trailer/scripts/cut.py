"""Cut a car how-to export into a trailer or a Short from a spec file.

    python3 -I cut.py <spec.json>

Reads the finished export (never writes next to it). Writes, beside the spec:
work/seg_*.mp4, work/picture.mp4 (silent, framed to the spec's size), work/voice.wav,
work/mix.wav (the host's lines + the music bed ducked under them, loudness-normalised), and
cues.json (every shot and every caption word in output seconds) for type_layer.py.
"""
import json, os, subprocess, sys

def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg failed:\n" + r.stderr[-3000:])

def rate(s):
    a, _, b = str(s).partition("/")
    return float(a) / float(b or 1)

def main(spec_path):
    spec_path = os.path.abspath(spec_path)
    here = os.path.dirname(spec_path)
    spec = json.load(open(spec_path))
    rel = lambda p: p if os.path.isabs(p) else os.path.normpath(os.path.join(here, p))
    src_file, ff = spec["source"], rel(spec["ffmpeg"])
    W, H, FPS = spec["width"], spec["height"], rate(spec.get("fps", "30000/1001"))
    work = os.path.join(here, "work"); os.makedirs(work, exist_ok=True)
    bed = spec["bed"]
    beats = json.load(open(rel(bed["beats"])))
    # Output beat times for the bed as played: each [from, to) beat range follows the last.
    out_beats, t0 = [], 0.0
    for a, b in bed["play"]:
        b = len(beats) if b is None else b
        out_beats += [t0 + (x - beats[a]) for x in beats[a:b]]
        t0 += (beats[b] if b < len(beats) else beats[-1]) - beats[a]
    frame = lambda t: round(t * FPS)

    def framing(fr, dur):
        """Filter that turns a 16:9 source picture into W x H."""
        mode = fr.get("mode", "full")
        if mode == "full":
            return f"scale={W}:{H}:flags=lanczos,setsar=1"
        c0 = fr.get("center", 0.5); c1 = fr.get("pan_to", c0)
        cx = f"({c0}+({c1}-{c0})*t/{dur:.4f})"
        if mode == "crop":
            z = fr.get("zoom", 1.0)
            return (f"crop=w='ih*{W}/{H}/{z}':h='ih/{z}':x='clip({cx}*iw-ow/2,0,iw-ow)':y='(ih-oh)/2',"
                    f"scale={W}:{H}:flags=lanczos,setsar=1")
        if mode == "fit":
            z = fr.get("zoom", 1.0)
            fw = round(W * z / 2) * 2
            return (f"split[fa][fb];[fa]scale=-2:{H},crop={W}:{H},gblur=sigma=40,eq=brightness=-0.12:saturation=0.8[bg];"
                    f"[fb]scale={fw}:-2:flags=lanczos,crop=w='min(iw,{W})':h=ih:x='clip({cx}*iw-ow/2,0,iw-ow)':y=0[fg];"
                    f"[bg][fg]overlay=x=(W-w)/2:y=(H-h)/2,setsar=1")
        sys.exit(f"unknown frame mode {mode}")

    cues, segs, vox = [], [], []
    t = 0.0
    for i, sh in enumerate(spec["shots"]):
        kind, speed = sh["kind"], sh.get("speed", 1)
        spans = [list(s) for s in sh.get("src", [])]
        min_s = sh.get("min", 0)
        if kind in ("voice", "last"):
            min_s = max(min_s, sum(b - a for a, b in spans))
        if kind == "last":
            end_t = t + min_s  # the end-card freeze hides this seam
        else:
            end_t = next((b for b in out_beats if b >= t + min_s - 1e-6), None)
            if end_t is None:
                sys.exit(f"shot {i}: the bed runs out of beats at {t:.2f}s; add a later range to bed.play")
        f0, f1 = frame(t), frame(end_t)
        nfr, dur = f1 - f0, (f1 - f0) / FPS
        seg, wav = os.path.join(work, f"seg_{i:02d}.mp4"), os.path.join(work, f"vox_{i:02d}.wav")
        if kind == "end":
            last_png = os.path.join(work, "last.png")
            run([ff, "-y", "-loglevel", "error", "-sseof", "-0.1", "-i", segs[-1], "-frames:v", "1", last_png])
            run([ff, "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", last_png,
                 "-frames:v", str(nfr), "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", seg])
            run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{dur:.6f}", wav])
            pic = []
        else:
            if kind == "pic":
                pic = [(spans[-1][0], spans[-1][0] + dur * speed)]
            else:
                # The last span's picture runs on to fill the slot; the host's sound stops at its out point.
                head = sum(b - a for a, b in spans[:-1])
                pic = [tuple(s) for s in spans[:-1]] + [(spans[-1][0], spans[-1][0] + dur - head)]
            ins, vf, af = [], [], []
            for k, (a, b) in enumerate(pic):
                ins += ["-ss", f"{a:.4f}", "-t", f"{b - a + 0.2:.4f}", "-i", src_file]
                say = (spans[k][1] - a) if kind != "pic" else (b - a)
                vf.append(f"[{k}:v]trim=duration={b - a:.4f},setpts=PTS-STARTPTS[v{k}]")
                af.append(f"[{k}:a]atrim=duration={b - a:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,"
                          f"afade=t=out:st={max(say - 0.06, 0):.4f}:d=0.06[a{k}]")
            m = len(pic)
            g = ";".join(vf + af) + ";" + "".join(f"[v{k}][a{k}]" for k in range(m)) + f"concat=n={m}:v=1:a=1[cv][ca]"
            g += f";[cv]setpts=PTS/{speed},fps={FPS:.6f},trim=end_frame={nfr},setpts=PTS-STARTPTS,{framing(sh.get('frame', {}), dur)}[vo]"
            g += f";[ca]aresample=48000,{'volume=0,' if kind == 'pic' else ''}apad,atrim=duration={dur:.6f}[ao]"
            run([ff, "-y", "-loglevel", "error", *ins, "-filter_complex", g,
                 "-map", "[vo]", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", "-an", seg,
                 "-map", "[ao]", "-ac", "2", wav])
        segs.append(seg); vox.append(wav)

        def to_out(ts):
            acc = 0.0
            for a, b in spans:
                if a - 0.05 <= ts <= b + 0.05:
                    return f0 / FPS + acc + (ts - a)
                acc += b - a
            sys.exit(f"shot {i}: word at {ts} is outside its spans {spans}")
        words, ws = [], sh.get("words", [])
        for k, w in enumerate(ws):
            s = to_out(w[1])
            e = to_out(w[2]) if len(w) > 2 else to_out(ws[k + 1][1])
            words.append([w[0], round(s, 3), round(e, 3)])
        cues.append(dict(i=i, kind="voice" if kind == "last" else kind, start=round(f0 / FPS, 4), duration=round(dur, 4),
                         speed=speed, src=[[round(a, 3), round(b, 3)] for a, b in (spans if kind != "pic" else pic)],
                         label=sh.get("label", {}), words=words, hot=sh.get("hot", [])))
        print(f"{i:02d} {kind:5s} t={f0 / FPS:6.2f} dur={dur:5.2f} x{speed} {sh.get('label', {}).get('main', '')}")
        t = f1 / FPS
    total = t
    lst = os.path.join(work, "list.txt")
    open(lst, "w").writelines(f"file '{s}'\n" for s in segs)
    run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(work, "picture.mp4")])
    vl = os.path.join(work, "vlist.txt")
    open(vl, "w").writelines(f"file '{w}'\n" for w in vox)
    run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", vl, "-c:a", "pcm_s16le", os.path.join(work, "voice.wav")])

    # Bed: the beat ranges in order, joined by short crossfades that land on the beat, ducked under the host's voice.
    xf = bed.get("xfade", 0.2)
    ins, g, labels = [], [], []
    for k, (a, b) in enumerate(bed["play"]):
        ins += ["-i", rel(bed["file"])]
        start = beats[a] - (xf if k else 0)
        end = f":end={beats[b]:.4f}" if b is not None and b < len(beats) else ""
        g.append(f"[{k}:a]atrim=start={start:.4f}{end},asetpts=PTS-STARTPTS[p{k}]")
        labels.append(f"p{k}")
    cur = labels[0]
    for k in range(1, len(labels)):
        g.append(f"[{cur}][{labels[k]}]acrossfade=d={xf}:c1=tri:c2=tri[x{k}]"); cur = f"x{k}"
    n = len(labels)
    g.append(f"[{cur}]atrim=duration={total:.4f},afade=t=out:st={total - 1.8:.3f}:d=1.8,aresample=48000,volume={bed.get('gain_db', -3)}dB[bed]")
    g.append(f"[{n}:a]asplit[v1][v2]")
    g.append("[bed][v1]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350:makeup=1[duck]")
    g.append(f"[duck][v2]amix=inputs=2:normalize=0,loudnorm=I={bed.get('lufs', -14)}:TP=-1.5:LRA=9[out]")
    run([ff, "-y", "-loglevel", "error", *ins, "-i", os.path.join(work, "voice.wav"), "-filter_complex", ";".join(g),
         "-map", "[out]", "-ar", "48000", "-ac", "2", os.path.join(work, "mix.wav")])
    json.dump(dict(total=round(total, 4), fps=spec.get("fps", "30000/1001"), width=W, height=H,
                   layout=spec.get("layout", "landscape" if W >= H else "portrait"), end_card=spec.get("end_card", {}),
                   shots=cues), open(os.path.join(here, "cues.json"), "w"), indent=1)
    print("total", round(total, 3))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from lint import lint
    problems = lint(spec_path)
    for p in problems:
        print("LINT", p)
    if problems:
        sys.exit(f"lint: {len(problems)} problem(s). The cut is written, but fix the spec and re-cut before the type layer.")
    print("lint: ok")

if __name__ == "__main__":
    main(sys.argv[1])
