#!/usr/bin/env python3
"""/sfv-edit build: timeline.json + style.md -> index.html (a HyperFrames composition). No per-video code: everything
comes from the plan (via plan.py) and the style's JSON block. Effect ids and parameters: references/plan-format.md.

Run from the project folder with PY, the skill's Python (see SKILL.md):
PY build.py            writes index.html
PY build.py --safe     same + red Instagram safe-zone guide (snapshots only, never render with it)

Needs: assets/aroll.mp4, segments.json (assemble.py), words.json (transcribe_cut.py), timeline.json (plan.py),
style.md (copied from the skill's styles/), materials.json (materials.py, if the plan uses material).
assets/subject.webm (cutout.py) only when the plan uses behind-head (or wants orbit / window-behind behind the speaker).
The footage is never filtered or graded: the base video goes in untouched.
"""
import html as H
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys

SAFE = '--safe' in sys.argv or bool(os.environ.get('SAFE'))
FFPROBE, FFMPEG = shutil.which('ffprobe') or 'ffprobe', shutil.which('ffmpeg') or 'ffmpeg'


def load(p, default=None):
    if not os.path.exists(p):
        if default is not None:
            return default
        sys.exit(f'missing {p}')
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def probe_dur(f):
    return float(subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                                capture_output=True, encoding='utf-8', errors='replace').stdout.strip() or 0)


DUR = probe_dur('assets/aroll.mp4')
SEGS = load('segments.json')
WORDS = load('words.json')
TL = load('timeline.json')
MATS = {m['name']: m for m in load('materials.json', [])}
with open('style.md', encoding='utf-8') as _f:
    _m = re.search(r'```json\s*(\{.*?\})\s*```', _f.read(), re.S)
if not _m:
    sys.exit('style.md has no ```json values block')
ST = json.loads(_m.group(1))
ACC = ST['accent']
CUTOUT = os.path.exists('assets/subject.webm')

T0 = {s['id']: s['frame'] / 30 for s in SEGS}                        # segment start in the cut
T1 = {s['id']: (s['frame'] + s['frames']) / 30 for s in SEGS}        # segment end in the cut
ORDER = [s['id'] for s in SEGS]
SEC_OF = {s['id']: s.get('sec', '') for s in SEGS}
SEC_END = {}
for s in SEGS:
    SEC_END[SEC_OF[s['id']]] = max(SEC_END.get(SEC_OF[s['id']], 0), T1[s['id']])
# cut times = first frame of each segment, nudged 2ms early so a tl.set lands ON that frame
CUT = {s['id']: s['frame'] / 30 - .002 for s in SEGS[1:]}


def norm(w):
    return re.sub(r'[^\wäöüß]', '', w.lower())


def find_word(anchor, segs):
    """First (or #n-th) word in the given segments whose text starts with the anchor."""
    word, _, nth = anchor.partition('#')
    want, n = norm(word), int(nth or 1)
    for sid in segs:
        cands = [w for w in WORDS if T0[sid] - .15 <= w['start'] < T1[sid] + .05]
        hits = [w for w in cands if norm(w['text']) == want] or [w for w in cands if norm(w['text']).startswith(want)]
        if len(hits) >= n:
            return hits[n - 1]
        n -= len(hits)
    said = ' '.join(w['text'] for w in WORDS if T0[segs[0]] - .15 <= w['start'] < T1[segs[0]] + .05)
    sys.exit(f"anchor '{anchor}' not found in segment {segs[0]} (Whisper heard: {said}). Fix the anchor in plan.md.")


def t_at(seg, a):
    if not a:
        return T0[seg]
    if re.fullmatch(r'[+]?\d+(\.\d+)?', a):
        return T0[seg] + float(a)
    return max(T0[seg], find_word(a, [seg])['start'] - .05)


def t_until(seg, a):
    i = ORDER.index(seg)
    if not a or a == 'end':
        return T1[seg]
    if a == 'sec':
        return SEC_END[SEC_OF[seg]]
    if a == 'next':
        return T1[ORDER[min(i + 1, len(ORDER) - 1)]]
    if re.fullmatch(r'[+]?\d+(\.\d+)?', a):
        return T0[seg] + float(a)
    later = [s for s in ORDER[i:] if SEC_OF[s] == SEC_OF[seg]]
    return min(DUR, find_word(a, later)['end'] + .1)


# ------------------------------------------------------------------ output collectors
BACK, FRONT, TW, SFX = [], [], [], []
CLIP_AUDIO = []  # <audio> of cutaways with sound=
_n = [0]
_track = [20]


def nid(p='x'):
    _n[0] += 1
    return f'{p}{_n[0]}'


def track():
    _track[0] += 1
    return _track[0]


def exit_(sel, b, how="autoAlpha:0,duration:.15,ease:'power2.in'"):
    if b < DUR - .01:
        TW.append(f"tl.to('{sel}',{{{how}}},{max(0, b - .15):.3f});")
        TW.append(f"tl.set('{sel}',{{autoAlpha:0}},{b:.3f});")


def sfx_for(kind, t, vol=.25):
    name = ST.get('sfx', {}).get(kind)
    if name:
        SFX.append((name, t, vol))


def text_html(txt):
    """escape, then *word* -> accent colour; wrapped in .bx, which a style can turn into a pill (type.<role>.box).
    "small | big": the part before | is a smaller lead line above (type.<role>.lead, a share of the size)"""
    acc = lambda t: re.sub(r'\*([^*]+)\*', r'<span class="acc">\1</span>', H.escape(t.strip()))
    lead, bar, main = txt.partition('|')
    if not bar:
        return '<span class="bx">' + acc(txt) + '</span>'
    return f'<span class="bx ld">{acc(lead)}</span><br><span class="bx">{acc(main)}</span>'


# chest band: text without a y= stacks downward under whatever text is still on screen
BAND = []
BOXES = []   # (t, b, x0, y0, x1, y1, what) of pips / photo stacks, checked against BAND text at the end


def band_y(t, b, h, fx):
    if 'y' in fx['params']:
        return float(fx['params']['y'])
    bd = ST['band']
    y = bd['top']
    for (a, z, top, bot) in sorted(BAND, key=lambda r: r[2]):
        if a < b and t < z and y < bot and y + h > top:
            y = bot + bd['gap']
    if y + h > bd['bottom']:
        print(f"  warning: text at {t:.2f}s runs below the chest band (y {y:.0f}+{h:.0f}); split it or set y=")
    BAND.append((t, b, y, y + h))
    return y


def role_h(role, txt=''):
    r = ST['type'][role]
    pad = 0
    if r.get('box'):   # a pill adds its vertical padding (first value of "pad", in em) top and bottom
        pad = 2 * float(r['box'].get('pad', '.2em').split()[0].replace('em', '') or 0)
    h = r['size'] * (r.get('line', 1) + pad)
    return h * (1 + r.get('lead', .6)) if '|' in txt else h


# ------------------------------------------------------------------ camera
def cam_effects():
    flags = {}
    for fx in TL['fx']:
        flags.setdefault(fx['seg'], set()).add(fx['fx'])
    cp = ST.get('cut_punch', {})
    if cp.get('on'):
        for sid, c in CUT.items():
            if not flags.get(sid, set()) & {'no-punch', 'push-in', 'split'}:
                TW.append(f"tl.fromTo('#cam1',{{scale:{cp['scale']}}},{{scale:1,duration:{cp['dur']},ease:'power2.out',"
                          f"immediateRender:false}},{c:.3f});")


def fx_push_in(fx, t, b):
    TW.append(f"tl.fromTo('#cam2',{{scale:1}},{{scale:{ST['push_in']['scale']},duration:{b - t:.3f},ease:'none',"
              f"immediateRender:false}},{t:.3f});")
    TW.append(f"tl.set('#cam2',{{scale:1}},{b:.3f});")


def fx_focus_in(fx, t, b):
    TW.append(f"tl.fromTo('#cam1',{{filter:'blur(18px) brightness(1.35)'}},{{filter:'blur(0px) brightness(1)',duration:.45,"
              f"ease:'power3.out',immediateRender:false}},{t:.3f});")
    TW.append(f"tl.set('#cam1',{{filter:'none'}},{t + .47:.3f});")
    sfx_for('focus-in', t)


def fx_light_sweep(fx, t, b):
    i = nid('sw')
    FRONT.append(f'<div id="{i}" class="fx sweep"></div>')
    TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});", f"tl.set('#{i}',{{autoAlpha:1}},{t:.3f});",
               f"tl.fromTo('#{i}',{{backgroundPosition:'130% 0%'}},{{backgroundPosition:'-30% 0%',duration:1.3,ease:'power2.inOut',"
               f"immediateRender:false}},{t:.3f});", f"tl.set('#{i}',{{autoAlpha:0}},{t + 1.35:.3f});"])


# ------------------------------------------------------------------ text
def pop(i, t, b):
    TW.append(f"gsap.set('#{i}',{{autoAlpha:0}});")
    TW.append(f"tl.fromTo('#{i}',{{autoAlpha:0,scale:1.22,filter:'blur(22px)'}},{{autoAlpha:1,scale:1,filter:'blur(0px)',"
              f"duration:.2,ease:'power3.out',immediateRender:false}},{t:.3f});")
    exit_(f'#{i}', b, "autoAlpha:0,scale:.96,filter:'blur(16px)',duration:.12,ease:'power2.in'")


def fx_caption_lead(fx, t, b, role='caption'):
    i = nid('t')
    y = band_y(t, b, role_h(role, fx['text']), fx)
    FRONT.append(f'<div id="{i}" class="tx r-{role}" style="top:{y:.0f}px">{text_html(fx["text"])}</div>')
    pop(i, t, b)


def fx_blur_pop(fx, t, b):
    fx_caption_lead(fx, t, b, 'punch')
    sfx_for('blur-pop', t)


def head_top(t):
    png = subprocess.run([FFMPEG, '-loglevel', 'error', '-c:v', 'libvpx-vp9', '-ss', f'{t:.2f}', '-i', 'assets/subject.webm',
                          '-frames:v', '1', '-vf', 'alphaextract,scale=270:480', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                         capture_output=True).stdout
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert('L')
    px, (w, h) = im.load(), im.size
    return next((y * 4 for y in range(h) if any(px[x, y] > 128 for x in range(0, w, 2))), None)


def fx_behind_head(fx, t, b):
    if not CUTOUT:
        sys.exit('behind-head needs assets/subject.webm: run cutout.py first')
    S = ST['type']['behind']['size']
    if 'y' in fx['params']:
        top = float(fx['params']['y'])
    else:
        ht = head_top(t + .1)
        if ht is None:
            sys.exit(f'behind-head at {t:.2f}s: no person in the cutout frame')
        top = ht + .15 * S - .72 * S   # baseline ~30% of the x-height below the head top (layout.md)
        if top < 220:
            print(f"  warning: behind-head '{fx['text']}' at {t:.2f}s would start at y {top:.0f}, above the safe zone; "
                  'use a shorter word or put it in front')
    i = nid('t')
    BACK.append(f'<div id="{i}" class="tx r-behind" style="top:{top:.0f}px">{text_html(fx["text"])}</div>')
    pop(i, t, b)
    sfx_for('behind-head', t)


def fx_caps_track(fx, t, b):
    i = nid('t')
    y = band_y(t, b, role_h('caps'), fx)
    spans = '<span class="bx">' + ''.join(f'<span class="tw">{H.escape(w)}</span>' for w in fx['text'].split()) + '</span>'
    FRONT.append(f'<div id="{i}" class="tx r-caps" style="top:{y:.0f}px">{spans}</div>')
    # "tracking in" done with scaleX: letterSpacing tweens are rejected by lint
    # hide the whole line (a style's pill box too) until its start, not only the words
    TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});", f"tl.set('#{i}',{{autoAlpha:1}},{t:.3f});",
               f"gsap.set('#{i} .tw',{{autoAlpha:0}});",
               f"tl.fromTo('#{i} .tw',{{autoAlpha:0,scaleX:1.45,filter:'blur(8px)'}},{{autoAlpha:1,scaleX:1,filter:'blur(0px)',"
               f"duration:.45,ease:'power3.out',stagger:.1,immediateRender:false}},{t:.3f});"])
    exit_(f'#{i}', b)


def fx_serif_rise(fx, t, b):
    i = nid('t')
    y = band_y(t, b, role_h('serif'), fx)
    chars = ''.join(f'<span class="mk"><span class="ch">{"&nbsp;" if c == " " else H.escape(c)}</span></span>' for c in fx['text'])
    FRONT.append(f'<div id="{i}" class="tx r-serif" style="top:{y:.0f}px">{chars}</div>')
    TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});", f"tl.set('#{i}',{{autoAlpha:1}},{t:.3f});",
               f"tl.fromTo('#{i} .ch',{{yPercent:115}},{{yPercent:0,duration:.6,ease:'expo.out',stagger:.028,immediateRender:false}},{t:.3f});",
               f"tl.fromTo('#{i}',{{scale:1.06,filter:'blur(6px)'}},{{scale:1,filter:'blur(0px)',duration:.4,ease:'power3.out',"
               f"immediateRender:false}},{t:.3f});"])
    exit_(f'#{i}', b, "autoAlpha:0,y:-14,filter:'blur(10px)',duration:.15,ease:'power2.in'")


def fx_italic_punch(fx, t, b):
    i = nid('t')
    y = band_y(t, b, role_h('italic'), fx)
    FRONT.append(f'<div id="{i}" class="tx r-italic" style="top:{y:.0f}px">{text_html(fx["text"])}</div>')
    TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});",
               f"tl.fromTo('#{i}',{{autoAlpha:0,y:22,scale:.92}},{{autoAlpha:1,y:0,scale:1,duration:.4,ease:'power2.out',"
               f"immediateRender:false}},{t:.3f});"])
    exit_(f'#{i}', b)


def fx_sparkle(fx, t, b):
    x, y = float(fx['params'].get('x', 540)), float(fx['params'].get('y', ST['band']['top'] - 40))
    for k, (dx, dy, sz) in enumerate([(-380, 10, 58), (380, 100, 40), (340, -130, 30)]):
        i = nid('sp')
        FRONT.append(f'<div id="{i}" class="spark" style="left:{x + dx:.0f}px;top:{y + dy:.0f}px;font-size:{sz}px">&#10022;</div>')
        tk = t + k * .14
        TW.extend([f"gsap.set('#{i}',{{autoAlpha:0,scale:0}});",
                   f"tl.to('#{i}',{{autoAlpha:1,scale:1,duration:.3,ease:'back.out(2.5)'}},{tk:.3f});",
                   f"tl.to('#{i}',{{scale:.7,duration:.4,yoyo:true,repeat:1,ease:'sine.inOut'}},{tk + .3:.3f});"])
        exit_(f'#{i}', b)
    sfx_for('sparkle', t)


def fx_hand_note(fx, t, b):
    p = fx['params']
    x, y = float(p.get('x', 120)), float(p.get('y', 300))
    S = ST['type']['note']['size']
    tx, ty = (float(v) for v in p.get('to', f'{x + 220:.0f},{y + 300:.0f}').split(','))
    sx, sy = x + 60, y + S * 1.1
    mx, my = sx + (tx - sx) * .2, sy + (ty - sy) * .8   # bow the line like a hand-drawn arrow
    ang = math.atan2(ty - my, tx - mx)
    head = ' '.join(f'M{tx:.0f} {ty:.0f} L{tx - 34 * math.cos(ang + d):.0f} {ty - 34 * math.sin(ang + d):.0f}' for d in (.5, -.5))
    i = nid('hn')
    FRONT.append(f'<div id="{i}" class="hn"><div class="tx r-note" style="left:{x:.0f}px;right:auto;top:{y:.0f}px">'
                 f'{H.escape(fx["text"])}</div><svg width="1080" height="1920" viewBox="0 0 1080 1920" style="position:absolute;inset:0">'
                 f'<path d="M{sx:.0f} {sy:.0f} Q{mx:.0f} {my:.0f} {tx:.0f} {ty:.0f} {head}" pathLength="1" fill="none" stroke="{ACC}" '
                 f'stroke-width="7" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1" stroke-dashoffset="1"/></svg></div>')
    TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});", f"tl.set('#{i}',{{autoAlpha:1}},{t:.3f});",
               f"tl.fromTo('#{i} .tx',{{autoAlpha:0,y:10}},{{autoAlpha:1,y:0,duration:.3,ease:'power2.out',immediateRender:false}},{t:.3f});",
               f"tl.fromTo('#{i} path',{{strokeDashoffset:1}},{{strokeDashoffset:0,duration:.6,ease:'power2.inOut',immediateRender:false}},{t + .2:.3f});"])
    exit_(f'#{i}', b)


# ------------------------------------------------------------------ media
def mat(name):
    m = MATS.get(name)
    if m:
        return m['file'], m['kind'], m['w'], m['h']
    if not os.path.exists(name):
        sys.exit(f'material {name} not found')
    kind = 'video' if name.lower().endswith(('.mp4', '.mov', '.webm', '.m4v')) else 'img'
    return name, kind, 0, 0


def media_el(name, t, b, style='', frm=0.0):
    """<img> or a timed <video> for one material, filling its box. The wrapper is what gets animated."""
    f, kind, _, _ = mat(name)
    css = f'width:100%;height:100%;object-fit:cover;display:block;{style}'
    if kind == 'img':
        return f'<img src="{H.escape(f)}" style="{css}">'
    return (f'<video id="{nid("v")}" src="{H.escape(f)}" muted playsinline data-start="{max(0, t - .05):.3f}" '
            f'data-media-start="{frm:.3f}" data-duration="{b - t + .15:.3f}" data-track-index="{track()}" style="{css}"></video>')


def item_times(fx, seg, t, b):
    """start time of each media item: its own @anchor, else spread evenly from the effect start"""
    n = len(fx['media'])
    return [t_at(seg, m['at']) if m['at'] else t + k * min(.5, (b - t) / max(n, 1)) for k, m in enumerate(fx['media'])]


def aspect(name, default=4 / 3):
    _, _, w, h = mat(name)
    return w / h if w and h else default


def overlap_warnings():
    for (a, z, top, bot) in BAND:
        for (t, b, x0, y0, x1, y1, what) in BOXES:
            if a < b and t < z and top < y1 and bot > y0:
                print(f'  warning: text at {a:.2f}s overlaps the {what} at {t:.2f}s; give them different moments or set y=')


def chin(t, b):
    """lowest chin (y in the frame) of the segments on screen between t and b; inserts start below it"""
    return max([s['chin_y'] for s in SEGS if 'chin_y' in s and T0[s['id']] < b and t < T1[s['id']]] or [0])


def below_chin(t, b, top, h, what):
    """push a box below the chin, shrink it to end above the safe line (y 1450); returns top, max height"""
    top = max(top, chin(t, b) + 40)
    if top + h > 1450:
        h = 1450 - top
        if h < 260:
            print(f'  warning: little room under the chin for the {what} at {t:.2f}s (h {h:.0f}); use split instead')
    return top, max(h, 200)


def room(t, b):
    """top and bottom of the free area under the chin for big material (the speaker never moves for it)"""
    return chin(t, b) + 55, ST.get('material_bottom', 1450)   # beard and hand reach a bit below the detected chin


def card_box(i, css, inner):
    r, sh = ST['media']['radius'], ST['media']['shadow']
    FRONT.append(f'<div id="{i}" class="mbox" style="{css}"><div class="mclip" style="border-radius:{r}px;box-shadow:{sh}">'
                 f'{inner}</div></div>')


def fx_photo_stack(fx, t, b):
    ps = dict(ST['photo_stack'])
    sp, tilt = ps['spread'], ps['tilt']
    if ST['photo_stack'].get('big'):
        top, bot = room(t, b)
        ps['max_h'] = bot - top
    else:
        top, ps['max_h'] = below_chin(t, b, ps['cy'] - ps['max_h'] / 2 - 40, ps['max_h'] + 80, 'photo-stack')
    ps['max_h'] -= 80   # 40px each side for the drop offsets and tilt
    ps['cy'] = top + 40 + ps['max_h'] / 2
    offs = [(-sp, -10, -tilt), (sp, 20, tilt * .8), (-sp * .75, -30, tilt * .6), (sp * .9, 10, -tilt * .7),
            (-sp, 40, -tilt), (sp * .75, -20, tilt)]
    ids = []
    for k, (m, tk) in enumerate(zip(fx['media'], item_times(fx, fx['seg'], t, b))):
        a = aspect(m['file'])
        w, h = (ps['max_w'], ps['max_w'] / a) if a >= ps['max_w'] / ps['max_h'] else (ps['max_h'] * a, ps['max_h'])
        dx, dy, rot = offs[k % len(offs)]
        i = nid('ps')
        ids.append(i)
        BOXES.append((tk, b, ps['cx'] + dx - w / 2, ps['cy'] + dy - h / 2, ps['cx'] + dx + w / 2, ps['cy'] + dy + h / 2, 'photo-stack'))
        card_box(i, f"left:{ps['cx'] + dx - w / 2:.0f}px;top:{ps['cy'] + dy - h / 2:.0f}px;width:{w:.0f}px;height:{h:.0f}px",
                 media_el(m['file'], tk, b, frm=float(fx['params'].get('from', 0))))
        TW.extend([f"gsap.set('#{i}',{{autoAlpha:0,y:420,rotation:{rot * 2.2:.1f},scale:1.12}});",
                   f"tl.to('#{i}',{{autoAlpha:1,y:0,rotation:{rot:.1f},scale:1,duration:.55,ease:'power3.out'}},{tk:.3f});"])
        sfx_for('photo-stack', tk, .16)
    if b < DUR - .01:
        TW.append(f"tl.to([{','.join(repr('#' + i) for i in ids)}],{{autoAlpha:0,y:260,duration:.35,ease:'power2.in',"
                  f"stagger:.04}},{max(t, b - .35):.3f});")
        TW.append(f"tl.set('{','.join('#' + i for i in ids)}',{{autoAlpha:0}},{b + .1:.3f});")


def swap_items(fx, box_id, t, b):
    """several media in one box (pip, split): each shows from its start until the next one starts"""
    ts = item_times(fx, fx['seg'], t, b)
    inner = []
    for k, (m, tk) in enumerate(zip(fx['media'], ts)):
        end = ts[k + 1] if k + 1 < len(ts) else b
        j = f'{box_id}-{k}'
        inner.append(f'<div id="{j}" class="mlayer">{media_el(m["file"], tk, end, frm=float(fx["params"].get("from", 0)))}</div>')
        if k:
            TW.extend([f"gsap.set('#{j}',{{autoAlpha:0}});",
                       f"tl.to('#{j}',{{autoAlpha:1,duration:.2,ease:'power1.out'}},{tk:.3f});"])
    return ''.join(inner)


def fx_pip(fx, t, b):
    pp, p = ST['pip'], fx['params']
    a = aspect(fx['media'][0]['file'])
    if pp.get('big') and 'top' not in p:   # big card centred under the chin, as large as the room allows
        top, bot = room(t, b)
        w = min(float(p.get('width', pp['width'])), 1080 - 2 * 60)
        h = min(w / a, bot - top)
        w = h * a
        x = (1080 - w) / 2
        i = nid('pip')
        BOXES.append((t, b, x, top, x + w, top + h, 'pip'))
        card_box(i, f'left:{x:.0f}px;top:{top:.0f}px;width:{w:.0f}px;height:{h:.0f}px', swap_items(fx, i, t, b))
        TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});",
                   f"tl.fromTo('#{i}',{{autoAlpha:0,y:60,scale:.92}},{{autoAlpha:1,y:0,scale:1,duration:.4,ease:'power3.out',"
                   f"immediateRender:false}},{t + .15:.3f});"])
        exit_(f'#{i}', b, "autoAlpha:0,y:40,duration:.2,ease:'power2.in'")
        sfx_for('pip', t, .2)
        return
    w = float(p.get('width', pp['width']))
    h = w / a
    if h > pp['max_h']:   # tall photo: keep its shape, shrink the width instead of cropping
        h, w = pp['max_h'], pp['max_h'] * a
    side = p.get('side', pp['side'])
    x = 1080 - pp['margin'] - w if side == 'right' else pp['margin']
    top, mh = below_chin(t, b, float(p.get('top', pp['top'])), h, 'pip')
    if h > mh:
        h, w = mh, mh * a
    i = nid('pip')
    BOXES.append((t, b, x, top, x + w, top + h, 'pip'))
    card_box(i, f'left:{x:.0f}px;top:{top:.0f}px;width:{w:.0f}px;height:{h:.0f}px', swap_items(fx, i, t, b))
    TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});",
               f"tl.fromTo('#{i}',{{autoAlpha:0,scale:.85}},{{autoAlpha:1,scale:1,duration:.3,ease:'power3.out',immediateRender:false}},{t:.3f});"])
    exit_(f'#{i}', b, "autoAlpha:0,scale:.9,duration:.15,ease:'power2.in'")
    sfx_for('pip', t, .2)


def fx_split(fx, t, b):
    sp, p = ST['split'], fx['params']
    h, shift = float(p.get('height', sp['height'])), float(p.get('shift', sp['shift']))
    i = nid('split')
    FRONT.append(f'<div id="{i}" class="split" style="height:{h:.0f}px">{swap_items(fx, i, t, b)}</div>')
    TW.extend([f"gsap.set('#{i}',{{yPercent:-100}});",
               f"tl.to('#{i}',{{yPercent:0,duration:.45,ease:'power3.out'}},{t:.3f});",
               f"tl.to('#cam2',{{y:{shift:.0f},duration:.45,ease:'power3.out'}},{t:.3f});"])
    if b < DUR - .01:
        TW.extend([f"tl.to('#{i}',{{yPercent:-100,duration:.4,ease:'power2.in'}},{b - .4:.3f});",
                   f"tl.to('#cam2',{{y:0,duration:.4,ease:'power2.in'}},{b - .4:.3f});"])
    sfx_for('split', t, .2)


def mat_audio(name):
    """a material's own sound as <copy>.m4a (materials.py strips audio from the copies), cut once from the original"""
    m = MATS.get(name) or sys.exit(f'sound= needs a material from materials.json: {name}')
    out = os.path.splitext(m['file'])[0] + '.m4a'
    if not os.path.exists(out):
        subprocess.run([FFMPEG, '-loglevel', 'error', '-y', '-i', m['src'], '-vn', '-c:a', 'aac', '-b:a', '192k', out])
        if not os.path.exists(out):
            sys.exit(f'{name}: its original {m["src"]} has no sound (slowed copies are made without it)')
    return out


def fx_cutaway(fx, t, b):
    """full-frame material with a hard cut in and out, no whoosh (Arne: no swipe, no whoosh on cutaways).
    sound=<vol> also plays each clip's own audio under the voice (e.g. sound=0.5)."""
    i = nid('cut')
    FRONT.append(f'<div id="{i}" class="split" style="height:1920px;box-shadow:none">{swap_items(fx, i, t, b)}</div>')
    TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});", f"tl.set('#{i}',{{autoAlpha:1}},{t:.3f});", f"tl.set('#{i}',{{autoAlpha:0}},{b:.3f});"])
    if 'sound' in fx['params']:
        vol, frm = float(fx['params']['sound']), float(fx['params'].get('from', 0))
        ts = item_times(fx, fx['seg'], t, b)
        for k, (m, tk) in enumerate(zip(fx['media'], ts)):
            if mat(m['file'])[1] != 'video':
                continue
            end = ts[k + 1] if k + 1 < len(ts) else b
            CLIP_AUDIO.append(f'<audio id="{nid("ca")}" src="{H.escape(mat_audio(m["file"]))}" data-start="{tk:.3f}" '
                              f'data-media-start="{frm:.3f}" data-duration="{end - tk:.3f}" data-track-index="{track()}" '
                              f'data-volume="{vol:.3f}"></audio>')


def fx_reel_cards(fx, t, b):
    rc = ST['reel_cards']
    spots = [(55, 430, -7), (765, 400, 6), (70, 480, -5), (745, 470, 5)]
    credit = fx['params'].get('credit')
    r, sh = ST['media']['radius'], ST['media']['shadow']
    for k, (m, tk) in enumerate(zip(fx['media'], item_times(fx, fx['seg'], t, b))):
        x, y, rot = spots[k % len(spots)]
        i = nid('rc')
        pill = f'<div class="pill">{H.escape(credit)}</div>' if credit else ''
        FRONT.append(f'<div id="{i}" class="mbox" style="left:{x}px;top:{y}px;width:{rc["w"]}px">'
                     f'<div class="mclip" style="height:{rc["h"]}px;border-radius:{r}px;box-shadow:{sh}">{media_el(m["file"], tk, b)}</div>{pill}</div>')
        TW.extend([f"gsap.set('#{i}',{{autoAlpha:0,rotation:{rot},scale:.4,y:60}});",
                   f"tl.to('#{i}',{{autoAlpha:1,scale:1,y:0,duration:.42,ease:'back.out(1.6)'}},{tk:.3f});"])
        exit_(f'#{i}', b, f"autoAlpha:0,scale:.7,y:-40,rotation:{rot * 2},duration:.15,ease:'power2.in'")
        sfx_for('reel-cards', tk, .2)


def fx_orbit(fx, t, b):
    o = ST['orbit']
    n, step = len(fx['media']), .1
    r = ST['media']['radius'] * .7
    sides = ('b', 'f') if CUTOUT else ('f',)   # without a cutout nothing can pass behind the speaker
    for k, m in enumerate(fx['media']):
        frames, tt = [], t
        while tt <= b + 1e-6:
            th = 2 * math.pi * ((tt - t) / o['rev']) + k * 2 * math.pi / n + .35
            s = math.sin(th)
            frames.append((tt, o['cx'] + o['rx'] * math.cos(th), o['cy'] + o['ry'] * s, .6 + .4 * (s + 1) / 2, s))
            tt = round(tt + step, 4)
        for side in sides:
            i = nid('ob')
            (BACK if side == 'b' else FRONT).append(
                f'<div id="{i}" class="orb" style="width:{o["w"]}px;height:{o["h"]}px"><div class="opop mclip" '
                f'style="border-radius:{r:.0f}px;box-shadow:{ST["media"]["shadow"]}">{media_el(m["file"], t, b)}</div></div>')
            if len(sides) == 1:
                vis = lambda s: 1   # noqa: E731
            elif side == 'f':
                vis = lambda s: 1 if s > 0 else 0   # noqa: E731
            else:
                vis = lambda s: 0 if s > 0 else 1   # noqa: E731
            t0, x0, y0, sc0, s0 = frames[0]
            kf = ','.join(f"{{x:{x:.1f},y:{y:.1f},scale:{sc:.3f},autoAlpha:{vis(s)},duration:{step},ease:'none'}}"
                          for _, x, y, sc, s in frames[1:])
            TW.extend([f"gsap.set('#{i}',{{xPercent:-50,yPercent:-50,x:{x0:.1f},y:{y0:.1f},scale:{sc0:.3f},autoAlpha:0}});",
                       f"tl.set('#{i}',{{autoAlpha:{vis(s0)}}},{t0:.3f});",
                       f"tl.to('#{i}',{{keyframes:[{kf}]}},{t0:.3f});", f"tl.set('#{i}',{{autoAlpha:0}},{b:.3f});",
                       f"gsap.set('#{i} .opop',{{scale:0}});",
                       f"tl.to('#{i} .opop',{{scale:1,duration:.45,ease:'back.out(1.8)'}},{t + k * .07:.3f});",
                       f"tl.to('#{i} .opop',{{scale:0,duration:.2,ease:'power2.in'}},{b - .24:.3f});"])
    sfx_for('orbit', t)


def overlay_webm(fx, t, b, layer, css):
    i = nid('ov')
    layer.append(f'<div id="{i}" class="ov" style="{css}">{media_el(fx["media"][0]["file"], t, b, "object-fit:contain")}</div>')
    TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});", f"tl.set('#{i}',{{autoAlpha:1}},{t:.3f});", f"tl.set('#{i}',{{autoAlpha:0}},{b:.3f});"])


def fx_window_behind(fx, t, b):
    p = fx['params']
    overlay_webm(fx, t, b, BACK, f"left:{p.get('left', 40)}px;top:{p.get('top', 230)}px;width:{p.get('w', 1000)}px;height:{p.get('h', 720)}px;"
                                 "filter:drop-shadow(0 30px 60px rgba(0,0,0,.35))")
    sfx_for('window-behind', t)


def fx_card_under_chin(fx, t, b):
    p = fx['params']
    overlay_webm(fx, t, b, FRONT, f"left:{p.get('left', 110)}px;top:{p.get('top', 745)}px;width:{p.get('w', 860)}px;height:{p.get('h', 1000)}px;"
                                  f"transform:perspective(1800px) rotateX({p.get('tilt', 7)}deg) scale({p.get('scale', .72)});transform-origin:50% 0%;"
                                  "filter:drop-shadow(0 40px 80px rgba(0,0,0,.55))")
    sfx_for('card-under-chin', t)


def subtitles():
    """Running subtitles for every kept line (style "subtitles"): the plan's text (what was said, names fixed), timed by
    the cut's Whisper words, in chunks of a few words that may run across cuts; *starred* words turn the accent colour."""
    sb = ST.get('subtitles')
    if not sb:
        return
    stream = []   # (word, start in the cut, end of its segment)
    for s in SEGS:
        sid, pw = s['id'], s.get('line', '').split()
        ww = [w for w in WORDS if T0[sid] - .1 <= w['start'] < T1[sid] - .02]
        for k, w in enumerate(pw):
            # plan word k gets the time of Whisper word k scaled to the counts (they differ where Whisper split or merged words)
            t = (ww[min(len(ww) - 1, k * len(ww) // len(pw))]['start'] - .05) if ww else T0[sid] + (T1[sid] - T0[sid]) * k / len(pw)
            stream.append((w, max(T0[sid], t), T1[sid]))
    chunks, cur = [], []
    for k, (w, t, e) in enumerate(stream):
        cur.append(k)
        text = ' '.join(stream[j][0] for j in cur).replace('*', '')
        gap = k + 1 < len(stream) and stream[k + 1][1] - e > .6   # a long pause after this word: start a new chunk
        if len(cur) >= sb['max_words'] or len(text) >= sb['max_chars'] or re.search(r'[.,!?;:]$', w.replace('*', '')) or gap:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    for c, idx in enumerate(chunks):
        a = stream[idx[0]][1]
        z = min(stream[chunks[c + 1][0]][1], stream[idx[-1]][2] + .4) if c + 1 < len(chunks) else stream[idx[-1]][2]
        if z - a < .12 or any(a < t1 and t0 < z - .05 for t0, t1 in NOSUBS):   # hidden if it overlaps a no-subs span at all
            continue
        words = [stream[j][0] for j in idx]
        words[-1] = re.sub(r'[,;:](\*?)$', r'\1', words[-1])   # no trailing comma on screen
        # material on screen: the subtitle moves down onto the picture's bottom edge
        y = max([sb['y']] + [y1 - 45 for (t0, t1, x0, y0, x1, y1, what) in BOXES if t0 < z and a < t1])
        i, inner = nid('sub'), text_html(' '.join(words))
        FRONT.append(f'<div id="{i}" class="tx r-sub" style="top:{y:.0f}px">{inner}</div>')
        TW.extend([f"gsap.set('#{i}',{{autoAlpha:0}});", f"tl.set('#{i}',{{autoAlpha:1}},{a:.3f});",
                   f"tl.fromTo('#{i}',{{y:10}},{{y:0,duration:.18,ease:'power2.out',immediateRender:false}},{a:.3f});",
                   f"tl.set('#{i}',{{autoAlpha:0}},{min(z, DUR) - .002:.3f});"])


NOSUBS = []   # (t, b): no subtitles start in here (the line is already on screen as big text)


def fx_no_subs(fx, t, b):
    NOSUBS.append((t, b))


def fx_sfx(fx, t, b):
    SFX.append((fx['params']['name'], t, float(fx['params'].get('vol', .5))))


HANDLERS = {'push-in': fx_push_in, 'focus-in': fx_focus_in, 'light-sweep': fx_light_sweep,
            'caption-lead': fx_caption_lead, 'blur-pop': fx_blur_pop, 'behind-head': fx_behind_head,
            'caps-track': fx_caps_track, 'serif-rise': fx_serif_rise, 'italic-punch': fx_italic_punch,
            'sparkle': fx_sparkle, 'hand-note': fx_hand_note, 'photo-stack': fx_photo_stack, 'pip': fx_pip,
            'split': fx_split, 'cutaway': fx_cutaway, 'reel-cards': fx_reel_cards, 'orbit': fx_orbit, 'window-behind': fx_window_behind,
            'card-under-chin': fx_card_under_chin, 'sfx': fx_sfx, 'no-punch': None, 'no-subs': fx_no_subs}


def audio():
    out, lanes, lens = list(CLIP_AUDIO), [], {}
    for k, (name, t, vol) in enumerate(sorted(SFX, key=lambda x: x[1])):
        f = f'assets/sfx/{name}.mp3'
        if not os.path.exists(f):
            print(f'  warning: sound {f} missing, skipped')
            continue
        lens.setdefault(name, probe_dur(f))
        d = min(lens[name], DUR - t)
        lane = next((i for i, end in enumerate(lanes) if end <= t), None)
        if lane is None:
            lanes.append(0)
            lane = len(lanes) - 1
        lanes[lane] = t + d
        out.append(f'<audio id="sfx{k}" src="{f}" data-start="{t:.3f}" data-duration="{d:.3f}" '
                   f'data-track-index="{10 + lane}" data-volume="{vol * ST.get("sfx_gain", .75):.3f}"></audio>')
    return out


def type_css():
    out = []
    for role, r in ST['type'].items():
        col = ACC if r.get('color') == 'accent' else r.get('color', ST['text_color'])
        out.append(f".r-{role}{{font-family:'{r['font']}';font-weight:{r['weight']};font-size:{r['size']}px;"
                   f"letter-spacing:{r.get('tracking', 'normal')};line-height:{r.get('line', 1)};text-transform:{r.get('case', 'none')};"
                   f"font-style:{r.get('style', 'normal')};color:{col}}}")
        bx = r.get('box')
        if bx:   # text on a pill or, with "display": "inline", a bar behind each line (bg may be a gradient): no shadow needed
            out.append(f".r-{role}{{text-shadow:none}} .r-{role} .bx{{display:{bx.get('display', 'inline-block')};background:{bx['bg']};"
                       f"padding:{bx.get('pad', '.2em .6em')};border-radius:{bx.get('radius', 9999)}px;border:{bx.get('border', 'none')};"
                       f"box-shadow:{bx.get('shadow', 'none')};box-decoration-break:clone;-webkit-box-decoration-break:clone}}")
        out.append(f".r-{role} .ld{{font-size:{r.get('lead', .6)}em}}")
    return '\n'.join(out)


CSS = f'''
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:#000}}
#root{{position:relative;width:1080px;height:1920px;overflow:hidden;background:#000}}
#cam1,#cam2{{position:absolute;inset:0;transform-origin:50% 45%}}
/* explicit z-index on every layer: the renderer composites <video> frames by z-index, and an overlay without one
   ends up UNDER the video in the render (snapshots still look right) */
#cam2{{z-index:0}}
#front{{position:absolute;inset:0;z-index:8}}
.full{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
#cutwrap{{position:absolute;inset:0;z-index:4}}
.back{{position:absolute;inset:0;z-index:3}}
.tx{{position:absolute;left:0;right:0;text-align:center;white-space:nowrap;text-shadow:{ST['text_shadow']};transform-origin:50% 60%}}
.acc{{color:{ACC}}}
.r-caps .tw{{display:inline-block;margin:0 .1em;transform-origin:50% 50%}}
.r-serif .mk{{display:inline-block;overflow:hidden;padding:0 .02em .14em;margin-bottom:-.14em;vertical-align:bottom}}
.r-serif .ch{{display:inline-block}}
{type_css()}
.spark{{position:absolute;color:{ACC};line-height:1;text-shadow:0 0 18px color-mix(in oklab,{ACC} 50%,transparent)}}
.hn{{position:absolute;inset:0}}
.fx{{position:absolute;inset:0;pointer-events:none}}
.sweep{{mix-blend-mode:screen;background:linear-gradient(105deg,rgba(255,240,220,0) 38%,rgba(255,240,220,.22) 50%,rgba(255,240,220,0) 62%);
  background-size:260% 100%;background-repeat:no-repeat}}
.mbox{{position:absolute}}
.mclip{{position:relative;width:100%;height:100%;overflow:hidden;background:#111}}
.mlayer{{position:absolute;inset:0}}
.split{{position:absolute;left:0;right:0;top:0;overflow:hidden;background:#000;box-shadow:0 20px 50px rgba(0,0,0,.45)}}
.pill{{margin:14px auto 0;width:max-content;max-width:330px;padding:8px 16px;border-radius:99px;background:rgba(10,10,12,.78);
  color:#fff;font:600 24px Inter}}
.orb{{position:absolute;left:0;top:0}}
.opop{{width:100%;height:100%}}
.ov{{position:absolute}}
.ov video{{width:100%;height:100%;display:block}}
'''

# PY build.py --safe: draws the Instagram safe zone (red = UI covers it) for snapshot checks, never for renders
SAFE_GUIDE = ('<div style="position:absolute;inset:0;z-index:99;pointer-events:none">'
              '<div style="position:absolute;left:0;right:0;top:0;height:220px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;left:0;right:0;top:1470px;bottom:0;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;left:0;width:35px;top:220px;height:1250px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;right:0;width:35px;top:220px;height:935px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;right:0;width:100px;top:1155px;height:315px;background:rgba(255,0,0,.28)"></div></div>')


def build():
    cam_effects()
    for fx in TL['fx']:
        h = HANDLERS[fx['fx']]
        if h is None:
            continue
        seg = fx['seg']
        t = t_at(seg, fx['at'])
        b = t_until(seg, fx['until'])
        if b <= t:
            sys.exit(f"{fx['fx']} in {seg}: ends ({b:.2f}s) before it starts ({t:.2f}s); check its @ and .. anchors")
        h(fx, t, b)
    subtitles()
    overlap_warnings()
    cut = (f'<div id="cutwrap"><video id="cut" class="full" src="assets/subject.webm" muted playsinline data-start="0" '
           f'data-media-start="0" data-duration="{DUR:.3f}" data-track-index="1"></video></div>') if CUTOUT and BACK else ''
    nl = '\n'
    return f'''<!doctype html>
<html lang="en" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<link rel="stylesheet" href="assets/fonts/fonts.css" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR:.3f}" data-width="1080" data-height="1920">
  <audio id="bga" src="assets/aroll.mp4" data-start="0" data-media-start="0" data-duration="{DUR:.3f}" data-track-index="2" data-volume="1"></audio>
{nl.join(audio())}
  <div id="cam2"><div id="cam1">
    <video id="bgv" class="full" src="assets/aroll.mp4" muted playsinline data-start="0" data-media-start="0" data-duration="{DUR:.3f}" data-track-index="0"></video>
    <div class="back">
{nl.join(BACK)}
    </div>
    {cut}
  </div></div>
  <div id="front">
{nl.join(FRONT)}
  </div>
{SAFE_GUIDE if SAFE else ''}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{nl.join(TW)}
tl.set({{}}, {{}}, {DUR:.3f});
window.__timelines["main"] = tl;
</script>
</body>
</html>
'''


# utf-8 on every OS: the page declares charset UTF-8, and Windows would otherwise write cp1252 (broken accents, emoji)
_html = build()
with open('index.html', 'w', encoding='utf-8', newline='\n') as _f:
    _f.write(_html)
print(f"wrote index.html {DUR:.3f}s, {len(SEGS)} segments, {len(TL['fx'])} effects, {len(SFX)} sounds"
      + ('' if CUTOUT else ' (no cutout)'))
