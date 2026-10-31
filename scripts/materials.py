#!/usr/bin/env python3
"""Register the user's own material (photos, b-roll clips) for a /sfv-edit project.

Usage:  PY materials.py <project_dir> <files or folders ...>

Writes into <project_dir>:
  assets/materials/<name>.jpg|.mp4   browser-ready copies (photos upright, max 2160px; clips H.264 30fps, no audio)
  materials.json                     [{"name", "file", "kind": "img"|"video", "w", "h", "dur", "src", "note": ""}]
  work/materials.jpg                 contact sheet, one numbered row per item: LOOK at it, then fill each "note"
                                     (what is in it, where it could go) so the plan can match material to lines
Originals are never modified. Re-running keeps existing notes and skips files already converted.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skillenv  # noqa: E402

FF, FP = skillenv.tool('ffmpeg'), skillenv.tool('ffprobe')
IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.tif', '.tiff')
VID_EXT = ('.mp4', '.mov', '.m4v')


def probe(f):
    j = json.loads(subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                   '-show_entries', 'format=duration', '-of', 'json', f], **skillenv.TEXT).stdout)
    s = j['streams'][0]
    return int(s['width']), int(s['height']), float(j['format'].get('duration', 0))


def convert_img(src, dst):
    if src.lower().endswith(('.heic', '.heif')):   # Pillow cannot read HEIC; ffmpeg can (and applies the rotation)
        subprocess.run([FF, '-loglevel', 'error', '-y', '-i', src, '-frames:v', '1', '-q:v', '2', dst], check=True)
        src = dst
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    im.thumbnail((2160, 2160))
    im.save(dst, quality=90)
    return im.size


def convert_vid(src, dst):
    # HDR phone clips: Apple tone mapping first (same as the A-roll, see assemble.py), retag only as the fallback
    from assemble import sdr_source
    src = sdr_source(src, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(dst))), 'work'))
    # scale so the short side is at most 1080 (inserts are never bigger than the frame), keyframe every 30 for seeking
    subprocess.run([FF, '-loglevel', 'error', '-y', '-i', src, '-an', '-vf',
                    "scale='if(lt(iw,ih),min(1080,iw),-2)':'if(lt(iw,ih),-2,min(1080,ih))':flags=lanczos,fps=30,format=yuv420p,"
                    "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709",
                    '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-g', '30', '-color_primaries', 'bt709',
                    '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart', dst], check=True)
    return probe(dst)


def sheet(items, proj, out):
    rows = []
    for k, it in enumerate(items):
        f = os.path.join(proj, it['file'])
        if it['kind'] == 'img':
            ims = [Image.open(f)]
        else:
            ims = []
            for p in (.1, .4, .7, .95):
                png = subprocess.run([FF, '-loglevel', 'error', '-ss', f"{it['dur'] * p:.2f}", '-i', f, '-frames:v', '1',
                                      '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
                if png:
                    ims.append(Image.open(__import__('io').BytesIO(png)))
        row = Image.new('RGB', (1400, 260), (24, 24, 24))
        x = 260
        for im in ims:
            im = im.convert('RGB')
            im.thumbnail((280, 240))
            row.paste(im, (x, 10))
            x += im.size[0] + 10
        d = ImageDraw.Draw(row)
        d.text((14, 14), f"{k + 1}. {it['name']}", fill=(255, 255, 255))
        d.text((14, 36), f"{it['kind']} {it['w']}x{it['h']}" + (f" {it['dur']:.1f}s" if it['kind'] == 'video' else ''), fill=(170, 170, 170))
        rows.append(row)
    if not rows:
        return
    out_im = Image.new('RGB', (1400, 260 * len(rows)))
    for k, r in enumerate(rows):
        out_im.paste(r, (0, 260 * k))
    out_im.save(out, quality=80)


def main():
    skillenv.utf8_stdio()
    proj, args = skillenv.path_arg(sys.argv[1]), sys.argv[2:]
    files = []
    for a in map(skillenv.path_arg, args):
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a)) if f.lower().endswith(IMG_EXT + VID_EXT)]
        elif os.path.exists(a):
            files.append(a)
        else:
            print(f'  skipped (not found): {a}', flush=True)
    mdir = os.path.join(proj, 'assets', 'materials')
    os.makedirs(mdir, exist_ok=True)
    os.makedirs(os.path.join(proj, 'work'), exist_ok=True)
    mj = os.path.join(proj, 'materials.json')
    old = {}
    if os.path.exists(mj):
        with open(mj, encoding='utf-8') as fh:
            old = {m['src']: m for m in json.load(fh)}
    items, names = [], set()
    for src in files:
        src = os.path.abspath(src)
        stem = skillenv.safe_name(os.path.splitext(os.path.basename(src))[0]).replace(' ', '_')
        kind = 'img' if src.lower().endswith(IMG_EXT) else 'video'
        name = stem + ('.jpg' if kind == 'img' else '.mp4')
        n = 2
        while name in names:   # two originals with the same stem (photo.HEIC + photo.jpg)
            name = f"{stem}_{n}{os.path.splitext(name)[1]}"; n += 1
        names.add(name)
        dst = os.path.join(mdir, name)
        if src in old and os.path.exists(dst):
            it = old[src]
        else:
            print(f'  {name} ...', flush=True)
            if kind == 'img':
                w, h = convert_img(src, dst); dur = 0
            else:
                w, h, dur = convert_vid(src, dst)
            it = {'name': name, 'file': f'assets/materials/{name}', 'kind': kind, 'w': w, 'h': h, 'dur': round(dur, 2),
                  'src': src, 'note': old.get(src, {}).get('note', '')}
        items.append(it)
    items += [m for s, m in old.items() if s not in {i['src'] for i in items}]   # keep earlier registrations
    with open(mj, 'w', encoding='utf-8') as fh:
        json.dump(items, fh, indent=1, ensure_ascii=False)
    sheet(items, proj, os.path.join(proj, 'work', 'materials.jpg'))
    for k, it in enumerate(items):
        print(f"{k + 1:3d}. {it['name']:40s} {it['kind']:5s} {it['w']}x{it['h']}" + (f" {it['dur']:.1f}s" if it['kind'] == 'video' else ''))
    print(f'{len(items)} items -> materials.json, contact sheet work/materials.jpg')


if __name__ == '__main__':
    main()
