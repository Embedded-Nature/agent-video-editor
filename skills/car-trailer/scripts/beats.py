"""Detect every beat of a music bed and save it next to the track.

    uv run --no-project --python 3.12 --with librosa python -I beats.py <track> [out.json]

Writes <track minus extension>.beats.json (a list of beat times in seconds) and prints the
tempo, the tempo per 15 s window (so a drifting track shows up) and the loudness per 5 s
(so a quiet stretch to jump over shows up).
"""
import json, os, sys
import librosa, numpy as np

track = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(track)[0] + ".beats.json"
y, sr = librosa.load(track)
oenv = librosa.onset.onset_strength(y=y, sr=sr)
tempo, frames = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, tightness=400)
bt = librosa.frames_to_time(frames, sr=sr)
json.dump([round(float(x), 4) for x in bt], open(out, "w"))
print(f"tempo {float(np.atleast_1d(tempo)[0]):.1f} BPM, {len(bt)} beats, first at {bt[0]:.2f}s -> {out}")
d = np.diff(bt)
for a in range(0, int(bt[-1]), 15):
    m = (bt[:-1] >= a) & (bt[:-1] < a + 15)
    if m.any():
        print(f"  {a:3d}-{a + 15:3d}s  {60 / np.median(d[m]):6.1f} BPM  beats {int(np.argmax(m))}..")
rms = librosa.feature.rms(y=y)[0]; tt = librosa.times_like(rms, sr=sr)
print("loudness per 5 s (dBFS):", " ".join(f"{a}:{20 * np.log10(rms[(tt >= a) & (tt < a + 5)].mean() + 1e-9):.0f}" for a in range(0, int(tt[-1]), 5)))
