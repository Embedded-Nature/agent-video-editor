"""Check a cut against the rules that keep it from playing like a pile of clips.

    python3 -I lint.py <spec.json>          (reads cues.json beside it; cut.py runs this itself)

Exits 1 with one line per problem. Fix the spec and re-cut; don't loosen the limits to pass.

What it checks:
- coverage: the spec's `steps` (every step of the job, in order, with the source range where it
  happens) each have a shot whose source starts inside that range, unless the step says `skip`
  with a reason (a Short may drop a step; a trailer should not).
- order: shot sources start in how-to order.
- labels: every shot but the end card has a kicker and a main line; no two shots in a row carry
  the same main line; `STEP n` kickers count 1, 2, 3 ... with no gaps.
- pace: no voice shot over 4.0 s, no picture shot over 2.7 s (2.3 s in a Short); the host's lines are
  at most half the running time; 4-7 voice shots; at least 16 shots in a trailer, 14 in a Short.
"""
import json, os, re, sys

LIMITS = {
    "landscape": dict(voice_max=4.0, pic_max=2.7, min_shots=16),
    "portrait": dict(voice_max=4.0, pic_max=2.3, min_shots=14),
}

def lint(spec_path):
    here = os.path.dirname(os.path.abspath(spec_path))
    spec = json.load(open(spec_path))
    cues = json.load(open(os.path.join(here, "cues.json")))
    lim = LIMITS[cues.get("layout", "landscape")]
    shots = [s for s in cues["shots"] if s["kind"] != "end"]
    errs = []

    steps = spec.get("steps")
    if not steps or len(steps) < 3:
        errs.append("spec has no `steps`: list every step of the job in order, each with its source range "
                    "(from the chapters / edit list / frames), before writing shots")
    else:
        for k, st in enumerate(steps):
            a, b = st["src"]
            if k and a < steps[k - 1]["src"][0]:
                errs.append(f"step '{st['name']}' starts before the step above it")
            hit = [s["i"] for s in shots if s["src"] and a <= s["src"][0][0] < b]
            if not hit and not st.get("skip"):
                errs.append(f"step '{st['name']}' ({a}-{b} s) has no shot: add one, or give it a `skip` reason")

    starts = [(s["i"], s["src"][0][0]) for s in shots if s["src"]]
    for (i0, a0), (i1, a1) in zip(starts, starts[1:]):
        if a1 < a0:
            errs.append(f"shot {i1} ({a1} s) comes from before shot {i0} ({a0} s): out of how-to order")

    n_step = 0
    prev_main = None
    for s in shots:
        lab = s.get("label") or {}
        if not lab.get("kicker") or not lab.get("main"):
            errs.append(f"shot {s['i']} is missing a kicker or a main line")
        if lab.get("main") and lab.get("main") == prev_main:
            errs.append(f"shot {s['i']} repeats the main line of the shot before it: '{lab['main']}'")
        prev_main = lab.get("main")
        m = re.fullmatch(r"STEP\s+(\d+)", (lab.get("kicker") or "").strip().upper())
        if m:
            n = int(m.group(1))
            if n != n_step + 1:
                errs.append(f"shot {s['i']} is STEP {n} but the last step label was STEP {n_step}")
            n_step = n
        d = s["duration"]
        if s["kind"] == "voice" and d > lim["voice_max"] + 0.05:
            errs.append(f"shot {s['i']} is a {d:.1f} s voice shot (max {lim['voice_max']}): use a shorter line or trim words")
        if s["kind"] == "pic" and d > lim["pic_max"] + 0.05:
            errs.append(f"shot {s['i']} is a {d:.1f} s picture shot (max {lim['pic_max']}): lower its `min` or raise `speed`")

    voice = [s for s in shots if s["kind"] == "voice"]
    share = sum(s["duration"] for s in voice) / cues["total"]
    if share > 0.5:
        errs.append(f"the host's lines fill {share:.0%} of the running time (max 50%): cut lines, show more steps")
    if not 4 <= len(voice) <= 7:
        errs.append(f"{len(voice)} voice shots (want 4-7)")
    if len(shots) < lim["min_shots"]:
        errs.append(f"{len(shots)} shots before the end card (want at least {lim['min_shots']}): a step is probably missing")
    return errs

if __name__ == "__main__":
    problems = lint(sys.argv[1])
    for p in problems:
        print("LINT", p)
    print("lint: ok" if not problems else f"lint: {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)
