# sfv-edit

A [Claude Code](https://claude.com/claude-code) skill that cuts short-form vertical videos (9:16 Reels, TikTok,
Shorts) from talking-head clips plus your own photos and b-roll.

You point it at a folder. It writes a plan, waits while you edit that plan, and then renders the finished video.

- **The footage is never graded or filtered.** Everything the skill adds (text, inserts, zooms, sound) sits on top of
  the video. HDR phone clips are tone-mapped to SDR so the colours match what the phone shows.
- **Nothing is built before you approve the plan.**
- **Zooms always centre on the face**, which is detected per segment.
- **The look comes from swappable style files** in `styles/`.

## How it works

1. **Plan.** It transcribes the clips with faster-whisper and sorts your photos and b-roll. Then it writes `plan.md`:
   the full transcript as segments, the lines it suggests cutting (struck through, with a reason), and the material
   and effects for each line, anchored to the word where they should happen. A review page shows the plan with a
   frame per segment.
2. **Edit (hard stop).** You change `plan.md` yourself, or tell Claude what to change. The review page updates after
   each round. Nothing is built until you say go.
3. **Build.** The skill cuts the A-roll, places the effects, renders with [HyperFrames](https://www.npmjs.com/package/hyperframes)
   and checks every cut frame by frame. Animated UI inserts (app screens, receipts, diagrams) are built by
   sub-agents in parallel.

## Install

```sh
git clone https://github.com/arne-be/sfv-edit.git ~/.claude/skills/sfv-edit
```

You need:
- Python 3
- ffmpeg
- Node 22 or newer

The first run of `scripts/setup.py` creates the skill's Python venv (faster-whisper, Pillow, OpenCV) and writes
`.platform.json`. If something is missing, it prints the exact install command for your OS. It works on macOS,
Linux and Windows. On Apple silicon, the background cutout runs on CoreML.

On the first run, Claude also asks where your projects should live and saves that in `config.json`.

## Use

In Claude Code, type `/sfv-edit` and name a folder, or ask something like "cut this video" or "make a reel from this
folder".

## Effects

A plan line looks like this:

```markdown
## hook
c1 6.30-10.70 | Five years ago, my hometown had the biggest flood in over a century
- zoom 1.3
- caption-lead "five years ago | the *biggest* flood" @five
- photo-stack flood1.jpg@water flood2.jpg@street
- sfx whoosh-short @biggest
```

| Group | Effects |
|---|---|
| Automatic | cut punch on every cut, running subtitles |
| Camera | `zoom`, `no-punch`, `push-in`, `focus-in`, `light-sweep`, `no-subs` |
| Text | `caption-lead`, `blur-pop`, `behind-head`, `caps-track`, `serif-rise`, `italic-punch`, `sparkle`, `hand-note` |
| Material | `photo-stack`, `pip`, `split`, `cutaway`, `reel-cards`, `orbit`, `window-behind`, `card-under-chin` |
| Sound | `sfx` with the bundled whoosh, pop, sparkle, click and impact sounds, or any mp3 you add (for example one made with ElevenLabs) |

The full syntax is in [`references/plan-format.md`](references/plan-format.md).

To see every effect as a looping animation, build the gallery:

```sh
python3 references/effects-gallery/build.py
open references/effects-gallery/effects-gallery.html
```

## Styles

| Style | Look |
|---|---|
| `default` | Inter Tight, lowercase punch words, yellow accent |
| `deilbach` | The Deilbach Pegel website: Space Grotesk and Manrope, white text on a tight dark teal bar, one orange accent word |

To make your own, copy a style file to `styles/<name>.md` and change both parts: the prose Claude reads when it
writes the plan, and the JSON block `build.py` reads for exact values. Then put `style: <name>` at the top of a plan.

## Layout

| Path | What's there |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `scripts/` | Setup, ingest, plan check, review page, assembly, cutout, cut checks |
| `assets/template/` | The HyperFrames project copied into each video, with fonts and sound effects |
| `assets/overlay-examples/` | Example animated inserts made by sub-agents |
| `references/` | Plan format, layout and safe zone, gotchas, insert briefs, effects gallery |
| `styles/` | Style files |
| `tests/` | Tests for the plan parser and platform setup |

The fonts are under the SIL Open Font License (`assets/template/assets/fonts/OFL.txt`).
