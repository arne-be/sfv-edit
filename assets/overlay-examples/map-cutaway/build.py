#!/usr/bin/env python3
"""Deilbach catchment map cutaway, 1080x1920 opaque, 27.6s @30fps.
Map layers (zones, outline, rivers, forecast grid, zone labels, markers) are copied from the source page's own SVG;
base map = assets/base-crop.jpg (the page's embedded tile image, cropped to units 380..1520 x 380..1560).
PY build.py -> index.html
"""
import math
import re

SRC = '/Users/arne/Documents/kornerpiece/deilbach/videos/videos/day2/deilbach-catchment.html'
W, H, DUR = 1080, 1920, 27.6
K = 1.06                      # px per map unit
U0, V0 = 435.6, 147.6         # map unit at px (0,0)
ORIGIN = (560, 855)           # push-in origin (catchment centre)
OR, WHITE, CARD = '#f08a3c', '#f5f3ee', '#17262b'

src = open(SRC, encoding='utf-8').read()


def grab(pat):
    m = re.search(pat, src, re.S)
    assert m, pat
    return m.group(0)


def P(u, v):  # map unit -> px
    return (u - U0) * K, (v - V0) * K


zones = grab(r'<g id="l-zones">.*?</g>')
outline = grab(r'<path class="outline"[^>]*/>')
rivers = grab(r'<g id="l-rivers">.*?</g>')
icons = grab(r'<g id="l-icon">.*?</g>')
zlabels = re.sub(r'<tspan[^>]*class="zkm">[^<]*</tspan>', '', grab(r'<g id="l-zlabels">.*?</g>'))  # names only
# at 30px the source label spots for Lower / Middle collide with Kupferdreh and the Nierenhof pill: nudge them
for old, new in (('798.5', '790'), ('720.5', '650'), ('1162.1', '1176'), ('873.4', '940')):
    zlabels = zlabels.replace(f'"{old}"', f'"{new}"')
# markers: the source shapes without their 13px text labels (replaced by big pills)
mk = grab(r'<g id="l-markers">.*?</g></g>')
mk = re.sub(r'<text[^>]*class="lbl">[^<]*</text>', '', mk)
mk = re.sub(r'<title>[^<]*</title>', '', mk)
for name, rid in (('x="837.3"', 'g-lang'), ('x="914.2"', 'g-nier'), ('x="692.4"', 'g-nev'), ('x="881.9"', 'g-grenz')):
    mk = mk.replace(f'<rect {name}', f'<rect id="{rid}" {name}', 1)
mk = re.sub(r'<path d="(M[^"]+)" class="m-rain"/>', lambda m: f'<path class="m-rain tri" d="{m.group(1)}"/>', mk)

GAUGE = {'nev': (700.4, 1095.3), 'lang': (845.3, 888.3), 'nier': (922.2, 819.6), 'grenz': (889.9, 772.3)}
KUP = (703.9, 691.5)
TRI = [tuple(map(float, re.match(r'M([\d.]+),([\d.]+)', d).groups())) for d in re.findall(r'class="m-rain tri" d="([^"]+)"', mk)]
INPTS = [(float(x), float(y)) for x, y in re.findall(r'class="icon in" cx="([\d.]+)" cy="([\d.]+)"', icons)]
assert len(INPTS) == 36 and len(TRI) == 3

# Deilbach line: 2nd subpath of the main river, reversed (source -> mouth), cut at Kupferdreh, resampled evenly
main_d = re.search(r'class="river main" d="([^"]+)"', src).group(1)
dl = [tuple(map(float, p)) for p in re.findall(r'(-?[\d.]+),(-?[\d.]+)', main_d.split('M')[2])][::-1]
cut = min(range(len(dl)), key=lambda i: math.dist(dl[i], KUP))
dl = dl[:cut + 1]
seg = [0.0]
for a, b in zip(dl, dl[1:]):
    seg.append(seg[-1] + math.dist(a, b))
NS = 70
flow = []
for j in range(NS):
    s_ = seg[-1] * j / (NS - 1)
    i = max(k for k in range(len(seg)) if seg[k] <= s_) if s_ < seg[-1] else len(seg) - 2
    t = (s_ - seg[i]) / ((seg[i + 1] - seg[i]) or 1)
    flow.append((round(dl[i][0] + t * (dl[i + 1][0] - dl[i][0]), 1), round(dl[i][1] + t * (dl[i + 1][1] - dl[i][1]), 1)))

# ---------- river network inside the catchment: downstream distance to Kupferdreh per vertex ----------
OUTL = [tuple(map(float, p)) for p in re.findall(r'(-?[\d.]+),(-?[\d.]+)', re.search(r'class="outline" d="([^"]+)"', src).group(1))]


def inside(p):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(OUTL, OUTL[1:] + OUTL[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


trib_d = re.search(r'<path class="river" d="([^"]+)"', src).group(1)
LINES = [dl] + [q for q in ([tuple(map(float, p)) for p in re.findall(r'(-?[\d.]+),(-?[\d.]+)', sp)]
                            for sp in trib_d.split('M')[1:]) if all(inside(p) for p in q)]
nodes, adj, idx = [], {}, []
for q in LINES:
    ids = list(range(len(nodes), len(nodes) + len(q)))
    nodes += q
    idx.append(ids)
    for a, b in zip(ids, ids[1:]):
        w = math.dist(nodes[a], nodes[b])
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))


def dijkstra():
    import heapq
    D, h = {idx[0][-1]: 0.0}, [(0.0, idx[0][-1])]
    while h:
        d, u = heapq.heappop(h)
        if d > D.get(u, 1e9):
            continue
        for v, w in adj.get(u, []):
            if d + w < D.get(v, 1e9):
                D[v] = d + w
                heapq.heappush(h, (d + w, v))
    return D


def link(tol, only=None):  # join each line end to the nearest vertex of another line (stream junctions)
    for li, ids in enumerate(idx):
        if only is not None and li not in only:
            continue
        for e in (ids[0], ids[-1]):
            best = min(((math.dist(nodes[e], nodes[j]), j) for lj, jds in enumerate(idx) if lj != li for j in jds))
            if best[0] < tol:
                adj.setdefault(e, []).append((best[1], best[0]))
                adj.setdefault(best[1], []).append((e, best[0]))


link(8)
D = dijkstra()
miss = {li for li, ids in enumerate(idx) if ids[0] not in D}
if miss:  # a few side streams end a little off their parent line
    link(30, miss)
    D = dijkstra()
assert all(ids[0] in D for ids in idx), 'unconnected stream'
DMAX = max(D.values())
FT0, FT1 = 22.55, 24.65            # flow front: farthest source starts at FT0, everything reaches Kupferdreh at FT1
VF = DMAX / (FT1 - FT0)            # front speed, map units/s
NET = []                           # (d attr, length, D upstream end, D downstream end), oriented downstream
for ids in idx:
    q = [nodes[i] for i in ids]
    du, dd = D[ids[0]], D[ids[-1]]
    if du < dd:
        q, du, dd = q[::-1], dd, du
    L = sum(math.dist(a, b) for a, b in zip(q, q[1:]))
    NET.append(('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in q), L, du, dd))
assert all(n[2] >= n[3] for n in NET)

# ---------- chips ----------
ICON = {
    'c1': '<path d="M12 6v36M12 10h7M12 17h4M12 24h7M12 31h4M12 38h7"/><path d="M22 30c3.5-4 7 4 10.5 0s7 4 10.5 0M22 38c3.5-4 7 4 10.5 0s7 4 10.5 0"/>',
    'c2': '<path d="M14 28h21a7 7 0 0 0 .5-14A10 10 0 0 0 16.3 13 7.6 7.6 0 0 0 14 28z"/><path d="M17 34l-2.5 6M25 34l-2.5 6M33 34l-2.5 6"/>',
    'c3': '<path d="M12 27h17M30 11.5a7 7 0 0 1 7.2 6.2M27.5 11A10 10 0 0 0 14.3 12 7.6 7.6 0 0 0 12 27"/><circle cx="33" cy="31" r="10"/><path d="M33 25.5v5.5l3.6 2.4"/>',
}
CHIPS = [('c1', 'River gauges', 'LANUV'), ('c2', 'Measured rain', 'DWD'), ('c3', 'Forecast', '48 h')]
CW, CG, CX0, CY0, CHT = 324, 19, 35, 240, 160
chips = ''.join(
    f'<div class="chip" id="{cid}" style="left:{CX0 + i * (CW + CG)}px;top:{CY0}px">'
    f'<svg class="ic" width="52" height="52" viewBox="0 0 48 48">{ICON[cid]}</svg>'
    f'<div class="num">0{i + 1}</div><div class="ct">{t}</div><div class="cs">{s}</div></div>'
    for i, (cid, t, s) in enumerate(CHIPS))

# ---------- gauge rings + pills (px coordinates, inside the push-in wrapper) ----------
PILLS = {  # id: (anchor unit pos, side, text)
    'nev': (GAUGE['nev'], 'l', 'Neviges'),
    'lang': (GAUGE['lang'], 'l', 'Langenberg'),
    'nier': (GAUGE['nier'], 'r', 'Nierenhof'),
    'kup': (KUP, 'l', 'Kupferdreh'),
}
over = []
for pid, ((u, v), side, txt) in PILLS.items():
    x, y = P(u, v)
    gap = 22 if pid == 'kup' else 30
    pos = f'right:{W - x + gap:.0f}px' if side == 'l' else f'left:{x + gap:.0f}px'
    over.append(f'<div class="ring{" w" if pid == "kup" else ""}" id="r-{pid}" style="left:{x - 24:.1f}px;top:{y - 24:.1f}px"></div>')
    over.append(f'<div class="pillpos" style="{pos};top:{y - 27:.1f}px"><div class="pill{" w" if pid == "kup" else ""}" id="p-{pid}">{txt}</div></div>')
x, y = P(*KUP)
over.append(f'<div class="ring w big" id="r-kup2" style="left:{x - 24:.1f}px;top:{y - 24:.1f}px"></div>')

# ---------- extra svg (in map units) ----------
ex = []
for g in ('nev', 'lang', 'nier'):
    u, v = GAUGE[g]
    for k in range(2):
        ex.append(f'<rect class="halo" id="h-{g}{k}" x="{u - 8}" y="{v - 8}" width="16" height="16"/>')
for i, (u, v) in enumerate(TRI):
    ex.append(f'<circle class="rip" id="rip{i}" cx="{u}" cy="{v + 12}" r="14"/>')
drops = []
for i, (u, v) in enumerate(INPTS):
    ju, jv = (i * 37) % 23 - 11, (i * 53) % 29 - 14
    drops.append((u + ju, v + jv))
    ex.append(f'<line class="drop" id="d{i}" x1="{u + ju}" y1="{v + jv - 16}" x2="{u + ju}" y2="{v + jv}"/>')
NDOT = 10
for k in range(NDOT):
    ex.append(f'<circle class="fdot" id="f{k}" cx="0" cy="0" r="{7.5 - k * 0.3:.1f}"/>')

flowsvg = ('<g id="l-flow"><g id="flow-lit">'
           + ''.join(f'<path class="lit{" main" if i == 0 else ""}" id="lt{i}" d="{d}"/>' for i, (d, *_) in enumerate(NET))
           + '</g><g id="flow-dots">'
           + ''.join(f'<path class="fd" id="fd{i}" d="{d}"/>' for i, (d, *_) in enumerate(NET) if i)
           + '</g></g>')
vb = f'{U0} {V0} {W / K:.2f} {H / K:.2f}'
mapsvg = (f'<svg id="map" width="{W}" height="{H}" viewBox="{vb}">'
          f'<image href="assets/base-crop.jpg" x="380" y="380" width="1140" height="1180"/>'
          f'<rect x="380" y="380" width="1140" height="1180" fill="#0f1b1f" opacity=".28"/>'
          f'{zones}{outline}{rivers}{flowsvg}{icons}{zlabels}{"".join(ex[:6])}{mk}{"".join(ex[6:])}</svg>')

CSS = f"""
@font-face{{font-family:'Manrope';font-style:normal;font-weight:200 800;font-display:block;src:url('assets/fonts/Manrope-variable.woff2') format('woff2')}}
@font-face{{font-family:'Space Grotesk';font-style:normal;font-weight:300 700;font-display:block;src:url('assets/fonts/SpaceGrotesk-variable.woff2') format('woff2')}}
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#121816;--surface:#1a2220;--fg:#e3ebe7;--z1:#a68bd4;--z2:#5fa8dc;--z3:#e6a65a;--z4:#6cc497;--z5:#e7766b;
  --river:#6fb8ec;--icon:#e3ebe7;--gauge:#5cc3d1;--rain:#8cc8f5;
  --map-filter:invert(1) hue-rotate(180deg) brightness(.85) contrast(.9)}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#0f1b1f}}
#root{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:#0f1b1f}}
#mapwrap{{position:absolute;inset:0}}
#map{{position:absolute;left:0;top:0}}
#map image{{filter:var(--map-filter)}}
.zone{{fill-opacity:.34;stroke-width:1.6;stroke-opacity:.95}}
.z-neviges{{fill:var(--z1);stroke:var(--z1)}}.z-langenberg_rest{{fill:var(--z2);stroke:var(--z2)}}
.z-nierenhof{{fill:var(--z3);stroke:var(--z3)}}.z-grenzweg_rest{{fill:var(--z4);stroke:var(--z4)}}.z-lower{{fill:var(--z5);stroke:var(--z5)}}
.outline{{fill:none;stroke:var(--fg);stroke-width:3.4;stroke-linejoin:round}}
.river{{fill:none;stroke:var(--river);stroke-width:1;stroke-linecap:round;stroke-linejoin:round;opacity:.7}}
.river.main{{stroke-width:2.8;opacity:1}}
.icon{{fill:var(--icon);opacity:.2}}.icon.in{{opacity:.85}}
.m-gauge{{fill:var(--gauge);stroke:var(--surface);stroke-width:2.5}}
.m-gauge.brw{{fill:var(--surface);stroke:var(--gauge);stroke-width:3.5}}
.m-target{{fill:none;stroke:var(--fg);stroke-width:4}}.m-target-dot{{fill:var(--fg)}}
.m-rain{{fill:var(--rain);stroke:var(--surface);stroke-width:2}}
.zlbl{{font-family:'Space Grotesk',sans-serif;font-size:29px;font-weight:650;fill:#f5f3ee;paint-order:stroke;
  stroke:#141d1f;stroke-width:6px;stroke-linejoin:round;letter-spacing:-.01em}}
.halo{{fill:none;stroke:var(--gauge);stroke-width:2.5}}
.rip{{fill:none;stroke:var(--rain);stroke-width:2.5}}
.drop{{stroke:#bfe3ff;stroke-width:2.6;stroke-linecap:round}}
#flow-lit{{filter:drop-shadow(0 0 3px rgba(111,184,236,.95))}}
.lit{{fill:none;stroke:#a8dcff;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}}
.lit.main{{stroke-width:3.6}}
.fd{{fill:none;stroke:#eaf7ff;stroke-width:4.2;stroke-linecap:round;stroke-dasharray:.1 38}}
.fdot{{fill:#d9f0ff;filter:drop-shadow(0 0 4px #6fb8ec)}}
.vig{{position:absolute;left:0;right:0;pointer-events:none}}
.chip{{position:absolute;width:{CW}px;height:{CHT}px;border-radius:14px;background:{CARD};color:{WHITE};
  border:2px solid rgba(170,200,205,.22);box-shadow:0 10px 26px rgba(4,10,12,.5),0 2px 6px rgba(4,10,12,.35)}}
.chip .ic{{position:absolute;left:20px;top:18px;fill:none;stroke:currentColor;stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round}}
.chip .num{{position:absolute;right:20px;top:22px;font-family:'Manrope',sans-serif;font-weight:700;font-size:20px;
  letter-spacing:.12em;opacity:.55}}
.chip .ct{{position:absolute;left:22px;top:78px;font-family:'Space Grotesk',sans-serif;font-weight:650;font-size:33px;
  letter-spacing:-.01em;line-height:1}}
.chip .cs{{position:absolute;left:22px;top:118px;font-family:'Manrope',sans-serif;font-weight:700;font-size:22px;
  letter-spacing:.06em;opacity:.7}}
.ring{{position:absolute;width:48px;height:48px;border-radius:50%;border:3.5px solid {OR};
  box-shadow:0 0 14px rgba(240,138,60,.45)}}
.ring.w{{border-color:{WHITE};box-shadow:0 0 12px rgba(245,243,238,.3)}}
.pillpos{{position:absolute;height:54px}}
.pill{{height:54px;padding:0 18px;display:flex;align-items:center;border-radius:12px;background:{CARD};
  border:2px solid {OR};color:{WHITE};font-family:'Space Grotesk',sans-serif;font-weight:650;font-size:31px;
  letter-spacing:-.01em;white-space:nowrap;box-shadow:0 8px 20px rgba(4,10,12,.5)}}
.pill.w{{border-color:rgba(245,243,238,.7)}}
#tog{{position:absolute;right:35px;top:432px;height:54px;padding:0 16px 0 14px;display:flex;align-items:center;gap:12px;
  border-radius:12px;background:rgba(23,38,43,.92);border:2px solid rgba(170,200,205,.22);color:{WHITE};
  font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:28px;box-shadow:0 8px 20px rgba(4,10,12,.45)}}
#trk{{position:relative;width:58px;height:32px;border-radius:16px;background:#33413f}}
#knob{{position:absolute;left:4px;top:4px;width:24px;height:24px;border-radius:50%;background:#9aa8a1}}
"""

VIG = (f'<div class="vig" style="top:0;height:470px;background:linear-gradient(#0f1b1f 0,#0f1b1f 300px,rgba(15,27,31,0) 470px)"></div>'
       f'<div class="vig" style="top:1250px;bottom:0;background:linear-gradient(rgba(15,27,31,0) 0,rgba(15,27,31,.85) 120px,#0f1b1f 220px)"></div>'
       f'<div class="vig" style="top:0;bottom:0;background:linear-gradient(90deg,rgba(15,27,31,.85) 0,rgba(15,27,31,0) 90px,rgba(15,27,31,0) 990px,rgba(15,27,31,.85) 1080px)"></div>'
       f'<div class="vig" style="top:0;bottom:0;background:radial-gradient(ellipse 75% 45% at 52% 45%,rgba(15,27,31,0) 60%,rgba(15,27,31,.5) 100%)"></div>')

# ---------- timeline ----------
J = []
T = J.append
T("const tl = gsap.timeline({ paused: true });")
T("gsap.set('.chip',{autoAlpha:0,scale:.86,y:10});")
T("gsap.set('.ring',{autoAlpha:0,scale:.4});")
T("gsap.set('.pill',{autoAlpha:0,x:0,y:8});")
T("gsap.set('#l-zones path, #l-zlabels text, #l-icon circle, .tri, .halo, .rip, .drop, .fdot, .fd',{autoAlpha:0});")
T(f"gsap.set('#l-icon .in',{{fill:'#e3ebe7'}});")
T(f"tl.fromTo('#mapwrap',{{scale:1}},{{scale:1.04,duration:{DUR},ease:'sine.inOut',transformOrigin:'{ORIGIN[0]}px {ORIGIN[1]}px',immediateRender:false}},0);")


def chip_on(c, t):
    T(f"tl.to('#{c}',{{autoAlpha:1,scale:1,y:0,duration:.45,ease:'back.out(1.6)'}},{t});")
    T(f"tl.to('#{c}',{{color:'{OR}',borderColor:'{OR}',duration:.3,ease:'power1.out'}},{t + .05:.2f});")


def chip_settle(c, t):
    T(f"tl.to('#{c}',{{color:'{WHITE}',borderColor:'rgba(170,200,205,0.22)',duration:.5,ease:'power1.inOut'}},{t});")


def mark(pid, t):
    T(f"tl.to('#r-{pid}',{{autoAlpha:1,scale:1,duration:.4,ease:'back.out(2)'}},{t});")
    T(f"tl.to('#p-{pid}',{{autoAlpha:1,y:0,duration:.4,ease:'power2.out'}},{t + .06:.2f});")


chip_on('c1', 1.14)
for i, g in enumerate(('nev', 'lang', 'nier')):  # soft pulse of the three upstream gauges, "upstream river gauges"
    for k in range(2):
        T(f"tl.fromTo('#h-{g}{k}',{{autoAlpha:.9,scale:1}},{{autoAlpha:0,scale:3,duration:1.1,ease:'power1.out',"
          f"transformOrigin:'50% 50%',immediateRender:false}},{2.85 + k * .55 + i * .08:.2f});")
mark('nev', 3.96)
mark('lang', 5.06)
mark('nier', 6.30)
mark('kup', 6.95)
chip_settle('c1', 8.58)

chip_on('c2', 11.62)
T("const tris = gsap.utils.toArray('.tri');")
for i in range(3):  # rain gauges drop in
    T(f"tl.fromTo(tris[{i}],{{autoAlpha:0,y:-40}},{{autoAlpha:1,y:0,duration:.5,ease:'power2.in',immediateRender:false}},{13.32 + i * .12:.2f});")
for i in range(3):
    T(f"tl.fromTo('#rip{i}',{{autoAlpha:.9,scale:.3}},{{autoAlpha:0,scale:1.6,duration:.7,ease:'power1.out',transformOrigin:'50% 50%',immediateRender:false}},{13.80 + i * .12:.2f});")

chip_settle('c2', 15.68)
chip_on('c3', 15.68)
# forecast grid wave: left->right, top->bottom, done before "48 hours"
wave = "(i,el)=>((+el.getAttribute('cx'))-430)*0.0009+((+el.getAttribute('cy'))-430)*0.00035"
T(f"tl.to('#l-icon circle:not(.in)',{{autoAlpha:.2,duration:.35,ease:'power1.out',stagger:{wave}}},16.0);")
T(f"tl.to('#l-icon .in',{{autoAlpha:.85,duration:.35,ease:'power1.out',stagger:{wave}}},16.0);")

chip_settle('c3', 20.14)
T("tl.to('#knob',{x:26,backgroundColor:'#f5f3ee',duration:.25,ease:'power2.inOut'},20.0);")
T(f"tl.to('#trk',{{backgroundColor:'{OR}',duration:.25,ease:'power2.inOut'}},20.0);")
ZORDER = ['z-neviges', 'z-langenberg_rest', 'z-nierenhof', 'z-grenzweg_rest', 'z-lower']
for i, z in enumerate(ZORDER):
    t = 20.14 + i * .25
    T(f"tl.to('#l-zones .{z}',{{autoAlpha:1,duration:.45,ease:'power1.out'}},{t:.2f});")
    T(f"tl.fromTo('#l-zlabels text:nth-child({i + 1})',{{autoAlpha:0,y:10}},{{autoAlpha:1,y:0,duration:.4,ease:'power2.out',immediateRender:false}},{t + .1:.2f});")
T(f"tl.to('#trk',{{backgroundColor:'#5cc3d1',duration:.5}},21.6);")

for i in range(len(drops)):  # rain on the zones
    t = 22.38 + (i * 7 % 36) * .033
    T(f"tl.fromTo('#d{i}',{{y:-70,autoAlpha:0}},{{keyframes:{{y:[-70,0],autoAlpha:[0,1,1,0]}},duration:.55,ease:'power1.in',repeat:1,repeatDelay:.35,immediateRender:false}},{t:.3f});")

PER = seg[-1] / VF  # Deilbach dots move with the network flow front
START = FT1 - PER   # first dot reaches Kupferdreh at FT1
for i, (d, L, du, dd) in enumerate(NET):  # light every stream from its upstream end as the front passes
    t0, dur = FT1 - du / VF, max((du - dd) / VF, .05)
    T(f"gsap.set('#lt{i}',{{autoAlpha:0,strokeDasharray:{L + 2:.1f},strokeDashoffset:{L + 2:.1f}}});")
    T(f"tl.set('#lt{i}',{{autoAlpha:1}},{t0:.3f});")
    T(f"tl.to('#lt{i}',{{strokeDashoffset:0,duration:{dur:.3f},ease:'none'}},{t0:.3f});")
    if i:
        T(f"tl.fromTo('#fd{i}',{{autoAlpha:0}},{{autoAlpha:.9,duration:{max(dur, .3):.3f},ease:'power1.in',immediateRender:false}},{t0:.3f});")
        T(f"tl.fromTo('#fd{i}',{{strokeDashoffset:0}},{{strokeDashoffset:{-.6 * VF * (DUR - t0):.1f},duration:{DUR - t0:.3f},ease:'none',immediateRender:false}},{t0:.3f});")
xs = ','.join(str(p[0]) for p in flow)
ys = ','.join(str(p[1]) for p in flow)
op = ','.join(['0'] + ['1'] * 8 + ['0'])
for k in range(NDOT):
    st = START + k * .14
    rep = int((DUR - st) // PER) - 1
    T(f"tl.fromTo('#f{k}',{{x:{flow[0][0]},y:{flow[0][1]},autoAlpha:0}},{{keyframes:{{x:[{xs}],y:[{ys}],autoAlpha:[{op}],easeEach:'none'}},"
      f"duration:{PER},ease:'none',repeat:{rep},immediateRender:false}},{st:.2f});")
T("tl.fromTo('#r-kup2',{autoAlpha:.9,scale:1},{autoAlpha:0,scale:2.4,duration:.9,ease:'power1.out',immediateRender:false},24.6);")
T("tl.to('#r-kup',{scale:1.25,duration:.2,ease:'power1.out',yoyo:true,repeat:1},24.6);")

T(f"tl.to('#l-icon .in',{{fill:'{OR}',attr:{{r:7}},duration:.22,ease:'power1.out'}},26.84);")
T("tl.to('#l-icon .in',{fill:'#e3ebe7',attr:{r:5},duration:.4,ease:'power1.inOut'},27.12);")
T(f"tl.set({{}}, {{}}, {DUR});")
T('window.__timelines = window.__timelines || {};')
T('window.__timelines["main"] = tl;')

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<link rel="stylesheet" href="assets/fonts/fonts.css" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-fps="30" data-width="{W}" data-height="{H}">
<div id="mapwrap">
{mapsvg}
{''.join(over)}
</div>
{VIG}
<div id="tog"><div id="trk"><div id="knob"></div></div><span>Zones</span></div>
{chips}
</div>
<script>
{chr(10).join(J)}
</script>
</body>
</html>
"""
if __name__ == '__main__':
    with open('index.html', 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    print('wrote index.html', len(page), 'bytes; flow pts', len(flow), 'deilbach len', round(seg[-1]), 'streams', len(NET), 'Dmax', round(DMAX), 'VF', round(VF))
