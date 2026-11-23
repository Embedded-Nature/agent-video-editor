---
name: car-trailer
description: >-
  Cut a short promo from a finished car how-to export: a 16:9 YouTube trailer, a 9:16 Short / Reel /
  TikTok, or both. Shots run in how-to order, every shot carries a label naming what is on screen,
  the host's own lines play at 1x with word-by-word captions, and every cut lands on a beat of a licensed
  music bed. Use when asked for a trailer, teaser, promo, Short, Reel or TikTok of a car DIY / how-to
  video, or to make one "fun" or "viral".
license: MIT (code and text); SIL OFL 1.1 (assets/fonts/Anton-Regular.ttf, see assets/fonts/OFL.txt; assets/fonts/Michroma-Regular.ttf, see assets/fonts/OFL-Michroma.txt)
compatibility: >
  Python 3 and ffmpeg on the PATH (an ffmpeg with drawtext helps for labelled contact sheets). uv runs the
  helpers that need numpy/scipy/soundfile (make_beat.py), librosa (beats.py) or mlx-whisper (words.py, Apple
  silicon), and numpy/scipy/pillow (grade.py, cover.py). The type layer and render need HyperFrames and its skills.
metadata:
  author: Embedded-Nature
  version: "1.1.0"
---

# Car trailer and Short

One engine makes both formats from a spec file:

- `scripts/cut.py <spec.json>`: cuts the export, frames it (16:9 full, or 9:16 crop / pan / fit), mixes the host's lines over the bed, writes `cues.json`.
- `scripts/type_layer.py <cues.json> <hf dir>`: writes the HyperFrames type layer (labels, captions, progress bar, punch-ins, flashes, end card).
- `scripts/lint.py <spec.json>`: coverage, order, labels and pace (`cut.py` runs it after every cut and fails on any problem).
- `scripts/make_beat.py`: an original drift-phonk bed with an exact beat grid. `scripts/beats.py`: the beat map of any other track. `scripts/words.py`: word timings for the host's lines.
- `scripts/grade.py`: the look (black and white with one colour kept, crushed blacks, vignette, grain) on the bare picture, before the type. `scripts/cover.py`: the Short's cover in the same look, with the brand's logo and the car as the headline.
- `references/posting.md`: the title, description, tags and upload settings for a Short, with a template.
- Spec fields and framing modes: `references/spec.md`. Worked example (one trailer and one Short of the same job, a Porsche Panamera air-filter swap): `references/examples/trailer.json` and `references/examples/short.json`. Read them for the shape of a spec; don't copy their shots or labels.

Load the `hyperframes` skill before touching the type layer (its contract, check and render) and run its CLI the way that skill says (`npx hyperframes <command>`, or its plugin launcher), from inside the HyperFrames project.

## What a rejected cut looked like

A cut was turned down because the shots were out of order and nothing said what the viewer was looking at; it "played like a pile of clips." Every rule below exists to stop that.

A later cut made with this skill was "close but not as clean cut" and "the details are missing": 12 shots instead of 22, two 5 s talking shots up front, the host's lines filling 70% of the running time, half the job's steps (shrouds, wheels, lights, clips, bumper back on, wheels on) never shown, three shots in a row of the same bench angle, and an orchestral bed. Rules 3a and 5a and `lint.py` exist to stop that.

## Non-negotiables

1. **Read the how-to before cutting.** The transcript, the `.srt`, `YOUTUBE.md` (chapters are the order of the job) and the description. Then look at frames: one every 3 s across the whole export, one every 2 s where a step is unclear. The transcript finds lines; frames decide shots.
2. **How-to order.** Every shot's source time is later than the one before it. No teaser pulled from the end. The hook is the first shot with a bold line over it, not a flash-forward.
3. **Every shot is labelled** with what is on screen: `STEP n` + the action (`UNPLUG THE LIGHTS`), a spec as the sub-line (`M30 + T30s`, `five T20s`), `PRO TIP`, `WHY SWITCH`, `DONE`, `NEXT UP`. Labels say only what the footage and transcript show; no invented claims or specs.
3a. **Every step of the job gets a shot.** Before any shot, write the spec's `steps`: every step in order with the source range where it happens (from the chapters, the edit list and the frames). The cut shows each one; a Short may drop a step only with a `skip` reason. `STEP n` labels count 1, 2, 3 with no gaps; extras between steps are `PRO TIP`, `WAIT...`, `THE FIX`, `WHY SWITCH`. Open on the car and the part (what this video is about), end on the car buttoned up. Don't spend two shots on the same angle back to back.
4. **Readable.** HyperFrames `check` flags `line_unread`: fix every one by shortening the label or raising that shot's `min`, never by ignoring it. Two to four words in the main line.
5. **The host's voice at 1x, captioned.** Pick 4-7 short lines that carry the story (the surprise, the problem, the tip, the payoff, the sign-off). Get word times with `scripts/words.py`; cut on word boundaries; never mid-word. Whisper stretches a word over the pause after it: trim span edges with ffmpeg `silencedetect` (-35 dB). Measure each line in the export (`volumedetect`): one more than about 6 dB under the host's other lines (around −21 dB mean) vanishes under the beat, so pick another line; Whisper will happily transcribe a mumble. Captions are 2-3 words, key words in yellow.
5a. **Pace: the pictures carry it, the host's lines punctuate it.** Picture shots 1.7-2.6 s in a trailer (1.5-2.2 s in a Short), sped up 2-6x when the action is long. Voice shots 1.5-4 s: one short sentence, trimmed on word boundaries (join two spans to drop the middle), never a whole paragraph. The host's lines fill at most half the running time. A 45-60 s trailer is about 20 shots; a 35-45 s Short about 16.
6. **Sped-up spans are muted** (4x / 6x picture, the music carries them); fast-forwarded audio sounds broken.
7. **Every cut on a beat** of the bed (`cut.py` snaps each shot to the next detected beat after its `min`).
8. **Music must be licensed for the upload and fit the channel.** Read the license next to the track. A non-commercial bed (e.g. MusicGen CC BY-NC) is audition-only for a monetized channel: say so. Car channels usually want an underground car sound (drift phonk / trap: 808 bass, cowbell, rap drums, a little synth and lo-fi grit), not orchestral or organ; the channel this was built for rejected an orchestral CC0 bed. Don't pick a bed because it already has a beat map; ask what the channel sounds like. Free CC0 libraries have almost none of that. Use a track the person supplies or picks (e.g. from YouTube Audio Library, attribution not required). Otherwise make an original with `scripts/make_beat.py`: it's synthesised from scratch, so it's the person's own, and it writes an exact beat grid. Record any track's origin and license in a license file next to it (e.g. `music/LICENSE.txt`). If a bed has a quiet stretch, jump over it on a 16-beat phrase with `bed.play` ranges.
9. **Never write next to the export or change it.** Everything goes under the project's render folder (`render/<name>-trailer/`, `render/<name>-short/`). Camera originals, if mounted, are read only too.
10. **Don't drive Finder.** Don't write a second FCPXML writer; if a Final Cut timeline is wanted, use the existing fcp-mcp-server.

## Workflow

1. **Read** (rule 1). Note the export's burned-in labels and watermark: they will show through.
2. **Bed and beat map.**
   - Your own beat: `uv run --no-project --python 3.12 --with numpy --with scipy --with soundfile python -I scripts/make_beat.py music/<name>.wav --bpm 140 --bars 44 --key F --seed 7` writes the WAV and an exact `.beats.json`. `--key` moves it to another key, `--bpm` changes the tempo (130-150 suits phonk), `--seed` changes only the noise texture; the riff and the chord progression stay the same. It prints the drop beat (16) and the breakdown. Start the trailer's bed 2 bars before the drop (`"play": [[8, null]]`) so the drop lands on the first cut; start a Short on the drop (`[[16, null]]`). Its master is loud (about −7 LUFS), so use `"gain_db": -9`. Measure it with `beats.py` and look at the band levels; nobody can listen for you.
   - Anyone else's track: `uv run --no-project --python 3.12 --with librosa python -I scripts/beats.py <track>` → `<track>.beats.json` beside it. Read its per-window tempo and loudness lines to choose `bed.play`.
   - After cutting, check the duck. Your lines should sit at least 10 dB over the beat. Render the ducked bed alone (the same sidechain as `cut.py`) and compare it with `work/voice.wav` over each voice shot's words.
3. **Word times** for each line you'll use: `scripts/words.py <export> <start:dur> ...` (via `uv ... --with mlx-whisper`; point `HF_HOME` at a cached `whisper-large-v3-turbo`).
4. **Write the spec** (`references/spec.md`): `steps` first (rule 3a), then one or more shots per step plus 4-7 voice shots. Trailer ~45-60 s, 16:9, `frame.mode: full`. Short ~35-45 s, 9:16: hook label with `"hook": true` (on screen at frame 0, it is the thumbnail), 1.5-2 s shots, one subject per frame.
5. **Cut:** `python3 -I scripts/cut.py spec.json`. It ends with `lint`; fix every `LINT` line in the spec and re-cut (don't edit the limits). Then sheet the middle frame of every shot (ffmpeg `tile`) and look: is the action in frame, does the label match the picture? For 9:16, re-aim `center` / `pan_to`, or switch wide shots (car on jacks, long parts on a bench) to `fit` with `zoom` 1.3-1.6.
6. **Type:** first time, `hyperframes init hf --skip-skills`; then `python3 -I scripts/type_layer.py cues.json hf`. In `hf/`: `check --json` (add `--safe-zone shorts` for a Short); fix every error, every `line_unread` and every `outside_safe_zone`. `snapshot --at 0,<one time per shot>` and read the contact sheets.
7. **Render** in `hf/`: `render -o ../<name>.mp4 --fps 30000/1001 -q delivery`. Verify: ffprobe (size, fps, duration), loudness about −14 LUFS (`ffmpeg -af ebur128`), and a frame sheet of the final file.
8. **Deliver:** show the file and give its path; say which music was used and its license, what came from the 1080p export vs camera originals, and anything not verified (nobody has listened to it).

## Look and cover (after the cut is approved)

The cover sells the tap; the video must look like the cover, or people who tapped swipe away. Both come from one function in `grade.py`.

1. **Study what trends first.** Search YouTube for the car and the job as Shorts and look at the covers with the most views. For car Shorts in 2026: dark, moody car shots with little or no text, and tight shots of gloved hands on the part. Big outlined meme type only shows up on toy and kid content; a cover built that way was called "terrible".
2. **Lead with the car and the upgrade.** The keyword is the car (`PANAMERA TURBO`) and what was done to it (`AIR FILTER UPGRADE`); the brand appears as its official logo. How the job is done (the bumper comes off) is an aside in the description, not the hook. A title and cover built on "the air filter is behind the bumper" were rejected: "who cares".
3. **Use the brand's official logo, never its name typed in red.** If it has black ink, make a dark-ground version: `cover.py --reverse-logo <logo.png> <out.png>` (the kept colour stays, black turns white, white goes clear). Ask for the logo file; don't invent one.
4. **Lettering:** Michroma (`assets/fonts`, OFL), the wide flat caps of a car badge. A maker's own typeface (Porsche Next and the like) is not licensed for public use: say so and don't use it.
5. **Cover:** `cover.py --frame "<export>@<sec>" --cx <0-1> --logo ... --kicker PORSCHE --title "PANAMERA TURBO" --tag "971 · AIR FILTER UPGRADE" --accent 971 --top <y>`. Pick a frame with the part and the car in one shot (a 9:16 slice of 16:9 is narrow: try several `--cx`). The type goes below the subject: if the logo covers the part, raise `--top`. Show the person 3-4 options side by side before settling.
6. **Grade the Short to match:** `grade.py hf/assets/picture.mp4 hf-graded/assets/picture.mp4 --keep red --strength 0.6 --open-end <first cut>`: the full look on the first shot (where the cover's promise is checked), 60% after it. Check a still sheet first (`--test t1,t2,t3`): calipers in shadow must stay red. Copy `hf/` to `hf-graded/` (not `node_modules`) and grade there, so the original stays; change the opening label to the cover's wording in `hf-graded/compositions/labels.html`; run `check --safe-zone shorts`; render beside the original and make a side-by-side (`hstack`) so the person can choose.
7. **Copy:** `references/posting.md`.

## Framing a Short (16:9 source → 9:16)

- Text lives in the band every platform leaves clear: y 288-1248, x 120-888 (`type_layer.py` portrait layout already does). The progress bar at the top is decoration.
- `crop` for hands and close work; aim `center` at the hands or the part, `pan_to` when the action moves across.
- `fit` (full frame over a blurred fill) for anything wide: the car on the jacks, the whole bumper, a long filter on a bench. Use `zoom` 1.3-1.6 so it isn't a letterbox strip.
- The watermark (top right) is cropped away in most 9:16 shots; that's expected.
