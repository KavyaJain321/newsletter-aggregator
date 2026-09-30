"""Deterministic cleaning + link extraction (NO AI).

Turns a raw Gmail message into (clean_text, links[]). Prefers text/plain;
falls back to HTML->text. Strips boilerplate/tracking; never invents content.
"""
from __future__ import annotations
import base64
import re
from bs4 import BeautifulSoup

# lines that are pure plumbing/boilerplate/render-noise -> dropped
_BOILER = re.compile(
    r"unsubscribe|view (this|in) (email|browser|online)|update your preferences|"
    r"manage.*subscription|©|all rights reserved|sent to notifyy|you are reading a plain text|"
    r"copy and paste this link|refer\.|referral link|advertise (with|in)|"
    r"want to advertise|track your referrals|"
    r"^\s*view image\b|^\s*follow image link\b|^\s*caption:?\s*$|"      # beehiiv render noise
    r"^\s*!\[|media\.beehiiv\.com",
    re.I,
)
_DIVIDER = re.compile(r"^\s*[-=_*]{3,}\s*$")
# section markers that indicate an ad/sponsor block
AD_MARKERS = re.compile(
    r"\b(sponsor|from our partners|presented by|together with|in partnership with|"
    r"advertisement|save your seat|register for this|book a demo|grab your copy)\b",
    re.I,
)


def _walk(part: dict, acc: dict) -> None:
    mt = part.get("mimeType", "")
    if mt.startswith("multipart"):
        for p in part.get("parts", []):
            _walk(p, acc)
        return
    body = part.get("body", {}).get("data")
    if body and mt in ("text/plain", "text/html"):
        txt = base64.urlsafe_b64decode(body + "==").decode("utf-8", "replace")
        acc[mt] = acc.get(mt, "") + txt


def extract_bodies(payload: dict) -> tuple[str, str]:
    """Return (text_plain, text_html) concatenated across parts."""
    acc: dict[str, str] = {}
    _walk(payload, acc)
    return acc.get("text/plain", ""), acc.get("text/html", "")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    return soup.get_text("\n")


def _apply(raw: str) -> str:
    # TLDR-style: split off the "[n] url" footnote table and resolve [n] inline,
    # so per-story links survive rather than being lost or dumped on one card.
    main, _, footer = raw.partition("\nLinks:")
    footnotes = dict(re.findall(r"^\s*\[(\d+)\]\s+(https?://\S+)", footer, re.M))
    main = re.sub(r"\[(\d+)\]", lambda m: f" ({footnotes[m.group(1)]})"
                  if m.group(1) in footnotes else "", main)
    out = []
    for ln in main.splitlines():
        ln = ln.rstrip()
        if _BOILER.search(ln) or _DIVIDER.match(ln):
            continue
        out.append(ln)
    t = "\n".join(out)
    t = re.sub(r"https?://[^\s)\]]+utm_[^\s)\]]+", "[link]", t)   # kill tracking urls
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def clean_text(text_plain: str, text_html: str) -> str:
    """Prefer text/plain, but fall back to HTML when the plain part is a thin
    stub (some senders, e.g. FindLaw, ship real content only in HTML)."""
    plain = _apply(text_plain) if text_plain else ""
    if word_count(plain) >= 50:
        return plain
    html_txt = _apply(html_to_text(text_html)) if text_html else ""
    return html_txt if word_count(html_txt) > word_count(plain) else plain


def extract_links(text_plain: str, text_html: str) -> list[dict]:
    """Deterministic anchor->url pairs. HTML anchors first; else bare URLs."""
    links: list[dict] = []
    seen: set[str] = set()
    if text_html:
        for a in BeautifulSoup(text_html, "html.parser").find_all("a", href=True):
            url = a["href"].strip()
            if url.startswith("http") and "utm_" not in url and url not in seen:
                seen.add(url)
                links.append({"anchor": a.get_text(" ", strip=True)[:120], "url": url})
    if not links:
        for url in re.findall(r"https?://[^\s)\]>]+", text_plain):
            if "utm_" not in url and url not in seen:
                seen.add(url)
                links.append({"anchor": "", "url": url})
    return links


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))
