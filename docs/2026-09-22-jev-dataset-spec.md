---
title: "2026-09-22 Jev Dataset Spec"
type: pre-registration
substrate: jev-1.13.0
instrument: Prove (proofload CLI)
status: written before any calibration call; zero provider spend incurred; awaiting Taylor's approval
written: 2026-09-22
serves: "2026-09-21-jev-prove-study-spec.md"
executed_by: "2026-09-22 Jev Study Calibration (Antigravity)"
projects: [proofload]
tags: [jev, prove, proofload, pre-registration, dataset, candidate-pool, licences, sampling]
---

# 2026-09-22 Jev Dataset Spec

> **What this is.** The candidate pool for the Jev paired-replay study: which public datasets the
> 900 items come from, how a row becomes a Jev request, the sampling rule, the exclusions, and what
> happens if a band does not fill. It is written so that a different session can execute it exactly,
> without asking this one a question.
>
> **What this is not.** It is not a change to [2026-09-21 Jev Prove Study Spec](2026-09-21-jev-prove-study-spec.md). That document's
> cuts, strata, bands, statistics and outcome sentences stand untouched. This one fills in the two
> sentences that document left open: *"Items are drawn from a separate candidate pool of textual
> decision states"* and *"candidates are ordered by a fixed hash of their text."*
>
> **No Jev call has been made, by this session or any other.** Everything here about what Jev
> returns is a vendor statement or somebody else's published measurement, tagged as such.
>
> **One thing may stop the study before it starts.** Two independent public audits report that Jev
> returns probabilities quantised to 0.01. The study spec's §2.5 gate fires on exactly that. §3
> below says what it means and what the pool builder does about it. It is the first thing to read.
>
> **One yes/no is owed to Taylor** (§8). Everything else is settled.

---

## 0. In plain language

The study asks one question: *send Jev the identical request twice, and does the decision at the
threshold come out the same way both times?*

To ask it you need items that sit close to a threshold. An item Jev scores 0.02 or 0.98 will never
flip, however noisy the model is, so a pool of easy items answers the question trivially and wrongly.
So the study picks items *because* their score lands near a cut. That choice is the study's biggest
caveat and it is carried in every sentence the note will print.

Where the items come from is the part this document settles. There were two ways to get them. We
could write the items ourselves from templates, which gives complete control and produces a pool
nobody outside Poisson Labs has any reason to trust. Or we could take them from public datasets
that other people built, published under licences that let us use them, in domains where Jev is
actually used. **Taylor ruled for the second**, and this document is that ruling made executable.

Three sources, one per use case that TypeSafe itself puts on its evaluation page:

- **Banking77** — 13,083 real customer-support messages with the intent each one expresses. The Jev
  question is the one TypeSafe's own quickstart asks: *should this message go to this queue?*
- **CLINC150** — 15,250 assistant utterances plus 1,000-odd human-written queries that deliberately
  fall outside the assistant's scope. The question is *is this inside what the assistant handles?*
- **HelpSteer2** — 21,362 prompt-and-response pairs with human helpfulness ratings. The question is
  *is this response ready to send?* — which is TypeSafe's "Agent Trace Observability" workflow and
  the single most-circulated Jev demo on X.

All three are CC BY. All three have been used in published Jev evaluations by other people, so the
choice is not ours alone. None of them needs us to invent an item.

The rest of this document is the machinery that makes the pool defensible: a hash ordering fixed
before anything is scored, exclusions written down before anything is excluded, a per-source cap so
no one dataset carries a stratum, a rule for what happens if a band comes up short, and a checklist
the building session has to pass before it may make a single call.

**There is no template arm.** Two of TypeSafe's five shown workflows — invoice processing and
expense claims — have no public text-only labelled source, so under Taylor's ruling they would be
the case for templates. §4.4 recommends cutting them instead, and says why.

---

## 1. How Jev is actually used, and shown

Everything in this section is `docs` — read from TypeSafe's own pages on 2026-09-22 through a
fetch-and-summarise tool. Links and dates in `data/pool/SOURCES.md`.

### 1.1 What TypeSafe says Jev is for

The launch post frames Jev as **"smart if-statements"**: structured outputs that "slot into ordinary
software as fuzzy decision rules: classify, route, score, extract, or branch where hand-written logic
is too brittle." ([typesafe.ai/blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev),
2026-09-15.)

That sentence is the study's whole premise. A branch is a threshold. The study measures whether the
branch reproduces.

### 1.2 What TypeSafe evaluates

[evals.typesafe.ai](https://evals.typesafe.ai/) shows **five workflows**, and this is the strongest
available evidence of what TypeSafe thinks Jev is for, because it is where they chose to be measured:

| Workflow | What it decides | Public text-only labelled source? |
|---|---|---|
| **Customer Service** | assistant response and action for a customer message | **Yes** — Banking77, CLINC150 |
| **Agent Trace Observability** | whether a support-agent interaction needs quality review | **Yes** — HelpSteer2 (response-quality ratings) |
| **Security Incidents** | close, analyst review, or contain | Weak — see §4.4 |
| **Invoice Processing** | pay, hold, or reject a vendor bill | **No** — §4.4 |
| **Expense Claims** | approve or review an employee claim | **No** — §4.4 |

Two things about that page are worth the study's attention. Its reference labels are "generated via
an average of the responses of GPT-6 Astra and Claude Fable 5.1" — no external ground truth — and
**no public dataset is named anywhere on it**. KDnuggets made the same point on 2026-09-21: "The
reference answers come from frontier models, not independently verified ground truth."

That matters for us in one specific way, stated so it is not overclaimed: the Poisson study makes no
accuracy or calibration claim at all (study spec §7.10), so it does not need ground truth. It needs
items that land near a threshold, and it needs them to look like the traffic Jev is sold for.

### 1.3 The documented use-case list

[The use-case map](https://docs.typesafe.ai/concepts/use-case-map.md) names nineteen. Ranked by how
well a public dataset can stand in for them:

| Use case | Public source quality | In the pool? |
|---|---|---|
| #9 Customer support — "Classify tickets, extract issues, detect urgency/churn risk, verify responses against policies" | **Strong** | **Yes** (S1, S2) |
| Universal Verification / agent-output review | **Strong** | **Yes** (S3) |
| #4 LLM guardrails — jailbreaks, prompt injection, policy violations | Moderate; the obvious set is 662 rows | No — §4.4 |
| #14 Moderation and trust and safety | Strong on paper, bad on content | No — §4.4 |
| #1 Search and retrieval — ranking | Strong | No — it is a sort, not a branch (§4.4) |
| #2 Scientific discovery — screen papers, verify citations | Moderate | No — §4.4 |
| #11 Financial crime, #17 Risk assessment | Weak | No |
| #10 Insurance claims, #12 Legal and compliance | Weak | No |

### 1.4 The threshold, in TypeSafe's own words

The [noul page](https://docs.typesafe.ai/primitives/noul.md) is where a reader learns to use the
number. It ships a worked routing example with `YES = 0.8` and `NO = 0.2`, and this guidance:

> "Use 0.5 when yes and no are equally easy to act on. Raise it when acting on a false yes is
> expensive. Lower it when missing a true yes is expensive."

The study's three cuts — 0.50, 0.60, 0.90 — are the shipped shape of that sentence. The independent
Jevals benchmark reports its own worked confidence gates at **choice 0.96 and noul 0.91**, which is
the 0.90 cut in the wild. Janus found the optimal cascade threshold moving from **0.67 to 0.37**
between two datasets, which is the reason the study fixes its cuts in advance rather than fitting
them.

### 1.5 What the vendor admits, and what it does not

The [jev-1.13 jaggedness page](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md) lists eleven
known weak spots. Four of them constrain how a row becomes a request, and §5.3 obeys all four:

- "answers the question you wrote, not the one you meant" → one clause per question, no compound.
- "Jev is not a calculator" and "cannot reliably judge whether two values are near each other" →
  no arithmetic, no quantities, no comparisons in the question.
- "reads dates as text, not as ordered quantities" → no dates.
- "Instructions carrying double negatives or complex indirection are answered less reliably" →
  positive phrasing, no negation, no reference to anything outside the state.
- "Accuracy falls as the state grows with content unrelated to the decision" → the state carries the
  item and nothing else.

**The page says nothing about determinism, about repeated identical requests, or about behaviour near
a decision boundary.** Neither does any other documentation page — the full index at
`docs.typesafe.ai/llms.txt` was checked.

The nearest thing the vendor has is the [self-consistency cookbook for
nouls](https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook.md). It repeats a question
fifteen times, and it varies a throwaway `uid` field between repeats. Its own words:

> the setup "cannot separate sensitivity to the irrelevant field from variation that would occur on
> identical requests."

That sentence is the gap this study fills, and it is TypeSafe's.

### 1.6 What other people have already measured

`third-party`. Other people's numbers, not replicated here. They are in this document because they
change what the pool has to survive, and because the note will have to cite them.

| Study | Datasets | The finding that bears on us |
|---|---|---|
| [jev-orderby-bench](https://github.com/yodablocks/jev-orderby-bench) | 20 Newsgroups, Amazon ESCI (Apache-2.0) | **"Jev returns probabilities at two decimal places."** 45 distinct values across 360 rows; 53 rows tied at 0.99 |
| [jev-ood-calibration](https://github.com/scienthoon/jev-ood-calibration) | OpenBookQA, CommonsenseQA, HellaSwag, + 900 rule-generated tickets | **"Probabilities quantize to 0.01."** 1,051 of 2,000 option probabilities exactly 0. Boolean questions *under*confident; choice and score overconfident |
| [jev-calibration-audit](https://github.com/jujumilk3/jev-calibration-audit) | KoBBQ (MIT), MMLU-ProX (MIT) | **"50 identical requests gave 15 distinct answers; the cookbook `uid` trick adds variance rather than revealing it."** |
| [jev-certify](https://github.com/nikkoxgonzales/jev-certify) | CLINC150 | Top probability exactly 1.0 on **56.4%** of answers; 94 distinct values across 860; "α = 1% is unreachable" because of the resolution floor |
| [Janus](https://github.com/FirasSX914/Janus) | Banking77 (CC BY 4.0), Web of Science | The threshold does not transfer: 0.67 → 0.37 |
| [Jevals](https://jevals.com/) | PubMedQA, Banking77, HelpSteer2 | Worked gates at noul 0.91 |

The third row deserves a straight word. **Somebody has already shown that identical Jev requests do
not reproduce.** The Poisson study is not the first to notice. What it adds, and what that audit does
not report, is a *branch-flip rate at a cut people ship, with an interval, under a pre-registration,
on items chosen before any score was seen.* "15 distinct answers out of 50" is a fact about the
values. This study is about the decision. The note must cite the audit and say exactly this.

---

## 2. What is said and shown about Jev on X

**Reachability, first.** X post pages could not be opened from this session: a direct fetch of an
x.com status URL returned **HTTP 402 Payment Required**. Post pages need an authenticated session or
a paid tier and this session had neither.

**Therefore every claim in this section is second-hand.** It comes from search-result snippets and
from one published aggregate analysis of 12,759 tweets
([OpenChamber](https://openchamber.dev/blog/jev-typesafe-ai/), 2026-09). Handles, view counts and
quoted sentences are reproduced as that source printed them. **No X post was read on X**, and none of
this may be cited in the lab note as a first-hand read.

### 2.1 What circulates

- **Agent context pruning** is the demo that travelled furthest: a post proposing to score and drop
  unnecessary tool calls out of a session's history, reported at **1.45M views**, with a counter-post
  at 256k arguing that compaction and filtering are not the same operation.
- **Games.** Chess, Snake, Pokémon, StarCraft, Doom, a MuJoCo quadrotor, an NES controller. TypeSafe
  led with Doom and Wikiracing. These are the loudest and the least representative.
- **Agent plumbing.** Model routers, commit hooks, issue triage, log triage, semantic grep.
- **Judgement at volume.** 16 typed judgements as you type; 10,000 synthetic personas reacting to a
  post; 1,204 pages judged in under three minutes.

Reported mention counts by use case: **routing 604, classification 565, ranking and scoring 263.**

### 2.2 What is criticised

| Criticism | Attributed to | Reach |
|---|---|---|
| "a really smart switch statement" — the launch repackages existing classifier technology | @NathanFlurry | 590k views |
| "fast, inexpensive zero-shot classifiers have existed for years" | @alexisgallagher | — |
| the model "tend[s] to answer yes even to false propositions" | @mattn_jp | — |
| the game demos mainly reward low latency; the comparisons make the LLM write an explanation and then bill it for the tokens | various | — |
| no access — waitlist | 507 mentions, plus 363 "no access" | — |

And the one the aggregate analysis names as unresolved, in its own words: *"Does that score
correspond to the observed frequency of correct answers on your task?"*

### 2.3 What this changes about the pool

Four things, and they are the reason this section exists.

1. **The pool follows the evaluated use, not the viral one.** Games are where the demos are and
   classification, routing and output review are where the measurements are — TypeSafe's own evals
   page and every one of the six independent audits. A pool of chess positions would be about the
   demos; this one is about the thing people are shipping.
2. **"A smart switch statement" is a compliment the study takes seriously.** If Jev is a switch
   statement, then the question of whether the switch takes the same branch twice on the same input
   is not a small question about it. It is the whole question. The note should quote the criticism
   and agree with it.
3. **The open question on X is calibration, and this study does not answer it.** It cannot: there is
   no external ground truth in the design (study spec §7.10). The note has to say so early enough
   that nobody reads a flip rate as a calibration result.
4. **"Answers yes to false propositions" is a hazard for question design, not a hypothesis.** If the
   affirmative form of a question is answered high regardless, then the scores in the near-cut bands
   would be an artefact of phrasing. §5.3 answers it by using one fixed question shape per source and
   letting the *item* vary — never the polarity — and by requiring the builder to report the marginal
   distribution of `p_cal` per source so a phrasing artefact would be visible.

---

## 3. The finding that may stop the study before it starts

**Two independent audits say Jev returns probabilities quantised to 0.01.** jev-orderby-bench:
"Jev returns probabilities at two decimal places", 45 distinct values across 360 rows.
jev-ood-calibration: "Probabilities quantize to 0.01."

The study spec's §2.5 gate reads:

> "if the returned precision is two decimals or coarser, the study is not run as specified; an
> addendum is filed and the band definitions are reopened."

So the gate is not a remote possibility. **On the public evidence it is the expected outcome.**

### 3.1 What quantisation does to this design

Bands are half-open, per Taylor's ruling of 2026-09-22. At 0.01 resolution they contain:

| Stratum | Band | Attainable values | Count |
|---|---|---|---|
| S(0.50) | [0.45, 0.55) | 0.45 … 0.54 | **10** |
| S(0.60) | [0.55, 0.65) | 0.55 … 0.64 | **10** |
| S(0.90) | [0.85, 0.95] | 0.85 … 0.95 | **11** |

Three consequences, and they do not all point the same way.

**It does not make the study meaningless.** The event is `Action = 1 iff p ≥ c`, evaluated on the
value exactly as returned. With 0.01 resolution, a one-tick move at the boundary flips the branch.
That is a real flip in a real pipeline, not a rounding artefact of ours — the pipeline sees the same
quantised value we do. If anything, coarse resolution makes near-cut items *more* likely to flip, and
the study's estimand is unchanged.

**It does make ties at `p = c` common, and possibly dominant.** At cut 0.50 the value 0.50 is one of
ten attainable band values and is plausibly the modal one. The study already rules this: the
comparison is `p ≥ c` on the returned decimal with no rounding (§3 of the study spec), and the tie
count is reported per cut (§2.5 item 2). But a stratum that is 40% exact ties is a different object
from one that is 4% ties, and the note has to say which it got.

**It makes yield unpredictable.** Six or seven percent of candidates need to land in a ten-value
window. If the mass concentrates on 0.50 and 0.90 exactly, yield could be *higher* than estimated.
If it concentrates at 0.00, 0.01, 0.99 and 1.00 — which is what jev-certify's 56.4%-at-1.0 and
jev-ood-calibration's 1,051-of-2,000-at-zero suggest — it could be far lower.

### 3.2 What the pool builder does about it

**The contract check runs first and alone, before a single candidate call.** That is already the
study spec's sequencing (§2.2) and Taylor confirmed it on 2026-09-22. This document adds three
requirements to it:

1. Record the **raw response bytes** for every contract call, not the parsed float. Precision is a
   property of the bytes on the wire, and `json.loads` will happily turn `0.5` into `0.5` and hide
   whether the provider wrote two digits or seventeen.
2. Report the **set of distinct returned values** across the contract calls and the number of
   decimal digits in each, as strings.
3. State the verdict against the §2.5 gate explicitly: *two decimals or coarser — yes or no* — and
   stop if yes.

**If the gate fires, the pool builder stops and files.** It does not build the pool, it does not
adjust the bands, and it does not quietly proceed. The bands are reopened by an addendum to the study
spec, which is Taylor's call and not the building session's. The candidate pass is cheap to restart
and the freeze is not cheap to undo.

**Nothing else in this document changes either way.** The sources, the requests, the exclusions, the
ordering key, the quotas and the under-fill rule are all independent of the returned precision. If
the bands are widened by an addendum, this spec executes unchanged against the new bands.

---

## 4. Candidate datasets

### 4.1 The three adopted sources

| | **S1 Banking77** | **S2 CLINC150** | **S3 HelpSteer2** |
|---|---|---|---|
| **Jev use case** | Customer Service (evals); use-case #9 | Customer Service / scope gating; use-case #9 | Agent Trace Observability (evals); Universal Verification |
| **Repo** | `PolyAI/banking77` | `clinc/clinc_oos`, config `plus` | `nvidia/HelpSteer2` |
| **Licence** | **CC BY 4.0** | **CC BY 3.0** | **CC BY 4.0** |
| **Size** | 13,083 (10,003 + 3,080) | 15,250 / 3,100 / 5,500; 150 in-scope intents + `oos` | 21,362 |
| **Format** | `text`, `label` (0–76) | `text`, `label` (0–150) | `prompt`, `response`, five 0–4 human ratings |
| **Attribution** | Casanueva et al. 2020, arXiv:2003.04807 | Larson et al., EMNLP-IJCNLP 2019 | arXiv:2406.08673, arXiv:2410.01257 |
| **Row → request** | state = the message; question = "Should this message be routed to the queue that handles *&lt;label text&gt;*?" | state = the utterance + a committed scope paragraph; question = "Is this utterance within the assistant's stated scope?" | state = prompt + response; question = "Is this response ready to send to the user as it is?" |
| **Where near-cut mass should come from** | the **confusable sibling** variant: asking about the wrong-but-adjacent queue | the **1,000-odd human-written out-of-scope queries**, which are borderline by construction | **helpfulness 2 of 4** — the rating humans give when they could not decide |
| **Where high-band mass should come from** | the **gold-label** variant | clean in-scope utterances | **helpfulness 4 of 4** |
| **Used in a published Jev evaluation by someone else** | Yes — Janus, Jevals | Yes — jev-certify | Yes — Jevals |

The last row is not decoration. Each of the three has already been sent to `jev-1.13.0` by a third
party who published their code, which means the request shapes are known to work and the note is not
the first place anyone has seen these items in front of this model.

### 4.2 The one structural idea worth stating on its own

**Yield is bought with a source-side label, never with a Jev score.**

The trap in a near-cut design is obvious once named: the cheap way to fill narrow bands is to score
a big pool, look at what came back, and go find more of whatever landed in the middle. That is
choosing your items after seeing your scores, and it would void the study.

The way out is to pre-stratify the *candidates* on something the dataset already knows, before any
call. All three sources carry such a signal:

- Banking77's 77 intents contain confusable pairs. Asking "is this about *card arrival*?" of a
  message that is really about *card delivery estimate* is a genuinely hard question. Asking about
  the gold intent is an easy one. **The confusable pairing is computed from the published label
  names alone.**
- CLINC150 ships 1,000-odd out-of-scope queries **written by humans to sit at the edge** of a
  150-intent taxonomy. That is precisely a set of near-boundary items, and it was built that way for
  reasons that have nothing to do with Jev.
- HelpSteer2's helpfulness ratings are a 0–4 human consensus. A 2 is what people give a response
  they could not call good or bad.

None of that reads a model output. All of it is fixed in the declaration commit. This is what makes
the pool's near-cut yield defensible rather than fitted.

### 4.3 Risks, per source

**Licence.** All three CC BY. Attribution is discharged by a `SOURCES.md` in the corpus directory and
by the note's methods section. No source has a non-commercial or research-only restriction. Detail in
`log/jev-dataset-spec/licences.md`.

**Personal data.**

| Source | Card says | Real risk | Treatment |
|---|---|---|---|
| S1 | "no personal and sensitive information"; queries anonymised | Low. Short banking queries, pre-anonymised | Screen anyway; expect near-zero removals |
| S2 | "[More Information Needed]" — no statement either way | Low-moderate. Short synthetic-ish assistant utterances, but the card makes no promise | Screen; the screen does the work the card does not |
| S3 | nothing about the prompts themselves | **Real.** Prompts are "mostly user-contributed ShareGPT prompts" — things actual people pasted into a chat window, which is exactly where names, emails, keys and addresses turn up | Screen hard; **remove, never redact** (§5.5) |

This is the risk the brief flags — "support tickets often carry names and emails" — and it lands on
S3, not on the support datasets. Banking77 and CLINC150 are curated intent corpora, not scraped
tickets; that is part of why they were chosen over real ticket dumps (§4.4).

**Overlap with Jev's training data.** Banking77 and CLINC150 are famous benchmarks; HelpSteer2 is a
widely-used preference set. Assume all three are in the training mix.

Stated precisely, because it is the objection a reviewer will reach for first: **contamination cannot
manufacture flips.** A memorised item is one Jev is confident about, so it scores near 0 or 1, and
near 0 or 1 it never enters a stratum. Contamination's effect on this design is to **reduce yield**,
and yield is a cost line, not a result. The estimand is reproducibility of a decision, not accuracy,
so there is no accuracy number for contamination to inflate. What it *would* distort is a claim about
the items being "hard"; the note makes no such claim.

**Duplicates.** Banking77 has near-duplicate phrasings across its 77 intents by design. HelpSteer2
has multiple responses to the same prompt. Both are handled by §5.5's dedup, and the counts are
reported.

**Domain drift from real Jev use.** The honest version: Banking77 queries are one sentence long and
real support tickets are not; CLINC150 utterances are assistant commands, not tickets; HelpSteer2
responses are chat answers, not agent traces with tool calls. The pool is *shaped like* the workflows
TypeSafe shows and is not those workflows. The note says this in its own words rather than implying
the items are production traffic.

**Length.** S1 and S2 are far under any cap. S3 is not, and a 1,500-character cap (§5.5) excludes a
meaningful share of it and biases the S3 sub-pool toward shorter responses. Declared, counted,
reported, and driven by the token budget rather than by taste
(`log/jev-dataset-spec/budget.md`).

### 4.4 Alternatives considered and rejected

| Candidate | Why it was considered | Why it was rejected |
|---|---|---|
| **Civil Comments** (CC0, ~2M rows) | It carries a `toxicity` float that is *the fraction of human annotators who called the comment toxic*. That is the single best near-0.5 signal available in any public corpus, and moderation is use-case #14 | The content is abusive public comments, including identity attacks on real people. Sending it to a third-party processor and reprinting it in a lab note costs more than the yield is worth, and it would turn a note about reproducibility into a note about moderation. **Rejected on content, not on statistics** |
| **PubMedQA** (MIT, 1,000 labelled) | Its `maybe` class is genuine uncertainty by construction — near-0.5 items for free — and Jevals uses it | 1,000 rows total, of which the uncertain class is a small minority. It cannot carry a 300-item stratum, let alone a third of one. Scientific screening is also a minor Jev use |
| **Amazon ESCI** (Apache-2.0) | Four-level human relevance grades, and jev-orderby-bench has already run Jev on it | It is a **ranking** task. The study's event is a branch at a cut, not a sort. And the one published Jev result on it is that ordering by a Jev probability fails its own pre-registered gate (inversion 0.255 against a 0.15 bar) — so it would import a second, unrelated finding into the note |
| **20 Newsgroups** | Used by jev-orderby-bench; large; textual | **No explicit licence.** jev-orderby-bench's own note is that it is "conventionally redistributed", which is not a licence. Usenet posts also carry real names and period email addresses. Rejected twice over |
| **`deepset/prompt-injections`** (Apache-2.0) | Matches use-case #4 exactly; jev-sec-bench used exactly these 662 messages | 662 rows cannot carry a 300-item stratum, and the set is primarily German, which adds a language confound to a study that has nothing to say about language |
| **NSL-KDD** (used by the Jev IDS project) | Would cover Security Incidents | Tabular and numeric. The vendor's own jaggedness page says Jev "is not a calculator" and "cannot reliably judge whether two values are near each other". A near-cut study built on numeric comparison would measure a documented weakness, not reproducibility |
| **Real support-ticket dumps** (e.g. the Twitter customer-support corpus) | The most realistic possible match to "customer support" | Real handles, real names, unclear licence terms, and a live privacy exposure for third parties who never consented. The curated intent corpora are the defensible substitute |
| **Invoice / expense-claim templates** | Two of TypeSafe's own five shown workflows, and Taylor's ruling permits templates for a use case with no public source | **Recommended cut, not built.** See below |
| **Poisson's own τ² traces** | We hold 200 full-capture episodes with a non-judge truth; it is the closest thing to "Agent Trace Observability" anyone has | They are our data, not public, so a reader cannot check them. They also have zero public licence footing. HelpSteer2 gives the same *shape* of judgement with a licence and a link |

**On the template arm.** Invoice processing and expense claims have no public text-only labelled
source — jev-ood-calibration hit the same wall and wrote 900 tickets from 20 templates for exactly
that reason. Taylor's ruling permits a template fallback for such a use case, "labelled and analysed
separately." The recommendation here is to **cut both use cases rather than take the fallback**, for
one reason: with strata of 300 reported per cut and cross-cut comparison forbidden, a separately
analysed template sub-pool would have to be either large enough to carry its own interval — which
costs a fourth of the corpus and a fourth of the budget — or too small to say anything, in which case
it is a paragraph of apology in the note. The pool covers two of the five shown workflows properly
rather than four of them thinly. **If Taylor wants the template arm anyway, it is a separate
declaration and a separate 300, not a slice of these strata.**

---

## 5. The specification

Everything in this section is fixed **before any call**. The building session executes it; it does
not interpret it. Where it cannot proceed, it files and stops rather than choosing.

### 5.1 Sources, pinned

For each source the builder records, in `pool/SOURCES.md` and in the manifest:

| Field | Value |
|---|---|
| `source_id` | `S1`, `S2`, `S3` |
| `repo` | `PolyAI/banking77` · `clinc/clinc_oos` (config `plus`) · `nvidia/HelpSteer2` |
| `revision` | the **exact commit sha** of the dataset repo, resolved at download time and pinned thereafter |
| `files` | every file downloaded, with its **sha256** |
| `licence` | the licence string **as read from the card at that revision**, plus the URL and the date read |
| `citation` | the attribution required by CC BY |
| `row_count_raw` | rows before any exclusion |

Downloads are pinned by revision, never by a moving `main`. If a pinned revision cannot be resolved,
the builder stops and files; it does not fall back to the default branch.

**One known snag.** Banking77's dataset viewer was unavailable on 2026-09-22 (legacy script format).
The builder loads the parquet conversion or the raw files at the pinned revision and records which,
with the sha256. It does not substitute a mirror under a different repo name.

### 5.2 The request, exactly

One `noul` question per request. The body is:

```json
{"model":"jev-1.13.0","questions":{"q":{"type":"noul","instructions":"<question>"}},"state":{...}}
```

Serialised **canonically**, and the canonical bytes are the bytes POSTed:

```python
canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
```

`sort_keys=True` puts the top-level keys in the order `model`, `questions`, `state`, and orders the
state's keys too. `ensure_ascii=False` keeps non-ASCII characters as themselves. **The builder POSTs
`canonical` verbatim** — it does not re-serialise, and it does not let an SDK serialise for it.

> The probe script at `research/attachments/2026-09-20 jev_probe.py` does **not** do this: its
> `ask()` calls `json.dumps({...}).encode()` with defaults. It is not the harness and must not be
> copied into one. (It also retries five times on 429/529, which study spec §4.4 forbids.)

**The model pin `jev-1.13.0` is inside the hashed body.** The moving alias is forbidden and its
absence is checkable from the stored bytes.

### 5.3 What the question is, per source

One fixed question shape per source. The **item** varies; the polarity, the clause count and the
wording never do. All three are single-clause, affirmative, free of negation, numbers, dates and
references to anything outside the state — the five constraints §1.5 takes from the vendor's own
jaggedness page.

**S1 — Banking77**

```
state:    {"channel": "customer support chat", "message": "<row text>"}
question: "Should this message be routed to the queue that handles <label text>?"
```

`<label text>` comes from a committed `label_text.json`, built by one mechanical rule: **take the
Banking77 label name and replace underscores with spaces.** `card_arrival` → `card arrival`. No
rewriting, no judgement, 77 rows, committed in the declaration commit.

Which label is asked about is decided by a hash bit of the row, fixed before any call:

- `int(sha256(f"{source_id}:{row_id}".encode()).hexdigest(), 16) % 2 == 0` → the **sibling** label
- otherwise → the **gold** label

The sibling map is a committed `sibling_map.json` with all 77 rows, built by this rule: *the sibling
of intent `i` is the intent `j ≠ i` sharing the longest run of leading underscore-separated tokens
with `i`; ties broken by the lexicographically smallest `j`.* A hand-written map is permitted **only
if it is committed in the same declaration commit**, before any call.

**Each source row produces at most one request.** The parity bit chooses one variant; the other is
never sent. This keeps items independent, which the study's item-clustered bootstrap needs.

**S2 — CLINC150 (`plus`)**

```
state:    {"assistant_scope": "<committed scope paragraph>", "utterance": "<row text>"}
question: "Is this utterance within the assistant's stated scope?"
```

The scope paragraph is committed verbatim and is the same on every S2 request:

> `This assistant handles: banking, credit cards, kitchen and dining, home, auto and commute, travel, utility, work, small talk, and meta requests about the assistant itself.`

No variant. The expected height is driven by the gold label: `oos` rows should sit low-to-middle,
in-scope rows high.

**S3 — HelpSteer2**

```
state:    {"assistant_response": "<row response>", "user_request": "<row prompt>"}
question: "Is this response ready to send to the user as it is?"
```

No variant. The expected height is driven by the gold `helpfulness` rating.

**The question text is frozen by the declaration commit.** It is inside the hashed request body, so
changing a single character re-orders the entire pool and voids the freeze. That is the intended
property, not a side effect.

### 5.4 The ordering key — one hash, three jobs

```
request_hash = sha256(canonical).hexdigest()
```

over the exact bytes of §5.2. This single value is:

1. the **ordering key** for the candidate pass (Taylor's ruling, 2026-09-22: sha256 over canonical
   JSON of the full request);
2. the **item identifier** in the frozen corpus;
3. the **request-identity digest** of study spec §4.4's pair assertion.

They are the same value because they are the same bytes. The consequence worth stating: **the
calibration request and each measurement-arm request are byte-identical**, so the pair assertion is
already satisfied by construction for the body, and any later edit to a question, a state key or the
model pin is detectable as a changed corpus id rather than as a silent substitution.

### 5.5 Exclusions

Applied **in this order**, to the raw rows, before any request is built or any call is made. Every
step reports a count per source.

1. **Field presence.** Drop rows with a missing or empty required field.
2. **Language.** Keep rows detected as English at confidence ≥ 0.90 by `py3langid`, version pinned in
   the declaration commit. Applies to all three sources; it will bite only S3.
3. **Length.** Keep rows whose assembled state text is **≥ 20 and ≤ 1,500 characters**. Text is
   **never truncated** — a truncated item is a different item, and a pair assertion over a truncated
   state is not an assertion about the state. Over-length rows are excluded and counted.
4. **Personal-data screen.** Drop — not redact — any row matching any pattern in the committed
   `pii_patterns.json`: email addresses; international and NANP phone numbers; IBANs; 13–19 digit
   runs passing a Luhn check; US SSN-shaped strings; street addresses matching the committed
   pattern; URLs carrying a user path segment; `@handle` mentions; API-key-shaped tokens
   (`sk-`, `ghp_`, `AKIA`, and the rest of the committed list); and any run of ≥ 30 base64-ish
   characters. **Removal, not redaction**, because redaction rewrites the item and would put a
   synthetic artefact inside the state.
   Reported as a table: source × pattern × rows removed.
5. **Exact dedup.** Normalise for comparison only (NFC, collapse internal whitespace, casefold) and
   drop all but one member of each identical-text group. The survivor is the one with the smallest
   `request_hash`. Counted.
6. **Near dedup.** Within and across sources, 5-gram Jaccard ≥ 0.90 on the normalised text. The
   survivor is the one with the smallest `request_hash`. Counted, with the number of clusters and the
   size of the largest.
7. **Source composition.** S2 splits into two lists, `oos` and in-scope. S3 splits into four lists by
   `helpfulness ∈ {1,2,3,4}`; rating 0 is dropped as a separate counted exclusion. S1 is one list.

The screen and the dedup are code in the declaration commit. **No exclusion may depend on anything
returned by Jev.**

### 5.6 Sampling — deterministic, and executable as written

**Step 1. Order.** Within each list of §5.5 step 7, sort ascending by `request_hash` as a lowercase
hex string. This order is fixed the moment the declaration commit is signed.

**Step 2. Ranges.** Three ranges, declared now, taken in order. Range sizes per list:

| | S1 (1 list) | S2 (2 lists) | S3 (4 lists) | calls |
|---|---|---|---|---|
| **Range 1** | first 900 | first 450 each | first 225 each | **2,700** |
| **Range 2** | next 400 | next 200 each | next 100 each | **1,200** |
| **Range 3** | next 200 | next 100 each | next 50 each | **600** |
| **Ceiling** | 1,500 | 1,500 | 1,500 | **4,500** |

**Before the first call** the builder verifies that each list is long enough to supply its full
ceiling — in particular that S2 has ≥ 750 surviving `oos` rows and that each S3 helpfulness bucket
has ≥ 375 — and reports the realized list lengths. A short list is an under-fill condition (§5.8),
declared in advance rather than discovered at range 3.

**Step 3. Call.** Range 1 is called in full, in the global order defined as *(range, then
`request_hash` ascending across all sources)*. Then Range 2 if needed, then Range 3.

**Step 4. Place.** Walking that same global order, each response is placed by this rule and no other:

```
p = the returned value, parsed as a decimal from the response bytes, unrounded, unrescaled
band(p):  [0.45,0.55) -> S(0.50);  [0.55,0.65) -> S(0.60);  [0.85,0.95] -> S(0.90);  else none
place if: band(p) is not none
      and stratum is open (count < 300)
      and this source's count in that stratum < 120
```

The bands are **half-open**, per Taylor's ruling of 2026-09-22. They do not overlap, so the study
spec's lower-cut tie-breaker is unreachable and is retained only as a statement that the assignment
is not a judgement call. **This supersedes `log/jev-calibration/audit_protocol.md` §2**, which still
writes the bands closed.

A stratum closes at exactly 300 and nothing is added or swapped afterwards.

**Step 5. Stop.** The pass halts on the first of: all three strata full; 4,500 calls; 2,444,000
calibration input tokens; ranges exhausted.

### 5.7 Quotas and balance

**Per-source cap: 120 items per stratum.** Three sources × 120 = 360 ≥ 300, so a full stratum is
reachable whenever roughly two and a half sources deliver, and no single source can exceed 40% of a
cut.

**There is no per-source minimum, and that is deliberate.** Enforcing a floor would mean going back
to a source after seeing which sources were yielding — a decision taken on scores. The realized
per-source counts are reported per stratum instead, and the note prints them. If a cut ends up 120 /
120 / 60, the reader is told so.

Per-source flip counts may be reported **descriptively** in the note. They are not a comparison, they
carry no interval, and no claim is made that one source flips more than another — the same discipline
study spec §2.4 imposes across cuts, for the same reason.

### 5.8 The under-fill rule

Declared here, before any call. It is the answer to "what if a band comes up short", and it is fixed
so that it can never be chosen after a score is seen.

1. **Extend within the same sources, over the pre-declared next range.** Range 1 → Range 2 → Range 3,
   same sources, same revisions, same questions, same exclusions, same order. Nothing else changes.
2. **Never add a source, never change a question, never widen a band, never re-run an item.** If a
   stratum is short after Range 3 or after a budget stop, the extension is over.
3. **Then the study spec's own fallback fires:** 300 at the 0.50 stratum, 100 each at 0.60 and 0.90,
   filed as a §12 addendum before any measurement call. Study spec §2.4's ban on cross-cut comparison
   makes the unequal *n* harmless; §2.3's power and precision are recomputed at the realized *n*.
4. **If the 0.50 stratum itself cannot reach 300, the study does not proceed** on this pool. The
   shortfall is filed and the pool plan comes back to Taylor.
5. **The pool is never rebuilt in place.** If anything in §5.1–§5.6 has to change, the pool is voided
   and rebuilt from a new declaration commit, with the old pass's manifest kept as the record of what
   was abandoned and why. A second declaration commit is a visible event, which is the point.

### 5.9 What is recorded, per item

`pool/manifest_calibration.jsonl` — one line per **candidate called**, not merely per item kept:

| Field | Meaning |
|---|---|
| `source_id` | `S1` / `S2` / `S3` |
| `source_revision` | the pinned dataset commit sha |
| `source_row_id` | `<split>:<index>` plus the dataset's own id where it has one |
| `variant` | `sibling` / `gold` for S1; `null` for S2 and S3 |
| `gold_label` | the source-side label used for composition (`oos`, the helpfulness rating, the intent) |
| `template_id` | **`null` for every item in this pool.** The field exists so that a future template arm is visibly distinct, and so that "no templates were used" is checkable rather than asserted |
| `question_id` | the literal key `q` |
| `question_sha256` | sha256 of the question `instructions` string |
| `state_sha256` | sha256 of the canonical state object |
| `request_hash` | sha256 of the canonical request bytes — the ordering key and the item id |
| `range` | 1, 2 or 3 |
| `order_index` | position in the global call order |
| `p_cal_raw` | the returned value **as a string, exactly as it appeared in the response bytes** |
| `p_cal` | the same value parsed as a decimal |
| `response_sha256` | sha256 of the raw response bytes |
| `stratum` | `0.50` / `0.60` / `0.90` / `null` |
| `fill_index` | 0–299 within the stratum, or `null` |
| `not_placed_reason` | `out_of_band` / `stratum_full` / `source_cap` / `null` |
| `input_tokens`, `output_tokens` | from `usage` |
| `latency_s` | round-trip seconds |
| `http_status`, `error` | recorded; an errored candidate is **not** retried |

`pool/exclusions.json` — every exclusion count from §5.5, by source and by rule.

`pool/corpus_jev_900.json` — the frozen corpus: for each item, `request_hash`, the canonical request
bytes (base64), `source_id`, `source_row_id`, `stratum`, `fill_index`. **The bytes the measurement
sweeps send are read from this file**, not rebuilt from the source.

`pool/DIGESTS.txt` — sha256 of `corpus_jev_900.json`, of `manifest_calibration.jsonl`, of
`exclusions.json`, and of every committed declaration file.

---

## 6. Acceptance checklist

Two gates. **Gate A closes before the first candidate call.** **Gate B closes before the first
measurement call.** Every item names the evidence that settles it, and every piece of that evidence
lives in the building session's report at
`data/pool/` or in the pool directory it commits.

A gate item that cannot be shown is not waived by argument. The session stops and files.

### Gate A — before any candidate call

| # | Item | Evidence in the report |
|---|---|---|
| **A1** | **Licence recorded per source**, read at the pinned revision, with the URL and the date | `pool/SOURCES.md`: three rows, each with licence string, URL, date read, and the CC BY attribution |
| **A2** | **Sources pinned**: dataset repo commit sha and sha256 of every downloaded file | `pool/SOURCES.md` and `pool/DIGESTS.txt`. A moving `main` anywhere fails the gate |
| **A3** | **Declaration commit exists and is signed** (`taylor@poissonlabs.ai`), and contains: the generator code, the three question strings, `label_text.json` (77 rows), `sibling_map.json` (77 rows), the scope paragraph verbatim, `pii_patterns.json`, the pinned `py3langid` version, the range table, the band definitions, the per-source cap, and the under-fill rule | commit sha named in the report; `git verify-commit` output pasted; `git show --stat` listing the files |
| **A4** | **Personal-data screen run, with counts removed** | a table: source × pattern × rows removed, plus the total per source. Zero rows removed is a reportable result, not a skipped step |
| **A5** | **Dedup counts** | exact-dedup rows dropped per source; near-dedup clusters, rows dropped, and the largest cluster size, within and across sources |
| **A6** | **Every other exclusion counted** | language, length (with the over-length count called out separately), missing fields, helpfulness-0 rows. Row counts reconcile: `raw − excluded = eligible`, arithmetic shown |
| **A7** | **Every list is long enough for its ceiling**, or the shortfall is declared now | realized list lengths: S1 ≥ 1,500; S2 `oos` ≥ 750 and in-scope ≥ 750; each S3 helpfulness bucket ≥ 375. A short list is filed as a pre-declared under-fill condition, not discovered later |
| **A8** | **The sampling rule is reproducible from the committed code** | a dry run over the eligible frame, making no calls, printing the first 20 `request_hash` values of each list and the sha256 of the full ordered hash list per list. A second independent run reproduces both exactly |
| **A9** | **The under-fill rule is committed**, verbatim as §5.8 | quoted in the report with the commit sha it lives in |
| **A10** | **No templates.** `template_id` is `null` for every candidate and no template or generator-of-items file is in the commit | the dry-run output showing `template_id: null` across all rows; `git show --stat` showing no such file |
| **A11** | **Contract check complete and its gate answered** | raw response bytes for every contract call; the set of distinct returned values as strings with digit counts; an explicit verdict: *two decimals or coarser — yes / no*. **A "yes" stops the pass here** (§3.2) |
| **A12** | **Token budget re-estimated from real numbers** | mean `usage.input_tokens` from the contract calls, per source shape; projected calibration and measurement totals; both under the ceilings in `log/jev-dataset-spec/budget.md` |
| **A13** | **The invariant is stated that no Jev score has been or will be read before the freeze**, and the mechanism that makes it checkable is in place | the report states that the declaration commit precedes the first candidate call, and names where the timestamps will be compared at Gate B (B1) |

### Gate B — before any measurement call

| # | Item | Evidence in the report |
|---|---|---|
| **B1** | **No score was read before the freeze.** The signed declaration commit's timestamp precedes the first response timestamp in the manifest | both timestamps quoted side by side, with `git log --format=%aI` for the commit and the first `manifest_calibration.jsonl` line |
| **B2** | **The generator contains no score-dependent branch** other than the band test | the reviewer names file and line of the single comparison against `p_cal`, and states that no other line reads it except to record it |
| **B3** | **Per-source counts, per stratum**, all ≤ 120 | a 3 × 3 table, source × stratum, with row and column totals |
| **B4** | **Realized *n* per stratum is 300**, or the under-fill rule fired and is filed as a study-spec §12 addendum before any measurement call | the counts, and the addendum's text and commit if it fired |
| **B5** | **Tie count at `p = c`, per stratum** | the count and the share. This is the number that says whether the strata are mostly exact ties (§3.1) |
| **B6** | **Distribution of `p_cal` per stratum**, as a value-count table over the attainable values | one table per stratum. Quantisation, ties and any clumping are visible rather than argued about |
| **B7** | **The pool is frozen, hashed, committed and signed** | `pool/DIGESTS.txt` with the sha256 of `corpus_jev_900.json`, the commit sha, and `git verify-commit` output. The commit is made **before** the first measurement call and its timestamp shows it |
| **B8** | **Spend and tokens**, against the sub-cap | calibration `input_tokens` total, call count, and the margin remaining against the 6 MTok study cap with the measurement sweeps costed in |
| **B9** | **The manifest is complete and no call was retried** | one line per call including errors; error counts by cause; a statement that retries were zero, with the harness line that sets it |
| **B10** | **Attribution is discharged** | `pool/SOURCES.md` present in the corpus directory, and the three citations ready for the note's methods section |

---

## 7. Objections, and where the spec answers them

Written as a sceptical reader would put them, not as strawmen.

**"You chose items that were about to flip. Of course they flip."**
Yes — and it is pre-registered, not discovered. An item far from a cut cannot flip at all, so a pool
of easy items would answer the question trivially and wrongly. Every rate the study reports is
*conditional on near-cut items*, and that conditioning is in the study spec's scope section, its
withdrawals, and verbatim in all three outcome sentences. What the design cannot do — and does not
claim — is estimate the flip rate on ordinary traffic. §4.2 here is the part that makes the selection
honest: the near-cut *candidates* are found with a source-side label, never with a Jev score.

**"You wrote the items yourselves, so you wrote the result."**
We did not. Three public datasets, CC BY, pinned by commit sha, `template_id` null on every row, and
no template file in the declaration commit (A10). Each of the three has already been sent to
`jev-1.13.0` by a third party who published their code.

**"Those datasets are in Jev's training data."**
Assume so. It reduces yield and cannot manufacture flips: a memorised item is one the model is
confident about, so it scores near 0 or 1 and never enters a stratum. Contamination would inflate an
accuracy number and this study reports none (study spec §7.10). §4.3 states the one thing it does
bear on — a claim that the items are "hard", which the note does not make.

**"You picked the bands after you saw the scores."**
Checkable, not assertable. The bands, the questions, the exclusions, the ordering and the ranges are
in a signed commit whose timestamp precedes the first response in the manifest (B1), the ordering is
a hash of the request bytes (§5.4), and the committed generator contains exactly one comparison
against a returned value — the band test — with a reviewer naming its line (B2).

**"Selecting on a single noisy calibration draw is regression to the mean."**
A real objection, and the honest answer is that it is true. The calibration value is one draw of the
same request the measurement arms will send. Items selected because that one draw landed in
`[0.45, 0.55)` will, on average, sit further from the cut in the arms than in the calibration pass.
Three things contain it. The estimand is defined as conditional on the *selection procedure*, which
is pre-registered here in full, not on the arms' own values. The note reports the arm-A distribution
of `p` within each stratum, so the spread is visible rather than assumed away. And the direction is
conservative for the headline: regression away from the cut makes flips *less* likely, so a measured
flip rate is if anything an understatement of the rate on items truly at the boundary.

**"Jev returns two decimal places, so you are measuring rounding."**
This is the strongest objection and §3 is written for it. Two independent audits say 0.01 resolution.
The study spec already gates on it, the contract check runs first and alone, and a "two decimals or
coarser" verdict stops the pass (A11) rather than being worked around. On the substance: the
threshold comparison is made on the value exactly as returned, so a one-tick move at a boundary is a
real branch change in a real pipeline, which sees the same quantised value. The rounding would only
be ours if we rounded, and we do not (study spec §3).

**"Half your items will sit exactly on the cut."**
Possibly. The rule is `p ≥ c` on the returned decimal, declared in advance, and the tie count and the
full value distribution are reported per stratum (B5, B6). A stratum that is 40% exact ties is a
different object from one that is 4%, and the reader is told which one they got.

**"Banking chat and ShareGPT answers are not how anyone uses Jev."**
They are the public stand-ins for two of the five workflows TypeSafe itself put on its evaluation
page, and §1.2 maps each one. §4.3 states the drift plainly instead of implying otherwise: the
messages are shorter than real tickets, the utterances are commands rather than tickets, and the
responses are chat answers rather than agent traces with tool calls.

**"Support tickets carry names and emails."**
They do, and the exposure is on HelpSteer2, whose prompts are "mostly user-contributed ShareGPT
prompts" — things real people pasted into a chat window. §5.5 step 4 screens for emails, phone
numbers, IBANs, Luhn-valid card runs, SSN shapes, addresses, handles, key-shaped tokens and long
base64 runs, and **removes rather than redacts**, because redaction rewrites the item. Counts are
reported by source and by pattern (A4). Real scraped ticket dumps were rejected outright (§4.4).

**"The licences do not let you send this to a third party or print it."**
All three are CC BY — 4.0, 3.0, 4.0 — which permits transmission, publication and derivative use with
attribution. TypeSafe's MCA carries no benchmarking or publication clause and its §4.1 says it will
not train on customer data without consent (read 2026-09-22, MCA last updated 2026-09-19, summariser
read — study spec §7.11 still requires the first-hand re-read before publication). The one residual
is that HelpSteer2's licence covers the set as NVIDIA published it and does not warrant that every
ShareGPT prompt inside it was the submitter's to license; that is general to ShareGPT-derived corpora
and is part of why the screen removes rather than redacts.

**"One dataset will carry the whole result."**
Capped at 120 of 300 per stratum (§5.7), with the realized per-source counts reported per cut (B3). No
minimum is enforced, because a floor would mean returning to a source after seeing which sources were
yielding. If a cut ends up 120/120/60, the note says so.

**"Duplicates inflate your n."**
Exact dedup and 5-gram Jaccard near-dedup at 0.90, within and across sources, survivor chosen by
smallest hash, with cluster counts and the largest cluster reported (A5). It matters here more than
usual: Banking77 has near-duplicate phrasings by design and HelpSteer2 has multiple responses per
prompt.

**"A cache hit would make everything look stable."**
True, unfixable at the client boundary, and already withdrawn in study spec §7.5 — the measured rate
is a lower bound on the flip rate of an uncached replay. The pool neither helps nor hurts this.
Worth pairing with the vendor's own cookbook, which varies a throwaway `uid` between repeats and
admits it "cannot separate sensitivity to the irrelevant field from variation that would occur on
identical requests."

**"Someone already showed Jev is nondeterministic. What is new?"**
They did: `jev-calibration-audit` reports 50 identical requests giving 15 distinct answers. The note
must cite it. What is new is not the existence of variation but its consequence at a shipped
threshold — a branch-flip rate per cut, with an item-clustered interval, from a pool fixed before any
score was seen, computed by an instrument whose pairing predicate refuses to run if the two arms were
not the same request. "15 distinct answers" is a fact about values. This is a fact about decisions.

**"It is a really smart switch statement."**
The most-viewed criticism of the launch, at 590k views, and the study agrees with it. If Jev is a
switch statement, then whether it takes the same branch twice on the same input is not a minor
question about it — it is the question. The note should quote the line.

**"This is a Prove advertisement."**
Study spec §10 holds the line: Prove is named exactly once in the whole post, in "What we ran", with
no call to action, no waitlist link, no GitHub link and no slogan, and it is kept out of the title.
Nothing in this document changes that.

---

## 8. What is owed

**To Taylor — one yes/no.**

> **Approve this dataset spec so the pool-building session can execute it?**
> Yes means: Banking77, CLINC150 and HelpSteer2 as the three sources; no template arm and the invoice
> and expense-claim use cases cut; the questions, exclusions, hash ordering, 120-per-stratum cap,
> three declared ranges and the under-fill rule as written; the 4,500-call / 2.44 MTok calibration
> ceiling; and Gate A as the bar the building session has to clear before its first candidate call.

**Noted for whoever owns them, not asked here.**

- `log/jev-calibration/audit_protocol.md` §2 still writes the bands closed with a lower-cut tie rule.
  Taylor ruled half-open on 2026-09-22. §5.6 of this document supersedes it; the file itself belongs
  to the calibration session and was not edited.
- `log/jev-calibration/README.md` carries `$0.042 / MTok input` as a fact. It is a vendor docs figure,
  and study spec §6 deliberately removed price from the pre-registration. Read the pre-flight's
  dollar estimate as an order-of-magnitude check, not as a pre-registered quantity.
- The pre-flight's upper estimate of 5,000 candidate calls does not leave real margin under the
  6 MTok study cap once the measurement sweeps are costed. 4,500 does
  (`log/jev-dataset-spec/budget.md`).
- `research/attachments/2026-09-20 jev_probe.py` retries five times on 429/529 and serialises with
  `json.dumps` defaults. Study spec §4.4 forbids retries and §5.2 here requires canonical bytes on
  the wire. It is a probe, not a harness, and must not be copied into `jev_harness.py`.

---

## 9. Change log

**2026-09-22, written.** First version. Serves [2026-09-21 Jev Prove Study Spec](2026-09-21-jev-prove-study-spec.md) §2.2's candidate
pool and closes the calibration session's Ambiguity 1 (candidate pool source) with public datasets
rather than templates, on Taylor's ruling of 2026-09-22. Ambiguities 2, 3 and 4 were ruled the same
day and are written in here: half-open bands (§5.6), contract check first as a gate (§3.2, A11), and
sha256 over canonical JSON of the full request as the ordering key (§5.4).

Three things this document adds that the rulings did not ask for, each because the research turned
them up:

1. **§3, the quantisation gate.** Two independent public audits report 0.01 resolution, which is the
   condition study spec §2.5 gates on. It is now the first thing the building session resolves, with
   raw response bytes rather than parsed floats as the evidence.
2. **§4.2, source-side stratification.** Near-cut yield is bought with labels the datasets already
   carry — confusable intent siblings, human-written out-of-scope queries, middle helpfulness
   ratings — so that yield never becomes a reason to look at a score.
3. **§4.4, cutting the template arm.** Invoice processing and expense claims have no public source
   and would be the case for templates. Recommended cut rather than built, because a separately
   analysed sub-pool is either a quarter of the corpus or a paragraph of apology.
