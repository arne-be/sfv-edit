# UI recreations and animated inserts (built by parallel sub-agents)

The main session owns the cut, captions and integration; each animated insert (app recreation, social UI,
code file scroll) is delegated to its own sub-agent (Opus if available) working in its own folder, in parallel.

## Pattern
1. Lock the insert's timing to the speaker's words first (word timings from transcribe_cut.py / the clip's words json).
   Convert to the insert's own clock: insert t=0 at a known source moment, every beat = word time - that moment.
2. Spawn one sub-agent per insert (Agent tool, `model: opus`, `run_in_background: true`), all in parallel.
3. Each agent builds a standalone HyperFrames project in `<project>/agents/<name>/` and renders a TRANSPARENT VP9 WebM
   at a fixed size and duration. The plan places it: `- window-behind agents/<name>/renders/<name>.webm @word` (on the
   wall behind the speaker, needs the cutout) or `- card-under-chin agents/<name>/renders/<name>.webm @word` (tilted
   card under the face). Box params: left= top= w= h= (and scale= tilt= for the card).
4. When an agent reports back, read its notes (things it flags as "might look off" are usually real, e.g. a grid
   thumbnail with an off-brand title). Send fixes back with SendMessage instead of redoing the work.

## Brief template (fill every bracket; the specifics are what make the result good)
`[PY]` and `[skill]` are the `python` and `skill_dir` values from `.platform.json` (full paths, so the sub-agent
runs the same commands on Mac, Linux and Windows).
```
Build ONE short animated UI clip with HyperFrames: [what it shows]. It plays in an Instagram reel while [speaker]
says "[line]", so it must look premium, realistic and readable on a phone.

Where to work: [project]/agents/[name]/ (touch nothing else). Inputs: [files]. Copy setup (fonts.css + woff2,
hyperframes.json, package.json) from [project]/ ; mirror [skill]/assets/overlay-examples/[closest]/ for structure.

Output: composition [W x H], transparent background outside a [window/card] with ~[R]px rounded corners (corners
transparent, inside opaque). Duration [D]s, 30fps. Render renders/[name].webm with --format webm. Verify alpha
(ffprobe alpha_mode=1; decode a frame with -c:v libvpx-vp9 and check a corner pixel is transparent).

Look: [palette, fonts, real data to show, generic placeholders for anything that isn't real; no copied logos].
Readable sizes: key text >= 24px at the size it will be shown.
Colours that ANIMATE (tweened colour, crossfades) must be hex/rgb: GSAP cannot interpolate oklch() and the element is
drawn invisible mid-tween. Static colours may stay oklch.

Timeline (seconds, locked to the voice, keep within ±0.05s): [beat list].

HyperFrames rules: run it as `"[PY]" "[skill]/scripts/hf.py" <lint|snapshot|render ...>` from your folder (pinned
hyperframes@0.8.34 with Node 22+, same command on Mac, Linux and Windows; in PowerShell put `&` in front), run
build.py with "[PY]" and write index.html with encoding='utf-8', root div with data-composition-id/start/duration/
width/height, paused GSAP timeline registered in window.__timelines["main"], gsap.set for initial states OUTSIDE the
timeline, immediateRender:false on fromTo, no apostrophes in ids, no onUpdate text tricks (one span per typed
character revealed with tl.set), lint 0 errors, snapshot and LOOK at the PNGs, then render. Never delete files.
Several states of one insert: one build.py with a STATES table, one composition per state, each rendered to its own
webm (lint allows one root composition: build.py writes index.html for the state being rendered).
Verify transitions on EVERY frame around each beat (decode with libvpx-vp9 and tile the frames), not only one frame
before and after: a line that vanishes for 7 frames passes a before/after check.

Report back: path, exact duration, alpha confirmed, actual beat times (for sound effects), anything that looks off.
```

## Example inserts (assets/overlay-examples/ has their index.html / build.py)
Full-screen inserts (a map, a dashboard walk-through) are opaque mp4s placed with `cutaway`, not transparent WebMs.
- **claude-desktop** (1000x720, 4.35s): Claude desktop light theme, 5 clip thumbnails dragged into the input with a
  count badge, `/video-edit` typed with a slash-command menu, Claude reply with a "Using skill" pill and a checklist
  ending in a "reel.mp4 · ready" file card. Placed on the wall BEHIND the speaker (z between base video and cutout).
- **ig-follow** (760x1000, 2.9s): the creator's IG profile in dark mode (profile pic, verified badge, posts /
  followers / following, bio, post grid from their reels), a touch dot taps Follow at 0.70s (button -> Following),
  the comment sheet slides up, the CTA keyword is typed and posted at 1.75s. Scaled .7 under the chin in the CTA.
  Click sounds at the two taps. Fill it with the user's REAL numbers (ask for them). Example commenters must stay
  generic placeholders.
- **skill-md** (860x1000, 2.15s): dark code editor showing a SKILL.md with markdown highlighting, a smooth eased
  scroll on a wrapper `y`, a line glow as a section passes. Scaled .72 with a slight rotateX tilt under the face.

- **receipt** (640x800, 2-7.4s per state, 5 states): a paper receipt (zigzag torn edge, tilt 4deg baked in) that
  prints one cost line per state with the price counting in step with the voice, FREE stamps on free items, then a
  TOTAL with a crossed-out alternative ("Supabase + Vercel 40 €"). Each state starts with the earlier lines printed.
  Shown at 320x400 in the top-right corner (`card-under-chin ... left=715 top=230 w=320 h=400 tilt=0 scale=1`),
  `no-subs` while it is up. Line items are 30px mono (15px on screen): small; the total and stamps carry it.
- **arch-strip** (960x330, 3.9-6.6s per state, 5 states): a simplified system diagram, boxes and arrows only on a
  transparent background (no card: Arne's choice). Row Data sources -> Service -> Website, Database above Service.
  The part being talked about lights orange with a tool tag, lit arrows carry travelling dots. Each box has its own
  dark fill + shadow and each connector a dark casing so it reads over a white T-shirt. Shown at .85 below the chin
  (`left=60 top=1185 w=960 h=330 tilt=0 scale=.85`), popping in for a few seconds per part with `no-subs`.

- **map-cutaway** (1080x1920 OPAQUE mp4, 27.6s, day 2): the catchment map from Arne's own HTML page, animated as a
  full-screen `cutaway` (`- cutaway agents/map/renders/map.mp4 @map ..sec`). build.py copies the page's SVG layer
  groups (#l-zones, #l-rivers, #l-markers ...) and animates them directly; the base-map image is cropped and
  downscaled. Top band: three data-type chips with line icons that light orange when named. Gauges get rings + labels
  on their names, zones switch on one by one via the page's own toggle, and on "where the rain falls" a flow front
  runs along EVERY stream (79 lines, each oriented upstream -> downstream by distance along the network) into the
  gauge (Arne asked for all the arms, not only the main river). Map band y 420-1290 so the running subtitles stay
  readable below it. Render with `--sdr`, verify bt709. Placeholder for the review page: a PIL still looped to the
  span length with ffmpeg. Only build.py is kept here (its index.html is generated, ~230 KB).

## Placement of small inserts

## Placement of small inserts (learned on day 1)
- Measure first: segments.json has `chin_y` per segment. With a close framing (head from y ~300 to the chin ~1150)
  the only free band is chin+35 .. 1465, which is also the subtitle line (1310). A persistent strip there collides
  with the subtitles, so pop it in for 3-6s per beat with `no-subs` over its span instead.
- The top band (220 .. head top) is usually too thin; the top-right corner beside the hair (x >= 715) holds a small
  card. Overlapping hair is fine, never the eyes.
- `card-under-chin` only tilts in 3D (rotateX). An in-plane tilt has to be baked into the webm, with the rotated
  card and its shadow kept inside the canvas.
- Build placeholders (PIL stills -> 2s webm) for the review page so the user can judge layout before agents run;
  agents overwrite them in place.

## Other people's clips as cards
`reel-cards` shows portrait clips beside the face. Ask the user for the files (they register them with materials.py
like any other material) and always credit the creator on screen with `credit=@handle`.
