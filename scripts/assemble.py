#!/usr/bin/env python3
"""Cut the reel straight from the originals into <project>/assets/aroll.mp4 (1080x1920, clean 30fps CFR from t=0).

Usage:  PY assemble.py <project_dir>      (PY = the skill's Python, see SKILL.md; it has OpenCV for the face zoom)
Needs <project>/sources.json (from ingest.py) and <project>/edl.json:
  [{"id": "hook", "clip": "c1", "in": 12.66, "out": 15.72, "zoom": 1.0, "cx": 0.5, "cy": 0.5, "line": "Everybody's..."}, ...]
  zoom > 1 = punch-in cropped from the original (sharp when the source is 4K). Without cx/cy the crop is centred on the
  face found in that segment (OpenCV, 3 frames); cx/cy (frame fractions) override it. segments.json gets the crop
  centre used (cx/cy) and chin_y, the chin's y in the 1080x1920 output, which build.py keeps pips and photos below.
Writes segments.json with each segment's first frame in the cut ("frame") and frame count ("frames").

Why the CFR re-encode: ffmpeg concat leaves a 0.033s video start offset and timestamp gaps; `hyperframes remove-background`
then duplicates frames and the cutout drifts out of sync with the base video by the end. setpts=N/30 fixes it.
Sync: every segment is cut to a whole number of frames, video and audio to the same length, so the sound cannot drift
from the picture over many cuts (a fraction of a frame lost per cut added up to 0.6s over 39 cuts).
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skillenv  # noqa: E402

FF, FP = skillenv.tool('ffmpeg'), skillenv.tool('ffprobe')
# iPhone footage is HLG (HDR). The renderer's HDR path drops every HTML overlay, so the cut must be SDR (bt709).
# On macOS the source is converted once with Apple's own HDR->SDR tone mapping (avconvert, as Photos shows it in SDR);
# only retagging it (the fallback elsewhere) leaves the picture grey and washed out.
SDR = 'setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709'
FPS = 30


def sdr_source(f, work):
    """an SDR copy of an HDR clip (Apple tone mapping, cached in work/sdr/), or the clip itself"""
    trc = subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=color_transfer', '-of', 'csv=p=0', f],
                         **skillenv.TEXT).stdout.strip().split(',')[0]   # csv may add a trailing comma
    if trc not in ('arib-std-b67', 'smpte2084'):
        return f
    if sys.platform != 'darwin' or not shutil.which('avconvert'):
        print(f'  {os.path.basename(f)} is HDR ({trc}): no avconvert here, colours are only retagged and will look washed out')
        return f
    out = os.path.join(work, 'sdr', os.path.splitext(os.path.basename(f))[0] + '.mov')
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        print(f'  converting {os.path.basename(f)} HDR -> SDR (Apple tone mapping, once)')
        subprocess.run(['avconvert', '-s', f, '-p', 'PresetHighestQuality', '-o', out + '.part.mov', '--replace'],
                       check=True, capture_output=True)
        os.replace(out + '.part.mov', out)
    return out
SDR_TAGS = ['-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709']


def size(f):
    j = json.loads(subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                   'stream=width,height:stream_side_data=rotation', '-of', 'json', f], **skillenv.TEXT).stdout)
    s = j['streams'][0]
    w, h = int(s['width']), int(s['height'])
    # phone clips are stored landscape with a rotation flag; ffmpeg autorotates before our crop, so swap
    rot = next((int(d.get('rotation', 0)) for d in s.get('side_data_list', []) if 'rotation' in d), 0)
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


def crop_box(z, cx, cy, sw, sh):
    w, h = (round(sw / z / 2) * 2, round(sh / z / 2) * 2) if z > 1 else (sw, sh)
    return min(max(round(cx * sw - w / 2), 0), sw - w), min(max(round(cy * sh - h / 2), 0), sh - h), w, h


def crop(z, cx, cy, sw, sh):
    if z <= 1:
        return ''
    x, y, w, h = crop_box(z, cx, cy, sw, sh)
    return f'crop={w}:{h}:{x}:{y},'


def chin_y(fc, z, cx, cy, sw, sh):
    """y of the chin in the 1080x1920 output, from the face found in the source (inserts are placed below it)"""
    x0, y0, w, h = crop_box(z, cx, cy, sw, sh)
    s = max(1080 / w, 1920 / h)                  # scale to cover, then centre-crop (same as the -vf below)
    return round((fc[1] * sh + .6 * fc[2] * sh - y0) * s - (h * s - 1920) / 2)


def face(f, t_in, t_out):
    """Mean face centre (fractions of the upright frame) over 3 frames of the segment, or None."""
    import cv2
    det = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    found = []
    for t in (t_in + (t_out - t_in) * k for k in (.2, .5, .8)):
        png = subprocess.run([FF, '-loglevel', 'error', '-ss', f'{t:.3f}', '-i', f, '-frames:v', '1', '-vf', 'scale=540:-2',
                              '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
        im = cv2.imdecode(__import__('numpy').frombuffer(png, 'uint8'), cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        fs = det.detectMultiScale(im, 1.1, 6, minSize=(40, 40))
        if len(fs):
            x, y, w, h = max(fs, key=lambda r: r[2] * r[3])
            found.append(((x + w / 2) / im.shape[1], (y + h / 2) / im.shape[0], h / im.shape[0]))
    if not found:
        return None
    return tuple(sum(p[i] for p in found) / len(found) for i in range(3))   # centre x, centre y, face height (fractions)


def frames(f):
    return int(subprocess.run([FP, '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames',
                               '-of', 'csv=p=0', f], **skillenv.TEXT).stdout.strip().split(',')[0])


def main():
    skillenv.utf8_stdio()
    proj = skillenv.path_arg(sys.argv[1])
    work, assets = os.path.join(proj, 'work'), os.path.join(proj, 'assets')
    with open(os.path.join(proj, 'sources.json'), encoding='utf-8') as fh:
        src = json.load(fh)
    with open(os.path.join(proj, 'edl.json'), encoding='utf-8') as fh:
        edl = json.load(fh)
    os.makedirs(work, exist_ok=True)
    os.makedirs(assets, exist_ok=True)
    aroll = os.path.join(assets, 'aroll.mp4')
    parts, meta = [], []
    sdr = {c: sdr_source(f, work) for c, f in src.items() if any(s['clip'] == c for s in edl)}
    for k, s in enumerate(edl):
        f = sdr[s['clip']]
        sw, sh = size(f)
        n = max(1, round((s['out'] - s['in']) * FPS))   # whole frames, so audio and video stay the same length
        d = n / FPS
        out = os.path.join(work, f'seg_{k}.mp4')
        z, cx, cy = s.get('zoom', 1), s.get('cx'), s.get('cy')
        fc = face(f, s['in'], s['out'])   # every segment: zooms centre on it, build.py keeps inserts below the chin
        if fc is None:
            print(f"  {s['id']}: no face found" + (', zoom centred on the frame (set cx/cy in the plan)' if z > 1 else ''))
        elif z > 1:
            # face slightly above the middle of the zoomed frame (eyes near the upper third)
            cx = fc[0] if cx is None else cx
            cy = fc[1] + .08 / z if cy is None else cy
        # vertical fill: scale to cover 1080x1920 then centre-crop (handles 4K 9:16 and odd phone sizes)
        vf = (f"{crop(z, .5 if cx is None else cx, .5 if cy is None else cy, sw, sh)}"
              f'scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps={FPS},'
              'tpad=stop_mode=clone:stop_duration=0.2,' + SDR)
        subprocess.run([FF, '-loglevel', 'error', '-y', '-ss', f"{s['in']:.3f}", '-t', f'{d:.3f}', '-i', f,
                        '-map', '0:v:0', '-map', '0:a:0', '-vf', vf, '-frames:v', str(n),
                        '-af', f'apad,atrim=0:{d:.6f},afade=t=in:d=0.02,afade=t=out:st={d - 0.03:.3f}:d=0.03',   # no clicks at the joins
                        '-c:v', 'libx264', '-crf', '14', '-preset', 'medium', '-pix_fmt', 'yuv420p', *SDR_TAGS,
                        '-c:a', 'pcm_s16le', '-ar', '48000', out], check=True)
        parts.append(out)
        cx, cy = .5 if cx is None else cx, .5 if cy is None else cy
        meta.append({**s, 'src_in': s['in'], 'src_out': s['out'], 'cx': cx, 'cy': cy,
                     **({'chin_y': chin_y(fc, z, cx, cy, sw, sh)} if fc else {})})
    # the list holds bare file names (resolved next to concat.txt), so no drive letters or backslashes end up in it
    concat = os.path.join(work, 'concat.txt')
    with open(concat, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(skillenv.concat_entry(os.path.basename(p)) for p in parts))
    # video through the concat demuxer, audio through the concat filter: the demuxer added ~1/60s of audio per join
    # (0.67s over 40 cuts), the filter joins the samples exactly
    ains = [a for p in parts for a in ('-i', p)]
    afil = ''.join(f'[{k + 1}:a]' for k in range(len(parts))) + f'concat=n={len(parts)}:v=0:a=1[a]'
    subprocess.run([FF, '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', concat, *ains,
                    '-filter_complex', afil, '-map', '0:v:0', '-map', '[a]',
                    '-vf', 'setpts=N/30/TB', '-r', '30', '-fps_mode', 'cfr',
                    '-c:v', 'libx264', '-crf', '14', '-preset', 'medium', '-g', '30', '-keyint_min', '30', '-pix_fmt', 'yuv420p', *SDR_TAGS,
                    '-c:a', 'aac', '-b:a', '192k', aroll], check=True)
    fr = 0
    for k, m in enumerate(meta):
        n = frames(parts[k])
        m['frame'], m['frames'] = fr, n
        fr += n
    with open(os.path.join(proj, 'segments.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, indent=1)
    for m in meta:
        print(f"frame {m['frame']:4d} ({m['frame'] / 30:6.3f}s) +{m['frames']:3d}f  {m['id']:8s} {m['clip']} {m['in']}-{m['out']}  {m.get('line', '')}")
    total = frames(aroll)
    print(f'total frames {fr} (aroll.mp4 has {total})' + ('' if total == fr else '  << MISMATCH, investigate'))
    ad = float(subprocess.run([FP, '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=duration', '-of', 'csv=p=0', aroll],
                              **skillenv.TEXT).stdout.strip())
    print(f'audio {ad:.3f}s vs video {total / FPS:.3f}s' + ('' if abs(ad - total / FPS) < 1.5 / FPS else '  << OUT OF SYNC, investigate'))


if __name__ == '__main__':
    main()
