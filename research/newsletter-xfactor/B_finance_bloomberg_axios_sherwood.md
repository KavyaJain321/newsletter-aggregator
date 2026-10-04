# Batch B — Bloomberg, Axios & Sherwood

Research date: 2026-10-03. Methods: Exa semantic search (Reddit, HN, X/Bluesky, blogs, trade press), WebSearch, Jina Reader for full pages, and **read-only Gmail reads of real issues** in `notifyy1008@gmail.com` (5 of the 6 newsletters; Pro Rata isn't in our inbox). Word counts and link counts come from parsing the actual email bodies, so treat them as approximate (they include footer boilerplate).

Evidence quality at a glance:

| Newsletter | Real-user opinion evidence | Real issue read? |
|---|---|---|
| Money Stuff | **Strong** (many Reddit/HN threads, AMAs, profiles) | Yes (Oct 1 2026) |
| Businessweek Daily | **Thin** (almost no organic discussion; mostly editor statements) | Yes (Oct 1 + Oct 2 2026) |
| Axios Markets | **Thin for this title.** There is plenty of criticism of the Axios house style, but almost nothing specific to Markets | Yes (Oct 1 + Oct 2 2026) |
| Axios Pro Rata | Moderate (Reddit recommendation lists, trade press, practitioner blogs) | No. Read a public web edition (Aug 25 2026) |
| Snacks | Moderate (Reddit, 2019–2022 and polarized; LinkedIn) | Yes (Sep 30 + Oct 2 2026) |
| EntryPoint | **Very thin** (launched May 2026; one Bluesky endorsement, self-promo) | Yes (Sep 30 + Oct 2 2026, plus welcome email) |

---

### Money Stuff (Matt Levine, Bloomberg Opinion)

- **Snapshot:** Written solo by Matt Levine, a Bloomberg Opinion columnist. He was previously a Goldman Sachs equity-derivatives banker, a Wachtell M&A lawyer, a Dealbreaker editor and a high-school Latin teacher. The newsletter launched in **February 2015** as an email version of his column. Audience: ~150k in 2020 (NYT), "over 300,000" in Jan 2024 (Ritholtz podcast intro; Wikipedia), and "500,000 readers" in 2025 (Harvard Magazine). Frequency: weekdays, roughly 4–5 per week, with programming-note breaks. Arrives **in the afternoon**: our copies landed ~17:45–18:00 UTC, about 1:45–2pm ET. **Free by email.** The same pieces sit behind Bloomberg's web paywall, and the email carries one tiny sponsor slot. There is also a weekly **Money Stuff podcast**, which sends its own email ("Money Stuff: The Podcast: …").
- **Why people like it (social proof):**
  - People who don't work in finance say it is how they *learned* finance. Several HN commenters describe starting out confused, looking terms up, and gradually understanding everything. It is many readers' first recommendation for "how do I understand Wall Street" (HN 24727887; r/IAmA AMA; r/CFA).
  - It is funny without telling jokes. Readers call it "hilarious and brilliant" (r/CFA) and single out set-piece riffs, such as the SBF/FTX spreadsheet issue (r/BetterOffline 2026). Harvard Magazine says the whole text reads humorously even though it contains no specific jokes.
  - It sits outside the outrage cycle. Readers like that it avoids politics and anger. Levine explicitly keeps "sad political things" out (AMA). HN user on 27511156: "It's not connected to any outrage cycle."
  - Insiders respect it. Trading-firm interns are told to "go read Matt Levine" (r/slatestarcodex). Levine aims to "ring true to the specialists" while reframing things for them (Harvard Mag).
  - The consistency feels uncanny. One HN commenter half-jokes that it reads like a "well-calibrated financial article AI engine", given how much it covers and how steadily it ships (HN 45522117).
  - Readers feel personal loyalty. Some subscribed to Bloomberg mainly for him, and he writes back to reader emails (HN 24727887).
  - Sentiment is overwhelmingly positive, roughly 90/10. The negatives are about length, focus and moral tone, not about quality.
- **Speciality / niche:** He explains the economic intuition and incentives behind finance news (M&A, securities law, market structure, crypto, private credit), not the facts themselves. He only writes about something if he has an angle, and leaves straight coverage to Bloomberg News (Conversations with Tyler). Long-running conceptual frames recur and readers learn them like a language: "everything is securities fraud", legal realism, and right now "private markets are the new public markets."
- **How the content comes (format anatomy) — grounded in the Oct 1 2026 Gmail issue ("Money Stuff: Opening Private Markets to the Public"):**
  - **Subject:** `Money Stuff: <wry headline>`. **Preheader:** a deadpan list of keywords for the sections, e.g. "Fees, tests, votes, Knicks." (Other issue: "Man City, cotton, Waldron.")
  - **Length:** about **4,800 words (~20 min)**, 79 links, **8 numbered footnotes** [1]…[n]. Dan Stone's data analysis found issues getting longer and arriving ~47 minutes later each year since 2015.
  - **Sections, in order:** (1) the lead essay, split into two titled parts of a running series ("Private markets are the new public markets: Performance fees" / "…: Certificate of Smart Investment"); (2) a shorter section ("Shareholder voting"); (3) a light closing section ("Knicks and Rangers") that quotes a news story and then deflates it with a one-line wry take; (4) **"Things happen"**, about 15 headline links run together as one paragraph with no commentary; (5) a subscribe nudge; (6) **footnotes** collected at the end, holding asides, caveats and math; (7) Bloomberg upsell plus "Want to sponsor this newsletter?"
  - **Voice:** first person, conversational, built from long block quotes of source documents, followed by "I mean, sure…" style commentary, hypothetical dialogues, invented terms and "this is not investment advice" disclaimers. There are no images, no charts and essentially no ads.
- **X factor:** One expert voice who turns finance absurdity into readable stories every day, with a running set of frameworks readers learn over time. You read it for *how Matt sees it*, not for the news.
- **Criticisms / what people dislike:**
  - It is very long (~20 min) and has been growing. Some readers skim to the sections they care about.
  - Some find it unfocused. An HN thread calls it "incoherent… rambling musings" because it jumps across five unrelated topics (HN 14525261).
  - Its moral tone bothers some readers: it can present schemes as clever games rather than harms (HN 24727887).
  - It arrives in the afternoon and keeps getting later, so it is no use as a morning briefing. Bloomberg's web paywall also frustrates non-subscribers who click through (r/slatestarcodex).
- **What our aggregator should steal:**
  1. **Split by section and keep footnotes attached.** Parse the H-level sections into separate digest items, and carry each `[n]` footnote with the section that cites it. Show footnotes inline or expandable rather than dumping them at the end.
  2. **Treat the "Things happen" link-dump as its own entity type** (a list of curated headlines), separate from the essays. Merge those links into a de-duplicated "links the experts flagged today" panel across all newsletters.
  3. **Use the preheader keyword line as tags, and track running series.** Detect recurring section titles (e.g. "Private markets are the new public markets: …") and link each new installment to earlier ones, showing an "≈20-min read" length badge. Phase 5 enrichment could produce a "Levine's frames" glossary.
- **Sources:**
  - https://news.ycombinator.com/item?id=27511156
  - https://news.ycombinator.com/item?id=24727887
  - https://news.ycombinator.com/item?id=13669914
  - https://news.ycombinator.com/item?id=45522117
  - https://news.ycombinator.com/item?id=14525261
  - https://www.reddit.com/r/IAmA/comments/a72gc8/im_matt_levine_money_stuff_columnist_at_bloomberg/
  - https://www.reddit.com/r/CFA/comments/153l0jl/recommendations_for_finance_newsletters_or_data/
  - https://www.reddit.com/r/slatestarcodex/comments/hze13t/who_are_the_matt_levines_of_other_fields/
  - https://www.reddit.com/r/BetterOffline/comments/1venk8l/matt_levine_cooks/
  - https://www.reddit.com/r/UXDesign/comments/1j2s7nz/citi_keeps_hitting_the_wrong_buttons_matt_levines/
  - https://conversationswithtyler.com/episodes/matt-levine/
  - https://www.harvardmagazine.com/2025/07/harvard-bloomberg-column-matt-levine
  - https://www.nytimes.com/2020/10/08/business/matt-levine-bloomberg.html
  - https://ritholtz.com/2024/01/transcript-matt-levine/
  - https://danielstone.substack.com/p/money-stuff-is-linear-ish
  - https://www.morningbrew.com/stories/2021/12/17/icebreakers-with-bloomberg-columnist-matt-levine
  - Gmail: msg `1a0f89e670024007` (Oct 1 2026), `1a0f36cdd426619c` (Sep 30, list view only)

---

### Bloomberg Businessweek Daily

- **Snapshot:** From the Bloomberg Businessweek team (editor **Brad Stone** since 2024; the magazine went monthly in 2024). It became a **daily in December 2022** after previously being weekly. Bloomberg reported the audience up 26% since that switch and up 7% in H1 2024, but gives **no absolute number** (Nieman Lab / Bloomberg Media PR). Free and outside the paywall. It is a top-of-funnel product for Bloomberg.com subscriptions ($299/yr). Arrives in the early afternoon: our copies came ~17:00–17:45 UTC, about 1–1:45pm ET. Not to be confused with the *Bloomberg Businessweek Daily* radio show/podcast with Carol Massar & Tim Stenovec, which is a separate product.
- **Why people like it (social proof): EVIDENCE IS THIN.** We found no organic Reddit/HN/X threads specifically about this newsletter. What exists:
  - Stone says he wants it to be "the most interesting newsletter that Bloomberg has": each issue is led by a regular contributing writer, and it can switch from tech to politics to economics day to day (Nieman Lab 2024).
  - It is designed as "a satisfying sample… but never the whole meal". Nieman's interviewer noted it is meaty enough that you don't need to click every link.
  - Reader goodwill toward the parent brand: subscribers of the Businessweek magazine praise its quality, and its covers and design are famous (Reddit r/Design and r/funny threads about covers). Bloomberg says Businessweek has one of the highest subscriber-conversion rates in the company.
  - Sentiment: we can't quantify it. The growth numbers suggest steady acceptance, but nobody evangelizes it the way readers do for Money Stuff.
- **Speciality / niche:** Magazine-quality feature journalism, plus photography and illustration, delivered as a daily excerpt. It offers **"free links"** that unlock paywalled Bloomberg stories, a list-style franchise (e.g. "10 companies to watch this quarter" with ☀️/☁️ outlooks and a named "Trigger" catalyst per stock from Bloomberg Intelligence), and coverage of Bloomberg Live events (e.g. Screentime).
- **How the content comes (format anatomy) — grounded in two Gmail issues (Oct 1 "10 companies to watch this quarter", Oct 2 "Hollywood braces for another sequel"):**
  - **Subject:** a feature-style headline. **Preheader:** "Plus: <second story>". The in-body H1 is a longer headline.
  - **Length:** ~1,200–2,000 words (5–9 min), 50–60 links.
  - **Order:** (1) **editor's note**: 2–3 sentences framing today's lead, with "Plus:" teasers and a "(free link)"; (2) sign-up/subscribe nudge; (3) **lead piece**, either an essay by a contributing editor (e.g. the entertainment editor reporting from Screentime) or an excerpted list, with photo/illustration credits and "Read more"; (4) "Related Stories" (3 headlines with deks); (5) **"In Brief"**: 3–4 bullet news items; (6) **Big-number module**, a headline plus one number plus an explanatory sentence (e.g. "5.34%", the 10-year yield; "10,000" troops); (7) a second feature excerpt (e.g. Diesel's Effects, Granny Flats for NYC); (8) **Quote module** with speaker and title (e.g. Ben Affleck on AI); (9) **"Test Your Knowledge"**, a daily Bloomberg Games puzzle clue (Alphadots); (10) "More From Bloomberg" cross-promo for 5 other newsletters; (11) a feedback link.
  - **Tone:** polished, narrative magazine prose, third person, people-and-scenes ledes (a pumpkin farmer facing diesel costs). Images throughout. No third-party ads in our samples; the commercial goal is subscription conversion.
- **X factor:** It is the only daily in our set that delivers *narrative feature journalism* (scenes, characters, photography) rather than market commentary, and it unlocks paywalled stories with free links.
- **Criticisms / what people dislike (mostly inferred, given thin evidence):**
  - Most links point to the Bloomberg paywall. Reddit finance users complain about Bloomberg's paywall and "click-baity" headline style generally (r/FinancialCareers).
  - Its identity is fuzzy: it covers tech one day and politics the next, with no fixed beat. That is great for variety and weak for habit-building.
  - It is a funnel product. The excerpts are deliberately incomplete ("never the whole meal"), which can feel like teasers.
  - The name collides with the radio show/podcast, which causes discovery confusion (and could cause dedup confusion for us).
- **What our aggregator should steal:**
  1. **Recognize "module" types** (Big number, Quote of the day, In Brief bullets, Puzzle). Extract them as typed cards so the digest can build a cross-newsletter "Numbers of the day" or "Quotes of the day" strip.
  2. **Preserve "free link" (gift-link) URLs** and flag them in the UI. They are rare paywall-free entry points, and our archive should mark them as such. They may also expire, so capture the article text early in Phase 4.
  3. **The editor's-note pattern:** open each digest section with 2–3 framing sentences plus "Plus:" teasers, the same hook-then-list rhythm.
- **Sources:**
  - https://www.niemanlab.org/2024/07/bloomberg-businessweeks-editor-believes-print-remains-the-ultimate-distraction-free-news-product/
  - https://www.bloomberg.com/account/newsletters/businessweek
  - https://www.bloomberg.com/help/question/how-can-i-subscribe-to-bloomberg-businessweek/
  - https://www.reddit.com/r/FinancialCareers/comments/nbhr46/is_a_bloomberg_subscription_worth_it_im_doing_an/
  - https://www.reddit.com/r/Design/comments/4ycsq6/am_i_missing_something_here_this_bloomberg_cover/
  - Gmail: msgs `1a0f86e5e5b888de` (Oct 1 2026), `1a0fdb848cecea7f` (Oct 2 2026)

---

### Axios Markets (Emily Peck & Matt Phillips)

- **Snapshot:** From Axios, which Cox Enterprises bought for $525M in 2022. Current co-authors are **Emily Peck** (ex-HuffPost/WSJ, Slate Money co-host), who retook the newsletter in Feb 2026 from Madison Mills, and **Matt Phillips**, who returned to Axios ~June 2026 from Sherwood News (ex-NYT/WSJ/Quartz). Edited by Jeffrey Cane. The authors change often: Sam Ro and Madison Mills wrote it in 2024–25. **No title-specific subscriber number is public.** Axios-wide figures: 2.4M free subscribers across 34 newsletters with ~40% open rate (2022). Frequency: weekdays, **~7:30am ET** (our copies arrived 07:28–07:32 EDT). Free and ad-supported (presenting sponsor: Capital One). It launched ~Jan 2019 (Primack mentioned a new daily markets newsletter in the Recode interview). We subscribed on Sep 30 2026 and received the welcome email.
- **Why people like it (social proof): EVIDENCE THIN FOR THIS TITLE.**
  - A listing site cites it as a free, ~5-minute pre-market read and an alternative to paid Bloomberg/WSJ. That is marketing-ish, and it lists outdated authors (readless.app).
  - Practitioner Reddit threads recommend Axios newsletters as "short and sharp", though those mentions are mostly Pro Rata (r/CFA, r/FinancialCareers).
  - Readers like the Smart Brevity house style for speed and scannability. Mike Allen's pitch: sophisticated explanations, not long ones.
  - The authors' personality: a chatty emoji opening and sign-offs asking readers for recipes and questions. Both authors list their emails and invite replies.
  - Overall sentiment: mixed-to-neutral, with very little organic chatter. The format itself is polarizing (see criticisms).
- **Speciality / niche:** It connects the market to the real economy and household finances ("the stock market increasingly *is* the economy"). Every lead is anchored on **one original chart** with a descriptive caption and data source. It is macro-for-normal-people rather than trader-speak.
- **How the content comes (format anatomy) — grounded in Gmail issues of Oct 1 ("🤑 AI wealth effect") and Oct 2 ("😱 Shizzle meet fan") 2026:**
  - **Subject:** one emoji plus 2–4 punchy words. **Preheader:** "Plus: <item 2> | <date>".
  - **Top:** "Presented By Capital One" → byline → **emoji-bulleted cold open** (🎃/👻/🗓️): a seasonal aside, overnight futures and yields in one line, today's agenda, then an **explicit length promise: "925 words, a 3.5-minute read."**
  - **"1 big thing"** (author byline) → chart → a run of bold Axios signposts: *Why it matters → By the numbers → Zoom out → Zoom in → Between the lines → What to watch → Reality check → The bottom line*, each followed by 1–3 short bullets.
  - Optional **"Bonus chart"** → sponsor block ("A MESSAGE FROM CAPITAL ONE") → **"2."** second story (same signpost skeleton, e.g. Q3 winners and losers) → second sponsor block → **sign-off** with a personal note and an invitation to reply, editor and copy-editor credits → an upsell for **Axios Pro Deals**.
  - About 925–1,070 words of editorial (≈1,500 with chrome), 2 stories, 2–3 charts, ~40–50 links, two ad units. The share buttons sit under each item.
- **X factor:** A small, predictable dose with a promised read time (always ~2 stories, one chart, the same signposts), so you can finish it before the open. The chart-first lead is the hook.
- **Criticisms / what people dislike** (mostly aimed at the Axios format, not this title specifically):
  - "Pre-chewed" bullets can be *harder* to understand. Timothy Noah (The New Republic) says he sometimes has to reread Axios pieces two or three times.
  - Mandatory signposts ("Why it matters", "What's next") push writers to fill slots with filler when there's no time to find out (TNR; CJR).
  - It strips context and nuance and maps an insider's conventional wisdom onto the news (The New Yorker, 2022).
  - The author churn (Ro → Mills → Peck → Peck+Phillips within ~2 years) weakens the "personal voice" bond.
- **What our aggregator should steal:**
  1. **Print an explicit word count and read time at the top of each digest**, as Axios does in its cold open. Cheap to compute in our pipeline and highly valued.
  2. **Use Axios signposts as parse anchors.** Bold "Why it matters:" / "The bottom line:" lines are near-perfect summary sentences, so extract them as a free "TL;DR" for each item without needing the LLM.
  3. **Keep chart alt-text.** Axios writes rich, data-bearing alt text (ranges and endpoints). Store it in the archive and surface it, since it makes charts searchable and quotable.
- **Sources:**
  - https://talkingbiznews.com/media-news/183897/
  - https://www.mediapost.com/publications/article/415277/matt-phillips-returns-to-axios-will-co-author-mar.html
  - https://www.axios.com/authors/epeck
  - https://www.readless.app/newsletters/axios-markets
  - https://www.newyorker.com/news/annals-of-communications/the-dubious-wisdom-of-smart-brevity
  - https://newrepublic.com/article/167857/axios-smart-brevity-book-hell-world
  - https://www.cjr.org/criticism/axios-smart-brevity-longform.php
  - https://pressgazette.co.uk/news/axios-pro-launch/
  - https://www.reddit.com/r/CFA/comments/153l0jl/recommendations_for_finance_newsletters_or_data/
  - Gmail: msgs `1a0f73c39d69f013` (Oct 1 2026), `1a0fc64b8a908aa5` (Oct 2 2026), welcome `1a0f123f9fba9bbe`

---

### Axios Pro Rata (Dan Primack)

- **Snapshot:** Written by **Dan Primack**, Axios business editor. He has written a deals newsletter since ~2002, first at Thomson Financial/Reuters (PE Week Wire), then at Fortune (Term Sheet, ~6 years), and has written Pro Rata at Axios since its January 2017 launch. Audience: **200,000+ free subscribers (2022)** per Nieman Lab / Press Gazette. A directory claim of "50k–80k" conflicts with that and looks unreliable. Frequency: weekdays, mornings (sent ~7–8am ET; the web version follows). Free and sponsored (presenting sponsor in 2026: J.P. Morgan; earlier: Cooley). Its success spawned the paid **Axios Pro** deal-tracking product ($600–1,800/yr, 2022). **Not yet in our inbox, so the web edition was used** (Aug 25 2026, "PE's pastime").
- **Why people like it (social proof):**
  - It is the industry default. A 2026 PE-practitioner blog says almost everyone in the industry reads it on the train, and "If you only read one, this is it" (notveryprivateequity.com, a practitioner listicle with some SEO feel).
  - It is consistently recommended on r/CFA and r/FinancialCareers ("Focus on VC, PE, and deal flow. Short and sharp") and on r/venturecapital's favorite-newsletter lists.
  - Readers have a personal relationship with the author. Emails come from Dan's own address and replies reach him; Axios's publisher credits that relationship for Pro Rata's success (Nieman Lab).
  - Readers value scoops and "something you don't know yet". Primack's stated goal is that nobody surprises you at the water cooler, and that you bring something new to it (Recode/Vox 2019).
  - It has spicy opinion columns. His 2024 "Dear venture capitalists" letter about VCs hoarding exits circulated widely on LinkedIn and in other newsletters (TheFundCFO).
  - Sentiment: strongly positive among practitioners. Criticism is aimed at the Axios format and a pro-business slant.
- **Speciality / niche:** The **daily comprehensive deal log** for VC, PE, M&A, IPOs, fund-raises and personnel moves: dozens of one-line items, each naming lead investors and valuations, combined with one sharp opinion column from the best-sourced deals reporter.
- **How the content comes (format anatomy) — from the Aug 25 2026 web edition and Primack's own description:**
  - **Subject/title:** `Axios Pro Rata: <2–3 word pun>` with a preheader of "Plus, <secondary item>".
  - **Order:** (1) **Top of the Morning**: Primack's first-person column (~300 words in Smart Brevity bullets), e.g. "When will sports leagues push PE out? Short answer: Never." (2) **The BFD** (big deal of the day): one deal with "Why it's the BFD", "By the numbers", "The bottom line". (3) **Venture Capital Deals**, ~20 items. (4) **Private Equity Deals**. (5) **Public Offerings**. (6) **Liquidity Events**. (7) **More M&A**. (8) **Fundraising** (funds raised). (9) **It's Personnel** (people moves). (10) **Final Numbers**, a closing chart or poll (here an "Unscientific poll").
  - Each deal item follows a strict template: **Company**, location, what it does, raised $X at series Y, lead investor in bold, "joined by…", then an `axios.link` short URL. **Emoji sector tags** (🚑 health, ⚡️ energy/climate, 🚀 space, ☕ food) let readers scan for their vertical. Primack says there are usually 30–40+ blurbs a day (we counted ~50 links), and "Monster" issues before holidays.
  - Tone: the column is opinionated and wry, and the deal log is terse and factual. One sponsor block, plus upsells to Axios Pro.
- **X factor:** A complete, structured, scannable record of every notable deal each morning, paired with one well-sourced insider take. It is reference data and a columnist in one email.
- **Criticisms / what people dislike:**
  - The Axios-format criticism applies here too: bullets and "why it matters" flatten nuance (a 2018 review of the Pro Rata podcast; New Yorker/TNR on Smart Brevity).
  - Pro-business framing: one critic notes the author called left-wing Amazon criticism "wealth-bashing", with no inequality angle (podcastreview.org, 2018).
  - The deal list is long and mostly links out; Primack himself says he won't analyze 40 deals.
  - Increasing upsell to the paid Axios Pro tier for deeper deal data (an inference from the product structure; not widely complained about).
- **What our aggregator should steal:**
  1. **Parse deal items into structured rows** (company, location, round, amount, valuation, lead investors, participants, sector emoji, source link). That gives us a queryable "deals" table in Phase 4 SQLite almost for free, because the template is so regular.
  2. **Fixed section taxonomy with sector-emoji tags.** Adopt a similar small emoji set for categorizing items across all newsletters, so readers can filter by their vertical.
  3. **Action item: subscribe `notifyy1008@gmail.com` to Pro Rata** (signup: https://www.axios.com/signup/pro-rata). It is the canonical deals feed, and it is missing from our inbox.
- **Sources:**
  - https://www.vox.com/2019/1/17/18185863/axios-dan-primack-business-economy-ipo-pro-rata-newsletter-media-podcast-interview-peter-kafka
  - https://www.niemanlab.org/2022/01/axios-launches-a-premium-subscription-product-aimed-at-the-dealmakers-among-us/
  - https://pressgazette.co.uk/news/axios-pro-launch/
  - https://www.inpublishing.co.uk/articles/axios-launches-subscription-product-axios-pro-20371
  - https://www.pressprofilespodcast.com/dan-primack-the-man-behind-the-axios-newsletter-that-informs-the-pe-industry/
  - https://www.notveryprivateequity.com/top-10-private-equity-newsletters/
  - https://www.reddit.com/r/CFA/comments/153l0jl/recommendations_for_finance_newsletters_or_data/
  - https://www.reddit.com/r/venturecapital/comments/qzx00l/favorite_vc_newslettersblogs/
  - https://www.reddit.com/r/FinancialCareers/comments/13zb323/probably_no_existent_but_is_there_a_free/
  - https://thefundcfonewsletter.beehiiv.com/p/150-primacks-letter-to-vcs-and-cfo
  - https://podcastreview.org/review/smarter-faster-axios-pro-rata-reviewed/
  - https://www.axios.com/newsletters/axios-pro-rata-60ba74b4-004e-4f57-b2e5-496aa335b1f7 (web edition, read via Jina)
  - https://newsletterhunt.com/newsletters/pro-rata

---

### Snacks (Sherwood News, formerly Robinhood Snacks / MarketSnacks)

- **Snapshot:** It began as **MarketSnacks** (founded 2014 by Jack Kramer & Nick Martell). **Robinhood acquired it in March 2019**, its first acquisition, and renamed it Robinhood Snacks. It moved into **Sherwood Media** (Robinhood subsidiary, EIC Joshua Topolsky) in 2023 and was rebranded with the Sherwood News launch in April 2024. The main writer now appears to be **Walt Hickey**, Sherwood's executive editor and writer of Numlock News, who signs "The Takeaway" in our issues. Audience: **36M subscribers (June 2021)**, "40 million" (Observer 2023), "tens of millions" per Robinhood. **Caveat:** these numbers are inflated by Robinhood users being subscribed by default unless they opt out, so engaged readership is far smaller and not disclosed. In 2021 MarketSnacks' audience was 85% under 36. Frequency: weekdays, ~6:30am ET (our copies arrived 06:30–06:38 EDT). Free and ad-supported (since Sherwood). **Context:** in June 2026 Robinhood cut 10% of staff, laid off several Sherwood reporters and **wound down the Sherwood website**. Strategy is now "signature newsletters plus breaking news in the Robinhood app", with Snacks described as "one of the most widely read newsletters in the country" (InvestmentNews, Talking Biz News).
- **Why people like it (social proof):**
  - It makes markets fun for beginners. Reddit defenders call it a simple fun read and a quick rundown of stock news, a "stepping stone" for new investors (r/RobinHood 2019).
  - Readers love the puns, sarcasm and pop-culture analogies (LinkedIn comments on the Robinhood post; Fortune's Chipotle "burrito bowl" example).
  - It is a quick morning ritual: commenters say it makes them feel a little smarter as they open their inbox.
  - The **"Snack Fact of the Day"** gets shared on its own, and growth analysts cite it as a shareable signature element (RightMetric).
  - The new Hickey-era issues are more data- and number-driven, a Numlock influence (observed in Gmail; we found no reader reaction to the change yet).
  - Sentiment: **polarized**. Beginners like it. Experienced investors on r/RobinHood dismiss it (a 2019 thread titled "Snacks sucks.").
- **Speciality / niche:** Business and markets news translated for young retail investors through humor and narrative. It typically does one deep story with a "takeaway" angle on *why investors should care*, not trading advice.
- **How the content comes (format anatomy) — grounded in Gmail issues of Sep 30 ("Wall Street has big expectations for Micron") and Oct 2 2026 ("Creative destruction prepares to go public"):**
  - **Subject:** a punny or curious headline. On the web it carries a leading emoji (e.g. "🍴 We're starving out here"); the email subject has none. **Preheader:** a one-line news hook ("Anthropic is reportedly aiming to go public before Thanksgiving.").
  - **Order:** (1) hero image with photo credit; (2) **"Hey Snackers,"** followed by a **cold-open micro-story**, a quirky, unrelated-seeming anecdote (e.g. a Dutch bird-radar company pivoting to drone detection); (3) a deadpan one-line market recap ("Stocks rose on Thursday."); (4) **main story** under an ALL-CAPS pun kicker (e.g. "AIPO", "MEMORY TEST") with an H2 headline, 3–5 bullets of numbers ("the good numbers / the bad ones / the crazy one"); (5) **"THE TAKEAWAY"**: a ~250-word signed analysis (— Walt Hickey); (6) **number-of-the-day** blurb (e.g. a supertanker day-rate); (7) **"What else we're Snackin'"**: 5 linked headlines; (8) **"Snack Fact of the Day"**; (9) a day's **calendar** ("Friday: Sept payrolls 8:30am ET"); (10) cross-promo for **EntryPoint and Scoreboard**, plus the Robinhood-ownership disclosure.
  - **Length:** ~800–1,050 words (~4 min), ~35–40 links, ~7 images. Tone: witty, casual, pun-heavy. Sherwood ad slots exist, but none showed in these two issues.
- **X factor:** The "story-first, then the money angle" structure, delivered with jokes at 6:30am, plus default distribution to millions of Robinhood users. Few rivals can match that reach to young retail investors.
- **Criticisms / what people dislike:**
  - It is "dumbed down" and has a "fellow kids" tone; experienced investors find it a waste of time (r/RobinHood "Snacks sucks.").
  - **Conflict of interest:** it is owned by a broker. It originally didn't cover Robinhood at all, and now covers it "with disclosures" (Axios 2023). Sister newsletter EntryPoint carries an IPO "quiet period" restriction notice.
  - Its subscriber numbers are seen as vanity because of auto-subscription; emails also land in spam or stop arriving (r/RobinHood 2022 thread).
  - The June 2026 Sherwood cuts and the website shutdown raise questions about its long-term editorial independence and depth (trade press).
- **What our aggregator should steal:**
  1. **A "cold open" in our daily digest:** lead with one surprising micro-story or number before the briefing. Snacks and Businessweek both show this hook works.
  2. **A typed "Fact / Number of the day" extractor** across all newsletters (Snacks' Snack Fact, its number blurb, Businessweek's big number). Rotate the best one into the digest header.
  3. **Extract the per-issue calendar** ("What to watch" / day lists) into a merged forward-looking **econ and earnings calendar**. Snacks, EntryPoint and Axios all include one.
- **Sources:**
  - https://fortune.com/2019/03/25/robinhood-acquires-marketsnacks/
  - https://www.axios.com/2023/01/17/robinhood-media-joshua-topolsky
  - https://www.axios.com/2024/04/09/robinhood-launches-sherwood-media
  - https://observer.com/2023/01/is-robinhoods-new-media-venture-actually-brilliant/
  - https://rightmetric.co/outsight-library/pro-members-how-robinhood-created-a-newsletter-with-36-million-subscribers
  - https://www.reddit.com/r/RobinHood/comments/b6kazf/snacks_sucks/
  - https://www.reddit.com/r/RobinHood/comments/b8kfcb/snacks/
  - https://www.reddit.com/r/RobinHood/comments/uw95p9/did_robinhood_snacks_change/
  - https://www.linkedin.com/posts/robinhood_last-march-we-launched-robinhood-snacks-activity-6622855475170025472-fm1f
  - https://www.investmentnews.com/fintech/exclusive-robinhood-cuts-sherwood-news-staff-in-app-content-push/267068
  - https://talkingbiznews.com/media-news/sherwood-news-is-ending-its-website/
  - https://sherwood.news/author/walt-hickey/
  - Gmail: msgs `1a0fc311622efb85` (Oct 2 2026), `1a0f1e4a1249fe71` (Sep 30 2026)

---

### EntryPoint (Sherwood News — pre-market / technical signals)

- **Snapshot:** **Launched May 11 2026** by Sherwood Media, written by **Luke Kawa**, Sherwood's head of markets (ex-UBS Asset Management rates/commodities research, ex-Bloomberg cross-asset reporter who chronicled WallStreetBets, ex-Business Insider), with David Crowther at launch. Free. Pre-market: our copies arrived ~8:25–8:50am ET. **Frequency is inconsistent:** the launch post says Monday/Wednesday/Friday, while the welcome email says "every weekday". Our inbox shows Wed Sep 30 and Fri Oct 2, which fits M/W/F. **No audience number published.** It survived the June 2026 Sherwood layoffs, which suggests it is a strategic product.
- **Why people like it (social proof): VERY THIN, since it is ~5 months old.**
  - Market commentator Jesse Felder (Bluesky) said he'd add it to his morning routine because Kawa "has his finger on the pulse of the markets".
  - Sister newsletter Snacks calls it "must-read" (self-promotion, so discount it).
  - The main selling point is **proprietary Robinhood order-flow data**: what retail traders actually bought and sold, which Sherwood says is unavailable anywhere else. Kawa has credibility from his memestock/WSB coverage (Bloomberg Odd Lots "Lots More" episode, 2024).
  - Sentiment: we can't assess it. We found no Reddit, HN or X threads.
- **Speciality / niche:** Sell-side-style **macro-to-micro** strategy notes (breadth, rates, vol, skew, tax-loss selling) combined with **retail flow data from Robinhood**. It reads like a hedge-fund morning note written for sophisticated retail traders.
- **How the content comes (format anatomy) — grounded in Gmail issues of Sep 30 ("A record week for retail buying") and Oct 2 2026 ("The greatest thing since sliced breadth"):**
  - **Subject:** a pun headline. **Preheader/dek:** a one-sentence thesis. Then "— By Luke Kawa".
  - **Order:** (1) **"Good morning traders,"**, covering futures, the day's data, yesterday's tape, and **what Robinhood traders bought or sold yesterday** (e.g. photonics names dumped; record five-day net single-stock buying); (2) a regulatory **quiet-period disclaimer**; (3) **lead deep-dive** under a pun H2 ("Sliced Breadth"): historical analogs, several charts, quotes from strategists (McClellan, BTIG, Goldman), and a forward-return study with method notes; (4) a **second idea** under a pun H2 ("Just DooDoo", on Nike and tax-loss-selling candidates, with a screen); (5) **"Whispers from Wall Street"**, a verbatim excerpt of sell-side research (JPMorgan derivatives); (6) **"Seen on Socials"**, an embedded X post or chart; (7) **"What to watch"**, a **day-by-day calendar for the week ahead** (data, Fed speakers, earnings); (8) cross-promo for Snacks and Scoreboard, plus the ownership disclosure.
  - **Length:** ~1,200–1,750 words (5–8 min), 14–18 images (chart-heavy), ~30–37 links. Tone: trader-literate and wry ("VIX below the voting age", "color me surprised"), with dense jargon.
- **X factor:** It is the only newsletter in our set with **first-party retail order-flow data** (Robinhood buys and sells), wrapped in a professional-grade cross-asset strategy note.
- **Criticisms / what people dislike (inferred; we found no user complaints):**
  - Built-in conflict: it is a broker's media arm reporting its own customers' flows. It is barred from covering IPOs Robinhood underwrites during the quiet period, and the flow data doubles as marketing.
  - It leans heavily on quoting sell-side research, so its original analysis is concentrated in the lead.
  - The jargon density (skew, convexity, breadth, A/D line) puts off the Snacks audience it is cross-promoted to.
  - Its future is uncertain given Sherwood's 2026 restructuring.
- **What our aggregator should steal:**
  1. **Pull out "proprietary data" callouts** (e.g. "Robinhood traders net bought X") as a distinct, high-value item type, and label the source of exclusive data in the digest.
  2. **Merge the week-ahead calendars** from EntryPoint, Snacks and Axios into one de-duplicated calendar (date, time, event, ticker), so the digest can show "This week" without any LLM.
  3. **Tag research-excerpt blocks** ("Whispers from Wall Street") as *quoted third-party research*, separate from the author's own view. That keeps attribution honest in summaries, which matters for Phase 5 (Groq/Qwen) enrichment.
- **Sources:**
  - https://sherwood.news/markets/robinhood-traders-bought-the-dip-entrypoint-launch/ (read via Jina)
  - https://sherwood.news/author/luke-kawa/
  - https://www.linkedin.com/in/luke-kawa-067bb155
  - https://bsky.app/profile/jessefelder.com/post/3mllii73fic2e
  - https://www.bloomberg.com/news/audio/2024-05-23/lots-more-with-luke-kawa-on-memestock-mania-2-0-podcast
  - https://sherwood.news/snacks/newsletters/were-starving-out-here/
  - https://www.investmentnews.com/fintech/exclusive-robinhood-cuts-sherwood-news-staff-in-app-content-push/267068
  - Gmail: msgs `1a0fc94ae85e2d03` (Oct 2 2026), `1a0f25e3bfcb3ff6` (Sep 30 2026), welcome `1a0f11fad905ba37`

---

## Cross-cutting observations for the aggregator

- **Send-time spread** (all ET): Snacks ~6:30 → Axios Markets ~7:30 → EntryPoint ~8:30 → Businessweek Daily ~1:00–1:45pm → Money Stuff ~1:45–2pm. A single morning digest would miss the two Bloomberg titles, so consider a morning plus an afternoon edition, or defer them to the next morning's digest.
- **Parsing notes:** the Bloomberg emails have usable `body` text (plain-text part). Axios and Sherwood send **HTML-only** (`body` is empty and `htmlBody` is populated), so the Phase 4 capture must convert HTML to text/markdown. Bloomberg's plain text puts links as `<url>` on separate lines, and Axios embeds data-rich chart alt text.
- **Recurring typed modules worth a shared schema:** big-number/stat, quote-of-day, fact-of-day, link roundup ("Things happen", "What else we're Snackin'", "In Brief"), week-ahead calendar, deal rows (Pro Rata), footnotes (Money Stuff), proprietary data callouts (EntryPoint), sponsor blocks (to strip).
- **Gmail errors:** none. All reads were read-only. Pro Rata is not subscribed in our inbox.
