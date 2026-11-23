"""Write the HyperFrames type layer (labels, captions, progress bar, punch-ins, end card) from cues.json.

    python3 -I type_layer.py <cues.json> <hyperframes project dir>

The project dir must already exist (`hyperframes init <dir> --skip-skills`). This replaces its
index.html and compositions/{labels,captions,endcard}.html, and copies picture.mp4, mix.wav and
the Anton font into assets/.
"""
import html, json, os, shutil, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = lambda x: f"{x:.3f}"
E = html.escape

LAYOUT = {
    # Landscape: labels top-left, captions low centre.
    "landscape": dict(
        label="left:110px; top:120px; width:1300px; text-align:left;", origin="0 50%",
        kick=44, main=120, sub=44, cap="left:0; right:0; bottom:110px;", cap_size=96, cap_w=1600,
        end_top=300, end_t=150, end_s=46, exit_x=-60, end_lr=120, pop=1.35),
    # Portrait (1080x1920): everything inside the Shorts/Reels/TikTok safe band, y 288-1248, x 120-888.
    "portrait": dict(
        label="left:120px; top:300px; width:768px; text-align:center;", origin="50% 50%",
        kick=46, main=104, sub=46, cap="left:120px; width:768px; bottom:720px;", cap_size=92, cap_w=768,
        end_top=620, end_t=118, end_s=40, exit_x=0, end_lr=192, pop=1.12),
}

def main(cues_path, hf):
    c = json.load(open(cues_path))
    work = os.path.join(os.path.dirname(os.path.abspath(cues_path)), "work")
    W, H, total, L = c["width"], c["height"], c["total"], LAYOUT[c["layout"]]
    shots = c["shots"]
    end = shots[-1]
    os.makedirs(os.path.join(hf, "compositions"), exist_ok=True)
    os.makedirs(os.path.join(hf, "assets", "fonts"), exist_ok=True)
    for f in ("picture.mp4", "mix.wav"):
        shutil.copy(os.path.join(work, f), os.path.join(hf, "assets", f))
    shutil.copy(os.path.join(SKILL, "assets", "fonts", "Anton-Regular.ttf"), os.path.join(hf, "assets", "fonts"))
    face = '@font-face { font-family: "Anton"; src: url("assets/fonts/Anton-Regular.ttf"); }'
    stroke = "-webkit-text-stroke:{w}px #0b0b0b; paint-order:stroke fill;"

    # ---------- labels ----------
    lh, lj = [], []
    for s in shots:
        lab = s.get("label") or {}
        if s["kind"] == "end" or not lab.get("main"):
            continue
        i, st, du = s["i"], s["start"], s["duration"]
        sub = f'<div class="sub" id="lab{i}-sub">{E(lab["sub"])}</div>' if lab.get("sub") else ""
        kick = f'<div class="kicker" id="lab{i}-k">{E(lab["kicker"])}</div>' if lab.get("kicker") else ""
        lh.append(f'<div id="lab{i}" class="clip label" data-start="{R(st)}" data-duration="{R(du)}" data-track-index="1">'
                  f'<div class="tilt" id="lab{i}-in">{kick}<div class="main" id="lab{i}-m">{E(lab["main"])}</div>{sub}</div></div>')
        if not lab.get("hook"):  # a hook is already on screen at its first frame: it is the thumbnail
            if kick:
                lj.append(f'tl.fromTo("#lab{i}-k",{{scale:0.4,opacity:0,rotation:-8}},{{scale:1,opacity:1,rotation:0,duration:0.32,ease:"back.out(2.2)"}},{R(st + 0.02)});')
            lj.append(f'tl.fromTo("#lab{i}-m",{{scale:{L["pop"]},opacity:0,filter:"blur(10px)"}},{{scale:1,opacity:1,filter:"blur(0px)",duration:0.26,ease:"expo.out"}},{R(st + 0.08)});')
            if sub:
                lj.append(f'tl.fromTo("#lab{i}-sub",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.22,ease:"power3.out"}},{R(st + 0.3)});')
        lj.append(f'tl.to("#lab{i}-in",{{opacity:0,x:{L["exit_x"]},filter:"blur(6px)",duration:0.12,ease:"power3.in"}},{R(st + du - 0.13)});')
    labels = f'''<template>
<style>
{face}
#root {{ position:absolute; inset:0; }}
.label {{ position:absolute; {L["label"]} }}
.tilt {{ transform-origin:{L["origin"]}; }}
.kicker {{ display:inline-block; background:#FFD400; color:#0b0b0b; font-family:"Anton"; font-size:{L["kick"]}px; letter-spacing:0.04em;
  padding:4px 18px 2px; border-radius:6px; box-shadow:0 6px 0 #0b0b0b; }}
.main {{ font-family:"Anton"; font-size:{L["main"]}px; line-height:1.02; color:#fff; margin-top:14px; letter-spacing:0.01em; transform-origin:{L["origin"]};
  {stroke.format(w=10)} text-shadow:0 8px 0 #0b0b0b, 0 14px 30px rgba(0,0,0,.55); }}
.sub {{ font-family:"Inter"; font-weight:900; font-style:italic; font-size:{L["sub"]}px; color:#fff; margin-top:8px;
  {stroke.format(w=6)} text-shadow:0 5px 0 #0b0b0b; }}
</style>
<div id="root" data-composition-id="labels" data-width="{W}" data-height="{H}">
{chr(10).join(lh)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(lj)}
window.__timelines["labels"] = tl;
</script>
</template>'''
    open(os.path.join(hf, "compositions", "labels.html"), "w").write(labels)

    # ---------- captions: 2-3 words, broken at a pause, a span seam or punctuation ----------
    groups = []
    for s in shots:
        hot = set(s.get("hot", []))
        cur = []
        for k, (txt, ws, we) in enumerate(s.get("words", [])):
            if cur and (len(cur) == 3 or ws - cur[-1][2] > 0.15 or cur[-1][0].endswith(("...", ",", "."))):
                groups.append(cur); cur = []
            cur.append((txt, ws, we, txt.strip(".,?!").lower() in hot))
        if cur:
            groups.append(cur)
    ch, cj = [], []
    for g, words in enumerate(groups):
        gs, ge = max(words[0][1] - 0.06, 0.02), words[-1][2] + 0.12
        if g + 1 < len(groups):
            ge = min(ge, groups[g + 1][0][1] - 0.06)
        spans = "".join(f'<span class="w{" hot" if h else ""}" id="c{g}w{k}">{E(t.upper())}</span> ' for k, (t, _, _, h) in enumerate(words))
        ch.append(f'<div id="cap{g}" class="clip cap" data-start="{R(gs)}" data-duration="{R(ge - gs)}" data-track-index="1"><div class="line" id="cap{g}-l">{spans}</div></div>')
        cj.append(f'tl.fromTo("#cap{g}-l",{{scale:0.7,y:30}},{{scale:1,y:0,duration:0.2,ease:"back.out(2.5)"}},{R(gs)});')
        for k, (t, ws, _, _) in enumerate(words):
            cj.append(f'tl.fromTo("#c{g}w{k}",{{opacity:0.35}},{{opacity:1,duration:0.06}},{R(max(ws, gs))});')
    captions = f'''<template>
<style>
{face}
#root {{ position:absolute; inset:0; }}
.cap {{ position:absolute; {L["cap"]} text-align:center; overflow:visible; }}
.line {{ display:inline-block; max-width:{L["cap_w"]}px; font-family:"Anton"; font-size:{L["cap_size"]}px; line-height:1.05; color:#fff; letter-spacing:0.01em;
  {stroke.format(w=10)} text-shadow:0 7px 0 #0b0b0b, 0 12px 26px rgba(0,0,0,.5); }}
.w.hot {{ color:#FFD400; }}
</style>
<div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
{chr(10).join(ch)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(cj)}
window.__timelines["captions"] = tl;
</script>
</template>'''
    open(os.path.join(hf, "compositions", "captions.html"), "w").write(captions)

    # ---------- end card ----------
    ec = c.get("end_card") or {}
    kicker, title = ec.get("kicker", ""), ec.get("title", "WATCH THE FULL HOW-TO")
    line = ec.get("line", "")
    accent = ec.get("accent", "")
    sub_html = E(line) + (f' <b>{E(accent)}</b>' if accent else "")
    endcard = f'''<template>
<style>
{face}
#root {{ position:absolute; inset:0; }}
#end-dim {{ position:absolute; inset:0; background:#0b0b0b; }}
#end-box {{ position:absolute; left:{L.get("end_lr",120)}px; right:{L.get("end_lr",120)}px; top:{L["end_top"]}px; text-align:center; }}
#end-k {{ display:inline-block; background:#FFD400; color:#0b0b0b; font-family:"Anton"; font-size:52px; padding:6px 24px 4px; border-radius:8px; letter-spacing:0.04em; }}
#end-t {{ font-family:"Anton"; font-size:{L["end_t"]}px; color:#fff; line-height:1.05; margin-top:22px; }}
#end-s {{ font-family:"Inter"; font-weight:900; font-size:{L["end_s"]}px; color:#fff; margin-top:18px; letter-spacing:0.02em; }}
#end-s b {{ color:#FFD400; }}
</style>
<div id="root" data-composition-id="endcard" data-width="{W}" data-height="{H}">
  <div id="end-dim"></div>
  <div id="end-box">
    <div id="end-k" data-var-text="end_kicker">{E(kicker)}</div>
    <div id="end-t" data-var-text="end_title">{E(title)}</div>
    <div id="end-s">{sub_html}</div>
  </div>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
tl.fromTo("#end-dim",{{opacity:0}},{{opacity:0.72,duration:0.25,ease:"power2.out"}},0);
tl.fromTo("#end-k",{{scale:0.4,opacity:0}},{{scale:1,opacity:1,duration:0.3,ease:"back.out(2.2)"}},0.05);
tl.fromTo("#end-t",{{scale:1.3,opacity:0,filter:"blur(10px)"}},{{scale:1,opacity:1,filter:"blur(0px)",duration:0.3,ease:"expo.out"}},0.15);
tl.fromTo("#end-s",{{opacity:0,y:24}},{{opacity:1,y:0,duration:0.25,ease:"power3.out"}},0.4);
window.__timelines["endcard"] = tl;
</script>
</template>'''
    open(os.path.join(hf, "compositions", "endcard.html"), "w").write(endcard)

    # ---------- root ----------
    cuts = "\n".join(f'tl.fromTo("#frame",{{scale:1.10}},{{scale:1,duration:0.35,ease:"expo.out"}},{R(s["start"])});' for s in shots[1:-1])
    flash = "\n".join(f'tl.fromTo("#flash",{{opacity:0.85}},{{opacity:0,duration:0.18,ease:"power2.out"}},{R(s["start"])});'
                      for s in shots if (s.get("label") or {}).get("flash"))
    vars_ = json.dumps([{"id": "end_title", "type": "string", "label": "End card title", "default": title},
                        {"id": "end_kicker", "type": "string", "label": "End card kicker", "default": kicker}])
    index = f'''<!doctype html>
<html lang="en" data-composition-variables='{E(vars_, quote=True)}'>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{W}px; height:{H}px; overflow:hidden; background:#000; }}
#root {{ position:relative; width:100%; height:100%; overflow:hidden; }}
#frame {{ position:absolute; inset:0; }}
#cut {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; object-fit:cover; }}
#flash {{ position:absolute; inset:0; background:#fff; opacity:0; z-index:5; pointer-events:none; }}
#bar-track {{ position:absolute; left:0; right:0; top:0; height:12px; background:rgba(0,0,0,.45); z-index:6; }}
#bar {{ position:absolute; left:0; top:0; height:12px; width:{W}px; background:#FFD400; transform-origin:0 50%; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{R(total)}" data-width="{W}" data-height="{H}">
  <div id="frame">
    <video id="cut" class="clip" src="assets/picture.mp4" data-start="0" data-duration="{R(total)}" data-track-index="0" muted playsinline></video>
  </div>
  <audio id="mix" class="clip" src="assets/mix.wav" data-start="0" data-duration="{R(total)}" data-track-index="4" data-volume="1"></audio>
  <div id="flash"></div>
  <div id="bar-track" data-layout-ignore><div id="bar"></div></div>
  <div id="labels" data-composition-id="labels" data-composition-src="compositions/labels.html" data-start="0" data-duration="{R(end["start"])}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:7"></div>
  <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{R(end["start"])}" data-track-index="2" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:8"></div>
  <div id="endcard" data-composition-id="endcard" data-composition-src="compositions/endcard.html" data-start="{R(end["start"])}" data-duration="{R(end["duration"])}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:9"></div>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
tl.set("#frame",{{scale:1}},0);
tl.set("#flash",{{opacity:0}},0);
tl.fromTo("#bar",{{scaleX:0}},{{scaleX:1,duration:{R(end["start"])},ease:"none"}},0);
{cuts}
{flash}
window.__timelines["main"] = tl;
</script>
</body>
</html>'''
    open(os.path.join(hf, "index.html"), "w").write(index)
    print(f"{len(groups)} caption groups, {len(lh)} labels -> {hf}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
