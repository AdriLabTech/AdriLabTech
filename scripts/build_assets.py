#!/usr/bin/env python3
"""Genera los SVG del README (estilo Ryoku: papel negro, tinta hueso).

Uso:  python3 scripts/build_assets.py        # escribe en assets/

Fuentes locales (Arch): Fraunces, Space Grotesk, JetBrains Mono Nerd Font, Noto Sans CJK JP.
El texto se convierte a trazados, así que el resultado no depende de fuentes en GitHub.
Iconos: simple-icons (CC0) en scripts/src/icons. Sprite: hoja del personaje de Adrián
(plugin claude-code de Ryoku), celdas de 40x46.
"""
import base64
import io
import os
import re

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTCollection, TTFont
from fontTools.varLib import instancer
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts", "src")
OUT = os.path.join(ROOT, "assets")

PAPER, RAISED = "#000000", "#0a0a0a"
INK, DIM, MUTED = "#cdc4ba", "#b0a9a0", "#958f87"
LINE = "rgba(205,196,186,.26)"
LINE_SOFT = "rgba(205,196,186,.13)"
VERMILION = "#e2342a"

# ---------------------------------------------------------------- fuentes
_cache = {}


def font(key):
    if key in _cache:
        return _cache[key]
    if key == "serif":
        f = TTFont("/usr/share/fonts/TTF/Fraunces[SOFT,WONK,opsz,wght].ttf")
        f = instancer.instantiateVariableFont(f, {"wght": 800, "opsz": 144, "SOFT": 0, "WONK": 0})
    elif key == "ui":
        f = TTFont("/usr/share/fonts/OTF/SpaceGrotesk-Bold.otf")
    elif key == "ui-regular":
        f = TTFont("/usr/share/fonts/OTF/SpaceGrotesk-Regular.otf")
    elif key == "mono":
        f = TTFont("/usr/share/fonts/TTF/JetBrainsMonoNerdFontMono-Bold.ttf")
    elif key == "mono-regular":
        f = TTFont("/usr/share/fonts/TTF/JetBrainsMonoNerdFontMono-Regular.ttf")
    elif key == "jp":
        f = TTCollection("/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc").fonts[0]
    else:
        raise KeyError(key)
    _cache[key] = f
    return f


def text_width(key, text, size, tracking=0.0):
    f = font(key)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return sum(hmtx[cmap.get(ord(c), ".notdef")][0] * size / upm + tracking for c in text) - tracking


def text_path(key, text, size, x, y, fill=INK, tracking=0.0, anchor="start", extra=""):
    """Texto como <path>. y = línea base. tracking en px."""
    f = font(key)
    gs, cmap, hmtx, upm = f.getGlyphSet(), f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    w = text_width(key, text, size, tracking)
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    s = size / upm
    pen_x, parts = x, []
    for c in text:
        g = cmap.get(ord(c), ".notdef")
        pen = SVGPathPen(gs)
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, pen_x, y)))
        d = pen.getCommands()
        if d:
            parts.append(d)
        pen_x += hmtx[g][0] * s + tracking
    return f'<path d="{" ".join(parts)}" fill="{fill}" {extra}/>'


# ---------------------------------------------------------------- imágenes
def data_uri(im):
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def sprite_strip(first, last):
    """Tira horizontal con los fotogramas first..last (inclusive) de la hoja 10 columnas."""
    sheet = Image.open(os.path.join(SRC, "adrian.png")).convert("RGBA")
    w, h, cols = 40, 46, 10
    n = last - first + 1
    strip = Image.new("RGBA", (w * n, h), (0, 0, 0, 0))
    for k in range(n):
        i = first + k
        strip.paste(sheet.crop(((i % cols) * w, (i // cols) * h, (i % cols) * w + w, (i // cols) * h + h)), (k * w, 0))
    return strip, n, w, h


def sprite(first, last, x, y, scale, ms_per_frame, name):
    strip, n, w, h = sprite_strip(first, last)
    dur = n * ms_per_frame / 1000
    return f"""<g transform="translate({x} {y}) scale({scale})">
  <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" overflow="hidden">
    <image class="{name}" href="{data_uri(strip)}" width="{w * n}" height="{h}" style="image-rendering:pixelated"/>
  </svg>
</g>""", f"""@keyframes {name} {{ from {{ transform: translateX(0) }} to {{ transform: translateX(-{w * n}px) }} }}
.{name} {{ animation: {name} {dur}s steps({n}, end) infinite }}
"""


def halftone_scene(width):
    im = Image.open(os.path.join(SRC, "escena-torii.png")).convert("RGBA")
    h = round(im.height * width / im.width)
    return im.resize((width, h), Image.NEAREST)


# ---------------------------------------------------------------- piezas
GRAIN = """<filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7"/>
    <feColorMatrix values="0 0 0 0 0.8  0 0 0 0 0.77  0 0 0 0 0.73  0 0 0 0.9 -0.35"/>
  </filter>"""


def crosses(w, h, m=18, s=5):
    pts = [(m, m), (w - m, m), (m, h - m), (w - m, h - m)]
    return "".join(
        f'<path d="M{x - s} {y}H{x + s}M{x} {y - s}V{y + s}" stroke="{INK}" stroke-opacity=".42" stroke-width="1"/>'
        for x, y in pts
    )


def hero():
    W, H = 1200, 460
    scene = halftone_scene(580)
    char, css = sprite(21, 28, 868, 196, 5.2, 130, "type")
    title = text_path("serif", "ADRILABTECH", 88, 58, 252, INK, tracking=1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="AdriLabTech: Construyendo software, explorando tecnologías, compartiendo el proceso">',
        "<title>AdriLabTech</title>",
        f"<style>{css}</style>",
        "<defs>",
        GRAIN,
        '<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#000"/><stop offset=".38" stop-color="#fff"/></linearGradient>',
        f'<mask id="m"><rect x="620" y="0" width="580" height="{H}" fill="url(#fade)"/></mask>',
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
        f'<g mask="url(#m)" opacity=".92"><image href="{data_uri(scene)}" x="620" y="60" width="580" height="{scene.height}" style="image-rendering:pixelated"/></g>',
        # suelo bajo el personaje
        f'<path d="M700 410H1140" stroke="{INK}" stroke-opacity=".42"/>',
        char,
        # eyebrow
        f'<circle cx="64" cy="82" r="4" fill="{VERMILION}"/>',
        text_path("mono", "@ADRILABTECH  ·  LOW NOISE  ·  ONLINE", 13, 80, 87, MUTED, tracking=2.4),
        title,
        text_path("ui-regular", "Construyendo software · Explorando tecnologías · Compartiendo el proceso", 17, 62, 296, DIM),
        # ficha técnica
        f'<path d="M60 340H620" stroke="{INK}" stroke-opacity=".26"/>',
        text_path("mono-regular", "DEV MULTIPLATAFORMA", 12, 60, 372, INK, tracking=2.2),
        text_path("mono-regular", "SISTEMAS · CIBERSEGURIDAD · RUST", 12, 60, 394, MUTED, tracking=2.2),
        text_path("mono-regular", "PAPER #000000 · INK #CDC4BA · NO SHADOW", 11, 60, 424, MUTED, tracking=1.6),
        # texto vertical
        f'<g transform="translate(1166 400) rotate(-90)">{text_path("mono-regular", "SHOT ON BLACK", 11, 0, 0, MUTED, tracking=3)}</g>',
        text_path("mono-regular", "01 // HOME", 11, 1126, 44, MUTED, tracking=2, anchor="end"),
        crosses(W, H),
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="2" fill="none" stroke="{INK}" stroke-opacity=".13"/>',
        f'<rect width="{W}" height="{H}" filter="url(#grain)" opacity=".055"/>',
        "</svg>",
    ]
    return "\n".join(parts)


def section(num, label, title, kanji):
    W, H = 1200, 88
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{title}">',
            f"<title>{title}</title>",
            f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
            text_path("mono", f"{num} // {label}", 12, 20, 30, MUTED, tracking=2.6),
            text_path("serif", title, 34, 18, 68, INK),
            f'<circle cx="{W - 52}" cy="44" r="26" fill="none" stroke="{INK}" stroke-opacity=".26"/>',
            text_path("jp", kanji, 26, W - 52, 54, INK, anchor="middle"),
            f'<path d="M20 {H - .5}H{W - 100}" stroke="{INK}" stroke-opacity=".26"/>',
            f'<path d="M{W - 24} {H - .5}H{W - 20}" stroke="{INK}" stroke-opacity=".26"/>',
            "</svg>",
        ]
    )


def icon_path(slug):
    p = os.path.join(SRC, "icons", f"{slug}.svg")
    return re.search(r'<path d="([^"]+)"', open(p).read()).group(1)


def badge(label, slug):
    h, pad, ic = 34, 14, 16
    tw = text_width("mono", label, 12, 1.6)
    w = int(pad + ic + 10 + tw + pad + .5)
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">',
            f"<title>{label}</title>",
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="2" fill="{PAPER}" stroke="{INK}" stroke-opacity=".32"/>',
            f'<g transform="translate({pad} {(h - ic) / 2}) scale({ic / 24})"><path d="{icon_path(slug)}" fill="{INK}"/></g>',
            text_path("mono", label, 12, pad + ic + 10, 21.5, INK, tracking=1.6),
            "</svg>",
        ]
    )


def project_card(tag, name, desc_lines):
    W, H = 400, 132
    lines = [text_path("ui-regular", t, 14, 22, 84 + i * 20, DIM) for i, t in enumerate(desc_lines)]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{name}">',
            f"<title>{name}</title>",
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="2" fill="{RAISED}" stroke="{INK}" stroke-opacity=".26"/>',
            f'<circle cx="{W - 24}" cy="24" r="9" fill="{INK}" fill-opacity=".16"/>',
            text_path("mono", tag, 11, 22, 30, MUTED, tracking=2.2),
            text_path("ui", name, 26, 21, 62, INK),
            *lines,
            text_path("mono", "GITHUB →", 10, W - 20, H - 14, MUTED, tracking=2, anchor="end"),
            f'<path d="M22 {H - 18}H64" stroke="{INK}" stroke-opacity=".42"/>',
            "</svg>",
        ]
    )


def footer():
    W, H = 1200, 150
    char, css = sprite(35, 40, 1020, 62, 2.0, 160, "cheer")
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Build something worth understanding.">',
            "<title>AdriLabTech</title>",
            f"<style>{css}</style>",
            f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
            f'<circle cx="1062" cy="92" r="46" fill="{INK}" fill-opacity=".16"/>',
            f'<path d="M0 .5H{W}" stroke="{INK}" stroke-opacity=".26"/>',
            text_path("mono", "99 // END", 12, 20, 36, MUTED, tracking=2.6),
            text_path("serif", "Build something worth understanding.", 40, 18, 92, INK),
            text_path("mono-regular", "ADRILABTECH · LOW NOISE", 12, 20, 126, MUTED, tracking=2.6),
            char,
            f'<path d="M980 138H1146" stroke="{INK}" stroke-opacity=".42"/>',
            "</svg>",
        ]
    )


PROJECTS = [
    ("RUST · TUI", "sysTUI", ["Monitor de sistema para el terminal:", "CPU, memoria, red, disco y procesos."], "sysTUI"),
    ("RUST · TUI", "FileTUI", ["Explorador de archivos para la terminal", "con vista previa de imágenes."], "FileTUI"),
    ("RUST · TUI", "TUI-OS", ["Un sistema operativo dentro de", "un terminal."], "TUI-OS_Arching"),
    ("COMPILADOR", "N-Sharp", ["Mi propio lenguaje de programación", "y su compilador."], "N-Sharp"),
    ("ANDROID", "ryoku-transit", ["App de autobuses AUCORSA", "para Córdoba."], "ryoku-transit"),
    ("RYOKU · PLUGIN", "claude-companion", ["Compañero pixel art de Claude Code", "para el escritorio Ryoku."], "claude-companion"),
]

BADGES = {
    "lang": [("RUST", "rust"), ("JAVA", "openjdk"), ("TYPESCRIPT", "typescript"), ("PYTHON", "python"), ("BASH", "gnubash"), ("SQL", "postgresql")],
    "frame": [("SPRING BOOT", "springboot"), ("ANGULAR", "angular")],
    "tools": [("ARCH LINUX", "archlinux"), ("LINUX", "linux"), ("GIT", "git"), ("GITHUB", "github"), ("DOCKER", "docker"), ("PODMAN", "podman"), ("OBSIDIAN", "obsidian")],
    "links": [("YOUTUBE · LOW NOISE", "youtube"), ("GITHUB · ADRILABTECH", "github")],
}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def write(name, content):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(content)


def main():
    os.makedirs(OUT, exist_ok=True)
    write("hero.svg", hero())
    write("section-about.svg", section("02", "ACERCA", "Acerca de mí", "源"))
    write("section-work.svg", section("03", "TRABAJO", "Qué desarrollo", "道"))
    write("section-projects.svg", section("04", "PROYECTOS", "Proyectos", "蔵"))
    write("section-stack.svg", section("05", "STACK", "Tecnologías", "具"))
    write("section-videos.svg", section("06", "CANAL", "Últimos vídeos", "見"))
    write("section-stats.svg", section("07", "ACTIVIDAD", "Estadísticas", "数"))
    write("footer.svg", footer())
    for group in BADGES.values():
        for label, ic in group:
            write(f"badge-{slug(label)}.svg", badge(label, ic))
    for tag, name, desc, _repo in PROJECTS:
        write(f"project-{slug(name)}.svg", project_card(tag, name, desc))
    print("ok:", len(os.listdir(OUT)), "ficheros en", OUT)


if __name__ == "__main__":
    main()
