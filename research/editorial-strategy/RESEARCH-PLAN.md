# Deep Research — Per-Topic Editorial Strategy for the Aggregated Newsletter

**Scoped question:** For each of our 9 newsletter segments, what is the most *engaging* and *highest-retention* way to present aggregated content (format + structure + voice + representation), validated by proven real-world examples — including formats proven in *other* media, but only where they genuinely transfer to text/email?

**Decision it serves:** Choosing the default Step-3 (generation) content treatment(s) per segment, grounded in evidence rather than taste.

## Assumptions ledger (from Phase-0 interview, 2026-09-10)
1. Cover all 9 segments; deepest on Tech/AI, Mainstream News, Business/Finance. ✅
2. Reader persona tuned per topic (devs for GitHub, investors for small-cap, etc.). ✅
3. Evidence bar: named newsletters/creators + hard numbers where findable (open rate, CTR, growth, churn, A/B) + attention research; flag anecdote. ✅
4. Cross-medium proof allowed, BUT assess medium-transfer explicitly — a format loved on video/social is only recommended if it works in TEXT. ✅ (user emphasis)
5. Output: per-segment playbook file + tight chat summary. ✅
- Tooling: WebSearch + fetch + parallel research agents. Exa/Tavily/Firecrawl/academic MCPs NOT connected (noted in report).

## Sub-questions
- SQ1 Engagement levers (opens/CTR): subject, sender, preview, length, cadence, personalization — proven.
- SQ2 Retention/habit: why people stay vs churn; consistency, utility, identity, the "one job".
- SQ3 Content formats in email generally (roundup / essay / brief-sectioned / Q&A / debate / data / conversational) — tradeoffs + proof.
- SQ4 Cross-medium transfer: which video/social/podcast formats survive as text; which flop. (adversarial on transfer)
- SQ5 Winner teardown: why the biggest per vertical won (Morning Brew, Axios/Smart Brevity, Stratechery, TLDR, Ground News, Semafor, The Hustle, Matt Levine, Milk Road…).
- SQ6–14 Per segment: best representation + persona + proven examples + what to avoid.
- SQ-ADV (adversarial): strongest case that novel/"clever" formats (debate, sarcasm, gamified) HURT engagement/retention vs a plain reliable roundup (novelty fatigue, cognitive load, trust).

## Hypothesis tree (to test, not confirm)
- H1 Consistency + skimmability + utility beats novelty for *retention* (plain roundup wins long-term).
- H2 A signature distinctive format/voice drives *differentiation + word-of-mouth growth* (Brew voice, Smart Brevity, Stratechery depth).
- H3 Format must match the topic's job-to-be-done (news=orient, finance=decide, dev=use, satire=entertain).
- H4 Cross-medium formats transfer only when they *reduce effort or add clarity*, not when they add friction.

## Method
Orchestrator–worker fan-out: 3 cross-cutting agents (engagement science, retention science, winner teardown) + 9 segment agents (each applies medium-transfer judgment) + 1 red-team agent. Each returns structured, cited findings. Main session synthesizes into FINDINGS.md + the playbook, grading evidence and surfacing contradictions.
