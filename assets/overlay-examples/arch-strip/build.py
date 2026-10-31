#!/usr/bin/env python3
"""Deilbach Pegel architecture diagram, one composition per state.
960x330, fully transparent (boxes + arrows only), 30fps.
PY build.py  -> compositions/arch-<state>.html for every state (+ index.html = arch-build)
Render: PY hf.py render -c compositions/arch-<state>.html --format webm -o renders/arch-<state>.webm
"""
W, HT = 960, 330
BW, BH = 230, 90
ROW_Y, DB_Y = 214, 20
CY = ROW_Y + BH / 2  # row centre line
BOX = {  # id: (label, x, y)
    'ds': ('Data sources', 20, ROW_Y),
    'svc': ('Service', 365, ROW_Y),
    'web': ('Website', 710, ROW_Y),
    'db': ('Database', 365, DB_Y),
}
ENTER_ORDER = ['ds', 'svc', 'web', 'db']
G = 8  # gap between box edge and arrow
# connectors: id -> (x1, y1, x2, y2, arrowhead)
CON = {
    'ds_svc': (20 + BW + G, CY, 365 - G, CY, True),
    'svc_web': (365 + BW + G, CY, 710 - G, CY, True),
    'svc_db': (480, ROW_Y, 480, DB_Y + BH, False),
}

# state: duration, entrance (box stagger, box dur, arrows start, arrows dur), events
# events: (t, 'on'|'off', box, tag) or (t, 'flow', connector)
STATES = {
    'build': (6.6, (.08, .42, .32, .38), [
        (1.90, 'on', 'db', None),
        (3.62, 'off', 'db', None), (3.62, 'on', 'svc', None),
        (6.08, 'off', 'svc', None), (6.08, 'on', 'web', None)]),
    'db': (4.7, (.07, .32, .24, .26), [(0.35, 'on', 'db', 'Neon Postgres')]),
    'job': (5.7, (.07, .32, .24, .26), [
        (0.35, 'on', 'svc', 'AWS Lambda job'),
        (2.33, 'on', 'ds', None), (2.33, 'flow', 'ds_svc'),
        (4.21, 'flow', 'svc_db'), (4.21, 'on', 'db', None)]),
    'api': (4.7, (.07, .32, .24, .26), [(0.35, 'on', 'svc', 'FastAPI'), (2.95, 'flow', 'svc_web')]),
    'web': (3.9, (.07, .32, .24, .26), [(0.35, 'on', 'web', 'CloudFront'), (0.35, 'flow', 'svc_web')]),
}
FADE = .25
LIGHT = .28    # light-up crossfade
PERIOD = .8  # one dot crossing a connector
NDOTS = 3

CSS = f"""
@font-face{{font-family:'Manrope';font-style:normal;font-weight:200 800;font-display:block;src:url('assets/fonts/Manrope-variable.woff2') format('woff2')}}
@font-face{{font-family:'Space Grotesk';font-style:normal;font-weight:300 700;font-display:block;src:url('assets/fonts/SpaceGrotesk-variable.woff2') format('woff2')}}
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--fill:oklch(22% .025 215 / .92);--idle:oklch(76% .02 215 / .6);--muted:oklch(76% .02 215 / .55);
  --txt:oklch(97% .005 90);--or:oklch(72% .18 50)}}
html,body{{width:{W}px;height:{HT}px;overflow:hidden;background:transparent}}
#root{{position:relative;width:{W}px;height:{HT}px;overflow:hidden;background:transparent}}
#stage{{position:absolute;inset:0}}
svg{{position:absolute;left:0;top:0;overflow:visible}}
.box{{position:absolute;width:{BW}px;height:{BH}px;border-radius:14px;background:var(--fill);
  border:2px solid var(--idle);box-shadow:0 8px 20px rgba(8,16,20,.38),0 2px 5px rgba(8,16,20,.28)}}
.ring{{position:absolute;inset:-2px;border-radius:14px;border:2.5px solid var(--or);
  box-shadow:0 0 16px oklch(72% .18 50 / .35),inset 0 0 10px oklch(72% .18 50 / .12)}}
.nm{{position:absolute;left:0;right:0;top:0;height:{BH - 4}px;display:flex;align-items:center;justify-content:center;
  font-family:'Space Grotesk',sans-serif;font-weight:650;font-size:31px;letter-spacing:-.01em;color:var(--txt)}}
.nm.on{{color:var(--or)}}
.tag{{position:absolute;left:0;right:0;top:50px;text-align:center;font-family:'Manrope',sans-serif;font-weight:700;
  font-size:22px;color:var(--or)}}
"""


def build(state, fonts):
    dur, (stg, bdur, a0, adur), events = STATES[state]
    tags = {e[2]: e[3] for e in events if e[1] == 'on' and e[3]}

    boxes = []
    for b, (label, x, y) in BOX.items():
        tag = f'<div class="tag" id="{b}-tag">{tags[b]}</div>' if b in tags else ''
        boxes.append(f'<div class="box" id="{b}" style="left:{x}px;top:{y}px">'
                     f'<div class="ring" id="{b}-ring"></div>'
                     f'<div class="nm-wrap" id="{b}-nmw"><div class="nm" id="{b}-nm">{label}</div>'
                     f'<div class="nm on" id="{b}-nmo">{label}</div></div>{tag}</div>')

    svg = [f'<svg width="{W}" height="{HT}" viewBox="0 0 {W} {HT}">']
    for c, (x1, y1, x2, y2, head) in CON.items():
        hd = f'M{x2 - 9},{y2 - 7} L{x2},{y2} L{x2 - 9},{y2 + 7}' if head else ''
        # dark casing 'c' under each line keeps idle connectors readable over the white T-shirt
        for kind, col, sw in (('c', 'oklch(22% .025 215 / .8)', 7), ('i', 'var(--muted)', 2.5), ('l', 'var(--or)', 3)):
            svg.append(f'<path id="{c}-{kind}" d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="{sw}" '
                       f'stroke-linecap="round" fill="none"/>')
            if hd:
                svg.append(f'<path id="{c}-{kind}h" d="{hd}" stroke="{col}" stroke-width="{sw}" '
                           f'stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
        for k in range(NDOTS):
            svg.append(f'<circle id="{c}-d{k}" cx="0" cy="0" r="5" fill="var(--or)"/>')
    svg.append('</svg>')

    J = []
    T = J.append
    T("const tl = gsap.timeline({ paused: true });")
    # initial states (outside the timeline)
    T("gsap.set('.box',{autoAlpha:0,y:14});")
    T("gsap.set('.ring,.nm.on,.tag',{autoAlpha:0});")
    T("gsap.set('circle',{autoAlpha:0});")
    for c, (x1, y1, x2, y2, head) in CON.items():
        L = abs(x2 - x1) + abs(y2 - y1)
        for kind in ('c', 'i', 'l'):
            T(f"gsap.set('#{c}-{kind}',{{strokeDasharray:{L},strokeDashoffset:{L}}});")
            if head:
                T(f"gsap.set('#{c}-{kind}h',{{autoAlpha:0}});")
    # entrance
    for i, b in enumerate(ENTER_ORDER):
        T(f"tl.to('#{b}',{{autoAlpha:1,y:0,duration:{bdur},ease:'power2.out'}},{i * stg:.3f});")
    for c, (*_, head) in CON.items():
        T(f"tl.to(['#{c}-c','#{c}-i'],{{strokeDashoffset:0,duration:{adur},ease:'power1.inOut'}},{a0});")
        if head:
            T(f"tl.to(['#{c}-ch','#{c}-ih'],{{autoAlpha:1,duration:.15,ease:'power1.out'}},{a0 + adur - .1:.3f});")
    # beats
    for e in events:
        t = e[0]
        if e[1] in ('on', 'off'):
            b, tag, on = e[2], e[3], e[1] == 'on'
            a = 1 if on else 0
            T(f"tl.to(['#{b}-ring','#{b}-nmo'],{{autoAlpha:{a},duration:{LIGHT},ease:'power1.inOut'}},{t});")
            T(f"tl.to('#{b}-nm',{{autoAlpha:{1 - a},duration:{LIGHT},ease:'power1.inOut'}},{t});")
            if tag:
                T(f"tl.to('#{b}-nmw',{{y:-14,duration:.4,ease:'power2.out'}},{t});")
                T(f"tl.fromTo('#{b}-tag',{{autoAlpha:0,y:8}},{{autoAlpha:1,y:0,duration:.4,ease:'power2.out',immediateRender:false}},{t + .08:.3f});")
        else:
            c = e[2]
            x1, y1, x2, y2, head = CON[c]
            T(f"tl.to('#{c}-l',{{strokeDashoffset:0,duration:.35,ease:'power1.inOut'}},{t});")
            if head:
                T(f"tl.to('#{c}-lh',{{autoAlpha:1,duration:.12}},{t + .25:.3f});")
            # dots: inset from the ends, stop short of the arrowhead
            sx = (x2 - x1) and (1 if x2 > x1 else -1)
            sy = (y2 - y1) and (1 if y2 > y1 else -1)
            pad0, pad1 = 6, (16 if head else 8)
            p0 = (x1 + sx * pad0, y1 + sy * pad0)
            p1 = (x2 - sx * pad1, y2 - sy * pad1)
            for k in range(NDOTS):
                st = t + .1 + k * PERIOD / NDOTS
                rep = int((dur - st) // PERIOD) - 1  # finite: keep every tween inside the clip
                if rep < 0:
                    continue
                T(f"tl.fromTo('#{c}-d{k}',{{x:{p0[0]},y:{p0[1]},autoAlpha:0}},"
                  f"{{keyframes:{{x:[{p0[0]},{p1[0]}],y:[{p0[1]},{p1[1]}],autoAlpha:[0,1,1,1,0],easeEach:'none'}},"
                  f"duration:{PERIOD},ease:'none',repeat:{rep},immediateRender:false}},{st:.3f});")
    T(f"tl.to('#stage',{{autoAlpha:0,duration:{FADE},ease:'power1.in'}},{dur - FADE:.3f});")
    T(f"tl.set({{}}, {{}}, {dur});")
    T('window.__timelines = window.__timelines || {};')
    T('window.__timelines["main"] = tl;')

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={HT}" />
<link rel="stylesheet" href="{fonts}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-fps="30" data-width="{W}" data-height="{HT}">
<div id="stage">
{''.join(svg)}
{''.join(boxes)}
</div>
</div>
<script>
{chr(10).join(J)}
</script>
</body>
</html>
"""
    return page


if __name__ == '__main__':
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else 'build'  # state copied to index.html (snapshot only reads index.html)
    for s in STATES:
        outs = [f'compositions/arch-{s}.html'] + (['index.html'] if s == root else [])
        for n in outs:
            with open(n, 'w', encoding='utf-8', newline='\n') as f:
                f.write(build(s, 'assets/fonts/fonts.css'))
            print('wrote', n)
