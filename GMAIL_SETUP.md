# Gmail Setup — Auto-sort newsletters into 9 folders

**Base account:** `notifyy1008@gmail.com` (the only real account — you make nothing else)

The 9 `+tag` addresses below all deliver into this one inbox. These filters read the
`+tag` and drop each newsletter into its own label (Gmail's word for a folder).

Do this ONCE, before or after signing up — either order works. Takes ~10 minutes total.

---

## Part A — Create the parent label (optional but tidy)

1. Gmail → left sidebar → scroll down → **+ Create new label**
2. Name it `Newsletters` → **Create**

All 9 topic labels below will nest under it.

---

## Part B — Create 9 filters (one per segment)

**IMPORTANT:** Use the **"Has the words"** field with `deliveredto:` — NOT the "To" field.
Gmail's "To" field is unreliable for `+tag` (plus-addressed) mail and often fails to match.
`deliveredto:` matches the exact delivery address every time.

For EACH row in the table below, do this:

1. In the Gmail search bar, click the **filter/sliders icon** (right side of the box).
2. In the **"Has the words"** field, paste the `deliveredto:` line (e.g. `deliveredto:notifyy1008+techai@gmail.com`). Leave "To" blank.
3. Click **Create filter**.
4. Tick **"Apply the label"** → choose the label (e.g. `Newsletters/1-TechAI`).
5. Tick **"Also apply filter to matching conversations"** to sort anything already arrived.
6. (Optional, do LATER) Tick **"Skip the Inbox (Archive it)"** so newsletters bypass the inbox — but only after confirmations are done (see note below).
7. Click **Create filter**.

Repeat 9 times:

| # | Filter "Has the words" | Label to apply |
|---|---|---|
| 1 | `deliveredto:notifyy1008+techai@gmail.com`   | `Newsletters/1-TechAI` |
| 2 | `deliveredto:notifyy1008+biz@gmail.com`      | `Newsletters/2-BizFinance` |
| 3 | `deliveredto:notifyy1008+legal@gmail.com`    | `Newsletters/3-Legal` |
| 4 | `deliveredto:notifyy1008+hr@gmail.com`       | `Newsletters/4-HR` |
| 5 | `deliveredto:notifyy1008+github@gmail.com`   | `Newsletters/5-GitHub` |
| 6 | `deliveredto:notifyy1008+indie@gmail.com`    | `Newsletters/6-IndieHacker` |
| 7 | `deliveredto:notifyy1008+satire@gmail.com`   | `Newsletters/7-Absurdist` |
| 8 | `deliveredto:notifyy1008+smallcap@gmail.com` | `Newsletters/8-SmallCap` |
| 9 | `deliveredto:notifyy1008+news@gmail.com`     | `Newsletters/9-News` |

---

## Tip: don't hide confirmation emails from yourself

If you tick "Skip the Inbox", the **confirm-your-subscription** emails also get archived into
the folder instead of the inbox. That's fine — just remember to open each of the 9 labels after
signing up and click any "Confirm" / "Verify" links waiting there.

Two easy options:
- **Simplest:** set up the filters AFTER you've signed up and confirmed everything.
- **Or:** set up filters now but DON'T tick "Skip the Inbox" until confirmations are done.

---

## How to verify it's working

Send yourself a test: from any other email, send a message to `notifyy1008+techai@gmail.com`.
It should land in your inbox tagged `Newsletters/1-TechAI` within a few seconds. If it does,
all 9 are good (they're identical setups).
