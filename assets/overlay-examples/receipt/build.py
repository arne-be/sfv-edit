#!/usr/bin/env python3
"""Running-cost receipt that prints line by line, one composition per state.
640x800, transparent outside the paper, receipt tilted 4deg clockwise, 30fps.
PY build.py <1|2|3|4|total>  -> index.html  (then hf.py lint / snapshot / render)
Beat times are locked to the voice-over (seconds from clip start).
"""
import sys
import random
import html as H

W, HT = 640, 800
PW = 560                       # paper width
PAD = 34                       # paper side padding
INK = '#1d1d1b'
GREY = '#8f8b82'
PAPER = '#faf8f0'
ORANGE = 'oklch(72% .18 50)'
ORANGE_RGB = '#fa7c20'   # same orange in sRGB: GSAP cannot interpolate oklch (text vanished mid-tween)
LINE0, LH = 166, 56            # first line-item row top, row height
ITEMS = [('Database · Neon', '0.00 €', True),
         ('Service · AWS job', '3–4 €', False),
         ('API · FastAPI', '0.00 €', True),
         ('Website · CloudFront', '0.00 €', True)]
RULE2 = LINE0 + 4 * LH + 14    # double rule top (404)
TOT_TOP, TOT_H = RULE2 + 18, 88
SUP_TOP, SUP_H = TOT_TOP + TOT_H + 2, 46


def h_lines(n):
    return LINE0 + LH * n + 24


H_TOT = TOT_TOP + TOT_H + 16
H_SUP = SUP_TOP + SUP_H + 26

# state: (duration, index of new line or None, beats)
STATES = {
    '1': dict(dur=4.85, new=0, name_t=0.30, cps=0.034, price=[0.90], free=4.03),
    '2': dict(dur=5.4, new=1, name_t=0.30, cps=0.036, price=[2.41, 3.22, 3.28, 3.36, 3.43], free=None),
    '3': dict(dur=2.55, new=2, name_t=0.15, cps=0.026, price=[0.60], free=1.85),
    '4': dict(dur=3.45, new=3, name_t=0.20, cps=0.025, price=[0.80], free=2.63),
    'total': dict(dur=7.4, new=None),
}


def chars(text, prefix):
    return ''.join(f'<span class="c" id="{prefix}{k}">{H.escape(ch)}</span>' for k, ch in enumerate(text))


def teeth_svg():
    rnd = random.Random(7)     # fixed seed: same torn edge in every clip
    pts, x = ['0,0'], 0.0
    while x < PW:
        x = min(PW, x + rnd.uniform(9, 14))
        pts.append(f'{x:.1f},{rnd.uniform(9, 14):.1f}')
        x = min(PW, x + rnd.uniform(9, 14))
        pts.append(f'{x:.1f},{rnd.uniform(0, 2):.1f}')
    pts.append(f'{PW},0')
    return (f'<svg id="teeth" width="{PW}" height="15" viewBox="0 0 {PW} 15">'
            f'<polygon points="{" ".join(pts)}" fill="{PAPER}"/></svg>')


def build(state):
    S = STATES[state]
    DUR = S['dur']
    new = S['new']
    n_before = 4 if new is None else new
    shown = 4 if new is None else new + 1

    CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{HT}px;overflow:hidden;background:transparent}}
#root{{position:relative;width:{W}px;height:{HT}px;overflow:hidden;background:transparent}}
#wrap{{position:absolute;left:0;top:0;width:{W}px;height:{HT}px;
  filter:drop-shadow(0 1px 1.5px rgba(30,25,15,.22)) drop-shadow(0 9px 11px rgba(30,25,15,.24))}}
#bump{{position:absolute;left:0;top:0;width:{W}px;height:{HT}px}}
#rcpt{{position:absolute;left:{341 - PW // 2}px;top:42px;width:{PW}px;transform:rotate(4deg);transform-origin:50% 0}}
#body{{position:relative;width:{PW}px;height:{h_lines(n_before)}px;overflow:hidden;background:{PAPER};
  background-image:linear-gradient(180deg,rgba(255,255,255,.55),rgba(255,255,255,0) 90px),
    linear-gradient(90deg,rgba(120,100,60,.05),rgba(120,100,60,0) 22px,rgba(120,100,60,0) {PW - 22}px,rgba(120,100,60,.05));
  color:{INK}}}
#teeth{{display:block;margin-top:-0.5px}}
#title{{position:absolute;left:0;top:34px;width:{PW}px;text-align:center;font-family:'Space Grotesk',sans-serif;font-weight:700;
  font-size:50px;line-height:58px;letter-spacing:.015em}}
#sub{{position:absolute;left:0;top:94px;width:{PW}px;text-align:center;font-family:'Manrope',sans-serif;font-weight:500;
  font-size:25px;line-height:32px;color:#6b675e;letter-spacing:.03em}}
.rule{{position:absolute;left:{PAD}px;width:{PW - 2 * PAD}px;height:2px;background:{INK};transform-origin:0 50%}}
.row{{position:absolute;left:{PAD}px;width:{PW - 2 * PAD}px;height:{LH}px;display:flex;align-items:baseline;white-space:pre;
  font-family:'JetBrains Mono',monospace;font-weight:500;font-size:30px;line-height:{LH}px;font-variant-ligatures:none;color:{INK}}}
.ld{{flex:1;height:3px;margin:0 9px;background-image:radial-gradient(circle,currentColor 1.4px,transparent 1.7px);
  background-size:11px 3px;background-repeat:repeat-x;background-position:0 0;opacity:.55}}
.pr{{text-align:right}}
.new{{color:{ORANGE_RGB}}}
.stamp{{position:absolute;right:-6px;top:6px;padding:0 12px;border:3.5px solid {ORANGE};border-radius:9px;color:{ORANGE};
  font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:30px;line-height:38px;letter-spacing:.08em;
  transform:rotate(-9deg);mix-blend-mode:multiply;background:rgba(250,248,240,.35)}}
#tot{{position:absolute;left:{PAD}px;top:{TOT_TOP}px;width:{PW - 2 * PAD}px;height:{TOT_H}px;display:flex;align-items:baseline;
  justify-content:space-between;white-space:pre;font-family:'Space Grotesk',sans-serif;font-weight:700;line-height:{TOT_H}px}}
#totl{{font-size:46px;letter-spacing:.04em}}
#totp{{font-size:78px;color:{ORANGE};font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
#tp0{{display:inline-block;transform-origin:50% 70%}}
#sup{{position:absolute;left:{PAD}px;top:{SUP_TOP}px;width:{PW - 2 * PAD}px;height:{SUP_H}px;display:flex;justify-content:space-between;
  white-space:pre;font-family:'JetBrains Mono',monospace;font-weight:500;font-size:28px;line-height:{SUP_H}px;color:{GREY}}}
#strike{{position:absolute;left:-8px;right:-8px;top:{SUP_H // 2 - 1}px;height:4px;border-radius:2px;background:{ORANGE};
  transform-origin:0 50%;transform:rotate(-1.5deg)}}
"""

    body = []
    A = body.append
    A('<div id="title">DEILBACH PEGEL</div><div id="sub">monthly running cost</div>')
    A('<div class="rule" style="top:146px"></div>')
    for i in range(shown):
        name, price, free = ITEMS[i]
        cls = 'row new' if i == new else 'row'
        stamp = f'<div class="stamp" id="st{i}">FREE</div>' if free else ''
        A(f'<div class="{cls}" id="r{i}" style="top:{LINE0 + i * LH}px"><span class="nm">{chars(name, f"l{i}n")}</span>'
          f'<span class="ld" id="ld{i}"></span><span class="pr">{chars(price, f"l{i}p")}</span>{stamp}</div>')
    if new is None:
        A(f'<div class="rule" id="ru1" style="top:{RULE2}px"></div><div class="rule" id="ru2" style="top:{RULE2 + 6}px"></div>')
        A(f'<div id="tot"><span id="totl">{chars("TOTAL", "t")}</span><span id="totp">{chars("3–4 €", "tp")}</span></div>')
        A(f'<div id="sup"><span>{chars("Supabase + Vercel", "sa")}</span><span>{chars("40 €", "sb")}</span>'
          f'<div id="strike"></div></div>')

    J = []
    T = J.append
    T("const tl = gsap.timeline({ paused: true });")
    # initial states, outside the timeline
    T("gsap.set('#wrap',{autoAlpha:0,y:-46});")
    T("gsap.set('#bump',{y:0});")
    # earlier free lines keep their stamp
    for i in range(n_before):
        if not ITEMS[i][2]:
            continue
        T(f"gsap.set('#st{i}',{{autoAlpha:1,scale:1}});")
        T(f"gsap.set('#r{i} .pr',{{opacity:0}});")   # stamped price sits faded under the ink
    # pop in + settle
    T("tl.to('#wrap',{autoAlpha:1,duration:.18,ease:'power1.out'},0);")
    T("tl.to('#wrap',{y:0,duration:.3,ease:'back.out(2.2)'},0);")

    beats = {}
    if new is not None:
        name, price, free = ITEMS[new]
        t0, cps = S['name_t'], S['cps']
        T(f"gsap.set('#r{new} .c',{{autoAlpha:0}});")
        T(f"gsap.set('#ld{new}',{{clipPath:'inset(0 100% 0 0)'}});")
        if free:
            T(f"gsap.set('#st{new}',{{autoAlpha:0,scale:2.3}});")
        # paper feeds while the line prints
        T(f"tl.to('#body',{{height:{h_lines(new + 1)},duration:.28,ease:'power2.out'}},{t0 - 0.04:.3f});")
        for k in range(len(name)):
            T(f"tl.set('#l{new}n{k}',{{autoAlpha:1}},{t0 + k * cps:.3f});")
        t_name_end = t0 + len(name) * cps
        beats['name'] = (t0, round(t_name_end, 3))
        pt = S['price']
        T(f"tl.to('#ld{new}',{{clipPath:'inset(0 0% 0 0)',duration:{max(0.12, min(0.3, pt[0] - t_name_end - 0.02)):.2f},ease:'none'}},{t_name_end:.3f});")
        if len(pt) == 1:   # 0.00 EUR: quick left-to-right print
            ts = [pt[0] + k * 0.035 for k in range(len(price))]
        else:              # 3 ... -4 EUR in step with the voice; pt maps to chars 0,1(dash),2(4),3(space),4(EUR)
            ts = pt
        for k, t in enumerate(ts):
            T(f"tl.set('#l{new}p{k}',{{autoAlpha:1}},{t:.3f});")
        beats['price'] = [round(t, 3) for t in ts]
        t_ink = ts[-1] + 0.45
        T(f"tl.fromTo('#r{new}',{{color:'{ORANGE_RGB}'}},{{color:'{INK}',duration:.4,ease:'power1.inOut',immediateRender:false}},{t_ink:.3f});")
        if free:
            tf = S['free']
            T(f"tl.to('#st{new}',{{autoAlpha:1,duration:.06,ease:'none'}},{tf - 0.11:.3f});")
            T(f"tl.to('#st{new}',{{scale:1,duration:.11,ease:'power3.in'}},{tf - 0.11:.3f});")   # lands exactly on the beat
            T(f"tl.to('#r{new} .pr',{{opacity:0,duration:.08,ease:'power1.out'}},{tf:.3f});")
            T(f"tl.to('#bump',{{y:4,duration:.05,ease:'power2.out'}},{tf:.3f});")
            T(f"tl.to('#bump',{{y:0,duration:.16,ease:'power2.out'}},{tf + 0.05:.3f});")
            beats['free_land'] = tf
    else:
        T("gsap.set(['#ru1','#ru2'],{scaleX:0});")
        T("gsap.set(['#tot .c','#sup .c'],{autoAlpha:0});")
        T("gsap.set('#strike',{scaleX:0,rotation:-1.5});")
        t0 = 1.19
        T(f"tl.to('#body',{{height:{H_TOT},duration:.3,ease:'power2.out'}},{t0 - 0.04:.3f});")
        T(f"tl.to('#ru1',{{scaleX:1,duration:.26,ease:'power2.out'}},{t0:.3f});")
        T(f"tl.to('#ru2',{{scaleX:1,duration:.26,ease:'power2.out'}},{t0 + 0.05:.3f});")
        for k in range(5):
            T(f"tl.set('#t{k}',{{autoAlpha:1}},{t0 + 0.1 + k * 0.04:.3f});")
        ts = [2.03, 2.30, 2.36, 2.43, 2.51]          # 3, dash, 4, space, EUR
        for k, t in enumerate(ts):
            T(f"tl.set('#tp{k}',{{autoAlpha:1}},{t:.3f});")
        T(f"tl.fromTo('#tp0',{{scale:1.35}},{{scale:1,duration:.22,ease:'back.out(2)',immediateRender:false}},{ts[0]:.3f});")
        ts_ = 3.47
        T(f"tl.to('#body',{{height:{H_SUP},duration:.28,ease:'power2.out'}},{ts_ - 0.04:.3f});")
        sup = 'Supabase + Vercel'
        for k in range(len(sup)):
            T(f"tl.set('#sa{k}',{{autoAlpha:1}},{ts_ + k * 0.02:.3f});")
        for k in range(4):
            T(f"tl.set('#sb{k}',{{autoAlpha:1}},{ts_ + len(sup) * 0.02 + 0.06 + k * 0.03:.3f});")
        T("tl.to('#strike',{scaleX:1,duration:.24,ease:'power2.inOut'},4.2);")
        beats = {'rule_total': t0, 'total_3': 2.03, 'total_done': 2.51, 'supabase': ts_, 'strike': (4.2, 4.44)}

    # exit: last 0.25s
    T(f"tl.to('#wrap',{{autoAlpha:0,y:-22,duration:.25,ease:'power2.in'}},{DUR - 0.25:.3f});")
    T(f"tl.set({{}}, {{}}, {DUR});")
    T('window.__timelines = window.__timelines || {};')
    T('window.__timelines["main"] = tl;')

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={HT}" />
<link rel="stylesheet" href="assets/fonts/fonts.css" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="{W}" data-height="{HT}">
<div id="wrap"><div id="bump"><div id="rcpt">
<div id="body">
{''.join(body)}
</div>
{teeth_svg()}
</div></div></div>
</div>
<script>
{chr(10).join(J)}
</script>
</body>
</html>
"""
    with open('index.html', 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    print(f'wrote index.html state={state} dur={DUR} beats={beats}')


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'total')
