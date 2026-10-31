# Builds effects-gallery.html from template.html: embeds the insert frames and the skill's sfx as data URIs.
import base64, json, pathlib
here = pathlib.Path(__file__).parent
sfx_dir = here.parent.parent / "assets/template/assets/sfx"
uri = lambda p, m: f"data:{m};base64," + base64.b64encode(p.read_bytes()).decode()
sfx = {p.stem: uri(p, "audio/mpeg") for p in sorted(sfx_dir.glob("*.mp3"))}
html = (here / "template.html").read_text(encoding="utf-8")
for k, f, m in [("receipt", "receipt.png", "image/png"), ("arch", "arch.png", "image/png"), ("map", "map.jpg", "image/jpeg")]:
    html = html.replace("{{" + k + "}}", uri(here / f, m))
html = html.replace("{{sfx}}", json.dumps(sfx))
assert "{{" not in html, "unfilled placeholder in template.html"
(here / "effects-gallery.html").write_text(html, encoding="utf-8")
print("wrote", here / "effects-gallery.html", len(html), "bytes")
