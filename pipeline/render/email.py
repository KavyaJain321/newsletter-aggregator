"""Step 10: render an Issue (compose/schema.py) as a send-ready email.

    html = render_html(issue)            # email-safe HTML: tables + inline styles, <102 KB
    text = render_text(issue)            # plain-text alternative part
    page = render_html(issue, preview=True)   # same email inside a review page (inbox row on top)

Email-client rules followed (Gmail, Apple Mail, Outlook desktop/web, iOS/Android apps):
  - layout is nested role="presentation" tables, 640px wide, every style inline; the only
    <style> is a mobile media query that stacks columns (clients that drop it still work)
  - no CSS grid/flex/variables/color-mix; web fonts are optional (system fallbacks set)
  - hidden preheader; MSO conditionals pin the width in Outlook
  - ESP placeholders ({{unsubscribe_url}} etc., see MERGE_TAGS) are filled at send time
Design: design/README.md (approved Oct 2 samples). Accent colour per edition.
"""
from __future__ import annotations

import html as _html
import re

from ..compose.schema import (Callout, Compact, Hits, Issue, Ledger, Markets, Morsels, Prose, Side,
                              Story)

MERGE_TAGS = {
    "{{web_url}}": "this issue on the web",
    "{{unsubscribe_url}}": "one-click unsubscribe (also sent as List-Unsubscribe header)",
    "{{preferences_url}}": "switch edition / frequency",
    "{{subscribe_url}}": "sign-up page (for forwarded copies)",
    "{{feedback_url}}": "issue rating endpoint (?r=loved|fine|no)",
    "{{postal_address}}": "sender's physical address (CAN-SPAM)",
}
MAX_BYTES = 102_000  # Gmail clips larger messages

INK, INK2, MUTED, FAINT = "#15181F", "#2B313B", "#5D6675", "#98A0AC"
RULE, PAPER, PANEL, CARD = "#E3E6EB", "#E6E9EE", "#F4F5F7", "#FFFFFF"
HL, UP, DOWN, AMBER, OFF = "#FFE45C", "#0E8A5F", "#C8372D", "#A86A12", "#E1E4E9"
ACCENTS = {"tech": ("#D4471F", "#A8360F", "#FBEEE8"), "finance": ("#0A6B4C", "#08573E", "#E4F1EB")}
SANS = "'Schibsted Grotesk','Helvetica Neue',Helvetica,Arial,sans-serif"
SERIF = "'Source Serif 4',Georgia,'Times New Roman',serif"
MONO = "'IBM Plex Mono',Menlo,Consolas,'Courier New',monospace"
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Schibsted+Grotesk:"
         "wght@600;700;900&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap")
T = 'role="presentation" cellpadding="0" cellspacing="0" border="0"'


def esc(text: str) -> str:
    """Escape, then allow **bold** as the only inline markup."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", _html.escape(text, quote=False))


def plain(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


class _R:
    def __init__(self, issue: Issue):
        self.i = issue
        self.acc, self.acc_ink, self.tint = ACCENTS[issue.edition]
        self.order = [r.id for r in issue.roster]

    # ---------------------------------------------------------------- atoms
    def mono(self, text: str, color: str = MUTED, size: int = 11, weight: int = 400, extra: str = "") -> str:
        return (f'<span style="font-family:{MONO};font-size:{size}px;font-weight:{weight};letter-spacing:.08em;'
                f'text-transform:uppercase;color:{color};{extra}">{text}</span>')

    def strip(self, coverage: list[str]) -> str:
        on = set(coverage)
        cells = "".join(
            f'<td style="width:9px;height:9px;background:{self.acc if b in on else OFF};font-size:0;'
            f'line-height:0;border-radius:2px">&nbsp;</td><td style="width:3px;font-size:0">&nbsp;</td>'
            for b in self.order)
        return f'<table {T} style="display:inline-table;vertical-align:middle"><tr>{cells}</tr></table>'

    def cov(self, coverage: list[str]) -> str:
        return (f'<span style="font-family:{MONO};font-size:11px;color:{INK2};white-space:nowrap">'
                f'<b>{len(coverage)} of {len(self.order)}</b><span class="hide-m"> newsletters</span></span>')

    def badge(self, kind: str) -> str:
        label, color = {"reported": ("Reported", AMBER), "differ": ("Sources differ", DOWN),
                        "self": ("Self-reported", MUTED), "paywalled": ("Paywalled", INK2)}[kind]
        return (f'<span style="display:inline-block;font-family:{MONO};font-size:10px;font-weight:600;'
                f'letter-spacing:.06em;text-transform:uppercase;color:{color};border:1px solid {color};'
                f'border-radius:2px;padding:1px 5px;margin-left:6px;white-space:nowrap">{label}</span>')

    def p(self, text: str, size: int = 17, color: str = INK2, margin: str = "0 0 14px") -> str:
        return (f'<p style="margin:{margin};font-family:{SERIF};font-size:{size}px;line-height:1.6;'
                f'color:{color}">{esc(text)}</p>')

    def label(self, text: str) -> str:
        return (f'<table {T} width="100%" style="margin:36px 0 14px"><tr>'
                f'<td style="white-space:nowrap;padding-right:10px">{self.mono(esc(text), self.acc_ink, 11, 600)}</td>'
                f'<td width="100%" style="border-bottom:1px solid {RULE};font-size:0;line-height:0">&nbsp;</td>'
                f'</tr></table>')

    def srcline(self, names: list[tuple[str, str | None]], prefix: str = "From") -> str:
        parts = []
        for name, url in names:
            n = esc(name)
            parts.append(f'<a href="{url}" style="color:{INK2};text-decoration:none;border-bottom:1px solid {RULE}">'
                         f'{n}</a>' if url else n)
        return (f'<p style="margin:12px 0 0;font-family:{SANS};font-size:13px;line-height:1.5;color:{MUTED}">'
                f'{self.mono(prefix, FAINT, 10, 600)}&nbsp; {" &middot; ".join(parts)}</p>')

    def link(self, text: str, url: str) -> str:
        return (f'<a href="{_html.escape(url)}" style="color:{self.acc_ink};text-decoration:underline">'
                f'{esc(text)}</a>')

    def divider(self) -> str:
        return f'<div style="height:1px;background:{RULE};margin:34px 0 0;font-size:0;line-height:0">&nbsp;</div>'

    # ---------------------------------------------------------------- header
    def header(self) -> str:
        i = self.i
        roster = " ".join(
            f'<span style="display:inline-block;margin:0 12px 6px 0;font-family:{SANS};font-size:12px;'
            f'color:{INK2};white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;'
            f'background:{self.acc};border-radius:2px;margin-right:5px"></span>{esc(r.label)}</span>'
            for r in i.roster)
        meta = " &nbsp;&middot;&nbsp; ".join([
            f"<b style=\"color:{INK}\">{len(i.roster)}</b> newsletters",
            f"<b style=\"color:{INK}\">{i.issues_read}</b> issues &rarr; <b style=\"color:{INK}\">1</b>",
            f"<b style=\"color:{INK}\">{i.read_minutes}-min</b> read",
            f"{i.ads_removed} ads removed"])
        today = "".join(
            f'<tr><td valign="top" style="width:26px;padding:10px 0;border-bottom:1px solid {RULE};font-family:{MONO};'
            f'font-size:12px;font-weight:600;color:{self.acc}">{n}</td><td style="padding:9px 0;border-bottom:1px solid '
            f'{RULE};font-family:{SANS};font-size:16px;font-weight:600;line-height:1.35;color:{INK}">{esc(t)}</td></tr>'
            for n, t in enumerate(i.today, 1))
        nd = i.number_of_day
        return f'''
<table {T} width="100%"><tr>
  <td>{self.mono(f"{esc(i.date_label)} &middot; No. {esc(i.issue_no)}", MUTED, 10)}</td>
  <td align="right"><a href="{{{{web_url}}}}" style="text-decoration:none">{self.mono("View in browser", MUTED, 10)}</a></td>
</tr></table>
<h1 class="mast" style="margin:22px 0 0;font-family:{SANS};font-weight:900;font-size:54px;line-height:.95;letter-spacing:-2px;color:{INK}">Twenty <em style="font-family:{SERIF};font-style:italic;font-weight:400;font-size:42px;letter-spacing:0;color:{self.acc}">to</em> One <span style="display:inline-block;vertical-align:middle;margin-left:6px;font-family:{MONO};font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#FFFFFF;background:{self.acc};padding:4px 8px 3px;border-radius:2px">{esc(i.edition_label)}</span></h1>
<p style="margin:10px 0 0;font-family:{SERIF};font-style:italic;font-size:18px;color:{INK2}">{esc(i.tagline)}</p>
<p style="margin:12px 0 0;font-family:{MONO};font-size:11.5px;line-height:1.7;color:{MUTED}">{meta}</p>
<table {T} width="100%" style="margin-top:20px;background:{PANEL};border-radius:6px"><tr><td style="padding:14px 16px 8px">
  <p style="margin:0 0 10px">{self.mono("Read for this issue", MUTED, 10)}<span style="font-family:{SANS};font-size:12px;color:{FAINT}"> &nbsp;&middot; each story shows which of these covered it</span></p>
  {roster}
</td></tr></table>
<table {T} width="100%" style="margin-top:26px;border-top:1px solid {RULE};border-bottom:1px solid {RULE}"><tr>
  <td class="stack" valign="middle" style="padding:18px 20px 18px 0;white-space:nowrap"><span class="notd-num" style="font-family:{SANS};font-weight:900;font-size:56px;line-height:1;letter-spacing:-2px;color:{self.acc}">{esc(nd.value)}</span></td>
  <td class="stack" valign="middle" style="padding:18px 0">
    <p style="margin:0 0 5px">{self.mono("Number of the day", MUTED, 10)}</p>
    {self.p(nd.text, 16, INK2, "0")}
    <p style="margin:5px 0 0;font-family:{SANS};font-size:12.5px;color:{MUTED}">{esc(nd.via)}</p>
  </td>
</tr></table>
<table {T} width="100%" style="margin-top:20px">{today}</table>'''

    # ---------------------------------------------------------------- blocks
    def ledger(self, lg: Ledger) -> str:
        colors = {"ok": UP, "claimed": AMBER, "unclear": MUTED}
        rows = "".join(
            f'<tr><td valign="top" style="width:92px;padding:9px 12px 9px 14px;border-top:1px solid {RULE};'
            f'font-family:{MONO};font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;'
            f'color:{colors[r.status]}">{esc(r.label)}</td><td style="padding:8px 14px 9px 0;border-top:1px solid {RULE};'
            f'font-family:{SANS};font-size:14.5px;line-height:1.5;color:{INK2}">{esc(r.text)}</td></tr>'
            for r in lg.rows)
        return (f'<table {T} width="100%" style="margin:18px 0;background:{PANEL};border-radius:6px">'
                f'<tr><td colspan="2" style="padding:11px 14px 9px">{self.mono(esc(lg.title), INK, 10.5, 600)}</td></tr>'
                f'{rows}</table>')

    def split(self, sides: list[Side]) -> str:
        w = 100 // len(sides)
        cols = []
        for n, s in enumerate(sides):
            last = n == len(sides) - 1
            items = "".join(
                f'<p style="margin:0 0 10px;font-family:{SANS};font-size:14px;line-height:1.5;color:{INK2}">'
                f'{esc(it.text)} <span style="font-family:{MONO};font-size:10.5px;color:{MUTED};white-space:nowrap">'
                f'&mdash; {esc(it.cite)}</span></p>' for it in s.items)
            bg = self.tint if not last else PANEL
            cols.append(
                f'<td class="stack" valign="top" width="{w}%" style="padding:0 {0 if last else 8}px 0 0">'
                f'<table {T} width="100%" style="background:{bg};border-radius:6px"><tr><td style="padding:14px 14px 6px">'
                f'<p style="margin:0 0 2px">{self.mono(esc(s.kicker), self.acc_ink if not last else MUTED, 10, 600)}</p>'
                f'<p style="margin:0 0 10px;font-family:{SANS};font-size:17px;font-weight:700;line-height:1.25;'
                f'color:{INK}">{esc(s.title)}</p>{items}</td></tr></table></td>')
        return f'<table {T} width="100%" style="margin:18px 0"><tr>{"".join(cols)}</tr></table>'

    def story(self, s: Story) -> str:
        solid = s.tag_style == "solid"
        tag = (f'<span style="display:inline-block;font-family:{MONO};font-size:10.5px;font-weight:600;'
               f'letter-spacing:.09em;text-transform:uppercase;padding:3px 7px 2px;border-radius:2px;white-space:nowrap;'
               f'color:{"#FFFFFF" if solid else self.acc_ink};background:{self.acc if solid else self.tint}">'
               f'{esc(s.tag)}</span>')
        eyebrow = (f'<table {T} style="margin:30px 0 12px"><tr><td style="padding-right:12px">{tag}</td>'
                   f'<td style="padding-right:7px">{self.strip(s.coverage)}</td><td style="padding-right:12px">'
                   f'{self.cov(s.coverage)}</td><td class="hide-m">{self.mono(esc(s.read_time), FAINT, 10.5)}</td></tr></table>')
        size = 30 if s.size == "lead" else 24
        out = [eyebrow,
               f'<h2 style="margin:0 0 12px;font-family:{SANS};font-weight:800;font-size:{size}px;line-height:1.15;'
               f'letter-spacing:-.5px;color:{INK}">{esc(s.headline)}{"".join(self.badge(b) for b in s.badges)}</h2>']
        if s.sowhat:
            out.append(f'<p style="margin:0 0 16px;font-family:{SANS};font-size:16.5px;font-weight:600;line-height:1.5;'
                       f'color:{INK}">{self.mono("So what", self.acc_ink, 10, 600)}&nbsp; <span style="background:{HL};'
                       f'padding:1px 2px">{esc(s.sowhat)}</span></p>')
        out += [self.p(t) for t in s.paragraphs]
        if s.ledger:
            out.append(self.ledger(s.ledger))
        if s.split:
            out.append(self.split(s.split))
        out += [self.p(t) for t in s.after]
        if s.note:
            out.append(self.p(s.note, 14, MUTED))
        if s.read_original:
            links = " &middot; ".join(self.link(l.text, str(l.url)) for l in s.read_original)
            out.append(f'<p style="margin:4px 0 0;font-family:{SANS};font-size:14px;color:{INK2}">'
                       f'Read the original: {links}</p>')
        out.append(self.srcline([(x.name, str(x.url) if x.url else None) for x in s.sources]))
        return "".join(out)

    def hits(self, h: Hits) -> str:
        rows = []
        for it in h.items:
            extra = f' &middot; {self.link(it.link.text, str(it.link.url))}' if it.link else ""
            rows.append(
                f'<tr><td style="padding:16px 0;border-bottom:1px solid {RULE}">'
                f'<table {T}><tr><td style="padding-right:7px">{self.strip(it.coverage)}</td><td>{self.cov(it.coverage)}'
                f'{"".join(self.badge(b) for b in it.badges)}</td></tr></table>'
                f'<h3 style="margin:8px 0 6px;font-family:{SANS};font-size:18px;font-weight:700;line-height:1.3;'
                f'color:{INK}">{esc(it.headline)}</h3>{self.p(it.text, 16, INK2, "0")}'
                f'<p style="margin:6px 0 0;font-family:{MONO};font-size:11px;color:{MUTED}">'
                f'{esc(" · ".join(it.sources))} &middot; {esc(it.read_time)}{extra}</p></td></tr>')
        return self.label(h.label) + f'<table {T} width="100%">{"".join(rows)}</table>'

    def markets(self, m: Markets) -> str:
        arrow = {"up": ("&#9650;", UP), "down": ("&#9660;", DOWN), "flat": ("&#9670;", MUTED)}
        rows = "".join(
            f'<tr><td style="padding:8px 0;border-bottom:1px solid {RULE};font-family:{SANS};font-size:15px;color:{INK}">'
            f'{esc(r.name)}</td><td align="right" style="padding:8px 14px;border-bottom:1px solid {RULE};font-family:{MONO};'
            f'font-size:14px;color:{INK}">{esc(r.value)}</td><td align="right" style="padding:8px 0;border-bottom:1px solid '
            f'{RULE};font-family:{MONO};font-size:14px;font-weight:600;color:{arrow[r.direction][1]};white-space:nowrap">'
            f'{arrow[r.direction][0]} {esc(r.change)}</td></tr>' for r in m.rows)
        out = [self.label(m.label), self.mono(esc(m.asof), MUTED, 10),
               f'<table {T} width="100%" style="margin-top:6px">{rows}</table>']
        if m.movers:
            mv = "".join(
                f'<tr><td valign="top" style="width:70px;padding:9px 10px 9px 0;border-bottom:1px solid {RULE};'
                f'font-family:{MONO};font-size:13px;font-weight:600;color:{INK}">{esc(x.ticker)}</td>'
                f'<td valign="top" style="width:70px;padding:9px 10px 9px 0;border-bottom:1px solid {RULE};font-family:{MONO};'
                f'font-size:13px;font-weight:600;color:{UP if x.direction == "up" else DOWN};white-space:nowrap">'
                f'{esc(x.change)}</td><td style="padding:8px 0;border-bottom:1px solid {RULE};font-family:{SANS};'
                f'font-size:14.5px;line-height:1.45;color:{INK2}">{esc(x.why)}</td></tr>' for x in m.movers)
            out.append(f'<p style="margin:20px 0 4px">{self.mono("Movers", MUTED, 10, 600)}</p>'
                       f'<table {T} width="100%">{mv}</table>')
        if m.note:
            out.append(self.p(m.note, 14, MUTED, "12px 0 0"))
        out.append(f'<p style="margin:8px 0 0;font-family:{MONO};font-size:11px;color:{MUTED}">'
                   f'{esc(" · ".join(m.sources))}</p>')
        return "".join(out)

    def compact(self, c: Compact) -> str:
        rows = []
        for e in c.items:
            link = f' {self.link(e.link.text, str(e.link.url))}' if e.link else ""
            src = (f'<br><span style="font-family:{MONO};font-size:11px;color:{MUTED}">{esc(e.source)}</span>'
                   if e.source else "")
            rows.append(
                f'<tr><td class="stack" valign="top" style="width:110px;padding:12px 14px 12px 0;border-bottom:1px solid '
                f'{RULE}">{self.mono(esc(e.key), self.acc_ink, 10, 600)}</td><td class="stack" style="padding:11px 0;'
                f'border-bottom:1px solid {RULE};font-family:{SANS};font-size:15px;line-height:1.5;color:{INK2}">'
                f'<b style="color:{INK}">{esc(e.title)}</b>{"".join(self.badge(b) for b in e.badges)}'
                f'{(" " + esc(e.text)) if e.text else ""}{link}{src}</td></tr>')
        return self.label(c.label) + f'<table {T} width="100%">{"".join(rows)}</table>'

    def callout(self, c: Callout) -> str:
        body = "".join(self.p(t, 16, INK2, "0 0 10px") for t in c.paragraphs)
        prompt = (f'<p style="margin:4px 0 12px;padding:12px 14px;background:{CARD};border:1px solid {RULE};'
                  f'border-radius:4px;font-family:{MONO};font-size:13px;line-height:1.6;color:{INK}">{esc(c.prompt)}</p>'
                  if c.prompt else "")
        src = (f'<p style="margin:0;font-family:{MONO};font-size:11px;color:{MUTED}">{esc(c.source)}'
               + (f' &middot; {self.link(c.link.text, str(c.link.url))}' if c.link else "") + '</p>'
               if c.source or c.link else "")
        return (self.label(c.label) +
                f'<table {T} width="100%" style="background:{self.tint};border-left:4px solid {self.acc};'
                f'border-radius:4px"><tr><td style="padding:16px 18px 14px">'
                f'<h3 style="margin:0 0 8px;font-family:{SANS};font-size:19px;font-weight:700;line-height:1.3;'
                f'color:{INK}">{esc(c.title)}</h3>{body}{prompt}{src}</td></tr></table>')

    def prose(self, x: Prose) -> str:
        out = [self.label(x.label)] + [self.p(t, 16.5) for t in x.paragraphs]
        if x.sources:
            out.append(self.srcline([(s.name, str(s.url) if s.url else None) for s in x.sources]))
        return "".join(out)

    def morsels(self, m: Morsels) -> str:
        rows = "".join(
            f'<tr><td valign="top" style="width:18px;padding:8px 0;font-family:{SANS};font-size:16px;color:{self.acc}">'
            f'&#9632;</td><td style="padding:7px 0;font-family:{SERIF};font-size:16px;line-height:1.55;color:{INK2}">'
            f'{esc(x.text)} <span style="font-family:{MONO};font-size:10.5px;color:{MUTED}">{esc(x.source)}</span>'
            f'</td></tr>' for x in m.items)
        return self.label(m.label) + f'<table {T} width="100%">{rows}</table>'

    def block(self, b) -> str:
        return {Story: self.story, Hits: self.hits, Markets: self.markets, Compact: self.compact,
                Callout: self.callout, Prose: self.prose, Morsels: self.morsels}[type(b)](b)

    # ---------------------------------------------------------------- footer
    def footer(self) -> str:
        i = self.i
        btn = (lambda t, r, pri: f'<a href="{{{{feedback_url}}}}?r={r}" style="display:inline-block;margin:0 6px 6px 0;'
               f'padding:9px 16px;border-radius:3px;font-family:{SANS};font-size:14px;font-weight:600;text-decoration:none;'
               f'{"background:" + INK + ";color:#FFFFFF" if pri else "border:1px solid " + RULE + ";color:" + INK}">{t}</a>')
        srcs = " &middot; ".join(
            f'<a href="{r.url}" style="color:{INK2};text-decoration:none;border-bottom:1px solid {RULE}">{esc(r.label)}</a>'
            if r.url else esc(r.label) for r in i.roster)
        return f'''
<table {T} width="100%" style="margin-top:40px;border-top:1px solid {RULE}"><tr><td align="center" style="padding:22px 0 6px">
  <p style="margin:0 0 12px;font-family:{SANS};font-size:16px;font-weight:700;color:{INK}">How was today's issue?</p>
  {btn("Loved it", "loved", True)}{btn("It was fine", "fine", False)}{btn("Not for me", "no", False)}
</td></tr></table>
<table {T} width="100%" style="margin-top:22px;background:{PANEL};border-radius:6px"><tr><td style="padding:16px 18px">
  <p style="margin:0 0 6px">{self.mono("How this issue was made", INK, 10.5, 600)}</p>
  {self.p(i.made, 14.5, INK2, "0 0 8px")}
  <p style="margin:0;font-family:{SANS};font-size:13px;line-height:1.7;color:{MUTED}">{srcs}</p>
</td></tr></table>'''

    def closing(self) -> str:
        return f'''
<tr><td class="px" style="padding:24px 44px 26px;background:{INK}">
  <p style="margin:0 0 10px;font-family:{SANS};font-weight:900;font-size:24px;letter-spacing:-.5px;color:#FFFFFF">Twenty <em style="font-family:{SERIF};font-weight:400;color:{self.acc}">to</em> One</p>
  <p style="margin:0 0 6px;font-family:{SANS};font-size:13px;line-height:1.6;color:#C9CED6">Forward this to one person who'd want it. Got this from a friend? <a href="{{{{subscribe_url}}}}" style="color:#FFFFFF">Get your own copy</a>.</p>
  <p style="margin:0 0 10px;font-family:{SANS};font-size:13px;line-height:1.6;color:#C9CED6"><a href="{{{{preferences_url}}}}" style="color:#FFFFFF">Change edition or frequency</a> &middot; <a href="{{{{unsubscribe_url}}}}" style="color:#FFFFFF">Unsubscribe</a></p>
  <p style="margin:0;font-family:{MONO};font-size:10.5px;line-height:1.6;color:{FAINT}">{esc(self.i.window_note)}<br>{{{{postal_address}}}}</p>
</td></tr>'''

    def inbox_preview(self) -> str:
        i = self.i
        return f'''
<tr><td style="padding:0 0 14px">
  <p style="margin:0 0 6px 4px">{self.mono("How it lands in your inbox", MUTED, 10)}</p>
  <table {T} width="100%" style="background:{CARD};border-radius:8px"><tr>
    <td style="padding:12px 0 12px 16px;width:120px;font-family:{SANS};font-size:13.5px;font-weight:800;color:{INK};white-space:nowrap">Twenty to One</td>
    <td style="padding:12px 10px;font-family:{SANS};font-size:13.5px;color:{INK}"><b>{esc(i.subject)}</b> <span style="color:{MUTED}">&mdash; {esc(i.preheader)}</span></td>
    <td align="right" style="padding:12px 16px 12px 0;font-family:{MONO};font-size:11px;color:{MUTED};white-space:nowrap">{esc(i.send_time)}</td>
  </tr></table>
</td></tr>'''


def render_html(issue: Issue, preview: bool = False) -> str:
    r = _R(issue)
    body = r.header() + "".join(r.block(b) for b in issue.blocks) + r.footer()
    pad = "&zwnj;&nbsp;" * 90
    return f'''<!doctype html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{esc(issue.subject)}</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
<link href="{FONTS}" rel="stylesheet">
<style>
body{{margin:0;padding:0;-webkit-text-size-adjust:100%}} table{{border-collapse:collapse}} a{{color:inherit}}
@media (max-width:620px){{
 .wrap{{width:100%!important}} .px{{padding-left:20px!important;padding-right:20px!important}}
 .stack{{display:block!important;width:100%!important;padding-right:0!important;box-sizing:border-box}}
 .mast{{font-size:42px!important}} .notd-num{{font-size:44px!important}} .hide-m{{display:none!important}}
}}
</style>
</head>
<body style="margin:0;padding:0;background:{PAPER}">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;font-size:1px;line-height:1px;color:{PAPER}">{esc(issue.preheader)}{pad}</div>
<table {T} width="100%" style="background:{PAPER}"><tr><td align="center" style="padding:24px 10px">
<!--[if mso]><table {T} width="640"><tr><td><![endif]-->
<table {T} class="wrap" width="640" style="width:640px;max-width:640px">
{r.inbox_preview() if preview else ""}
<tr><td style="height:5px;background:{r.acc};font-size:0;line-height:0">&nbsp;</td></tr>
<tr><td class="px" style="padding:30px 44px 36px;background:{CARD}">{body}</td></tr>
{r.closing()}
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table>
</body>
</html>
'''


def render_text(issue: Issue) -> str:
    """The plain-text alternative part (multipart/alternative)."""
    n = len(issue.roster)
    out = [f"TWENTY TO ONE · {issue.edition_label.upper()}", f"{issue.date_label} · No. {issue.issue_no}",
           issue.tagline, f"{n} newsletters · {issue.issues_read} issues -> 1 · {issue.read_minutes}-min read",
           "", f"NUMBER OF THE DAY: {issue.number_of_day.value}", plain(issue.number_of_day.text),
           f"({issue.number_of_day.via})", "", "TODAY"]
    out += [f"{k}. {plain(t)}" for k, t in enumerate(issue.today, 1)]
    for b in issue.blocks:
        out.append("")
        if isinstance(b, Story):
            out += [f"== {b.tag.upper()} · covered by {len(b.coverage)} of {n} · {b.read_time}", plain(b.headline)]
            if b.sowhat:
                out.append(f"SO WHAT: {plain(b.sowhat)}")
            out += [plain(t) for t in b.paragraphs]
            if b.ledger:
                out += [f"  {r.label}: {plain(r.text)}" for r in b.ledger.rows]
            for s in b.split:
                out.append(f"  {s.kicker} - {s.title}")
                out += [f"   * {plain(it.text)} ({it.cite})" for it in s.items]
            out += [plain(t) for t in b.after]
            out += [f"Read: {l.text} {l.url}" for l in b.read_original]
            out.append("From: " + ", ".join(s.name for s in b.sources))
        elif isinstance(b, Hits):
            out.append(f"== {b.label.upper()}")
            for h in b.items:
                out += [f"* {plain(h.headline)} ({len(h.coverage)} of {n})", f"  {plain(h.text)}",
                        f"  {' · '.join(h.sources)}" + (f" {h.link.url}" if h.link else "")]
        elif isinstance(b, Markets):
            out += [f"== {b.label.upper()} ({b.asof})"] + [f"  {r.name}: {r.value} {r.change}" for r in b.rows]
            out += [f"  {m.ticker} {m.change}: {plain(m.why)}" for m in b.movers]
        elif isinstance(b, Compact):
            out.append(f"== {b.label.upper()}")
            out += [f"* {e.key}: {plain(e.title)} {plain(e.text)}".rstrip() + (f" {e.link.url}" if e.link else "")
                    for e in b.items]
        elif isinstance(b, Callout):
            out += [f"== {b.label.upper()}: {plain(b.title)}"] + [plain(t) for t in b.paragraphs]
            if b.prompt:
                out.append(f'  "{plain(b.prompt)}"')
            if b.link:
                out.append(f"  Read: {b.link.text} {b.link.url}")
        elif isinstance(b, Prose):
            out += [f"== {b.label.upper()}"] + [plain(t) for t in b.paragraphs]
        elif isinstance(b, Morsels):
            out += [f"== {b.label.upper()}"] + [f"* {plain(m.text)} ({m.source})" for m in b.items]
    out += ["", "HOW THIS ISSUE WAS MADE", plain(issue.made), "",
            "Unsubscribe: {{unsubscribe_url}} · Preferences: {{preferences_url}}", "{{postal_address}}"]
    return "\n".join(out) + "\n"


def check_size(html: str) -> int:
    size = len(html.encode("utf-8"))
    if size > MAX_BYTES:
        raise ValueError(f"email is {size:,} bytes; Gmail clips above {MAX_BYTES:,}")
    return size
