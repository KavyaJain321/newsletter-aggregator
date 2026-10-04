# Export a built issue (*.html) to a single continuous-page PDF.
#   python design/export.py design/samples/tech_2026-10-02.html
# Needs: Edge or Chrome installed, Pillow (pip install pillow).
# Method: screenshot at email width to measure content height, then print with @page sized to fit.
import pathlib, shutil, subprocess, sys
from PIL import Image

WIDTH = 760
CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium", "msedge",
]

def browser():
    for c in CANDIDATES:
        if pathlib.Path(c).exists() or shutil.which(c):
            return c
    sys.exit("No Edge/Chrome found")

def run(exe, *args):
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--virtual-time-budget=8000", *args],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

def content_height(png):
    im = Image.open(png).convert("RGB"); w, h = im.size; px = im.load(); bg = px[5, h - 5]
    for y in range(h - 1, 0, -1):
        if any(px[x, y] != bg for x in range(60, w - 60, 5)):
            return y + 36
    return h

def export(html_path):
    exe = browser()
    src = pathlib.Path(html_path).resolve()
    shot = src.with_suffix(".measure.png")
    run(exe, f"--window-size={WIDTH},12000", f"--screenshot={shot}", src.as_uri())
    h = content_height(shot)
    page = src.with_suffix(".print.html")
    page.write_text(src.read_text(encoding="utf-8").replace(
        "</head>", f"<style>@page{{size:{WIDTH}px {h}px;margin:0}}</style></head>", 1), encoding="utf-8")
    pdf = src.with_suffix(".pdf")
    run(exe, "--no-pdf-header-footer", f"--print-to-pdf={pdf}", page.as_uri())
    shot.unlink(missing_ok=True); page.unlink(missing_ok=True)
    print(f"{pdf.name}: {WIDTH}x{h}px, single page")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        export(p)
