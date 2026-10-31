#!/usr/bin/env python3
"""plan.md -> edl.json (the cut) + timeline.json (every effect). Format: references/plan-format.md.

Usage:  PY plan.py <project_dir>            parse, check, write edl.json + timeline.json, print a summary
        PY plan.py <project_dir> --check    parse and check only

Checks: clips exist in sources.json, in < out, effect ids are known, material names exist in materials.json (or as a
file in the project), and every @word / ..word anchor appears in that segment's text. Errors name the plan line.
Standard library only (review.py imports parse()).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skillenv  # noqa: E402

# effect id -> what it takes: t = "text", m = media files, (nothing) = flags/params only
EFFECTS = {
    'zoom': '', 'no-punch': '', 'no-subs': '', 'push-in': '', 'focus-in': '', 'light-sweep': '',
    'caption-lead': 't', 'blur-pop': 't', 'behind-head': 't', 'caps-track': 't', 'serif-rise': 't',
    'italic-punch': 't', 'sparkle': '', 'hand-note': 't',
    'reel-cards': 'm', 'orbit': 'm', 'window-behind': 'm', 'card-under-chin': 'm',
    'pip': 'm', 'split': 'm', 'cutaway': 'm', 'photo-stack': 'm', 'sfx': '',
}
SEG_RE = re.compile(r'^(~~)?\s*(c\d+)\s+(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*\|\s*(.*)$')


def norm(w):
    return re.sub(r'[^\wäöüß]', '', w.lower())


class PlanError(Exception):
    pass


def parse_fx(body, lineno):
    m = re.search(r'"([^"]*)"', body)
    text = m.group(1) if m else None
    rest = (body[:m.start()] + ' ' + body[m.end():]) if m else body
    toks = rest.split()
    if not toks:
        raise PlanError(f'line {lineno}: empty effect')
    fx = {'fx': toks[0], 'text': text, 'at': None, 'until': None, 'media': [], 'params': {}, 'line': lineno}
    if fx['fx'] not in EFFECTS:
        raise PlanError(f"line {lineno}: unknown effect '{fx['fx']}' (known: {', '.join(EFFECTS)})")
    for t in toks[1:]:
        if t.startswith('@'):
            fx['at'] = t[1:]
        elif t.startswith('..'):
            fx['until'] = t[2:]
        elif '=' in t:
            k, v = t.split('=', 1)
            fx['params'][k] = v
        elif fx['fx'] == 'zoom' and re.fullmatch(r'\d+(\.\d+)?', t):
            fx['params']['zoom'] = float(t)
        elif fx['fx'] == 'sfx' and 'name' not in fx['params']:
            fx['params']['name'] = t
        else:
            f, _, at = t.partition('@')
            fx['media'].append({'file': f, 'at': at or None})
    if 't' in EFFECTS[fx['fx']] and text is None:
        raise PlanError(f"line {lineno}: {fx['fx']} needs its text in double quotes")
    if 'm' in EFFECTS[fx['fx']] and not fx['media']:
        raise PlanError(f"line {lineno}: {fx['fx']} needs at least one material file")
    return fx


def parse(text):
    plan = {'title': '', 'style': 'default', 'sections': []}
    sec, seg = None, None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('>') or line.startswith('<!--'):
            continue
        if line.startswith('# '):
            plan['title'] = line[2:].strip()
        elif re.match(r'^style\s*:', line):
            plan['style'] = line.split(':', 1)[1].strip()
        elif line.startswith('## '):
            name = re.sub(r'[^a-z0-9]+', '-', line[3:].strip().lower()).strip('-') or f's{len(plan["sections"])}'
            sec = {'name': name, 'title': line[3:].strip(), 'segs': []}
            plan['sections'].append(sec)
            seg = None
        elif line.startswith('- '):
            if seg is None:
                raise PlanError(f'line {n}: effect before any segment line')
            seg['fx'].append(parse_fx(line[2:], n))
        else:
            m = SEG_RE.match(line)
            if not m:
                continue   # free text between segments is allowed (notes)
            if sec is None:
                raise PlanError(f'line {n}: segment before the first "## section" heading')
            cut = bool(m.group(1))
            spoken, _, reason = m.group(5).partition('~~') if cut else (m.group(5), '', '')
            seg = {'id': f"{sec['name']}_{len(sec['segs'])}", 'sec': sec['name'], 'clip': m.group(2),
                   'in': float(m.group(3)), 'out': float(m.group(4)), 'text': spoken.strip(), 'cut': cut,
                   'reason': reason.strip(' ()—-:'), 'fx': [], 'line': n}
            if seg['out'] <= seg['in']:
                raise PlanError(f'line {n}: out ({seg["out"]}) must be after in ({seg["in"]})')
            sec['segs'].append(seg)
    return plan


def check(plan, proj):
    errs = []
    srcp = os.path.join(proj, 'sources.json')
    sources = json.load(open(srcp, encoding='utf-8')) if os.path.exists(srcp) else {}
    mp = os.path.join(proj, 'materials.json')
    mats = {m['name'] for m in json.load(open(mp, encoding='utf-8'))} if os.path.exists(mp) else set()
    for sec in plan['sections']:
        for s in sec['segs']:
            if sources and s['clip'] not in sources:
                errs.append(f"line {s['line']}: clip {s['clip']} is not in sources.json ({', '.join(sources)})")
            words = {norm(w) for w in s['text'].split()}
            for fx in s['fx']:
                if s['cut']:
                    errs.append(f"line {fx['line']}: effect on a cut segment (move it or un-cut the line)")
                for f in fx['media']:
                    if f['file'] not in mats and not os.path.exists(os.path.join(proj, f['file'])):
                        errs.append(f"line {fx['line']}: material '{f['file']}' not found (materials.json or project path)")
                # start anchors must be in this segment; an ..until word may sit in a later segment of the section
                for a in [fx['at']] + [f['at'] for f in fx['media']]:
                    if a and not re.fullmatch(r'[+]?\d+(\.\d+)?', a):
                        w = norm(a.split('#')[0])
                        if not any(x.startswith(w) for x in words):
                            errs.append(f"line {fx['line']}: anchor '{a}' is not in this segment's text")
    if not any(not s['cut'] for sec in plan['sections'] for s in sec['segs']):
        errs.append('no kept segments')
    return errs


def main():
    skillenv.utf8_stdio()
    proj = skillenv.path_arg(sys.argv[1])
    with open(os.path.join(proj, 'plan.md'), encoding='utf-8') as fh:
        try:
            plan = parse(fh.read())
        except PlanError as e:
            sys.exit(f'plan.md: {e}')
    errs = check(plan, proj)
    if errs:
        sys.exit('plan.md has problems:\n  ' + '\n  '.join(errs))
    kept = [s for sec in plan['sections'] for s in sec['segs'] if not s['cut']]
    cut = [s for sec in plan['sections'] for s in sec['segs'] if s['cut']]
    nfx = sum(len(s['fx']) for s in kept)
    print(f"{plan['title'] or 'plan'}: {len(kept)} segments kept ({sum(s['out'] - s['in'] for s in kept):.1f}s), "
          f"{len(cut)} cut, {nfx} effects, style '{plan['style']}'")
    if '--check' in sys.argv:
        return
    edl, tl = [], []
    for s in kept:
        z = next((fx['params'] for fx in s['fx'] if fx['fx'] == 'zoom'), {})
        e = {'id': s['id'], 'sec': s['sec'], 'clip': s['clip'], 'in': s['in'], 'out': s['out'],
             'zoom': float(z.get('zoom', 1)), 'line': s['text']}
        for k in ('cx', 'cy'):
            if k in z:
                e[k] = float(z[k])
        edl.append(e)
        tl += [{**{k: v for k, v in fx.items() if k != 'line'}, 'seg': s['id'], 'sec': s['sec']}
               for fx in s['fx'] if fx['fx'] != 'zoom']
    with open(os.path.join(proj, 'edl.json'), 'w', encoding='utf-8') as fh:
        json.dump(edl, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(proj, 'timeline.json'), 'w', encoding='utf-8') as fh:
        json.dump({'title': plan['title'], 'style': plan['style'], 'fx': tl}, fh, indent=1, ensure_ascii=False)
    print('wrote edl.json + timeline.json')


if __name__ == '__main__':
    main()
