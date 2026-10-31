---
name: sfv-edit
description: "Cuts short-form vertical videos (9:16 Reels/TikTok/Shorts) from talking-head clips plus the user's own photos and b-roll, in three steps: (1) a written plan with the full transcript, which lines to cut, where each photo or clip goes and which text and motion effects to add; (2) a hard stop while the user edits the plan, shown as a review page; (3) the build, render and frame checks. The footage is never graded or filtered. Look and options come from swappable style files. Trigger with /sfv-edit or 'cut this video', 'edit these clips with my photos', 'make a reel from this folder'."
---

# /sfv-edit

A folder of clips, photos and b-roll in, a finished 9:16 video out, in three steps with a hard stop in the middle.

- The footage stays exactly as filmed: no grade, filter, tint, vignette or grain. Everything this skill adds sits on
  top of the video. HDR phone clips are converted to SDR with Apple's tone mapping (assemble.py), so the colours match
  what the phone shows; never only retag them.
- Sound and picture stay in sync: assemble.py cuts every segment to whole frames and prints `audio vs video`; a
  difference over one frame is a bug.
- Zooms centre on the face (detected per segment), never on a fixed point.
- All styling comes from a style file (`styles/<name>.md`): prose for Claude, a JSON block for build.py. The plan's
  `style:` line picks it; new plans use `defaultStyle` from config.json. Styles: `deilbach` (the Deilbach Pegel
  website's look: Space Grotesk + Manrope, dark teal pills, orange accent) and `default`.

Read before planning: `references/plan-format.md` (the plan and every effect id) and the style file in use. Read
before building: `references/layout.md` (safe zone, placement) and `references/gotchas.md`. Read
`references/overlays.md` only when the plan has a `window-behind` / `card-under-chin` insert.

Visual reference: `references/effects-gallery/` shows every effect looping on a mini phone, published at
https://claude.ai/artifact/EiMURST6QgNZosMTW4QdCG. Keep it current: whenever an effect, style rule, sfx file or
finished insert is added or changed, edit `template.html` there (new insert frames go next to it, wired in build.py),
run `build.py`, and republish `effects-gallery.html` to that same URL with the Artifact tool (`url` set to it).

## Step 0: Setup (every run, a few seconds)

`SK` is this skill's folder (the one holding this SKILL.md), as a full path, usually `~/.claude/skills/sfv-edit`.

Run `python3 "SK/scripts/setup.py"` (then `python`, then `py -3` if that is missing). It checks ffmpeg, Node 22+, the
skill's Python venv (faster-whisper, Pillow, OpenCV) and the sound effects, prints `STATUS` lines with the exact fix
for anything missing, and ends with READY. Not READY: give the user the fix it printed and stop.

Then read `SK/.platform.json`:
- `PY` = its `python` value. Run EVERY script of this skill with it, never a bare `python3`.
- `HF` = `PY "SK/scripts/hf.py"`: the pinned HyperFrames with the right Node on any OS.
- `cutout`: CoreML (fast) or CPU (slow, run it in the background).

`SK/config.json` holds `projectsDir` (default `~/sfv-edits`) and `defaultStyle` (default `default`; set to `deilbach`). If it is missing,
ask where projects should live and write it (no secrets).

Commands: full paths in double quotes with forward slashes, one command per call, no `&&`, no `~` inside arguments.

## Step 1: Plan

1. **Intake.** The user names a folder (or files). Sort it into talking-head clips (the A-roll, people speaking to
   camera) and material (photos, b-roll clips). Unsure which a clip is: look at its frames. Create
   `<projectsDir>/<short-slug>/`.
2. **Ingest the A-roll:** `PY "SK/scripts/ingest.py" "<project>" <clips>` -> `sources.json`, `transcript.txt` (per
   clip, with silence marks), `words_cN.json`, `work/sheets.jpg`. Look at the sheet.
3. **Ingest the material:** `PY "SK/scripts/materials.py" "<project>" <files or folders>` -> browser-ready copies in
   `assets/materials/`, `materials.json`, contact sheet `work/materials.jpg`. LOOK at the sheet, then write a short
   `note` for every item in materials.json (what it shows, date or place if visible, where it could go).
   Prepared material goes into `work/src/` first and is then registered the same way: a sped-up timelapse of long
   b-roll (ffmpeg concat + `setpts=PTS/N`, ~6s), a headless-Chrome screenshot of an HTML diagram, a 16:9 crop of a
   portrait clip for a pip (gotchas.md "Assets").
4. **Write `<project>/plan.md`** (format: references/plan-format.md), following the style file:
   - The full transcript as segments, in order, every sentence of the chosen takes. Repeated takes: pick the
     faster one (higher wpm, shorter pauses) where Arne looks into the camera; eye contact can beat speed. Look for
     hidden retakes inside long mid-sentence pauses (gotchas.md "Timing") before cutting them. Times from `words_cN.json` (start ~0.06s before the first word, end at the silence after the last).
   - Lines to drop stay in the plan, struck through, each with a reason (repeat, filler, false start, off-topic).
   - For every kept segment: the material that fits (matched by the notes), zooms, text and motion effects, each
     anchored to the word where it should happen.
   - Use only effect ids that exist (plan-format.md) and the material names from materials.json.
5. `PY "SK/scripts/plan.py" "<project>" --check` until it reports no problems.
6. **Show it.** `PY "SK/scripts/review.py" "<project>"` writes `work/review.html` (each segment with a frame of the
   speaker, its text, cut lines struck through, effect chips with material thumbnails). Publish that file with the
   Artifact tool (always the same file path, so the link stays the same) and give the user the link. In chat, add a
   short summary: length before and after, what you cut and why, the 3-5 biggest editing ideas, any material you
   found no place for.

## Step 2: Edit the plan with the user (HARD STOP)

Do not assemble, cut out, build or render anything until the user explicitly approves the plan ("go", "build it",
"looks good"). Every round:
- The user either edits `plan.md` themselves (re-read it) or tells you what to change (you edit `plan.md`).
- `plan.py --check`, then `review.py`, then republish the same file path. Say in one or two lines what changed.
- Questions about why something is cut or placed: answer from the plan, do not build to show it.
- Choosing between takes or variants of a line: export short preview clips to `renders/takes/` (straight from
  `work/sdr/<clip>.mov`, or from the last render for a current splice; mind the cut-time offset) and `open` the
  folder. Arne decides faster by watching than by reading numbers.

## Step 3: Build

1. `PY "SK/scripts/plan.py" "<project>"` -> edl.json + timeline.json.
2. `PY "SK/scripts/assemble.py" "<project>"` -> `assets/aroll.mp4`, `segments.json` (zooms centre on the face; it
   prints segments where no face was found: set `cx= cy=` on that zoom in the plan if it matters).
3. `PY "SK/scripts/transcribe_cut.py" "<project>" "<names and keywords from the plan>"` -> `words.json`. Fix
   anchors in the plan that Whisper heard differently.
4. Only if the plan uses `behind-head` (or wants `orbit` / `window-behind` behind the speaker):
   `PY "SK/scripts/cutout.py" "<project>"` in the background, one at a time.
5. Inserts by sub-agents (`window-behind`, `card-under-chin`): spawn them in parallel as in references/overlays.md.
6. Copy into the project: `SK/assets/template/` (build.py, hyperframes.json, package.json, assets/fonts, assets/sfx)
   and the plan's style file `SK/styles/<style>.md` as `<project>/style.md`. Never edit build.py for one video; all content comes from the plan.
   An effect the plan needs that build.py does not have: tell the user, and add it to the skill's build.py (and
   plan-format.md, plan.py EFFECTS) only if they agree.
7. From the project folder: `HF lint` (0 errors), `PY build.py --safe`, `HF snapshot --at <10-20 moments> --no-end
   --describe false`. Read the contact sheet: face never covered, text readable, everything inside the safe zone,
   build.py warnings handled. Fix in the plan, re-run plan.py and build.py.
8. Render: `PY build.py` (without --safe), `HF render -o renders/<slug>-vN.mp4 --quality high --sdr --low-memory-mode`, then
   `PY "SK/scripts/check_cuts.py" "<project>" renders/<slug>-vN.mp4 --phone` and look at `work/cut_check.jpg`.
9. Thumbnail (when asked, or offer it): an HTML page in `work/thumb/` over a strong frame of the cut (a gesture
   matching the topic), in the style's look: eyebrow ("DAY 1"), a 3-line headline on the caption bars with the key
   word in the accent colour, one card (a photo or a still of an insert) with a small tilted label; nothing over the
   eyes to chin. Screenshot it with headless Chrome at 1080x1920 and crop y 285-1635 for the 4:5 grid version
   (keep everything inside that band); save `renders/<slug>-thumbnail.jpg` and `-thumbnail-grid-4x5.jpg`. Reuse the
   last video's thumbnail layout when there is one; `SK/assets/thumbnail-example/thumb.html` is the day-1 one.
10. Deliver the full render and the phone copy. Keep every version in `renders/`. Changes after the render go back
   through plan.md (a short Step 2 round for anything bigger than a tweak).

## Hard rules
1. Never grade, filter, tint or vignette the footage.
2. Never build before the user approves the plan.
3. Never cover the face (eyes to chin) with text or material. Everything inside the Reels safe zone (layout.md).
4. On-screen text says what was actually said; fix Whisper's mishearings of names. No em dashes in on-screen text.
5. Sound effects subtle, never louder than the voice.
6. Credit other creators on screen (`credit=@handle`) when their clips appear. Never fabricate numbers, quotes or
   people; placeholders stay obviously generic.
7. Never delete or modify the user's files. Originals are read, never changed.
8. Prove cuts from the final render (check_cuts.py), not from snapshots.
