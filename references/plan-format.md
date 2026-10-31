# plan.md format

`plan.md` in the project folder is the single source of truth. The user edits it (or tells Claude what to change),
`review.py` shows it as a page, `plan.py` turns it into `edl.json` (the cut) and `timeline.json` (the effects), and
`build.py` draws it. Never hand-edit edl.json or timeline.json: change the plan and re-run plan.py.

```markdown
# Deilbach, day 0
style: default

## hook
c1 6.30-10.70 | Five years ago, my hometown Essen had the biggest flooding in over a century
- zoom 1.3
- caption-lead "five years ago" @five ..ago
- blur-pop "*biggest* flood" @biggest
~~c1 11.52-13.12 | and we were directly impacted by it.~~ (repeats the next line)

## home
c1 14.15-17.78 | My family owns a home next to the Deilbach in Kupferdreh.
- split 20210714_213558.jpg Hochwasser_Container.mp4@kupferdreh @family
> a note for the user; ignored by the build
```

## Lines

| Line | Meaning |
|---|---|
| `# Title` | Name of the video. |
| `style: name` | Which `styles/<name>.md` to use (default `default`). |
| `## section` | Starts a section. Segment ids are `<section>_<n>` (n counts every line of the section, cut ones included). |
| `c1 6.30-10.70 \| text` | A segment: clip id (sources.json), in and out seconds in that clip, what is said. The text is also the subtitle (style `subtitles`): write it as said, names spelled right; `*word*` turns that word the accent colour: ONE word only; `*two words*` breaks when the subtitle chunks split it and shows the asterisks. |
| `~~c1 ... \| text~~ (reason)` | A segment that is cut. Stays in the plan so the user sees it and can bring it back by removing the `~~`. |
| `- effect ...` | An effect on the segment above. |
| `> text` | A note. Ignored. |

## Effect lines

`- <id> ["text"] [files...] [@start] [..end] [key=value ...]`

- `"text"`: the on-screen text for text effects. `*word*` turns a word the accent colour.
  `"small lead | big line"` puts the part before `|` on a smaller line above (style `lead`, a share of the size).
- files: material names from materials.json (or a path in the project, e.g. an agent's webm). Each file can have its
  own start: `photo.jpg@water`.
- `@start`: a word said in this segment (`@water`, the 2nd occurrence `@water#2`) or seconds from the segment
  start (`@1.5`). Default: the segment start. Effects start 0.05s before the word.
- `..end`: a word (in this or a later segment of the same section; the effect ends just after it), `..end` (segment
  end, the default), `..next` (end of the next segment), `..sec` (end of the section), or seconds from segment start.
- Anchors match the transcript of the CUT (words.json), which can differ from the plan text where Whisper misheard.
  build.py stops with the words it heard if an anchor is missing: fix the anchor.

## Effects

Camera
| id | what | params |
|---|---|---|
| `zoom 1.3` | punch-in for this segment, centred on the face | `cx= cy=` (0-1) to override the face |
| `no-punch` | no cut punch into this segment | |
| `push-in` | slow zoom 1 -> 1.05 across the effect | |
| `no-subs` | no subtitles from @start to ..end (when the line is already big on screen) | |
| `focus-in` | blur to sharp at the start | |
| `light-sweep` | one soft light band across the frame | |

Text (stack in the chest band unless `y=` is given)
| id | what |
|---|---|
| `caption-lead "text"` | lead-in line, blur-pop entrance |
| `blur-pop "text"` | big punch words |
| `behind-head "text"` | big word behind the head (needs `cutout.py` first); placed from the head position |
| `caps-track "TEXT"` | small tracked caps, words track in one by one |
| `serif-rise "text"` | big serif, letters rise from a mask |
| `italic-punch "text"` | italic serif in the accent colour |
| `sparkle` | three twinkles; `x= y=` centre |
| `hand-note "text"` | handwritten label + drawn arrow; `x= y=` label, `to=X,Y` arrow tip (1080x1920 px) |

Material
| id | what | params |
|---|---|---|
| `photo-stack a.jpg@w1 b.jpg@w2 ...` | prints drop onto a pile below the chin (placed from the face found per segment), each on its word; all leave together | `from=` (s into a clip) |
| `pip a.jpg [b.jpg@w ...]` | box below the chin while the speaker stays visible; several files swap in turn. With style `pip.big` it is a big centred card filling the room under the chin | `width=`, `side=left/right top=` (small side box) |
| `split a.jpg [clip.mp4@w ...]` | material fills the top, speaker moves down; several files swap | `height= shift= from=` |
| `cutaway a.mp4 [b.mp4@w ...]` | full-screen cutaway: material fills the whole frame, hard cut in and out, silent unless `sound=`; voice and subtitles keep running; several files swap | `from=`, `sound=0.5` (play each clip's own audio at that volume, under the voice) |
| `reel-cards a.mp4 b.mp4` | tilted portrait clips beside the face | `credit=@handle` |
| `orbit a b c d e` | portrait tiles circle the speaker (behind them when the cutout exists) | |
| `window-behind agents/x/renders/x.webm` | sub-agent insert on the wall behind the speaker | `left= top= w= h=` |
| `card-under-chin agents/x/renders/x.webm` | sub-agent insert, tilted card under the face | `left= top= w= h= scale= tilt=` |

Sound
| id | what |
|---|---|
| `sfx whoosh-short @word` | one sound (assets/sfx: whoosh-short, pop, sparkle, click, click-soft, impact-bass-1, or any mp3 you add there); `vol=` |

Effects also play the style's default sound (style `sfx` map).

Not built yet (in the catalogue, not in build.py): slow zoom on a still (kenburns), lower third,
date stamp.

Subtitles: with the style's `subtitles` block, every kept line is shown as running subtitles (chunks of a few
words, timed by the cut's words). Don't repeat a line with `caption-lead` then. Prefer `pip` / `photo-stack` over
`split` (Arne's preference); portrait clips go full screen as `cutaway`.
