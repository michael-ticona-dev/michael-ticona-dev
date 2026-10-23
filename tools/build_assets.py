"""Generate the SVG assets used by the profile README.

Text is converted to outlines because GitHub serves README images with a CSP
that blocks external fonts. Animations are plain CSS inside the SVG: GitHub
renders SVGs through <img>, which disables scripts but keeps CSS animations.

Requirements:
    pip install fonttools
    npm pack geist simple-icons   # Geist fonts (OFL) and Simple Icons (CC0)

Usage:
    python tools/build_assets.py --fonts <geist>/dist/fonts --icons <simple-icons>/icons
"""

import argparse
import html
import re
import shutil
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

INK = "#080808"
PANEL = "#111111"
MUTED = "#858585"
PAPER = "#F2F2F2"
SHU = "#D2452C"  # vermilion, the single accent

TAGLINE = "Ingeniería de Sistemas e Informática."

# (label, icon) per category; icon is a Simple Icons slug or a key of GLYPHS.
CATALOG = [
    ("Languages", [
        ("Python", "python"), ("Java", "openjdk"), ("C", "c"),
        ("C++", "cplusplus"), ("C#", "csharp"), ("JavaScript", "javascript"),
    ]),
    ("Web", [
        ("HTML", "html5"), ("CSS", "css"), ("Laravel", "laravel"),
        ("Vite", "vite"), ("React", "react"), ("React Native", "react"),
    ]),
    ("Databases", [
        ("MySQL", "mysql"), ("SQL", "database"), ("PostgreSQL", "postgresql"),
    ]),
    ("Systems", [
        ("Arch Linux", "archlinux"), ("Ubuntu", "ubuntu"), ("Hyprland", "hyprland"),
    ]),
    ("Embedded & hardware", [
        ("ESP32", "chip"), ("Espressif", "espressif"), ("Raspberry Pi", "raspberrypi"),
    ]),
    ("Also", [
        ("Unity", "unity"), ("Ethical hacking", "key"), ("Cybersecurity", "shield"),
    ]),
]

# Crops (x, y, size) in icon units for logos that include a wordmark.
CROP = {"mysql": (13.6, 2.6, 10.4)}

# Outline glyphs (24x24, stroked) for items without an official icon.
GLYPHS = {
    "csharp": '<path d="M12 2.5l8.2 4.75v9.5L12 21.5l-8.2-4.75v-9.5z"/>'
              '<path d="M10.6 8.5l-1 7M14.4 8.5l-1 7M8.2 10.6h7.8M7.8 13.4h7.8"/>',
    "database": '<ellipse cx="12" cy="5.5" rx="7.5" ry="3"/>'
                '<path d="M4.5 5.5v13c0 1.66 3.36 3 7.5 3s7.5-1.34 7.5-3v-13"/>'
                '<path d="M4.5 12c0 1.66 3.36 3 7.5 3s7.5-1.34 7.5-3"/>',
    "chip": '<rect x="6" y="6" width="12" height="12" rx="1.5"/>'
            '<rect x="9.5" y="9.5" width="5" height="5" rx=".5"/>'
            '<path d="M9.5 2.5V6M14.5 2.5V6M9.5 18v3.5M14.5 18v3.5'
            'M2.5 9.5H6M2.5 14.5H6M18 9.5h3.5M18 14.5h3.5"/>',
    "key": '<circle cx="7.5" cy="12" r="4.5"/><path d="M12 12h9.5M18.5 12v3.5M21.5 12v2.5"/>',
    "shield": '<path d="M12 2.5l7.5 3v6c0 4.9-3.2 8.5-7.5 10-4.3-1.5-7.5-5.1-7.5-10v-6z"/>'
              '<path d="M8.75 12l2.25 2.25 4.25-4.5"/>',
}


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class Font:
    def __init__(self, path):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm

    def outline(self, text, size, x, y, tracking=0.0):
        """Return ([(char, path_d)], width) for text set at baseline (x, y)."""
        scale = size / self.upm
        out, cx = [], x
        for ch in text:
            glyph = self.glyphs[self.cmap[ord(ch)]]
            pen = SVGPathPen(self.glyphs, ntos=num)
            glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, cx, y)))
            out.append((ch, pen.getCommands()))
            cx += glyph.width * scale + tracking
        return out, cx - x - tracking

    def path(self, text, size, x, y, tracking=0.0):
        chars, width = self.outline(text, size, x, y, tracking)
        return "".join(d for _, d in chars), width


def svg(width, height, body, style="", label=None):
    a11y = f' role="img" aria-label="{html.escape(label)}"' if label else ' aria-hidden="true"'
    css = f"<style>{style}</style>" if style else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(width)}" height="{num(height)}" '
            f'viewBox="0 0 {num(width)} {num(height)}"{a11y}>{css}{body}</svg>\n')


def build_header(sans, sans_medium, mono, mono_semibold):
    W, H, X = 1000, 400, 72
    parts = []

    # Frame and a dot grid that fades in from the right edge.
    parts.append(
        '<defs>'
        '<pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">'
        f'<circle cx="10" cy="10" r="1" fill="{PAPER}"/></pattern>'
        '<linearGradient id="fade" x1="0" x2="1"><stop offset=".45" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity=".09"/></linearGradient>'
        '<mask id="m"><rect width="100%" height="100%" fill="url(#fade)"/></mask>'
        '</defs>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{INK}" stroke="#1C1C1C"/>'
        f'<rect x="1" y="45" width="{W - 2}" height="{H - 60}" fill="url(#dots)" mask="url(#m)"/>'
        f'<path d="M1 44.5h{W - 2}" stroke="#1C1C1C"/>'
    )

    # Status bar: Hyprland-style workspaces on the left, host on the right.
    parts.append(f'<rect x="24" y="19" width="18" height="6" rx="3" fill="{PAPER}"/>')
    for i in range(4):
        parts.append(f'<circle cx="{54 + i * 14}" cy="22" r="3" fill="#2E2E2E"/>')
    _, host_w = mono.outline("arch linux", 12, 0, 0)
    parts.append(f'<path d="{mono.path("arch linux", 12, W - 24 - host_w, 26)[0]}" fill="{MUTED}"/>')

    # Prompt typed character by character.
    chars, _ = mono.outline("~ $ whoami", 17, X, 124)
    for i, (ch, d) in enumerate(chars):
        if d:
            fill = PAPER if i >= 4 else MUTED
            parts.append(f'<path class="k" style="animation-delay:{num(.4 + i * .08)}s" d="{d}" fill="{fill}"/>')

    # Name, one letter at a time.
    name = "MICHAEL JESÚS TICONA"
    chars, name_w = sans_medium.outline(name, 52, X, 202, tracking=5)
    for i, (ch, d) in enumerate(chars):
        if d:
            parts.append(f'<path class="l" style="animation-delay:{num(1.4 + i * .035)}s" d="{d}" fill="{PAPER}"/>')

    # Hairline drawn under the name.
    parts.append(f'<path class="rule" d="M{X} 236.5h{num(name_w)}" stroke="{PAPER}" stroke-opacity=".28" '
                 f'stroke-dasharray="{num(name_w)}"/>')

    tag, _ = sans.path(TAGLINE, 24, X, 286)
    parts.append(f'<path class="fade" d="{tag}" fill="{MUTED}"/>')

    # A fresh prompt waiting for input.
    prompt, pw = mono.path("~ $", 17, X, 338)
    parts.append(f'<g class="next"><path d="{prompt}" fill="{MUTED}"/>'
                 f'<rect class="cursor" x="{num(X + pw + 10)}" y="323" width="9" height="19" fill="{SHU}"/></g>')

    # Hanko seal with initials.
    size = 48
    _, sw = mono_semibold.outline("MJT", 14, 0, 0)
    sx, sy = W - X - size, 332.5 - size / 2  # centred on the cursor line
    seal_d = mono_semibold.path("MJT", 14, sx + (size - sw) / 2, sy + size / 2 + 5)[0]
    parts.append(f'<g transform="rotate(-4 {sx + size / 2} {sy + size / 2})"><g class="stamp">'
                 f'<rect x="{sx}" y="{sy}" width="{size}" height="{size}" rx="4" fill="{SHU}"/>'
                 f'<path d="{seal_d}" fill="{INK}"/></g></g>')

    style = (
        "@keyframes show{from{opacity:0}to{opacity:1}}"
        "@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}"
        f"@keyframes draw{{from{{stroke-dashoffset:{num(name_w)}}}to{{stroke-dashoffset:0}}}}"
        "@keyframes blink{50%{opacity:0}}"
        "@keyframes stamp{from{opacity:0;transform:scale(1.25)}to{opacity:1;transform:none}}"
        ".k{animation:show .01s both}"
        ".l{transform-box:fill-box;animation:rise 1s cubic-bezier(.2,.7,.2,1) both}"
        ".rule{animation:draw 1.8s cubic-bezier(.65,0,.25,1) 2.3s both}"
        ".fade{animation:show 1.2s ease 3s both}"
        ".next{animation:show .01s 3.9s both}"
        ".cursor{animation:blink 1.2s steps(1) 4s infinite}"
        ".stamp{transform-box:fill-box;transform-origin:center;"
        "animation:stamp .45s cubic-bezier(.3,1.4,.5,1) 4.3s both}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )
    label = f"Michael Jesús Ticona — {TAGLINE}"
    (OUT / "header.svg").write_text(svg(W, H, "".join(parts), style, label))


THEME = (
    "@media (prefers-color-scheme:light){"
    ".bg{fill:#F6F6F6;stroke:#E1E1E1}.fg{fill:#111111}.st{stroke:#111111}}"
)


def icon_markup(slug, icons_dir, x, y, size):
    s = size / 24
    if slug in GLYPHS:
        return (f'<g class="st" transform="translate({num(x)} {num(y)}) scale({num(s)})" fill="none" '
                f'stroke="{PAPER}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                f'{GLYPHS[slug]}</g>')
    d = re.search(r' d="([^"]+)"', (icons_dir / f"{slug}.svg").read_text()).group(1)
    if slug in CROP:
        cx, cy, cs = CROP[slug]
        k = size / cs
        return (f'<clipPath id="crop"><rect x="{cx}" y="{cy}" width="{cs}" height="{cs}"/></clipPath>'
                f'<path class="fg" clip-path="url(#crop)" transform="translate({num(x - cx * k)} {num(y - cy * k)}) '
                f'scale({num(k)})" d="{d}" fill="{PAPER}"/>')
    return f'<path class="fg" transform="translate({num(x)} {num(y)}) scale({num(s)})" d="{d}" fill="{PAPER}"/>'


def build_chip(name, slug, mono, icons_dir):
    pad, h, icon, gap, margin = 12, 30, 16, 9, 3
    _, text_w = mono.outline(name, 13, 0, 0)
    w = pad + icon + gap + text_w + pad
    x0 = y0 = margin
    text_d, _ = mono.path(name, 13, x0 + pad + icon + gap, y0 + h / 2 + 4.6)
    body = (f'<rect class="bg" x="{x0 + .5}" y="{y0 + .5}" width="{num(w - 1)}" height="{h - 1}" rx="7" '
            f'fill="{PANEL}" stroke="#262626"/>'
            + icon_markup(slug, icons_dir, x0 + pad, y0 + (h - icon) / 2, icon)
            + f'<path class="fg" d="{text_d}" fill="{PAPER}"/>')
    return svg(w + 2 * margin, h + 2 * margin, body, THEME, name)


def build_label(index, title, mono):
    text = f"{index:02d}  {title.upper()}"
    d, w = mono.path(text, 11, 3, 15, tracking=1.6)
    return svg(w + 6, 22, f'<path d="{d}" fill="{MUTED}"/>', label=title)


def build_divider():
    body = ('<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" x2="1000">'
            f'<stop offset="0" stop-color="{MUTED}" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="{MUTED}" stop-opacity="1"/>'
            f'<stop offset="1" stop-color="{MUTED}" stop-opacity="0"/></linearGradient></defs>'
            '<path d="M0 8.5h1000" stroke="url(#g)" vector-effect="non-scaling-stroke"/>')
    return (svg(1000, 17, body).replace("<svg ", '<svg preserveAspectRatio="none" ', 1))


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("#", "sharp").replace("+", "p")).strip("-")


def catalog_markdown():
    blocks = []
    for title, items in CATALOG:
        chips = "\n".join(f'<img src="assets/chips/{slugify(name)}.svg" alt="{html.escape(name)}">'
                           for name, _ in items)
        blocks.append(f'<p>\n<img src="assets/labels/{slugify(title)}.svg" alt="{html.escape(title)}"><br>\n'
                      f'{chips}\n</p>')
    return "\n\n".join(blocks)


def update_readme():
    readme = ROOT / "README.md"
    start, end = "<!-- catalog:start -->", "<!-- catalog:end -->"
    text = readme.read_text()
    head, rest = text.split(start)
    _, tail = rest.split(end)
    readme.write_text(f"{head}{start}\n{catalog_markdown()}\n{end}{tail}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, required=True)
    parser.add_argument("--icons", type=Path, required=True)
    args = parser.parse_args()

    sans = Font(args.fonts / "geist-sans/Geist-Regular.ttf")
    sans_medium = Font(args.fonts / "geist-sans/Geist-Medium.ttf")
    mono = Font(args.fonts / "geist-mono/GeistMono-Regular.ttf")
    mono_semibold = Font(args.fonts / "geist-mono/GeistMono-SemiBold.ttf")

    for sub in ("chips", "labels"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
        (OUT / sub).mkdir(parents=True)

    build_header(sans, sans_medium, mono, mono_semibold)
    (OUT / "divider.svg").write_text(build_divider())

    titles = [title for title, _ in CATALOG] + ["Interests"]
    for i, title in enumerate(titles, 1):
        (OUT / "labels" / f"{slugify(title)}.svg").write_text(build_label(i, title, mono))
    for _, items in CATALOG:
        for name, slug in items:
            (OUT / "chips" / f"{slugify(name)}.svg").write_text(build_chip(name, slug, mono, args.icons))
    update_readme()


if __name__ == "__main__":
    main()
