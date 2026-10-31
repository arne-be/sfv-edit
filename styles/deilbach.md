# Style: deilbach

The look of the Deilbach Pegel website (deilbach-pegel.energiekonzepte-ruhr.de), so the videos and the site read
as one project. Dark mode of the site: deep teal-black surfaces, warm off-white text, one orange accent, and the
five gauge colours for water levels.

The footage stays exactly as filmed (no grade, filter or tint). The site's look lives only in what sits on top.

## Type

- **Space Grotesk** for anything big: headlines, punch words, numbers (water levels, dates, centimetres). Weight
  600-700, tight tracking (-.025em), normal case. Not lowercase-styled: the site writes German and English in
  normal sentence case.
- **Manrope** for small labels (eyebrows). Weight 600-800.
- **Eyebrows** (`caps-track`): Manrope 700, uppercase, wide tracking (.1em), orange, on the same dark teal marker bar
  as the captions. Use them for a place or date ("ESSEN, JULI 2021").
- Big Space Grotesk words (`serif-rise`, `blur-pop`) fit about 9 characters across the frame; longer ones run off
  the edge (check the snapshots).
- **Captions** (`caption-lead`, the signature element): bold white Space Grotesk on a dark teal marker bar that sits
  only behind the letters of each line (square ends, no pill). Write them as `"small lead | *key* words"`: the part
  before `|` is a smaller line above, the big line carries the orange accent word. Chosen by Arne over pills
  (2026-10-21).
- **Subtitles** for everything said (style `subtitles`): the plan's line text in chunks of up to 4 words, same white
  Space Grotesk on the teal marker bar, one line at y 1310. `*word*` in a plan line turns that word orange. With
  subtitles on, `caption-lead` is rarely needed (it would repeat the line).
- Never show the same words twice at once (Arne: "biggest / Barcelona / behind the scenes is on the screen twice").
  With subtitles on, skip `caps-track` / `blur-pop` that repeat the subtitle; for a line shown big at the top, add
  `no-subs` for those words so the bottom stays free for the material.
- No subtitles while a text-heavy card is on screen (day cards, timelines, lists): add `no-subs` over its span
  (Arne: "too much text to read").
- Text band (eyebrows, extra captions) y 1130-1290, between the chin and the subtitles.
- Accent words (`*word*`) turn orange. At most one per line.

## Colours (from the site's CSS, dark mode)

| Token | Value | Use |
|---|---|---|
| background | `oklch(18% .025 215)` | deep teal-black (panels, split background) |
| card | `oklch(22% .025 215)` | pill and card fill |
| brand | `oklch(36% .04 215)` | teal |
| foreground | `oklch(97% .005 90)` | warm off-white text |
| muted | `oklch(76% .02 215)` | secondary text |
| accent | `oklch(72% .18 50)` | orange: punch words, eyebrows, sparkles |
| level 1 | `oklch(66% .13 155)` | green, normal |
| level 2 | `oklch(85% .15 92)` | yellow |
| level 3 | `oklch(55% .19 30)` | red |
| level 4 | `oklch(50% .2 25)` | deep red |
| level 5 | `oklch(34% .12 15)` | dark wine, extreme |

The level colours are in the JSON `palette` for reference. build.py does not use them yet: colouring a number by
its water level is a planned addition (say so if a plan needs it).

## Cutting and effects

Same rules as `default` (cut dead air, zoom every second or third same-clip segment, face never covered), with a
calmer hand to match the site:
- Prefer `caption-lead` pills and `caps-track` eyebrows over big `blur-pop` words. Max one `blur-pop` per section.
- `behind-head` only for the one word of the video (e.g. "Deilbach").
- `serif-rise` uses Space Grotesk here (no serif on the site): use it for big numbers ("2021", "4,12 m").
- `italic-punch` is an orange Space Grotesk word here (no italics on the site).
- Skip `sparkle`, `hand-note`, `orbit` and `light-sweep`: they don't fit the calm, informational look.
- Photos and clips: rounded like the site's cards (14px), deep soft shadow, no frames. Only `pip` and `photo-stack`
  (Arne prefers them over `split`). They are big (`"big": true`): centred, filling the room from just below the chin
  to y 1600 (`material_bottom`, into Instagram's caption strip, Arne's choice for bigger pictures); the subtitle moves
  onto the picture's bottom edge while it is on screen. The speaker never moves or zooms for material: the only
  zooms are face-centred punch-ins (Arne, 2026-10-21: "only ever zoom in on my face").
- Portrait clips (b-roll, timelapses, phone screen recordings) go full screen as `cutaway`: hard cut in and out, no
  swipe, no sound effect (Arne, 2026-10-23: "make it a normal full screen cutaway", "remove sound effects"). He
  preferred the timelapse as a cutaway over a pip.
- Charts and graphs: above the head when he asks for them there (day 2: "put them above my head so they are not
  covered by the text"): baked rounded WebM via `card-under-chin` (gotchas.md "Assets"), covering the cap, never the
  eyes; no punch-in on those lines. Over b-roll they are the same cards, high on screen (top ~300-420) on top of the
  running b-roll, never a separate full-screen graph cutaway (day 3: "always a card ... over the broll"). Crop a
  multi-plot figure to just the plots he names. One figure that comes back later stays the FULL figure each time,
  with the part being talked about highlighted (orange frame or orange bands) and the rest dimmed white (day 3:
  train/test split, then extreme events).
- A formula or small diagram he names (day 3: the MAE formula) goes in as a card timed to a visual beat of the
  b-roll under it (the moment the clip zooms in), not just to the word.
- B-roll: every clip once, at full length, one after another, slowed with a shared factor (up to ~1.2x) to fill
  the run; never reuse parts of a clip (day 3: "use the full length ... or even slow them down instead of reusing
  only parts"). When the clips run out, the speaker carries the rest.
- A comedic beat: a hard cut to b-roll with its OWN sound for ~2s (day 3: the 2021 container in the flood, on the
  clip's loudest stretch) right after the hook line, no text on it.
- A map or diagram he made in HTML: rebuild it as an animated full-screen `cutaway` (overlays.md "map-cutaway"),
  using the page's own layers and toggles, beats on the words that name each part.
- When he points up at something, use `split` so the material sits above him (the one case for split).
- Explaining a system or costs: small animated inserts by sub-agents (overlays.md: arch-strip, receipt) in the site's
  colours. Diagrams as boxes and arrows only, no card behind them.
- The footage keeps its original colours: HDR phone clips are converted with Apple's tone mapping (assemble.py), never
  only retagged.

## Values

```json
{
  "accent": "oklch(72% .18 50)",
  "text_color": "oklch(97% .005 90)",
  "text_shadow": "0 6px 30px oklch(5% .02 215 / .6), 0 2px 6px oklch(5% .02 215 / .4)",
  "type": {
    "caption": {"font": "Space Grotesk", "weight": 700, "size": 88, "tracking": "-.03em", "case": "none", "line": 1.12, "lead": 0.57,
                "color": "#fff", "box": {"display": "inline", "bg": "linear-gradient(transparent 15%, oklch(22% .04 200 / .92) 15%, oklch(22% .04 200 / .92) 92%, transparent 92%)", "pad": "0 .08em", "radius": 0}},
    "sub":     {"font": "Space Grotesk", "weight": 700, "size": 66, "tracking": "-.02em", "case": "none", "line": 1.12,
                "color": "#fff", "box": {"display": "inline", "bg": "linear-gradient(transparent 15%, oklch(22% .04 200 / .92) 15%, oklch(22% .04 200 / .92) 92%, transparent 92%)", "pad": "0 .1em", "radius": 0}},
    "punch":   {"font": "Space Grotesk", "weight": 700, "size": 150, "tracking": "-.03em", "case": "none", "line": 1.0},
    "behind":  {"font": "Space Grotesk", "weight": 700, "size": 220, "tracking": "-.035em", "case": "none", "line": 0.9},
    "caps":    {"font": "Manrope", "weight": 700, "size": 34, "tracking": ".1em", "case": "uppercase", "line": 1.5, "color": "accent",
                "box": {"display": "inline", "bg": "linear-gradient(transparent 15%, oklch(22% .04 200 / .92) 15%, oklch(22% .04 200 / .92) 92%, transparent 92%)", "pad": "0 .3em", "radius": 0}},
    "serif":   {"font": "Space Grotesk", "weight": 600, "size": 170, "tracking": "-.035em", "case": "none", "line": 1.05},
    "italic":  {"font": "Space Grotesk", "weight": 700, "size": 150, "tracking": "-.03em", "case": "none", "line": 1.0, "color": "accent"},
    "note":    {"font": "Space Grotesk", "weight": 600, "size": 60, "tracking": "-.01em", "case": "none", "line": 1.1, "color": "accent"}
  },
  "palette": {"background": "oklch(18% .025 215)", "card": "oklch(22% .025 215)", "brand": "oklch(36% .04 215)",
              "muted": "oklch(76% .02 215)", "level1": "oklch(66% .13 155)", "level2": "oklch(85% .15 92)",
              "level3": "oklch(55% .19 30)", "level4": "oklch(50% .2 25)", "level5": "oklch(34% .12 15)"},
  "band": {"top": 1130, "bottom": 1290, "gap": 14},
  "subtitles": {"y": 1310, "max_words": 4, "max_chars": 22},
  "material_bottom": 1600,
  "cut_punch": {"on": true, "scale": 1.04, "dur": 0.32},
  "push_in": {"scale": 1.04},
  "media": {"radius": 14, "shadow": "0 30px 70px oklch(5% .02 215 / .55)"},
  "pip": {"big": true, "width": 960, "max_h": 600, "top": 1010, "side": "right", "margin": 110},
  "split": {"height": 900, "shift": 420},
  "photo_stack": {"big": true, "cx": 540, "cy": 1190, "max_w": 760, "max_h": 420, "spread": 80, "tilt": 4},
  "reel_cards": {"w": 260, "h": 462},
  "orbit": {"cx": 540, "cy": 1110, "rx": 460, "ry": 150, "w": 190, "h": 338, "rev": 5.2},
  "sfx": {"photo-stack": "whoosh-short", "pip": "whoosh-short", "split": "whoosh-short", "reel-cards": "whoosh-short",
          "window-behind": "whoosh-short", "card-under-chin": "whoosh-short", "blur-pop": "pop", "behind-head": "pop",
          "focus-in": "whoosh-short"},
  "sfx_gain": 0.75
}
```
