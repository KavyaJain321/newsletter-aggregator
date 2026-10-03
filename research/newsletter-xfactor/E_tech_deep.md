# Batch E — Deep tech

Researched 2026-10-03. Sources: Exa semantic search (Reddit/X/HN/blog highlights), the HN Algolia API (comments and story threads), Jina Reader for public pages, and read-only Gmail reads of real issues in `notifyy1008@gmail.com`. Reddit thread pages were blocked (403) for direct fetching, so the Reddit evidence comes from Exa highlights only. Per-newsletter notes on where evidence is thin are inline.

---

## 1. The Pragmatic Engineer (Gergely Orosz)

### Snapshot
- **Author:** Gergely Orosz, a former engineering manager at Uber, with earlier roles at Skype/Microsoft, Skyscanner and startups. He is based in Amsterdam.
- **Audience:** "Over 1,100,000 subscribers" according to the Substack subscribe page (Oct 2026). It passed 1M in April 2025, all through organic growth with no ads or paid acquisition, per Orosz's "One million" post. It claims to be the #1 technology newsletter on Substack, a position it has held since about 3 months after launch.
- **Founded:** The paid Substack launched in late 2021 (Orosz says "three and a half years" before April 2025). It was seeded with 9,000 subscribers from his earlier blog digest, and 1,000 people were paying within 6 weeks. The blog it grew out of dates from 2015.
- **Frequency:** About 3–4 emails a week.
  - Tue: paid deepdive.
  - Wed: free podcast episode.
  - Thu: paid "The Pulse".
  - Occasional free "bonus" issues.
- **Price:** $15/mo or $150/yr. Discounts exist for purchasing-power parity (PPP) and for students. Team plans start at 50 seats. He provides an "expense this to your L&D budget" email template and offers a 30-day no-questions refund.
- **Monetisation:** There are no ads in the paid deepdives or The Pulse; this is a deliberate choice so he isn't "incentivized to get more views". The free podcast emails do carry sponsor reads (our Sep 30 issue had three sponsors: turbopuffer, Linear and WorkOS).

### Why people like it (social proof)
- **Insider and peer view of Big Tech.** Readers value that he writes "from inside the arena as a peer, not just a commentator". He covers how Meta, Amazon, Google, Microsoft, Uber and others actually run engineering. An HN user said they read it alongside *Chaos Monkeys* for "an insider's" view and asked for more of the culture series.
- **Original reporting that beats mainstream outlets.** He reports on layoffs, hiring freezes and comp changes weeks ahead of Bloomberg or WSJ. On HN he is cited as a primary source; examples include the 80–85% of Linux contributions made by paid developers, the end of SDETs at Microsoft, the Builder.ai "did not fake" correction, Stack Overflow's decline and trimodal compensation. One HN commenter: "He validate[s] sources and has a good track record" (HN 44262332).
- **Career and compensation intel.** Recruiters and job-seekers say it pays for itself. Typical testimonials: the remote-comp insights "paid for about 200 years" of the subscription, and "the only Substack I pay for". The r/cscareerquestions consensus is that it is "the most consistently senior-focused newsletter out there", covering comp, system design at scale and staff+ career paths.
- **Practical, reusable artifacts.** EMs use the subscriber templates (docs and processes) when they are new to a role (HN 38804363).
- **Independence and no fluff.** Readers frame it as staunchly independent and impossible to buy or flatter.
- **Sentiment balance:** Strongly positive on X, LinkedIn and r/cscareerquestions. HN is mostly positive but has a vocal skeptic minority, and r/ExperiencedDevs is mixed (see Criticisms).

### Speciality / niche
Trade journalism for software engineers, written by a former senior EM. The beat is how engineering actually works inside named companies (stacks, org structures, incident handling, comp bands, migrations) and what the job market is doing right now. Mainstream tech press covers companies as businesses, and other engineering newsletters curate links. Pragmatic Engineer does named-company engineering deepdives with sourced interviews. Few journalists have the engineering depth to do this, and few engineers are willing to report and write every week.

### How the content comes (format anatomy)
This section is grounded in 3 real Gmail issues from Sep 29 – Oct 1, 2026.
- **Separate sender aliases per series.** Each series comes from its own address: `pragmaticengineer+deepdives@substack.com`, `pragmaticengineer+the-pulse@substack.com` and `pragmaticengineer@substack.com` (podcast). This is very useful for our classifier.
- **Deepdive (Tue, paid).**
  - Example subject: "Why has Shopify dropped React Native?"
  - It opens with a "Before we start:" promo; in this issue, a free ebook offer.
  - Next comes a 2–3 paragraph hook and an explicit **"We cover:" table of contents**, where each numbered section gets a one-sentence summary.
  - Then numbered sections (1., 2., 3. ...) mixing sourced quotes from company engineers, timelines, data lists, comparison tables and his first-person verdict ("Smart!", "My personal sense is...").
  - For free subscribers, the email **cuts off at section 4** (paywall). The free preview alone was about 3,000 words.
- **The Pulse (Thu, paid).** A news-and-trends column of about 4 topics. Free readers get a **"bonus, free issue"**: one of the four topics, delivered **7 days late**, and labelled as such.
  - The free Pulse we read (DHH's "death of coding by hand") was about 2,560 words.
  - Structure: news hook, long quotes, links back to his own earlier predictions ("In the first issue this year I wrote..."), and short bolded claim paragraphs.
  - It ends with a bulleted teaser of the other paid topics, each with a one-line summary.
- **Podcast (Wed, free).**
  - Example subject: "Distributed databases with Peter Mattis".
  - Contents: watch/listen links, a "Brought to You by" block of sponsors, an "In this episode" summary, then **"Takeaways from the conversation"** as 7+ numbered, bolded, fact-dense takeaways. It is about 1,900 words.
- **Tone:** Plain, functional and first-person. He bolds lead claims and uses functional diagrams and charts rather than decorative images.
- **Subject-line style:**
  - Plain declarative or question form for deepdives.
  - "The Pulse: <topic>" for the news column.
  - "<Topic> with <Guest>" for podcasts.
  - No emoji and no clickbait punctuation.

### X factor
He is a credible insider-reporter with named-company specifics. He verifies claims with the engineers involved and has the engineering literacy to explain why a decision was made. Readers treat his issues as primary sources, not commentary.

### Criticisms / what people dislike
- **Padding versus density.** An r/ExperiencedDevs commenter (2025) found it the opposite of information-dense. They said the best value is clicking through to the cited originals, and that the prose feels stretched to justify the paywall.
- **"Reporting on reporting."** An HN thread from 2022 accused some Scoop issues of leaning on The Information and on tweets, and cited one retracted rumour. Orosz replied in the thread, conceded that he hadn't marked his exclusives clearly, and defended the share of original reporting.
- **Headline/content mismatch and an info-product vibe.** Some HN readers find titles over-optimised. Others see the success as self-referential: selling career advice and ebooks to engineers.
- **Audience drift toward leadership.** A blogger (lmika.org, Aug 2026) found an issue grating for its "business speak" about equity and ROI, which was not relatable for a salaried IC. Separately, HN warns against managers "parroting" PE templates as their own.

### What our aggregator should steal
1. **Route by sender alias.** Map `+deepdives`, `+the-pulse` and the base address to content types (analysis / news / podcast) in `sources.csv`. Add the flags `is_bonus_free_repost` (The Pulse "bonus" issues are 7-day-old reposts, so we should not treat them as fresh news) and `paywall_truncated` (deepdives cut at about section 4).
2. **Extract the built-in TOC.** Deepdives include a "We cover:" list of numbered sections with one-line summaries. Parse it straight into the digest as the summary instead of LLM-summarising 3,000 words; it is cheaper and in the author's own words. Do the same for the podcast "Takeaways" numbered list.
3. **Track the claims he links back to.** He routinely links to his own earlier predictions. A "claim / prediction ledger" (who said what, when, and was it right) across newsletters would be a differentiated digest feature.

### Sources
- https://www.reddit.com/r/ExperiencedDevs/comments/1mhelel/your_favorite_blogsnewsletters/
- https://www.reddit.com/r/cscareerquestions/comments/19bg7af/content_creatorsnewsletters_to_follow_as_an/
- https://news.ycombinator.com/item?id=32285375 (2022 critique thread, with the author's replies)
- https://news.ycombinator.com/item?id=38804363 (templates; "parroting" caution)
- https://news.ycombinator.com/item?id=44262332 (trust in sourcing)
- https://news.ycombinator.com/item?id=40526900 (insider culture series)
- https://newsletter.pragmaticengineer.com/about
- https://newsletter.pragmaticengineer.com/p/one-million
- https://www.pragmaticengineer.com/ (aggregated X testimonials)
- https://www.linkedin.com/pulse/pragmatic-engineer-newsletter-high-earning-audience-andy-griffiths (growth-source breakdown; formatting notes)
- https://lmika.org/2026/08/20/the-pragmatic-engineer-newsletter-had.html
- Gmail (read-only): msg 1a0edf09b32dbec3 (deepdive), 1a0f86751a8bcbab (free Pulse), 1a0f331e20987de0 (podcast)

---

## 2. Import AI (Jack Clark)

### Snapshot
- **Author:** Jack Clark. He co-founded Anthropic and was previously Policy Director at OpenAI. Before that he was Bloomberg's "neural network reporter" and a distributed-systems reporter at The Register. He also co-founded the Stanford AI Index.
- **Audience:** "Over 142,000 subscribers" according to the Substack subscribe page (Oct 2026), up from about 34,000 in April 2023 (Business Insider). Readers include policymakers, politicians and executives (BI). The newsletter is cross-posted to jack-clark.net (WordPress) and importai.net.
- **Founded:** About 2016. In 2026 he describes it as being "in its tenth year", and it is now at issue #474.
- **Frequency:** Weekly, on Mondays (about 12:30 UTC in our inbox).
- **Free vs paid:** Entirely free; there is no paid tier. The "please subscribe" line is the only call to action. Clark calls it his "main hobby outside of work".
- **Sender:** `importai@substack.com`, display name "Jack Clark from Import AI".

### Why people like it (social proof)
- **It reads the papers so you don't have to.** It is a long-standing pick in r/MachineLearning "best newsletters" threads, and HN users list it as a go-to AI source from 2017 onward (HN 30989169, 18492824). One 2018 reviewer called it "invaluable for staying on top of AI capability development" (Rosie Campbell, Medium/DataDrivenInvestor).
- **The "Why this matters" analysis.** Readers value that every item ends with a short take on implications, not just a summary. LinkedIn recommenders highlight its blend of technical depth and digestibility.
- **Tech Tales.** Every issue ends with a short original science-fiction story. Readers repeatedly single this out as delightful and moving; Substack comments on #458 call the story "moving and thought provoking". Interviewers such as Odd Lots ask about it, and it is the newsletter's most distinctive feature.
- **Insider credibility and candour.** Readers like hearing from someone "so close to the core" of AI development, including his explicit caveats (for example, "I don't work at OpenAI and don't have privileged information...").
- **Agenda-setting.** Its essays travel well beyond the newsletter. Import AI 455 (automated AI R&D odds) drew 561 points and 128 comments on r/singularity, and "Technological Optimism and Appropriate Fear" (#431) circulated widely.
- **Breadth of primary sources.** It pulls in arXiv papers, Chinese labs (Zhipu, Huawei), robotics, policy polling and space compute, much of which never reaches mainstream AI news.
- **Sentiment balance:** Very positive among AI/ML practitioners and policy people. Broader Reddit audiences (r/singularity, r/ChatGPT) engage heavily, but with a skeptical strand aimed at Clark-as-Anthropic-exec rather than at the newsletter's quality.

### Speciality / niche
Import AI is research-paper-first frontier AI analysis written by a lab co-founder, with a safety and policy lens and a fiction coda. Clark deliberately refuses to make it "super accessible and digestible", because he writes it to learn himself (BI, 2023). He calls himself an "AI Wikipedia" for policymakers. Other AI newsletters are product- or news-led; Import AI tracks capability trends paper by paper and asks "what does this imply for the trajectory?"

### How the content comes (format anatomy)
This section is grounded in a real Gmail issue: Import AI 474, Sep 28, 2026, about 3,440 words.
- **Subject:** "Import AI 474: Platonic mindspace; TPUs in space; Zhipu starts an outer RSI loop". The fixed pattern is `Import AI <N>: <item>; <item>; and <item>`, a numbered semicolon list of 3 headline items.
- **Preheader/subtitle:** A wry question or one-liner, such as "Where do you exceed the capabilities of an LLM?" or "Is the wall AI is hitting in the room with us right now?"
- **Fixed opener:** A boilerplate welcome line about the newsletter running on "arXiv, cappuccinos, and feedback from readers".
- **Item anatomy (6–7 per issue, separated by `***`):**
  1. A **headline** in sentence case (sometimes ALL-CAPS for fun, e.g. "SPACE COMPUTERS! I REPEAT: SPACE COMPUTERS!").
  2. An **ellipsis subhead** (`…Google prepares to put TPUs in space…`).
  3. Bolded inline labels such as "What they did:", "Results:" and "Some bizarre experiments:", followed by heavy direct quotes from the paper.
  4. **"Why this matters - <thesis>:"**, a 1–2 paragraph opinionated take.
  5. **"Read more: <title> (<source>)."** links.
- **Closer:** **Tech Tales**, a titled story with a bracketed in-world frame (e.g. "[Record from a captured site ... 2034]"), ending with **"Things that inspired this story:"** and a semicolon list. Then "Thanks for reading!"
- **Occasional special formats:** A whole issue may be a single essay or speech (e.g. #431, #458). There are also "DOUBLE FEATURE" items.
- **Tone:** Earnest, curious and openly emotional ("Worrying stuff", "Make yourself a bucket of coffee and spend a few hours with this paper"). The voice is first-person and includes self-caveats.
- **Free vs paid:** Everything is free and complete in the email; there is no truncation.

### X factor
It combines rigor with imagination. Every item follows the same paper, quotes and "Why this matters" structure, written by someone building frontier AI, and then the issue ends with fiction that makes the implications feel real. No other AI newsletter pairs primary-source research digestion with a weekly sci-fi story.

### Criticisms / what people dislike
- **Conflict-of-interest and "doomer marketing" suspicion.** Reddit and commentary threads argue that frontier-lab executives emphasising AI risk serves fundraising and regulatory moats (remio.ai summary of Reddit discourse, 2025). By extension, people question how neutral Import AI is when it covers competitors such as OpenAI. Clark adds caveats, but the perception persists.
- **Hype or alarm fatigue.** On r/singularity some commenters dismiss his timelines (the r/singularity thread on "parallel world" drew replies saying Clark himself "already is in a parallel world").
- **Density and length.** It runs to about 3,400 words of quote-heavy paper summaries with no TL;DR. Clark admits it is deliberately not built for accessibility. *Evidence for direct reader complaints here is thin; this is inferred from his own statements and the format.*
- **The fiction isn't for everyone.** *Thin evidence.* No substantial negative threads were found, but some readers skip Tech Tales as off-topic.

### What our aggregator should steal
1. **Parse the item grammar.** Split on `***` and extract each item's headline, ellipsis subhead, "Why this matters" paragraph and "Read more" links. That gives us author-written takes and primary-source URLs (arXiv and lab blogs) for free, which beats LLM summarisation. Store "Why this matters" as the item's `author_take` field.
2. **Store "Why this matters" separately from the summary.** Do this for all newsletters (the "what happened" vs "so what" split), and show the so-what first in the digest. Import AI proves readers value the take more than the recap.
3. **Make "creative/fiction" a content type.** Tag the Tech Tales section and exclude it from news dedup and clustering, but surface it as an optional "weekend read". Also treat the semicolon subject line as a ready-made 3-topic index for the issue.

### Sources
- https://www.reddit.com/r/MachineLearning/comments/8xbd84/d_what_are_the_best_newsletters_about_machine/
- https://www.reddit.com/r/singularity/comments/1t3russ/anthropic_cofounder_jack_clark_says_ai_is_nearing/
- https://www.reddit.com/r/singularity/comments/1puvhqn/anthropic_cofounder_warns_by_summer_2026_frontier/
- https://www.reddit.com/r/ChatGPT/comments/1ptj5iy/great_paragraph_from_the_jack_clark_at_import_ai/
- https://news.ycombinator.com/item?id=30989169, https://news.ycombinator.com/item?id=18492824, https://news.ycombinator.com/item?id=48018212, https://news.ycombinator.com/item?id=40565409
- https://www.businessinsider.com/anthropic-cofounder-artificial-intelligence-newsletter-import-ai-2023-4
- https://medium.datadriveninvestor.com/my-favorite-ai-newsletters-run-by-people-working-in-the-field-26fbdb9e803e
- https://importai.substack.com/about
- https://importai.substack.com/p/import-ai-458-reckoning-with-the (and /comments)
- https://jack-clark.net/2025/10/13/import-ai-431-technological-optimism-and-appropriate-fear/
- https://thetranscriptdesk.substack.com/p/anthropics-co-founder-and-top-economist (Odd Lots transcript)
- https://www.remio.ai/post/jack-clark-s-ai-fear-why-anthropic-sees-existential-risk (summary of skeptic discourse)
- Gmail (read-only): msg 1a0e805ac0ac34c4 (Import AI 474)

---

## 3. Exponential View (Azeem Azhar)

### Snapshot
- **Author:** Azeem Azhar, an entrepreneur, investor, author of *The Exponential Age* (2021) and member of WEF councils. He now runs it with a team: Marija Gavrilov is Managing Director, and researchers include Nathan Warren, Hannah Petrovic and William Gildea.
- **Audience:** "Over 165,000 subscribers" according to the Substack subscribe page. Azhar's site claims 286,000 newsletter subscribers once LinkedIn distribution is included. He passed 100K on Substack in May 2024 and also cited about 200K LinkedIn newsletter recipients, for "around 300,000 mailboxes".
- **Paid count:** Unclear. Third-party estimates range from "1K+" (Sidestack) to about 7.1K (NewsletterInsights).
- **Founded:** 2015; first email in about June 2015. It moved from Revue to Ghost and then to Substack in 2022.
- **Frequency:** Several emails a week.
  - Sun (sent Sat/Sun early UTC): numbered **"Sunday briefing"** (#603 on Sep 27, 2026).
  - Mon: **"Monday data"**.
  - Midweek: 1–3 essays or analyses.
  - Separately: the podcast/YouTube show, plus a new spin-off, **AI Investment Brief** (launched Sep 2026).
- **Price:** $19/mo or $120/yr (NewsletterInsights, Jan 2026). It was historically $12/mo. Annual members get perks: a Slack community, events, partner tools (Granola, Perplexity Pro promos) and data models. EV says about 80% of annual members renew (2023 promo post). It also offers an L&D expense template.

### Why people like it (social proof)
- **Cross-disciplinary synthesis.** It connects AI, energy and solar, economics, geopolitics and biotech into one frame. HN users describe it as wide-ranging "exponential thinking" across economics, climate and AI (HN 22281221); podcast fans on Reddit call it "very high complexity standards" across capitalism, biology and computing.
- **The curated Sunday ritual.** It is a long-standing weekend read. A LinkedIn reader in 2018: "One email that I'm actually happy to see in my inbox every Sunday." Fred Wilson (AVC, 2016) singled out the **"Short morsels to appear smart at dinner parties"** section.
- **Charts and data.** One paid reader blog said the best parts are the weekly chart collection and the Sunday curated research list (A Learning a Day, 2023). The "Monday data" and chart-led analyses continue that.
- **A balanced optimism.** Readers appreciate that it faces hard realities, such as the climate crisis, while still "dealing in hope". Azhar positions himself against both techno-pessimism and utopianism (WEF).
- **Contrarian, early calls.** EV markets itself on taking positions early: the AI-bubble framework, solar's exponential growth and "energy becomes technology". The solar piece got real HN traction ("Why everyone missed solar's exponential growth", 46 points, 41 comments).
- **Longevity and trust.** Some subscribers have stayed since 2015 and call it "one of my few trusted sources" (LinkedIn comments).
- **Sentiment balance:** Positive but lower-volume. There is far less organic Reddit/HN chatter than for the other two, and much of the praise is on LinkedIn or in EV's own testimonial pages. **Evidence is thin on independent user opinion.**

### Speciality / niche
It is a macro, economics-of-technology lens aimed at decision-makers (investors, executives, policymakers) rather than practitioners. EV asks what AI and energy do to the economy over the next 3–5 years, quantifies it with its own research (e.g. "The State of the AI Economy", a bottom-up demand-side analysis), and wraps it in a framework vocabulary ("exponential gap", "Is AI a bubble?" framework). Pragmatic Engineer serves engineers and Import AI serves the research and safety crowd; EV serves the boardroom.

### How the content comes (format anatomy)
**Our inbox only has onboarding emails so far:** a "🔮 Welcome to Exponential View" email (Sep 30) and an upsell, "👀 Is AI a bubble – or the start of a new economy?" (Oct 3). Both are HTML-only, with an empty plain-text body; note this for the parser. No regular Sunday issue has arrived yet, so the anatomy below comes from the public web: EV #603, Sep 27, 2026, via Jina, plus older editions found by Exa.
- **Sunday briefing (#NNN).**
  - Opens with "Happy Sunday!", then housekeeping and promos (launches, podcast appearances).
  - Next is **"Three reads from this week, in case you missed them"**: a recap of the week's own essays, each with a bolded title and a one-line hook.
  - Then the **lead commentary**: a 400–800-word opinionated take on the week's biggest idea (e.g. DeepMind's "collective AI" essay).
  - **The paywall cuts in after the lead** for free readers.
  - Historically, the paid body continued with curated sections: key reads by theme, data points and charts, **"Short morsels to appear smart at dinner parties"** (emoji-bulleted one-liners), and an end note.
- **Monday data:** A chart- and number-led short analysis, sometimes co-written with researchers.
- **Midweek essays:** These are single-thesis pieces such as "Safety in numbness" or "Your agent, whose interests?". Sometimes a paid post is "unlocked by" a sponsor (e.g. Granola).
- **Subject-line style:** An **emoji prefix encodes the series**.
  - 🔮 Sunday or essay.
  - 📈 Monday data.
  - 🚨 breaking take ("🚨 The first existential IPO").
  - 👀 or 🙌 promo.
  - Sunday subjects list themes separated by semicolons and end with "++ #NNN" (e.g. "🔮 Kimi K3 surprise & AI economics; the solar paradox; ...++").
- **Tone:** First-person, confident and position-taking ("I take positions... way ahead of consensus"). It reads like a polished analyst briefing, with team bylines.
- **Free vs paid:** Free readers get the intro, the recap and the lead take. Members get the full curation layer, the "what to do with it" analysis, a 10-year archive, the community and perks. Sender: `exponentialview@substack.com`, display name "Azeem Azhar, Exponential View".

### X factor
It frames technology as macroeconomics, connecting AI, energy and capital flows into a few memorable frameworks (exponential gap, bubble test, solar supercycle). That gives non-engineer decision-makers a coherent worldview each week, not just news. The Sunday ritual and the "dinner-party morsels" give it a personality no AI-news digest has.

### Criticisms / what people dislike
- **Over-optimism.** MIT Technology Review's review of Azhar's book called its "age of abundance" thesis "uber-optimism" that takes a leap of faith. Azhar himself concedes he is more pessimistic about governance.
- **Aggregation and repackaging.** On HN, EV's "OpenAI's unit economics" post (65 comments) drew a reply pointing to the original Epoch AI analysis and asking for the link to be swapped. A commenter on the solar piece called it overlong and "just a PR piece".
- **Heavy commercial layer.** This comes from our own observation, not from user complaints. Within 3 days of subscribing we received a welcome-plus-upsell and a separate upsell email. There are also sponsor-unlocked posts, partner-perk promos, spin-off product launches at the top of the Sunday issue, and a price that is high for the category ($19/mo against a $6 category median, per NewsletterInsights).
- **Mostly paywalled.** Free readers now get mainly the lead take. The curated-links Sunday that made its reputation sits behind the paywall. *Thin evidence of reader complaints specifically about this.*

### What our aggregator should steal
1. **Use the emoji prefix as a free classifier.** Map 🔮/📈/🚨/👀 to briefing, data, breaking and promo, and **auto-skip promo and onboarding emails** such as "Welcome" and the upsell sends. The parser also needs an **HTML-to-text fallback**, because EV emails have an empty `text/plain` body.
2. **Build our own "Short morsels" section.** A closing block of 5–8 emoji-tagged one-line surprising facts pulled from all newsletters that day. It is cheap to generate from extracted data points and gives the digest personality and shareability.
3. **Recap the week's links in the Sunday digest.** A "Three reads from this week, in case you missed them" block at the top of our weekly digest, picking the most-engaged or most-cross-cited items. Also detect "In case you missed it" recap sections in source newsletters and dedup them against the originals, so the same essay isn't counted twice.

### Sources
- https://www.reddit.com/r/podcasts/comments/iiwrg6/is_there_any_other_podcast_like_exponential_view/
- https://www.reddit.com/r/Futurology/comments/byj258/exponential_view_with_azeem_azhar_the_autonomous/
- https://news.ycombinator.com/item?id=22281221, https://news.ycombinator.com/item?id=14088139, https://news.ycombinator.com/item?id=11046165
- https://news.ycombinator.com/item?id=46807201 ("OpenAI's unit economics" thread; link-to-original request)
- https://news.ycombinator.com/item?id=42200149 ("Why everyone missed solar's exponential growth")
- https://avc.com/2016/02/the-exponential-view/ (Fred Wilson)
- https://alearningaday.blog/2023/07/24/6-things-and-hope-from-the-exponential-view/
- https://www.linkedin.com/posts/azhar_exponential-view-azeem-azhar-substack-activity-6441947516505325568-Xu83
- https://www.linkedin.com/posts/azhar_on-saturday-about-9-years-after-sending-activity-7196171626525216770-TZ-n
- https://www.technologyreview.com/2021/10/27/1037169/book-review-azeem-azhar/
- https://www.exponentialview.co/about, https://www.exponentialview.co/subscribe, https://www.exponentialview.co/archive
- https://www.exponentialview.co/p/ev-603, https://www.exponentialview.co/p/ev-496f, https://www.exponentialview.co/p/gain-clarity-amidst-the-noise-33
- https://newsletterinsights.io/newsletter/exponentialview/investor-report, https://sidestack.io/directory/substack/exponentialview
- https://www.azeemazhar.com/about
- Gmail (read-only): msg 1a0f127cf6ad45a8 (welcome), 1a1009add8351a04 (upsell). Both are onboarding emails, not regular issues.

---

## Cross-cutting notes for the aggregator
- **All three use Substack, but their bodies differ.** Pragmatic Engineer and Import AI ship a usable `text/plain` body. EV's plain-text body is empty, so we need the HTML fallback.
- **Free-tier truncation varies by publication:**
  - Import AI: full, with no paywall.
  - Pragmatic Engineer: deepdives cut at about section 4; Pulse topics reposted free 7 days late.
  - Exponential View: cut after the lead take.
  
  Our archive should record a `completeness` field so the digest doesn't present partial issues as complete.
- **Separate the author's take from the news.** All three readerships say the value is the author's judgement (Gergely's verdicts, Clark's "Why this matters", Azhar's positions), not the news itself. Our Phase 5 enrichment should extract the "so what" separately from the "what".
