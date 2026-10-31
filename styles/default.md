# Style: default

The footage stays exactly as filmed: no grade, no filter, no tint, no vignette, no film grain. Everything a style
changes sits on top of the video (text, inserts, motion, sound).

A style file is two things: this prose, which Claude reads when it writes the plan (what to use, when, how much),
and the JSON block at the bottom, which `build.py` reads for the exact values. To make a new style, copy this file
to `styles/<name>.md`, change both, and put `style: <name>` at the top of a plan.

## Cutting

- Cut dead air between sentences; keep a natural breath (start ~0.06s before the first word, end at the silence
  after the last word).
- Repeated takes: keep the last clean one unless the plan says otherwise.
- Cut filler ("um", false starts, "so, yeah") and sentences that repeat a point already made. Strike them in the
  plan with a reason so the user can bring them back.
- `cut-punch` on every cut (on by default, below). Turn it off for one cut with `- no-punch`.
- `zoom` (1.15-1.4) on every second or third segment when consecutive segments come from the same clip, so a hard
  cut does not look like a jump. The zoom centres on the face automatically. Use 1.5+ only for a dramatic beat.
- `push-in` for a calm, longer segment instead of a zoom. `focus-in` to open a new chapter (at most 2 per video).

## Text

One idea per caption, 1-4 words, lowercase. Text never covers the face (eyes to chin) and stays inside the
Reels safe zone (references/layout.md).

| ID | Use it for |
|---|---|
| `caption-lead` | Short lead-in lines over the chest band. The default for anything said that deserves text. |
| `blur-pop` | The one punch word of a sentence (big). Mark accent words with `*word*`. |
| `behind-head` | The most important word of a section, big, behind the head (needs the cutout). Max one per section. |
| `caps-track` + `serif-rise` | An editorial pair: small tracked caps line, then a big serif word. For dates, names, numbers. |
| `italic-punch` | A softer emphasis: one italic serif word in the accent colour. |
| `sparkle` | Twinkles next to an italic punch. Sparingly. |
| `hand-note` | A handwritten label with an arrow pointing at something in the frame. |

## Own material (photos and b-roll)

| ID | Use it for |
|---|---|
| `photo-stack` | Several photos that belong together (one event), each landing on its own word. The default for photos. |
| `pip` | One photo or clip shown while the speaker stays fully visible; for a reference ("this article", "the gauge"). |
| `split` | B-roll clips or a photo that needs to be big for a while (3s+); material on top, speaker below. |
| `reel-cards` | Portrait clips beside the face (e.g. other people's reels; add `credit=@handle`). |
| `orbit` | 4-6 portrait tiles circling the speaker. A show-off moment, at most once per video. |
| `window-behind` / `card-under-chin` | Animated screen recreations built by sub-agents (references/overlays.md). |

Photos and clips get rounded corners and a soft shadow. No white frames or borders.

Inserts never cover the face: `pip` and `photo-stack` sit below the chin (y ~960-1440), the same band as chest
text, so give text and a pip or photo stack different moments (or move the text with `y=`). For material that needs
to be big, use `split`.

## Sound

Subtle: a whoosh when material comes in, a pop for punch words, a sparkle with sparkles. Never louder than the voice.

## Values

```json
{
  "accent": "#FAE67A",
  "text_color": "#FFFFFF",
  "text_shadow": "0 10px 40px rgba(0,0,0,.55), 0 2px 8px rgba(0,0,0,.35)",
  "type": {
    "caption": {"font": "Inter Tight", "weight": 800, "size": 84, "tracking": "-.04em", "case": "lowercase", "line": 1.0},
    "punch":   {"font": "Inter Tight", "weight": 900, "size": 150, "tracking": "-.05em", "case": "lowercase", "line": 0.95},
    "behind":  {"font": "Inter Tight", "weight": 900, "size": 220, "tracking": "-.05em", "case": "lowercase", "line": 0.9},
    "caps":    {"font": "Montserrat", "weight": 500, "size": 34, "tracking": ".32em", "case": "uppercase", "line": 1.6},
    "serif":   {"font": "DM Serif Display", "weight": 400, "size": 210, "tracking": "-.02em", "case": "none", "line": 1.12},
    "italic":  {"font": "Instrument Serif", "weight": 400, "size": 170, "style": "italic", "case": "none", "line": 1.0, "color": "accent"},
    "note":    {"font": "Caveat", "weight": 600, "size": 80, "case": "none", "line": 1.0, "color": "accent"}
  },
  "band": {"top": 960, "bottom": 1440, "gap": 10},
  "cut_punch": {"on": true, "scale": 1.05, "dur": 0.32},
  "push_in": {"scale": 1.05},
  "media": {"radius": 28, "shadow": "0 30px 70px rgba(0,0,0,.5)"},
  "pip": {"width": 400, "max_h": 440, "top": 1010, "side": "right", "margin": 110},
  "split": {"height": 900, "shift": 420},
  "photo_stack": {"cx": 540, "cy": 1190, "max_w": 600, "max_h": 420, "spread": 80, "tilt": 6},
  "reel_cards": {"w": 260, "h": 462},
  "orbit": {"cx": 540, "cy": 1110, "rx": 460, "ry": 150, "w": 190, "h": 338, "rev": 5.2},
  "sfx": {"photo-stack": "whoosh-short", "pip": "whoosh-short", "split": "whoosh-short", "reel-cards": "whoosh-short",
          "orbit": "whoosh-short", "window-behind": "whoosh-short", "card-under-chin": "whoosh-short",
          "blur-pop": "pop", "behind-head": "pop", "sparkle": "sparkle", "focus-in": "whoosh-short"},
  "sfx_gain": 0.75
}
```
