# spec.json

Paths are relative to the spec file unless absolute. `cut.py` writes `work/` and `cues.json` beside it.

```json
{
  "source": "/abs/path/to/finished export.mov",
  "ffmpeg": "../../.tools/bin/ffmpeg",
  "width": 1080, "height": 1920, "fps": "30000/1001",
  "layout": "portrait",
  "bed": {
    "file": "../../music/track.mp3",
    "beats": "../../music/track.beats.json",
    "play": [[0, 96], [144, null]],
    "xfade": 0.2, "gain_db": 0, "lufs": -14
  },
  "end_card": {"kicker": "2017 PANAMERA TURBO", "title": "FULL HOW-TO ON THE CHANNEL", "line": "NEXT UP:", "accent": "SECONDARY CATS"},
  "steps": [
    {"name": "Wheels off", "src": [150, 240]},
    {"name": "Plastic shrouds off", "src": [40, 150], "skip": "Short: cut for time"}
  ],
  "shots": [ ... ]
}
```

- `ffmpeg`: any build works for cutting; one with `drawtext` helps for labelled contact sheets.
- `layout`: `landscape` (labels top-left, captions low) or `portrait` (everything inside the Shorts/Reels/TikTok safe band). Defaults from the aspect.
- `bed.play`: beat-index ranges `[from, to)` played in order; `null` = to the end. Each join is a `xfade`-second crossfade that lands on the beat. Use it to skip a quiet stretch: jump on a 16-beat boundary.
- `steps`: every step of the job in how-to order, each with the source range `[from, to)` in seconds where it happens. `lint.py` fails if a step has no shot whose source starts inside its range, unless it has a `skip` reason (Shorts only, in practice).
- `bed.gain_db`: bed level before ducking. `lufs`: final loudness (−14 for YouTube).

## A shot

```json
{
  "kind": "voice",
  "src": [[387.80, 389.25], [390.25, 391.36]],
  "min": 0, "speed": 1,
  "frame": {"mode": "crop", "center": 0.62, "pan_to": 0.42, "zoom": 1.0},
  "label": {"kicker": "STEP 4", "main": "BUMPER OFF", "sub": "", "flash": true, "hook": false},
  "words": [["Honestly", 387.82], ["if", 388.22], ["it...", 388.98, 389.22], ["it", 390.30], ["off", 390.98, 391.28]],
  "hot": ["wiggle", "off"]
}
```

| field | meaning |
| --- | --- |
| `kind` | `voice`: the host's words at 1x, `src` spans are exact `[in, out]` and are joined; the last span's picture runs on (muted) to the beat. `pic`: muted picture, `src` is `[[in, null]]` and runs as long as the slot × `speed`. `last`: the final voice shot; it ends exactly where the host's words end (the end card's freeze hides the seam). `end`: freeze of the last frame under the end card; only `min`. |
| `min` | shortest the shot may be, in seconds; it ends on the first bed beat at or after that. Voice shots are at least their spans. |
| `speed` | picture speed for `pic` shots (2, 3, 4, 6). |
| `frame.mode` | `full` (scale to the output), `crop` (a W:H window; `center` 0-1 across the source, `pan_to` moves it over the shot, `zoom` > 1 crops tighter), `fit` (whole frame scaled to the width × `zoom`, over a blurred, darkened fill; `center` picks the window when `zoom` > 1). |
| `label` | `kicker` (yellow chip), `main` (big line), `sub` (small italic spec line). `flash`: white flash on the cut (use on the 1-2 biggest moments). `hook`: already on screen at the shot's first frame (the Short's opener). |
| `words` | `[text, start]` or `[text, start, end]` in source seconds (last word of a run needs `end`). Captions break at 3 words, a 150 ms pause, or `...` `,` `.` |
| `hot` | caption words shown in yellow (compared lowercase, punctuation stripped). |
