#!/usr/bin/env python3
"""Export every <figure> SVG of docs/nova-schematic.html as a standalone SVG and a PNG.

Usage:  python3 scripts/export_figures.py [--html docs/nova-schematic.html] [--out docs/figures]
                                          [--scale 2] [--no-png] [--chrome PATH]

The page's CSS tokens (currentColor, var(--beam), ...) are resolved to the light-theme
colours and a <style> block is embedded, so the SVGs render outside the page.  PNGs are
rasterised with headless Chrome at --scale times the SVG's viewBox size.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LIGHT = {
    "var(--fg)": "#1d2126", "var(--muted)": "#5d6670", "var(--panel)": "#ffffff",
    "var(--beam)": "#0b6e8f", "var(--far)": "#8a3b2f", "var(--soil)": "#c9b79c",
    "var(--soil-fill)": "rgba(201,183,156,0.22)", "var(--bg)": "#ffffff",
}
STYLE = """
  svg { font-family: "IBM Plex Sans", "Helvetica Neue", Helvetica, Arial, sans-serif; }
  text { font-size: 12px; fill: #1d2126; }
  .small { font-size: 11px; fill: #5d6670; }
  .mono { font-family: "IBM Plex Mono", Menlo, Consolas, monospace; font-size: 11.5px; }
  .beam { stroke: #0b6e8f; }
  .beamtext { fill: #0b6e8f; font-weight: 600; }
  .fartext { fill: #8a3b2f; }
  .far { stroke: #8a3b2f; }
"""
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium", "chromium-browser", "chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def slug(title: str) -> str:
    s = re.sub(r"\(.*?\)", "", title)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s


def find_chrome(explicit: str | None) -> str | None:
    for c in ([explicit] if explicit else []) + CHROME_CANDIDATES:
        if c and (os.path.isfile(c) or shutil.which(c)):
            return c
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--html", default="docs/nova-schematic.html")
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--scale", type=float, default=2.0, help="PNG pixels per SVG unit (default 2)")
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--chrome", default=None, help="Chrome/Chromium executable for the PNGs")
    a = ap.parse_args()
    text = Path(a.html).read_text(encoding="utf-8")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    blocks = re.findall(r"<h2>(.*?)</h2>\s*<figure>\s*(<svg.*?</svg>)", text, flags=re.S)
    if not blocks:
        print("no figures found in", a.html, file=sys.stderr)
        return 1
    chrome = None if a.no_png else find_chrome(a.chrome)
    if not a.no_png and not chrome:
        print("Chrome not found; writing SVGs only (use --chrome PATH)", file=sys.stderr)
    written = []
    for i, (title, svg) in enumerate(blocks, 1):
        title = html.unescape(re.sub(r"<[^>]+>", "", title))
        m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
        w, h = (int(m.group(1)), int(m.group(2))) if m else (900, 400)
        s = svg
        for k, v in LIGHT.items():
            s = s.replace(k, v)
        s = s.replace("currentColor", "#1d2126")
        s = s.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" ' % (w, h), 1)
        s = re.sub(r"(<svg[^>]*>)", r'\1\n<style>%s</style>\n<rect width="100%%" height="100%%" fill="#ffffff"/>' % STYLE, s, count=1)
        name = "%02d-%s" % (i, slug(title))
        svg_path = out / (name + ".svg")
        svg_path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + s + "\n", encoding="utf-8")
        written.append(svg_path)
        if chrome:
            png_path = out / (name + ".png")
            cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                   "--force-device-scale-factor=%g" % a.scale, "--window-size=%d,%d" % (w, h),
                   "--screenshot=%s" % png_path.resolve(), svg_path.resolve().as_uri()]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            written.append(png_path)
    for p in written:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
