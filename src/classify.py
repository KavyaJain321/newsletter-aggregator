"""Deterministic is-this-a-real-issue classifier.

Drops notifications / confirmations / unsubscribe notices / marketing blasts
so they don't get treated as newsletter issues. Conservative by design:
when in doubt, keep it (better a stray promo than a dropped real issue).
"""
from __future__ import annotations
import re

_WORD = re.compile(r"\w+")
_PROMO = re.compile(r"billed as|cancel anytime|% off|\bsale\b|subscribe (today|now)|"
                    r"limited[- ]time offer|/four weeks|upgrade to (premium|pro)", re.I)


def classify(subject: str, sender_name: str, text: str) -> tuple[bool, str]:
    """Return (is_issue, reason)."""
    subj = (subject or "").lower()
    head = (text or "")[:600].lower()
    both = subj + "\n" + head
    wc = len(_WORD.findall(text or ""))
    name = (sender_name or "").strip().lower()

    # 1. platform social notifications (Substack "someone followed you", etc.)
    if name == "substack" or "follow back to see" in head or "is now on substack" in head:
        return False, "social-notification"
    # 2. unsubscribe / removal notices
    if re.search(r"you have been removed|you'?ve been (unsubscribed|removed)|due to inactivity", both):
        return False, "removed"
    # 3. confirm / verify / welcome (transactional, short)
    if re.search(r"\bconfirm\b|verify your email|complete your sign|activate your|"
                 r"your confirmation code|welcome", subj) and wc < 400:
        return False, "confirm/welcome"
    if re.search(r"thank you for subscribing|thanks for subscribing|subscription confirmed", head):
        return False, "welcome"
    # 4. marketing / subscription promo — short + multiple strong signals
    if wc < 260 and len(_PROMO.findall(both)) >= 2:
        return False, "promo"
    # 5. near-empty
    if wc < 25:
        return False, "empty"
    return True, "issue"
