# Gotchas (each one cost a render)

## Timing / sync
- ffmpeg concat -> 0.033s video start offset + VFR gaps -> remove-background outputs extra frames -> the cutout drifts
  (by 20s it lagged a few frames: two copies of the speaker on screen after a cut). assemble.py re-encodes with
  `setpts=N/30/TB -fps_mode cfr`; cutout.py asserts equal frame counts.
- `tl.set` at a rounded time fires one frame late: use `frame/30 - 0.002`.
- `hyperframes snapshot` seeks approximately at cut boundaries; it can show the next shot a frame early. Only frames
  extracted from the final render (`check_cuts.py`) prove a cut.
- When a segment's in-point is trimmed, every hard-coded word time after it shifts. Keep a `SHIFT` derived from
  segments.json and wrap later times in `S(t)` (see template) instead of retyping them.
- Whisper word starts can be ~0.1-0.3s off and it hallucinates a leading word at a cut. Confirm pauses with
  `silencedetect` (n=-40dB, d=0.08) before trimming dead air.

- Sentence ends got clipped ("days" / "brings" lost their s): Whisper's word START is not the end of speech, and a
  quiet sibilant sits below its timing. Set a segment's out-point from `silencedetect` (n=-40dB, d=0.08) on the
  source clip: the start of the silence after the last word.
- A segment can start over with the words of the one before it ("I'm running" + "I'm running one hourly job"):
  Whisper's per-clip transcript merges the two. Re-transcribe the cut around a suspicious join with word timestamps
  (small.en, device='cpu') and strike the partial take.
- An effect end given in seconds (`..4.6`) counts from the SEGMENT start, not from the @start word: an effect
  anchored late in a long segment ends almost at once. Compute `segment_start_offset + wanted_length`.

- Subtitle text comes from segments.json (written by assemble.py), not edl.json: after changing a line's TEXT in the
  plan (e.g. a *starred* word), re-run plan.py AND assemble.py before build.py, or the old text renders.
- Whole retakes hide in the per-clip transcript: ingest's Whisper pass skipped a second take inside what looked like
  a 7s mid-sentence pause ("ready for ... tomorrow": the gap held a full faster retake of the line), and another one
  inside a 5s pause after "gathering". Any pause over ~2s inside a sentence: re-transcribe just that span
  (vad_filter=False, condition_on_previous_text=False) before cutting it, and offer the retake.
- A cut that joins one take's start to another take's end can land mid-word ("gathering" + "...ing the right"):
  re-transcribe the joined span; prefer one continuous take when one exists.
- Whisper puts the first word on the in-breath before it (day 2: "Day"@7.74, breath 7.68-7.95, voice at 8.25). Set
  the first segment's in-point from a loudness profile (RMS per 20-30ms), just before the voice onset.
- Cutting a leading word ("Then I ingested" -> "I ingested"): find the dip between the words in an RMS profile
  (silencedetect at -25..-30dB, d=0.04), then re-transcribe from that point to prove it starts clean.
- A full retake hid where the speech map said "silence" (day 3: "Then I went to a cafe to..." then a complete
  "Then I went to cafe with the goal..." in a 2s gap the ingest pass skipped). Re-transcribing a span that STARTS
  before the gap merged both takes into one clean-looking sentence. Read transcribe_cut.py's output for doubled
  phrases before snapshotting; transcribe each suspicious gap on its own.
- On some clips Whisper's word starts run 0.3-0.5s early all through (day 3). Set in-points from the silence map
  and RMS, not from word starts; check one early segment to see which way the clip leans.
- A stumble inside a word pair ("deploy model ... model"): the dip between words can be a plosive inside a word
  ("de-p-loy" dipped at 30.25, the word ended 30.35). Re-transcribe the kept half ending at each candidate dip and
  take the earliest end where Whisper still hears the whole word.
- Splitting a segment in plan.md leaves its effect lines under whichever line they follow. Day 3: splitting the
  cafe line to cut a stumble left the cutaway on the second half, so the first half showed the face. After a
  split, move the effects to the first half and check the snapshot at the segment START.

## Rendering
- iPhone footage is HLG (HDR). An HDR-tagged aroll sends the renderer down its HDR path, which composites the video
  OVER every HTML overlay: the mp4 shows no text and no photos while snapshots look fine. assemble.py and
  materials.py make SDR copies, and renders always use `--sdr`. Check: `ffprobe ... color_transfer` must say bt709.
- Only RETAGGING HLG as bt709 leaves the picture grey and washed out (Arne: "why are the colours edited"). On macOS
  the clips go through `avconvert -p PresetHighestQuality` (Apple's tone mapping, cached in work/sdr/); this ffmpeg
  has no zscale. Elsewhere the retag fallback prints a warning.
- Cutting each segment with `-t d` + `fps=30` drops a fraction of a frame per cut while the audio keeps all of it:
  over 39 cuts the sound ran 0.6s ahead of the picture. Segments are now whole frames (n = round(d*30), video
  `-frames:v n`, audio `apad,atrim` to n/30).
- The renderer composites `<video>` frames by z-index (nearest positioned ancestor with one). Overlays without a
  z-index rendered UNDER the base video: no text, no photos in the mp4, while snapshots looked fine. build.py keeps
  every layer explicit: #cam2 0, .back 3, #cutwrap 4, #front 8. New effects go into FRONT or BACK, never loose.
- CSS `-webkit-mask-image` does not survive the renderer. Bake alpha into a VP9 WebM with ffmpeg alphamerge instead.
- `autoAlpha:1` sets opacity to 1 and overrides a CSS `opacity` on the same element. A "3% grain" layer shown with
  autoAlpha ran at 100%. Put low opacity on an inner element or tween opacity to the target value.
- Every `<video>` needs an `id` or it renders frozen. Each overlapping media element needs its own `data-track-index`.
  `<audio>` SFX need ids too, and overlapping SFX need separate track indices (the template's lane allocator does it).
- Never tween autoAlpha/opacity on an element that has data-start (the framework forces opacity 1 on active clips):
  wrap it in a plain div and animate the wrapper.
- Lint rejects tweening letterSpacing (layout snapping): fake tracking with scaleX.
- Element ids cannot contain apostrophes ("i've" broke the whole inline script). Use keys like 'ive'.
- `fromTo` renders its from-state immediately: pass `immediateRender:false` for anything hidden until its time.
- Heavy backdrop-filter/blur on many elements can make captures go black; keep it to a few.

- `HF render` stores every frame on disk (~27 GB for 110s at 1080x1920) and exits 0 with NO mp4 when space runs
  out (only a warning in the log). Always render with `--low-memory-mode` (streams frames, same speed), and check
  the mp4 exists before check_cuts.py.

- A CSS `filter` on a `<video>` never reaches the render (the renderer swaps the video for captured frames). This
  skill never filters the footage anyway; `focus-in` animates a filter on the wrapper `#cam1`: check it in the render.

- An HTML insert whose colour tween goes through oklch() renders transparent mid-tween (GSAP cannot interpolate
  oklch): a receipt line vanished for 7 frames in the final mp4. Animated colours in hex/rgb.

## Assets / tools
- A cutaway clip that must be HEARD: `cutaway clip.mp4 ... sound=0.5`. build.py cuts the clip's audio from its
  ORIGINAL (materials.json `src`) into `assets/materials/<name>.m4a` once, since the material copies have no audio;
  slowed copies (made with `-an`) have none, and build.py stops with a message. The voice keeps running under it.
  For a beat where ONLY the clip is heard (day 3: the water pause, the singing), add it as an extra A-roll clip
  instead: re-run ingest.py with all clips. ingest numbers clips oldest-first by file time, so adding one can
  renumber the talking head (day 3: c2 -> c3): fix every `cN` in plan.md.
- Non-speech A-roll can be far louder than the voice (day 3: flood water 12 dB over speech). Compare
  `volumedetect` mean on the aroll; if it jumps, make a quieter copy in work/src (`-c:v copy -af volume=-7dB`) and
  point sources.json at it (the original stays untouched), then re-run assemble.py.
- Phone b-roll and selfie clips often open with ~1-2s of handling blur (phone being turned round). Look at the
  first 3s at 5 fps before choosing an in-point.
- materials.py skips a name it already converted: after re-encoding a derived file (a re-timed slow copy), copy it
  over assets/materials/ yourself and update its `dur` in materials.json.
- B-roll run across several segments or sections: ONE cutaway on the first segment, each file at a seconds offset
  (`clip.mp4@6.08`, offsets count from that segment's start and may run past it), end in seconds (`..31.0`). Word
  anchors for file swaps must be in the same segment; seconds are not limited. Fill a run with every clip at full
  length by slowing them with one shared factor: `setpts=PTS*(run/sum of durations),fps=30`, `-an`, bt709 tags.
  Re-measure the run from segments.json after any cut change and re-time.
- A card over b-roll: list `card-under-chin` AFTER the `cutaway` line(s); later DOM order draws on top.
- This ffmpeg has no `drawtext`: label contact sheets with xstack order instead of burned-in numbers.
- Face-centred zoom uses OpenCV's Haar face detector, which OpenCV 5 removed: setup.py pins `opencv-python-headless<5`.
  No face found (looking away, out of frame) -> assemble.py prints it and centres the crop; set cx=/cy= on the zoom.
- Node 22+ for HyperFrames, pinned `hyperframes@0.8.34`. Start it with `HF` (`PY "SK/scripts/hf.py" <command>`): it
  puts a Node 22+ first on PATH on any OS (an nvm default of Node 20 otherwise gives "HyperFrames requires Node.js >= 22").
- Python scripts run in the skill's own venv. Its path differs per OS (`.venv/bin/python` on Mac and Linux,
  `.venv/Scripts/python.exe` on Windows), so read `python` from `SK/.platform.json` instead of typing it.
  The first transcription downloads the Whisper model (small.en ~0.5GB, medium.en ~1.5GB).
- Transcription dies with `open() got an unexpected keyword argument 'metadata_errors'`: the venv has PyAV 19, which
  faster-whisper 1.2.1 does not support. Run `scripts/setup.py` again (or the old `scripts/setup.sh`, which calls it);
  it pins `av<19` and repairs the venv.
- zsh: `for x in "a b"; do set -- $x` does not split; use `${=x}` or a Python loop.
- If a shell safety hook blocks inline heredoc scripts or moves into the Trash, write the script to a file and run
  it; download temp files into a scratch folder instead of moving things around. Never delete the user's files.
- Large file uploads to chat can fail: deliver a 720p crf 26-28 phone copy and keep the full render on disk.

- materials.py stops on the first missing file (the user moved two files out of the folder mid-run): nothing was
  registered. It now skips missing files with a warning; re-run it with the files that are left.
- A timelapse made with ffmpeg from HLG clips (concat + setpts) keeps the HLG tags: run the result through
  materials.py so it is tone-mapped like any other clip, and register derived files (crops, padded images) in
  materials.json so plan.py accepts them.
- Portrait material in a big `pip` below a close-framed speaker is ~190px wide (the room under the chin is ~330px
  tall). Use `cutaway` (full screen), or a 16:9 crop of the clip for the pip.
- `split` with a landscape image uses object-fit:cover: set `height` = 1080 / aspect so nothing is cropped, pad the
  image's top with ~220px (at 1080 wide) of its own background so it clears the IG header, and add `no-subs`: with the
  speaker shifted down the subtitles land on the mouth.
- materials.py reads `.tif/.tiff` as images (it used to register them as 0s videos). Charts dragged out of
  Preview/Keynote arrive as TIFF.
- Material ABOVE the head (pip always places itself under the chin): bake the still into a rounded alpha WebM
  (PIL rounded mask -> `ffmpeg -loop 1 -t 8 -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0`) and place it with
  `card-under-chin <webm> @word ..end left= top=222 w= h= tilt=0 scale=1`, bottom edge above the eyes (measure the
  eyes in an A-roll frame tiled with `drawgrid=w=1080:h=100`). Subtitles stay at chest height, so nothing overlaps.
- An HTML page (diagram, dashboard) as material: screenshot it with headless Chrome
  (`--headless=new --force-dark-mode --force-device-scale-factor=2 --window-size=1400,900 --virtual-time-budget=3000
  --screenshot=out.png "file:///...html#step"`), crop to the content, register the PNG with materials.py.

- Long b-roll (an 18-min desk recording) -> several timelapses: cut it into thirds and speed each up with
  `-ss A -t B -i src -vf "select='not(mod(n\,N))',setpts=N/30/TB"` (N = frames to skip, pick it so the output fits
  the line), `-pix_fmt yuv420p10le` + the HLG colour tags, then materials.py. Different thirds = no frame reused.
- `push-in` / `zoom` move the A-roll (#cam), never a cutaway. A zoom on b-roll is baked into the clip:
  `scale=w='trunc(1080*(1+0.12*t/D)/2)*2':h=-2:eval=frame,crop=1080:1920` (from the 4K source if there is one).
- A diagram ON a b-roll subject (tree model on a tree): `cutaway clip.mp4` plus `card-under-chin <alpha webm>` on the
  same span, placed over the subject (measure it in a frame of the clip); cards stack above cutaways.
- `sfx <name>` plays any `assets/sfx/<name>.mp3` in the project: no build.py change for new sounds. Sounds that
  are not in the set (a choir "ahh", a crowd "boo") are made with the ElevenLabs `sound-effects` skill (key in
  `.env.local` next to the projects folder; the API is blocked by the sandbox, run it unsandboxed). Make 2 variants
  of ~1.8s, keep them in work/sfx, copy the chosen one into assets/sfx. Generated sounds are loud (~-13 dB mean):
  vol=0.45 came out louder than the voice; 0.25 in a pause and 0.15 under speech sat right. Check with
  `volumedetect` on the render window vs. the same window of work/aroll.wav (hard rule 5).

## Windows (same skill, different shell)
- Claude Code on Windows runs commands in Git Bash when Git for Windows is installed, otherwise in PowerShell, and
  both can be available at once. Write commands that work in both: full paths in double quotes with forward
  slashes, one command per call, no `&&`, no `VAR=1 cmd`, no `~` in arguments. In PowerShell start a quoted program
  with `&`: `& "PY" "SK/scripts/assemble.py" "<project>"`.
- `python3` is usually a Microsoft Store stub ("Python was not found"). Use `PY` for everything. Before the venv
  exists, try `python`, then `py -3`.
- A program installed while Claude Code is open is not found until Claude Code is fully quit and reopened (it keeps
  the PATH it started with). setup.py says so when it sees ffmpeg installed but not visible.
- `npx` is `npx.cmd` there: Python cannot start it by bare name. `HF` and cutout.py start it through node directly.
- The background cutout has no GPU path on Windows (HyperFrames uses CoreML on Apple Silicon only, CUDA only with
  `HYPERFRAMES_CUDA=1` and a CUDA build of onnxruntime), so it runs on the CPU. Run it in the background.
- Windows opens text files as cp1252 unless told otherwise: every `open()` in build.py needs `encoding='utf-8'`,
  or accents, curly quotes and emoji in captions come out broken (the page says charset UTF-8).
- File paths inside an ffmpeg FILTER (subtitles=, movie=, a fonts file) need the drive colon and backslashes
  escaped (`C\:/Users/...`). Pass files with `-i` instead; the skill's scripts never put a path in a filter, and the
  concat list holds bare file names only.
- Git Bash rewrites arguments that start with `/` into Windows paths. Fine for file paths; for anything else
  (a `/flag`) set `MSYS_NO_PATHCONV=1` for that command.
- Smart App Control (Windows 11) can block the unsigned image library (sharp) that HyperFrames loads for snapshots
  (the cutout loads the same library); antivirus can make ffmpeg fail once with `spawn EBUSY`. Retry once, then
  tell the user what Windows blocked.
- Transcription dies with `Library cublas64_12.dll is not found or cannot be loaded`: the PC has an NVIDIA card, so
  Whisper's default device ('auto') chose CUDA, but the CUDA toolkit is not installed. The scripts pass
  `device='cpu'`; do the same in any one-off `WhisperModel(...)` call (a re-transcribed snippet, for example).
- Windows on ARM (Snapdragon): the transcription engine has no ARM build; setup.py asks for the x64 Python.

