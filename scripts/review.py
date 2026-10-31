#!/usr/bin/env python3
"""plan.md -> work/review.html: the plan as a page the user can read in one go (Step 2 of SKILL.md).

Usage:  PY review.py <project_dir>
Every segment shows a frame of the speaker, the spoken line (struck through when cut, with the reason), and its
effects as chips with thumbnails of the material they use. Self-contained (images inlined), so it publishes as an
Artifact as is. Re-run after every plan change and republish the same file path (same URL).
"""
import base64
import html as H
import io
import json
import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skillenv  # noqa: E402
from plan import EFFECTS, PlanError, check, parse  # noqa: E402

FF = skillenv.tool('ffmpeg')


def jpg_uri(im, w):
    im = im.convert('RGB')
    im.thumbnail((w, w * 2))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=70)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def frame(f, t):
    png = subprocess.run([FF, '-loglevel', 'error', '-ss', f'{t:.2f}', '-i', f, '-frames:v', '1', '-vf', 'scale=360:-2',
                          '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    return Image.open(io.BytesIO(png)) if png else None


CSS = '''
:root{--bg:#f4f5f3;--card:#fff;--fg:#1a1f1c;--muted:#5f6a64;--line:#d9dfdb;--accent:#1f6f78;--cut:#a8432f;--chip:#e7efed;
  --ui:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121715;--card:#1a211e;--fg:#e5ebe8;--muted:#98a59f;
  --line:#2d3934;--accent:#6cc1c9;--cut:#ec8f7b;--chip:#22302c;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#121715;--card:#1a211e;--fg:#e5ebe8;--muted:#98a59f;--line:#2d3934;--accent:#6cc1c9;--cut:#ec8f7b;
  --chip:#22302c;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--ui);font-size:15px;line-height:1.5}
.wrap{max-width:980px;margin:0 auto;padding-block:36px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));
  padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:28px}
h1{margin:0;font-size:28px;font-weight:600;text-wrap:balance}
h2{margin:0;font-size:18px;font-weight:600}
.sum{color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 18px;font-size:14px}
.err{background:var(--card);border:1px solid var(--cut);color:var(--cut);border-radius:8px;padding:12px 16px;font-family:var(--mono);font-size:13px}
section{display:grid;gap:12px}
.sh{display:flex;align-items:baseline;gap:10px;border-top:1px solid var(--line);padding-top:16px}
.sh span{color:var(--muted);font-family:var(--mono);font-size:12px}
.seg{display:grid;grid-template-columns:92px minmax(0,1fr);gap:14px;background:var(--card);border:1px solid var(--line);
  border-radius:10px;padding:12px}
.seg.cut{background:transparent;border-style:dashed;opacity:.75}
.seg img.f{width:92px;aspect-ratio:9/16;object-fit:cover;border-radius:6px;display:block;background:#000}
.seg.cut img.f{filter:grayscale(1)}
.body{display:grid;gap:8px;min-width:0;align-content:start}
.meta{font-family:var(--mono);font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 12px}
.line{font-size:16px}
.cut .line{text-decoration:line-through;color:var(--muted)}
.why{color:var(--cut);font-size:13px}
.fx{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:flex;align-items:center;gap:8px;background:var(--chip);border-radius:6px;padding:5px 9px;font-size:13px;max-width:100%}
.chip b{font-family:var(--mono);font-weight:500;color:var(--accent);font-size:12px}
.chip q{font-style:normal}
.chip img{height:44px;border-radius:4px;display:block}
.chip .t{color:var(--muted);font-family:var(--mono);font-size:11.5px}
footer{color:var(--muted);font-size:13px}
'''


def main():
    skillenv.utf8_stdio()
    proj = skillenv.path_arg(sys.argv[1])
    with open(os.path.join(proj, 'plan.md'), encoding='utf-8') as fh:
        try:
            plan = parse(fh.read())
        except PlanError as e:
            sys.exit(f'plan.md: {e}')
    errs = check(plan, proj)
    src = json.load(open(os.path.join(proj, 'sources.json'), encoding='utf-8'))
    mp = os.path.join(proj, 'materials.json')
    mats = {m['name']: m for m in json.load(open(mp, encoding='utf-8'))} if os.path.exists(mp) else {}
    thumbs = {}

    def mthumb(name):
        if name not in thumbs:
            m = mats.get(name)
            f = os.path.join(proj, m['file'] if m else name)
            im = None
            if os.path.exists(f):
                im = Image.open(f) if (m and m['kind'] == 'img') else frame(f, min(1.0, (m or {}).get('dur', 2) / 2))
            thumbs[name] = jpg_uri(im, 160) if im else ''
        return thumbs[name]

    kept = [s for sec in plan['sections'] for s in sec['segs'] if not s['cut']]
    allsegs = [s for sec in plan['sections'] for s in sec['segs']]
    out = [f'<title>{H.escape(plan["title"] or "Edit plan")}</title>',
           '<meta name="claude:viewport-fit-sides" content="cover">',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&'
           'family=IBM+Plex+Sans:wght@400;500;600&display=swap">', f'<style>{CSS}</style>', '<div class="wrap">',
           f'<header><h1>{H.escape(plan["title"] or "Edit plan")}</h1><div class="sum">'
           f'<span>{len(kept)} segments kept, {sum(s["out"] - s["in"] for s in kept):.0f}s</span>'
           f'<span>{len(allsegs) - len(kept)} cut</span><span>{sum(len(s["fx"]) for s in kept)} effects</span>'
           f'<span>style: {H.escape(plan["style"])}</span></div></header>']
    if errs:
        out.append('<div class="err">' + '<br>'.join(H.escape(e) for e in errs) + '</div>')
    clock = 0.0
    for sec in plan['sections']:
        dur = sum(s['out'] - s['in'] for s in sec['segs'] if not s['cut'])
        out.append(f'<section><div class="sh"><h2>{H.escape(sec["title"])}</h2><span>{dur:.1f}s</span></div>')
        for s in sec['segs']:
            im = frame(src[s['clip']], (s['in'] + s['out']) / 2) if s['clip'] in src else None
            when = '' if s['cut'] else f'at {int(clock // 60)}:{clock % 60:04.1f} · '
            if not s['cut']:
                clock += s['out'] - s['in']
            chips = []
            for fx in s['fx']:
                bits = [f'<b>{H.escape(fx["fx"])}</b>']
                if fx['fx'] == 'zoom':
                    bits.append(f'{fx["params"].get("zoom", "")}× on the face')
                if fx['text']:
                    bits.append(f'<q>“{H.escape(fx["text"])}”</q>')
                for m in fx['media']:
                    u = mthumb(m['file'])
                    bits.append(f'<img src="{u}" alt="{H.escape(m["file"])}">' if u else H.escape(m['file']))
                when_fx = ' '.join(x for x in [f'from “{fx["at"]}”' if fx['at'] else '', f'until “{fx["until"]}”' if fx['until'] else ''] if x)
                if when_fx:
                    bits.append(f'<span class="t">{H.escape(when_fx)}</span>')
                chips.append(f'<span class="chip">{" ".join(bits)}</span>')
            out.append(f'<div class="seg{" cut" if s["cut"] else ""}">'
                       + (f'<img class="f" src="{jpg_uri(im, 184)}" alt="">' if im else '<div></div>')
                       + f'<div class="body"><div class="meta"><span>{when}{s["clip"]} {s["in"]:.2f}–{s["out"]:.2f} '
                         f'({s["out"] - s["in"]:.1f}s)</span></div><div class="line">{H.escape(s["text"])}</div>'
                       + (f'<div class="why">Cut: {H.escape(s["reason"] or "no reason given")}</div>' if s['cut'] else '')
                       + (f'<div class="fx">{"".join(chips)}</div>' if chips else '') + '</div></div>')
        out.append('</section>')
    out.append(f'<footer>Generated from plan.md. Effect ids: {", ".join(EFFECTS)}.</footer></div>')
    dst = os.path.join(proj, 'work', 'review.html')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))
    print(f'wrote {dst}' + (f' ({len(errs)} plan problems shown at the top)' if errs else ''))


if __name__ == '__main__':
    main()
