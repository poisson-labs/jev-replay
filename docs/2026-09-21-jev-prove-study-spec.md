---
title: "2026-09-21 Jev Prove Study Spec"
type: pre-registration
substrate: jev-1.13.0
instrument: Prove (proofload CLI)
status: measurement sweeps S1-S3 complete; pre-registered analysis generated through Prove (addendum 6: k = 5, corpus 847, all windows held)
written: 2026-09-21
revised: 2026-09-22
bar: 45.0% and 44.0% lab note
projects: [proofload]
tags: [jev, prove, proofload, pre-registration, paired-study, decision-model, reproducibility, mcnemar]
---

# 2026-09-21 Jev Prove Study Spec

> **Pre-registration freeze.** This specification defines a paired study measuring TypeSafe's Jev (`jev-1.13.0`) using Poisson Prove (`proofload`). It ends in a lab note held to the exact standard of the [45.0% and 44.0% note](https://poissonlabs.ai/research/45-percent-and-44-percent/).
>
> **Role separation.** Jev is the result under test and Prove is the neutral statistical counter. This is not a Jev review, not an agent benchmark, and not a Prove product launch.
>
> **Frozen before any run.** Every cut, item count, schema definition, salt, test statistic, cluster unit, alpha, reportable floor and every outcome headline sentence is fixed in this document prior to issuing any live API call or spending any provider budget. Amendments, if any, are dated addenda under §12, never edits to the pre-registered body.
>
> **One open ruling.** §13 carries one yes/no question for Taylor. The study is executable either way; a yes changes only the per-cut item count.

---

## 0. Question and Scope

### Question
**Does a replay change Jev's action at a cut people ship?**

Automated decision pipelines deploy decision models behind sharp decision boundaries: if the model's assessed probability clears threshold $c$, take the action (e.g., approve claim, escalate ticket, route dispatch); otherwise, do not. When the exact same state and question are evaluated twice under identical parameters, does the resulting binary action reproduce, or does model variance flip the branch?

### Scope
- **Model pin:** `jev-1.13.0` explicitly pinned on every request. The moving alias `jev-latest` is forbidden.
- **Item set:** Three declared, frozen strata of 300 text items each, one stratum per cut, $N = 900$ in total. There is **no joint mid-mass corpus**: each stratum is calibrated to its own cut's band and is analysed only at that cut (§2.2).
- **Near-cut selection:** Items are chosen *because* their calibration probability sits near a cut. Every rate reported by this study is therefore **conditional on near-cut items** and is expected to run higher than the same rate on production traffic, where most items sit far from any threshold. This conditioning is load-bearing and is restated in §2.4, §7.4 and every outcome sentence in §8.
- **Execution window:** Three declared 20-minute operational windows, one per replicate paired sweep (§4.1). Not one window for all three.
- **Reporting unit:** Every statistic, every interval and every outcome sentence is reported **per cut**. Nothing in this study is pooled across cuts.

### Non-Generalization Clause
**Nothing generalizes beyond this scope.** This study measures `jev-1.13.0`, on these three declared near-cut strata, inside these execution windows. It makes no claim about:
- other model versions, checkpoints, or future updates from the vendor;
- prompt formats or task domains outside the declared item set;
- items whose probability does not sit near a cut, which is most production traffic;
- operational stability across hours, days, or weeks.

---

## 1. Pre-Registration Freeze

The following parameters are frozen before the study begins:

| Parameter | Value | Definition |
|---|---|---|
| **Model** | `jev-1.13.0` | Exact version string in POST `/v1/systemone` payload |
| **Cuts ($c$)** | `0.50`, `0.60`, `0.90` | Binary operational action boundaries ($p \ge c \implies \text{action}$) |
| **Question Schema** | `noul` | Direct proposition evaluating continuous probability $p \in [0, 1]$ |
| **Item Corpus ($N$)** | 3 strata × 300 items = 900 | Stratified, one stratum per cut, each calibrated to its own band (§2.2) |
| **Stratum analysed at** | its own cut only | An item in the 0.50 stratum is never thresholded at 0.60 or 0.90 (§2.4) |
| **Salts** | `S1`, `S2`, `S3` | Three 64-bit hex salts fixed in §4.2; their only function is to make pairing assertable |
| **Replicate sweeps** | 3 paired sweeps | One per salt, each in its own 20-minute window |
| **Cluster unit** | **item** | 300 item clusters per cut, each carrying its 3 replicate pairs (§5.3) |
| **Interval method** | percentile cluster bootstrap, $B = 10{,}000$, seed `20260921` | Resamples whole items with replacement, on the **paired** flip indicator (§5.3) |
| **Test** | McNemar's exact, two-sided, $\alpha = 0.05$ | Tests arm-order asymmetry, not flip prevalence (§2.3) |
| **Reportable floor $\delta^{*}$** | `0.01` | The smallest flip rate this study will call consequential (§2.3, §5.4) |
| **Capture cap** | `[capture].max_observation_bytes = "none"` | Required field, no default; `"none"` keeps request and response bytes whole (§4.4) |
| **Retries** | zero | An errored or retried call makes its pair ineligible (§4.4) |
| **Token cap** | 6 MTok input across the whole study | Hard stop; price-free so it is exactly pre-registrable (§6) |
| **Headline Sentences** | A, B and C | Pre-written verbatim in §8 |

---

## 2. Items and Schema

### 2.1 Schema Selection: Noul (Justified)
Jev exposes two candidate structured question types: `choice` and `noul`. This study specifies **`noul`** exclusively.

**Justification:**
1. **Direct scalar semantics:** `noul` evaluates a proposition against a provided `state` and returns a single continuous scalar $p \in [0, 1]$. Production systems using decision models place action thresholds directly on this probability ($p \ge c$).
2. **Absence of option-order confounding:** A `choice` schema returns a probability distribution across a set of discrete options. The vendor's own limitations page disclaims structural invariants, and `choice` distributions are therefore open to option-order sensitivity on identical states. `noul` has no option keys or option ordering, so no option permutation artifact can exist. *(Order sensitivity on `choice` has not been measured first-hand — the probe that would measure it, `p4`, was never run. The justification here rests on `noul` having no ordering to be sensitive to, which is structural, not on a measurement of `choice`.)*
3. **No confidence ambiguity:** The vendor documentation defines `confidence` for `choice` as an algebraic rescaling of maximum probability: $(k \cdot p_{\max} - 1)/(k - 1)$. It is not an independent signal. `noul` returns no confidence at all, so there is no secondary rescaling to reason about.

### 2.2 Stratified Near-Cut Calibration

A cut cannot flip on an item whose probability mass is far from the threshold. If all items in a test set evaluate to $p = 0.02$ or $p = 0.98$, small run-to-run variations of $\pm 0.03$ will never cross $c \in \{0.50, 0.60, 0.90\}$. The action would reproduce trivially ($0 \to 0$ or $1 \to 1$), yielding zero flips and hiding genuine threshold instability.

**Taylor's ruling, 2026-09-21.** The items are **stratified, one stratum per cut**, each stratum calibrated to its own band. There is **no joint mid-mass corpus**. Every stat, interval and outcome sentence is reported per cut.

**Taylor's ruling, 2026-09-21, later (§13, closed).** The per-cut $n$ is **300**, not 100: $N = 900$ items, 5,400 measurement calls. Filed as addendum 1 under §12. Every $n$ in this document is the ruled one; §2.3's power and precision are recomputed at it.

**Calibration criteria:**
- Items are drawn from a separate candidate pool of textual decision states (customer support triage, risk assessment, and policy routing propositions).
- In a preliminary calibration pass, candidate items are evaluated once against `jev-1.13.0`.
- Each stratum takes the items whose calibration probability $p_{\text{cal}}$ falls into the narrow band centred on that stratum's own cut:

| Stratum | Cut $c$ | Band on $p_{\text{cal}}$ | $n$ | Analysed at |
|---|---|---|---|---|
| $\mathcal{S}_{0.50}$ | 0.50 | $[0.45, 0.55]$ | 300 | 0.50 only |
| $\mathcal{S}_{0.60}$ | 0.60 | $[0.55, 0.65]$ | 300 | 0.60 only |
| $\mathcal{S}_{0.90}$ | 0.90 | $[0.85, 0.95]$ | 300 | 0.90 only |

- **Total corpus:** $N = 900$ items, as three disjoint strata. An item appears in exactly one stratum. If a candidate qualifies for two bands (impossible as declared — the bands do not overlap) it would be assigned to the lower cut; the rule is stated so the assignment is not a judgement call at fill time.
- **Fill order is declared before the calibration pass:** candidates are ordered by a fixed hash of their text, and each stratum takes the first 300 qualifying items in that order. No stratum is hand-picked, and no item is swapped after a stratum closes.
- **If a stratum cannot be filled to 300** from the candidate pool, the run does not proceed with a short stratum. The shortfall and the realized $n$ are filed as a §12 addendum before any measurement call, and the power statement in §2.3 is recomputed at the realized $n$.

**Reporting boundary:**
The calibration pass is an item **selection filter**, and its probabilities, candidate-pool size and per-band yield are **not reported as results** in the lab note. The *procedure* is reported, because it is what makes every rate in the note conditional (§2.4). The lab note begins from the frozen 900-item corpus and states plainly how that corpus was chosen.

**Sequencing.** Freeze (this document) → contract check (§2.5) → calibration pass → corpus frozen and its digest filed → three measurement sweeps. The contract check and the calibration pass incur provider spend; the measurement sweeps may not begin until the corpus digest is filed.

### 2.3 Power, under the alternative, for the paired design

The current design's own arithmetic is stated here rather than a null-hypothesis illustration. Two quantities have to be kept apart, and the previous version of this section conflated them.

**What McNemar tests, and what it does not.** McNemar's exact test evaluates marginal symmetry, $H_0: P(1\to0) = P(0\to1)$. It is a test of whether the flips are **lopsided**, not of whether there are any. In a replay design Arm $A$ and Arm $A'$ are exchangeable by construction, so McNemar's null is *expected to be true* however large the flip rate is: a process that flips 20% of items evenly in both directions produces $p \approx 1$. McNemar therefore has **no power at all against the symmetric flip process this study expects**, and it cannot be the test that establishes reproducibility or its absence. Its job here is narrower and real: Arm $A$ runs before Arm $A'$, so any provider-side drift across the window is confounded with arm, and McNemar is the check on that drift (§7.6). This is the same role it played in the 45/44 note, where $p = 0.880$ and the flips cancelled.

**The hard floor.** A two-sided exact binomial on $n_d = n_{10} + n_{01}$ discordant pairs cannot reach $p \le 0.05$ at all unless $n_d \ge 6$: the most lopsided possible split gives $p = 2 \cdot (1/2)^{n_d}$, which is $0.0625$ at $n_d = 5$ and $0.03125$ at $n_d = 6$. Below six discordant pairs McNemar cannot reject whatever the data look like.

**Power of McNemar's exact test at $n = 300$ per cut, $\alpha = 0.05$ two-sided.** Let $\delta = \pi_{10} + \pi_{01}$ be the flip rate and $\psi = \pi_{10}/\delta$ the share of flips in one direction ($\psi = 0.5$ is exact symmetry, $\psi = 1.0$ is every flip in the same direction).

| $\delta$ | $\psi = 1.0$ | $\psi = 0.9$ | $\psi = 0.8$ | $\psi = 0.75$ | $\psi = 0.7$ | $\psi = 0.6$ |
|---|---|---|---|---|---|---|
| 0.02 | 0.556 | 0.313 | 0.152 | 0.100 | 0.063 | 0.023 |
| 0.05 | 0.998 | 0.882 | 0.577 | 0.404 | 0.256 | 0.076 |
| 0.10 | 1.000 | 0.997 | 0.901 | 0.744 | 0.524 | 0.143 |
| 0.20 | 1.000 | 1.000 | 0.998 | 0.974 | 0.860 | 0.298 |
| 0.50 | 1.000 | 1.000 | 1.000 | 1.000 | 0.999 | 0.663 |

*(The same computation at $n = 100$, which the 2026-09-21 review ran and §13 was asked about, gave 0.015 / 0.384 / 0.942 / 1.000 / 1.000 down the $\psi = 1.0$ column. It is kept here only as the comparison the ruling was made on.)*

**Minimum detectable discordance rate at 80% power, $n = 300$ per cut:** $\delta = 0.030$ when every flip runs one way ($\psi = 1.0$), $0.045$ at $\psi = 0.9$, $0.080$ at $\psi = 0.8$, $0.115$ at $\psi = 0.75$, and $0.175$ at $\psi = 0.7$. At $\psi = 0.5$ there is no detectable $\delta$, because that is the null. (Rates are rounded up to the nearest 0.005 from the exact computation — 0.026, 0.042, 0.077, 0.112, 0.172 — the same convention the $n = 100$ figures used.)

**What 300 per cut buys, and what it still does not.** At 100 per cut McNemar was powered only against gross one-directional drift of 8 points or more; at 300 that floor is 3 points. It is still **not** a test of whether flips occur: against the symmetric process this design expects ($\psi = 0.5$) there is no detectable $\delta$ at any $n$, because that is McNemar's null. Larger $N$ moves the arm-order check and nothing else. The $N$ beyond this one, at 80% power and $\alpha = 0.05$: $n = 600$ gives a minimum detectable $\delta$ of $0.015$ at $\psi = 1.0$ and $0.060$ at $\psi = 0.75$; $n = 1000$ gives $0.010$ and $0.035$.

**What $n = 300$ per cut *can* do.** The primary estimand is the flip rate $\delta$, and it is **estimated with an interval, not tested** (§5.3). Precision at $n = 300$ pairs per cut per sweep, exact 95% intervals on $\delta$:

| flips $k$ | $\hat{\delta}$ | 95% interval | width |
|---|---|---|---|
| 0 | 0.000 | [0.0000, 0.0122] | 0.012 |
| 3 | 0.010 | [0.0021, 0.0289] | 0.027 |
| 9 | 0.030 | [0.0138, 0.0562] | 0.042 |
| 18 | 0.060 | [0.0359, 0.0932] | 0.057 |
| 45 | 0.150 | [0.1116, 0.1955] | 0.084 |

**The consequence for Outcome A.** With zero flips at $n = 300$, the one-sided 95% upper bound on $\delta$ is $0.0099$, which sits below the reportable floor $\delta^{*} = 0.01$. **Outcome A is therefore reachable**, which it was not at $n = 100$, where the same bound is $0.0295$ and the best available result was Outcome C. Outcome C stays in §8 for every case the interval does not resolve; it is no longer the ceiling of the design.

**Pooling across the three sweeps still does not rescue it.** Per cut there are $3 \times 300 = 900$ pairs but only **300 independent items**. At an item-level intraclass correlation of $0.5$ the effective sample size is $450$; at $0.8$ it is $346$; if items behave deterministically ($\text{ICC} = 1$) it is $300$. The design effect is $1 + 2\rho$ and it is reported alongside the interval (§5.3). Pooled $n$ is never quoted as 900.

**The reportable floor, and what it is compared against.** $\delta^{*} = 0.01$ is declared here, before any result: one decision in a hundred changing branch on replay is the smallest rate that is operationally consequential for an automated pipeline. Per the 45/44 note's own filed defect — a declared threshold with no stated null is not yet a test — $\delta^{*}$ is stated together with the comparison it is made against: the zero-flip upper bound at the realized $n$, which is $0.0099$ at $n = 300$ (and was $0.0295$ at $n = 100$). Where the upper bound sits above $\delta^{*}$, the design cannot separate them and Outcome C fires.

### 2.4 Cross-cut comparison is forbidden

Because each cut has its **own 300 items**, the three cuts are measured on three disjoint item sets. Any difference in $\hat{\delta}$ between cuts therefore conflates the position of the cut with the identity of the items, and the design cannot separate them. The lab note may not say that flips are more or less frequent at one cut than another, may not order the three cuts, and may not present the three flip rates as a trend in $c$. Three per-cut results are reported side by side as three separate measurements. This is a direct and accepted cost of the stratified design.

### 2.5 Contract check (gate, before the corpus is frozen)

Four facts about the API are currently **unobserved** — no live Jev call has ever been made — and three of them can invalidate the design. A single contract call set runs before the calibration pass and its results are filed as a §12 addendum:

1. **Returned precision of $p$.** If `noul` returns $p$ quantized to two decimal places or coarser, then items selected to sit within $\pm 0.05$ of a cut will frequently land *exactly on* the cut, ties will dominate the flip count, and the measurement becomes a measurement of quantization. **Gate:** if the returned precision is two decimals or coarser, the study is not run as specified; an addendum is filed and the band definitions are reopened.
2. **Tie behaviour.** The action rule is $p \ge c$, applied to the value **exactly as returned**, parsed as a decimal with no rounding and no rescaling. The count of pairs where $p = c$ in either arm is reported per cut.
3. **Latency, median and tail, at one `noul` question and a state of the size these items use.** Feeds §4.1's window feasibility.
4. **Determinism of the identical request.** Recorded, not gated: it is the study's own subject and must not be treated as a precondition.

---

## 3. Event Definition

The event is the **binary action taken at each declared cut**:
$$\text{Action}_{c}(x) = \begin{cases} 1 & \text{if } p(x) \ge c \\ 0 & \text{if } p(x) < c \end{cases}$$

Evaluated at each item's own cut, $c \in \{0.50, 0.60, 0.90\}$ per §2.2's strata.

The comparison $p \ge c$ is made on the value **as the provider returned it**, parsed as a decimal. No rounding, no re-scaling, no float normalisation is applied before the comparison, because a rounding step would move items across the cut and the study would be measuring the rounding.

### Strict Event Exclusions
- The event is **not** $|\Delta \text{confidence}|$. (`noul` returns no confidence.)
- The event is **not** a continuous score change $|\Delta p|$.
- A continuous score swing is **not a flip**. For example, if $p$ moves from $0.51$ in Arm $A$ to $0.58$ in Arm $A'$ at cut $0.50$, both arms evaluate $\text{Action}_{0.50} = 1$. This pair is concordant. A flip occurs if and only if $\text{Action}_c(A) \ne \text{Action}_c(A')$.

---

## 4. Experimental Arms and Prove Pair Assertion

### 4.1 Arm Execution and the window

- The study runs **three replicate paired sweeps**, one per declared salt. Each sweep is Arm $A_s$ followed by Arm $A'_s$, back to back, inside **its own** declared 20-minute window. Three windows, not one.
- Each arm evaluates all $N = 900$ items, one `noul` question per request. Per sweep that is $1{,}800$ calls; across the study, $5{,}400$ measurement calls. The three cuts do **not** multiply the call count, because each item is evaluated once per arm and thresholded only at its own cut.
- **Feasibility.** $1{,}800$ calls in 20 minutes is $1.5$ calls/second, far below the documented rate limit of 1,200 requests/minute, so the limit is not the binding constraint. Latency is unobserved until §2.5 runs. At a 2-second serial median, $1{,}800$ calls would take 60 minutes serially and do not fit the window at all — so **concurrency is declared at 4 requests in flight**, fixed, and identical in both arms of every sweep, which puts the sweep at about 15 minutes and inside the window with margin. The 300-per-cut ruling therefore did not need a longer window or a higher concurrency than the one already declared; §13's worry on that point was arithmetic on 1,800 calls per *arm* rather than per sweep. Concurrency is part of the pair assertion (§4.4), because changing it between arms would change the provider-side batching context that §7 withdraws any claim about.
- Items are matched pair-by-pair within a sweep: $(A_{s,i}, A'_{s,i})$ for $i = 1, \dots, N$.

**Pairs that straddle the window.** No pair is ever dropped, excluded, retried or truncated because of when it ran. Dropping pairs on a timing criterion would select on an outcome that is itself time-dependent, and that is forbidden. Instead:
- The **realized elapsed span** of each sweep (first request of $A_s$ to last request of $A'_s$) is measured and reported per sweep.
- If a sweep's realized span exceeds 20 minutes, the 20-minute claim is **withdrawn for that sweep** and the actual span is stated in the note. The data stand; the description changes.
- The **per-pair replay gap** — the elapsed time between $A_{s,i}$ and $A'_{s,i}$ — is reported per cut as min, median and max. Because the arms run back to back rather than interleaved, this gap is on the order of the arm duration, not seconds. "A replay" is not a well-defined quantity without it, so the note states the median gap wherever it states a flip rate.

### 4.2 Declared Salts, and what a salt actually does

Three 64-bit hex salts, one per replicate sweep:
- **Salt 1:** `9f4a1c62d08e5b37`
- **Salt 2:** `4c71e89b2a0f3d65`
- **Salt 3:** `d82e05b1f63a94c7`

**Corrected 2026-09-21.** An earlier draft of this spec said each salt "governs request scheduling and order in Prove". Read first-hand in `proofload/src/proofload/executor.py`, that is false. `run_salt` feeds exactly one thing, `derive_seed(run_salt, config_hash, replicate_index)`, which mints the 32-bit `seed` handed to the target. The plan's ordering comes from `spec.cells()` and is salt-independent. And the Jev request body carries `state`, `model` and `questions` and **no seed field**, so the derived seed reaches the harness and stops there.

**Therefore the salt varies nothing that reaches Jev.** Its real and sufficient function is to make pairing *assertable*: `proofload diff --method mcnemar_bh` refuses to run unless both manifests carry the same `run_salt` and every matched row carries the same stored `seed`. Each Arm $A'_s$ is executed with `--pair-with A_s` so it inherits the salt, and the assertion is checked rather than assumed.

**What the three sweeps therefore are:** three replications of the identical measurement on the identical item set, separated in time. They are not three conditions, and the salt is not a treatment. §5.4 says what their spread does and does not license.

### 4.3 Sweep configuration

One sweep file per salt. The item identity is a config axis, so each item is a cell with one replicate; `[capture].max_observation_bytes = "none"`, declared explicitly (the field is required and has no default), so request and response bytes are stored whole and the §4.4 hashes have their inputs. At an item state of roughly 0.5–2 kB the default 8192-byte cap would not truncate most items, but it would truncate some silently, and a pair assertion computed over a truncated state is not an assertion about the state.

### 4.4 Prove Pair Assertion

Before any statistical comparison or table construction, Prove asserts pair identity. The previous version of this section checked three things; the request can differ in more ways than that, so the assertion is over the **whole canonicalised request** with an explicit exemption list.

**Request identity.** `sha256` of the request body serialised with sorted keys and no insignificant whitespace, equal across arms, computed over every field including:
1. `state` bytes
2. `questions`, including the question key, `type == "noul"` and the `instructions` bytes
3. `model`, which must be the literal string `jev-1.13.0` in both arms — the pin is asserted, not assumed from the config
4. every other body field, present or absent, including any sampling parameter (`temperature`, `top_p`), any length limit, and any seed field the API may accept
5. the request target: endpoint URL, HTTP method, and every request header that is not on the exemption list

**Exemption list, declared here so it cannot be widened later.** Only these may differ between arms, because they cannot be held equal: the transport-level request identifier and any idempotency key, the `Date`/timestamp header, and the TLS session. Nothing else. A field that differs and is not on this list fails the pair.

**Harness and environment identity.** Equal across arms, and recorded: the `proofload` version, the `config_hash`, the `run_salt`, the per-row stored `seed`, the `sha256` of the harness module (`jev_harness.py`), the declared concurrency (§4.1), the capture cap, the Python version and the client library version.

**Response eligibility.** A pair is eligible only if **both** arms returned a well-formed `answers[...].noul` value in $[0, 1]$.

**Errors and retries.** **Retries are set to zero.** An HTTP error, a timeout, a rate-limit response or a malformed body on either arm makes that pair ineligible; the call is not repeated, because a repeat is a third draw and silently turns a pair into a best-of. Ineligible pairs are counted per cut, per arm and per cause, and the counts are reported in the note. If more than 5% of a cut's pairs are ineligible, the flip rate for that cut is reported with the ineligibility rate in the same sentence, because at that level the eligible set is no longer the frozen stratum.

**Exclusion record.** Every pair failing any condition above is excluded from analysis, recorded with its failing condition, and cited in the final receipt with a total.

---

## 5. Statistical Analysis Plan

All statistics are computed and reported **per cut** $c \in \{0.50, 0.60, 0.90\}$ on that cut's own 300-item stratum. Nothing is pooled across cuts (§2.4). Where a statistic is also reported per sweep $s \in \{S1, S2, S3\}$, that is stated.

### 5.1 Estimands
1. **Arm Action Rates** (descriptive only, per cut, per sweep):
   $$\hat{p}_A = \frac{1}{n}\sum_{i=1}^{n} \text{Action}_{c}(A_i), \quad \hat{p}_{A'} = \frac{1}{n}\sum_{i=1}^{n} \text{Action}_{c}(A'_i)$$
   No interval is placed on either arm's rate. The two marginals are not independent samples, and an interval on one arm answers a question this study is not asking.
2. **$2 \times 2$ Contingency Table** (per cut, per sweep):

| | $A'$ Action = 1 | $A'$ Action = 0 | Total |
|---|---|---|---|
| **$A$ Action = 1** | $n_{11}$ (concordant 1) | $n_{10}$ (flip $1 \to 0$) | $n_{1\cdot}$ |
| **$A$ Action = 0** | $n_{01}$ (flip $0 \to 1$) | $n_{00}$ (concordant 0) | $n_{0\cdot}$ |
| **Total** | $n_{\cdot 1}$ | $n_{\cdot 0}$ | $n$ |

3. **Action-flip rate (the primary estimand), per cut:**
   $$\hat{\delta}_{\text{flip}} = \frac{n_{10} + n_{01}}{n}$$
   Reported with the item-clustered interval of §5.3. This is the paired quantity: each item contributes one flip indicator built from *both* arms.
4. **Net swing (secondary), per cut:**
   $$\hat{\Delta} = \frac{n_{01} - n_{10}}{n}$$
   Also paired, also item-clustered, and the quantity the 45/44 note reported as "+1.0 points with a task-clustered interval running from −5.5 to +7.5".
   *Sign note, 2026-09-22 (Prove PR-2 Session B, on the ruling of 2026-09-22):* Prove reports the net swing exactly as this formula writes it, the second arm minus the first ($A'$ minus $A$), and labels every `net_swing` block `direction: "b_minus_a"`. The 45/44 note's "+1.0" was $A$ minus $A'$, so the same result reads **−1.0 points, −7.5 to +5.5** in Prove's output (the golden test pins −0.010 with [−0.075, +0.055]). One quantity, one sign convention; the note's sentence and Prove's number differ only in which arm is subtracted from which.
5. **McNemar's exact test** (per cut, per sweep), two-sided, $\alpha = 0.05$: a binomial test on the discordant pairs, $H_0: P(1\to0) = P(0\to1)$.
   $$p_{\text{McNemar}} = \min\left(1,\ 2 \sum_{k=0}^{\min(n_{10}, n_{01})} \binom{n_{10} + n_{01}}{k} \left(\tfrac{1}{2}\right)^{n_{10} + n_{01}}\right)$$
   Reported as the **arm-order drift check** of §2.3, never as a test of reproducibility. Where $n_{10} + n_{01} < 6$ the note states that the test could not have rejected (§2.3's floor) rather than reporting a non-significant $p$ as if it carried information.
6. **Ties.** The count of pairs with $p = c$ exactly, in either arm, per cut.

### 5.2 Why no interval goes on an arm's rate

The comparison is within-item. Arm $A$ and Arm $A'$ evaluate the same 300 items, so $\hat{p}_A$ and $\hat{p}_{A'}$ are strongly positively correlated and an interval built on either one, or on their unpaired difference, ignores the pairing that is the whole design. Every interval in this study is placed on a **paired** quantity: $\hat{\delta}_{\text{flip}}$ or $\hat{\Delta}$.

### 5.3 The clustered interval: unit, justification, method

**Cluster unit: the item.** Per cut there are 300 items, each contributing 3 paired observations (one per replicate sweep). The interval resamples **whole items with replacement**, 300 clusters per cut.

**Why the item, and not the alternatives:**
- **Salt is not usable as the cluster unit.** There are only three salts. A cluster bootstrap over three clusters resamples from three objects and a cluster-robust variance would carry $G - 1 = 2$ degrees of freedom; neither has any coverage worth reporting. Three is far below the cluster counts at which either method behaves.
- **Item-within-salt is not a cluster.** That is the individual observation. Treating it as the unit *is* the unclustered binomial assumption, which is precisely the assumption the design violates: the same item's three observations share its text and its distance from the cut, so they are not three independent draws. The 45/44 script carries this in its own words — "NOT binomial: pairs share episodes".
- **The item is the only unit that is repeated and correlated.** It is the level at which the design has both replication (3 observations) and enough clusters (300) for the interval to mean something. It is the direct analogue of the task-clustered interval in the 45/44 note, where four pairs shared a task; here three pairs share an item.

**Method: percentile cluster bootstrap.** Following `scripts/repro_r1_agreement.py` in the `proofload-repro` worktree, which produced the 45/44 note's clustered intervals: draw $B = 10{,}000$ resamples of the 300 item clusters with replacement, concatenate each resample's flip indicators, take the mean, and report the 2.5th and 97.5th percentiles. Bootstrap seed `20260921`, fixed here. The same procedure, on $d_i \in \{-1, 0, +1\}$, gives the interval on the net swing $\hat{\Delta}$.

**Declared fallback, because a percentile bootstrap degenerates near zero.** If the number of items with at least one flip is 0, every bootstrap resample has mean 0 and the interval collapses to $[0, 0]$, which would read as a precise zero and is not one. In that case the interval is **not** reported as a bootstrap; the one-sided exact 95% upper bound on the item-level flip probability is reported instead, together with the statement that the lower bound is 0 by observation and not by estimation. The same substitution applies if fewer than 5 item clusters carry a flip, where the percentile interval's lower tail is driven by a handful of clusters.

**Design effect, reported.** Alongside each per-cut interval, the note reports the item-level intraclass correlation and the design effect $1 + 2\rho$, so the reader can see how far the 900 observations fall short of 900 independent ones. The pooled $n$ is written as "300 items × 3 sweeps", never as 900.

**Per-sweep intervals are not clustered.** Within one sweep and one cut, each item contributes exactly one pair, so there is nothing to cluster and the per-sweep interval is the ordinary exact interval on 300 pairs. This is stated because calling it "clustered" would claim a correction that is not being made.

### 5.4 Spread across the three sweeps

- The three replicate sweeps yield three per-sweep intervals: $I_1, I_2, I_3$.
- **Definition of CI drift:** CI drift in this study is defined strictly as the **spread across these three intervals**. A single interval from one run is **not** CI drift.
- **What that spread is, and is not.** The three sweeps run the same items with the same requests in three different windows, so their spread is **between-sweep variation over time**. It is not variation attributable to the salt (§4.2: the salt reaches nothing), and it is not a variance estimate for the item population, because all three sweeps reuse the same 300 items and their intervals are therefore correlated. Any statement about the spread says "across three windows", never "across three seeds" and never "across items".

---

## 6. Cost Accounting

- Cost is computed from the provider's own response field, `usage.input_tokens`, summed over every call the study makes, multiplied by **the provider's input price at the time the run executes**. No price is fixed in this specification.
- The run-time price used for the calculation is **recorded in the receipt** alongside the token totals, so the arithmetic is reproducible after the price moves.
- Token totals are reported separately from dollars: the calibration pass, the contract check and the three measurement sweeps each carry their own `input_tokens` total.
- Output tokens are recorded even if the provider bills nothing for them, so the receipt does not depend on a billing assumption.
- **Hard stop:** 6 MTok of input across the whole study, contract check and calibration pass included. The cap is in tokens rather than dollars so it is exactly pre-registrable without a price. A dollar ceiling, if one is wanted, is applied at run time from the recorded price; the token cap halts the run either way.
- Per-episode and total token counts are printed in `receipt.html`.

---

## 7. Withdrawals and Epistemic Limits

The study design observes the client API boundary only. It explicitly cannot separate, and makes **no causal claim** about:

1. **Provider request routing.** Load balancing across disparate server clusters, GPU architectures, or datacenter locations.
2. **Dynamic batching.** Batch size fluctuations, sequence packing, or co-tenant interference in shared inference workers. The declared concurrency of 4 (§4.1) is part of what the study holds fixed, not something it can attribute an effect to.
3. **Sampling and nondeterminism.** Temperature or top-$p$ sampling implementations, floating-point reduction non-associativity in parallel matrix multiplication, or mixture-of-experts router jitter.
4. **Near-cut selection.** Every rate is conditional on items chosen to sit near a cut. The study cannot estimate the flip rate on unselected traffic, and the note must not be read as Jev's overall flip rate. This is the largest gap between what is measured and what a reader will want to conclude, and it is stated in the note's scope section and in every outcome sentence.
5. **Provider-side caching.** A cache hit on the replay would make $A'$ identical to $A$ by construction and drive the measured flip rate toward zero. Nothing at the client boundary can detect a cache hit or rule one out, so the measured $\delta$ is a **lower bound** on the flip rate of an uncached replay, and no upper-bound claim about provider variance follows from it.
6. **Arm order.** Arm $A$ always runs before Arm $A'$, so drift across the window is confounded with arm. McNemar is the check on gross asymmetry (§2.3), and at $n = 300$ per cut it is powered only against one-directional drift of 3 points or more. Interleaving the arms would reduce the confound and was not adopted, because the block ordering matches the 45/44 precedent and because a replay in production is separated by time rather than by microseconds; the cost is recorded here and the per-pair replay gap is reported (§4.1).
7. **What the version pin does and does not guarantee.** `jev-1.13.0` is a string the client sends and the provider echoes. Nothing at this boundary verifies which weights served the request, and the vendor states no retention period for old versions. Every number is dated to the run, not to the version.
8. **Cross-cut comparison.** Forbidden by §2.4: the three cuts have three disjoint item sets.
9. **Window length.** Twenty minutes per sweep is what is measured. The study says nothing about the flip rate over hours, days or weeks — the same withdrawal the 45/44 note makes about its own window.
10. **Calibration.** No external ground-truth labels exist for these items, so no statement about Jev's accuracy or calibration is available from this design, only about the reproducibility of its action.
11. **Vendor terms.** The reading that TypeSafe's MCA carries no benchmarking or publication restriction is second-hand, from a page summariser, on an MCA last updated 2026-09-19. Before publication the clause is **re-read first-hand**, and that re-read is a gate on the note, not a footnote in it.

**Standing constraint:** The resulting note will state the observed discordance rate and interval at the boundary, per cut. It will make zero assertions about internal provider mechanisms.

---

## 8. Pre-Registered Outcome Sentences

Pre-written verbatim, and reported **once per cut**. Every one of them carries the near-cut conditioning, because without it the number reads as Jev's overall flip rate, which this study does not measure.

Which outcome fires at a given cut is decided by the item-clustered interval on $\hat{\delta}_{\text{flip}}$ against the reportable floor $\delta^{*} = 0.01$:

| Condition on the 95% item-clustered interval $[L, U]$ | Outcome |
|---|---|
| $L = 0$ and $U < \delta^{*}$ | **A** — flips ruled out below the floor |
| $L > 0$ | **B** — flips detected |
| $L = 0$ and $U \ge \delta^{*}$ | **C** — too few flips to tell |

### Outcome A (interval covers 0 and excludes the floor)
> *"at this cut, on items picked to sit right beside it, a replay did not change the branch."*

### Outcome B (interval excludes 0)
> *"Two runs of the identical item set scored [X]% and [Y]% action rates while [D] of [N] actions flipped at the shipped cut — on items picked to sit right beside that cut, so this is not a rate for ordinary traffic — and the flips [nearly cancelled / moved the branch]."*

*(This mirrors the 45/44 finding: two scores that appear stable on aggregate conceal discordant flips on individual decisions).*

### Outcome C (interval covers both 0 and the floor)
> *"at this cut, on items picked to sit right beside it, [D] of [N] actions flipped, which puts the flip rate anywhere from [L]% to [U]% — too few to tell a rate worth acting on from none at all."*

Outcome C is not a null result and must not be written as one. It is the design reporting that it could not resolve the question at this $n$, and the note states the $n$ that would (§2.3).

---

## 9. Generated Artifacts and Pipeline

Prove executes the runs, stores the rows, enforces the pairing predicate and prints the receipt. The per-cut $2\times2$, McNemar and the item-clustered interval are **not** things `proofload` computes today — it carries no cluster bootstrap, and `mcnemar_bh` scores each cell and corrects across cells rather than producing one table per stratum, which at one replicate per item is vacuous.

**Being built into Prove before this study runs (ruled 2026-09-21).** The pair assertion of §4.4 and the paired per-cut analysis of §5 are specced as a Prove module, Prove Paired Replay Specification, so that the lab note can credit Prove with the pair, the interval and the receipt rather than with a script beside it. That spec takes **this document as its acceptance case**: running the module on this design has to produce every artifact the table below names, and it adds one — `cost.json` — for §6's arithmetic. It also reproduces the 45/44 note's own published numbers as its golden test.

**Until it is built,** the table below stands as written: the per-cut tables, intervals and timing come from one declared analysis script, exactly as the 45/44 note's clustered interval came from `repro_r1_agreement.py`, and the script is pinned by path and commit before it is run. **Once it is built,** the four rows attributed to "analysis script" are produced by `proofload paired` / `proofload report --paired`, the fifth artifact `analysis/cost.json` joins them, and the script is not run at all. Which of the two applies is filed as a §12 addendum before the measurement sweeps begin; it is not decided at analysis time.

| Artifact | Produced by | Path | Contents |
|---|---|---|---|
| **Stored runs** | `proofload sweep` | `proofload-runs/<run_id>/` | Episodes, configs, per-row seeds, captured request and response bytes, manifest with `run_salt` |
| **Diff** | `proofload diff` | stdout / JSON payload | Per-cell pairing predicate and the `mcnemar_bh` refusal if salts or seeds do not match |
| **Diff Report** | `proofload report` | `proofload-report-jev-s<N>/report.md` | The run-level report, per sweep |
| **Receipt** | `proofload report` | `proofload-report-jev-s<N>/receipt.html` | Run hashes, input tokens, the run-time price used, manifests, environment |
| **Pair assertion log** | analysis script | `analysis/pair_assertion.json` | Per-pair verification of §4.4: request digest, exemptions applied, harness and environment identity, eligibility, and every exclusion with its cause |
| **Per-cut tables** | analysis script | `analysis/contingency_by_cut.json` | $n_{11}, n_{10}, n_{01}, n_{00}$, tie count, McNemar $p$ and the $n_d \ge 6$ floor flag, per cut and per sweep |
| **Intervals** | analysis script | `analysis/intervals_by_cut.json` | $\hat{\delta}_{\text{flip}}$ and $\hat{\Delta}$ with item-clustered intervals, the ICC and design effect, the fallback flag, and the outcome (A/B/C) each cut resolved to |
| **Timing** | analysis script | `analysis/windows.json` | Realized span per sweep, the 20-minute claim held or withdrawn, and the per-pair replay gap distribution per cut |

### Execution Commands
```bash
# Sweep S1: Arm A, then Arm A' inheriting S1's salt
proofload sweep jev_study_s1.toml --target jev_harness:evaluate_item --salt 9f4a1c62d08e5b37
proofload sweep jev_study_s1.toml --target jev_harness:evaluate_item --pair-with RUN_A_S1

# Pairing predicate: refuses unless both manifests share the salt and every row shares its seed
proofload diff RUN_A_S1 RUN_APRIME_S1 --event action --method mcnemar_bh

# Run-level report and receipt
proofload report RUN_A_S1 RUN_APRIME_S1 --event action --out proofload-report-jev-s1

# Per-cut tables, clustered intervals and outcome resolution
python analysis/jev_flip_by_cut.py --sweeps S1 S2 S3 --out analysis/
```

Repeated for `S2` and `S3`, each in its own window.

---

## 10. Article Constraints for the Lab Note

The resulting publication must adhere to the following strict house constraints:
1. **Prove naming:** Prove is named exactly once in the entire post, inside the "What we ran" section, with `report.md` and `receipt.html` linked in the style of Go1 and Microduck:
   - In frontmatter metadata:
     ```yaml
     links: [{ label: "report", href: "/proofload/jev/report.md" }, { label: "receipt", href: "/proofload/jev/receipt.html" }]
     ```
   - In prose: `Runs [id_A] and [id_A'], [report](/proofload/jev/report.md) · [receipt](/proofload/jev/receipt.html).`
2. **No commercial friction:** No call-to-action (CTA), no waitlist link, no GitHub link, and no marketing slogans ("crash tests on every PR").
3. **Headline neutrality:** Prove is kept completely out of the post headline and title.
4. **Result closer:** The conclusion is held strictly to the three-sentence format of the 45/44 note:
   - Sentence 1: The two aggregate scores and the number of flipped decisions.
   - Sentence 2: The behavior of flips across the cuts and seeds.
   - Sentence 3: What is observable at the model boundary versus what is unknowable inside the provider.

---

## 11. Out of Scope

The following topics and phrases are strictly forbidden from the spec and the resulting lab note:
- Framing "same call twice, band moved" as an empirical finding.
- Calling that band movement "CI drift".
- Tasks (the tool or benchmark).
- Referring to Jev as an "agent" (Jev is an automated decision model / classifier).
- Adversary search, outcome labelling, or log-scan onboarding.
- Any claim of model calibration without external ground-truth labels.

---

## 12. Addenda and Amendments

*(Frozen 2026-09-21. All modifications must be appended here with dates and rationale).*

**Addendum 1 — 2026-09-21, the per-cut $n$. Ruled: 300.** §13's question was answered yes. The corpus is 900 items as three disjoint strata of 300, and the study makes 5,400 measurement calls. Rationale, unchanged from §13: at 100 per cut a zero-flip result could not rule out the reportable floor, so Outcome A was unreachable and the design's best possible answer at a quiet cut was "too few flips to tell". The structure of the study is untouched — stratified, one stratum per cut, everything reported per cut, cross-cut comparison forbidden. What moved: §0, §1, §2.2, §2.3 (power and precision recomputed at $n = 300$), §4.1 (call arithmetic and window feasibility), §5, §7.6 and §13. The fallback §13 named — 300 at the 0.50 stratum only, 100 at the other two — applies only if the candidate pool cannot supply 900 near-cut items, and it is filed here as its own addendum if it fires.

**Addendum 2 — 2026-09-21, who computes the result.** The pair assertion and the paired per-cut analysis are being built into Prove before this study runs (Prove Paired Replay Specification). §9 states both cases; which one applies is filed here before the measurement sweeps begin.

**Addendum 3 — 2026-09-22, the candidate pool.** §2.2 names a "separate candidate pool of textual decision states" and does not say where it comes from. It is now specified in full, as [2026-09-22 Jev Dataset Spec](2026-09-22-jev-dataset-spec.md), written before any calibration call and on Taylor's ruling of 2026-09-22 that the pool comes from existing public datasets matching Jev's documented uses rather than from templates we write. Three sources, all CC BY and all pinned by dataset commit sha: **Banking77** (support triage), **CLINC150** `plus` (scope gating) and **HelpSteer2** (agent-output review). No template arm; invoice processing and expense claims are cut for want of a public source. That document fixes, before any score is seen, the questions, the exclusions (personal-data screen, dedup, a 1,500-character length cap), the ordering key, a 120-per-stratum per-source cap, three declared candidate ranges with a 4,500-call / 2.44 MTok ceiling, the under-fill rule, what is recorded per item, and a two-gate acceptance checklist the pool-building session must pass. It also closes the calibration session's four ambiguities with Taylor's 2026-09-22 rulings: half-open bands `[0.45, 0.55)`, `[0.55, 0.65)`, `[0.85, 0.95]`; the contract check first as a gate; and `sha256` over canonical JSON of the full request as the ordering key, which is the same digest §4.4's pair assertion uses.

**One warning it raises against §2.5.** Two independent public audits — `jev-orderby-bench` and `jev-ood-calibration` — report that Jev returns probabilities quantised to `0.01`. That is exactly the condition §2.5's first gate fires on, so on the public evidence the gate is not a remote possibility but the expected outcome. The dataset spec requires the contract check to record raw response bytes rather than parsed floats, to report the distinct returned values as strings with their digit counts, and to state the gate verdict explicitly; a "two decimals or coarser" verdict stops the pool build and reopens the band definitions here, by Taylor's call rather than the building session's. Nothing else in the pool plan depends on the answer.

**Addendum 4 — 2026-09-22, resolution of the §2.5 precision gate and the action rule.** The §2.5 contract check was executed (16 calls, signed commit `8344f74`). As anticipated from public audits, `jev-1.13.0` returns probabilities quantized to $0.01$ (two decimals or coarser — yes). Taylor's ruling of 2026-09-22 resolves the gate and the action rule:
1. **Strata unchanged:** The three disjoint strata stand as specified in [2026-09-22 Jev Dataset Spec](2026-09-22-jev-dataset-spec.md) with half-open bands $[0.45, 0.55)$, $[0.55, 0.65)$, and $[0.85, 0.95]$, containing 10, 10, and 11 attainable grid points respectively.
2. **Primary action rule is $p > c$:** To match TypeSafe's documented threshold convention across its official code examples (`https://docs.typesafe.ai/primitives/noul.md`, e.g. `wants_human > YES`, `repeat > YES`, `noul > 0.9`, `noul > 0.7`), the primary decision event is defined strictly as:
   $$\text{Action}_{c}(x) = \begin{cases} 1 & \text{if } p(x) > c \\ 0 & \text{if } p(x) \le c \end{cases}$$
   applied to the raw returned decimal without rounding. A tie at $p = c$ evaluates to $\text{Action} = 0$ (does not act).
3. **Tie tracking:** The count of items with $p = c$ in either arm is recorded per cut and per sweep.
4. **Secondary sensitivity analysis:** The weak-inequality rule ($\text{Action} = 1 \iff p \ge c$, where a tie at $p = c$ evaluates to 1) is pre-declared as a secondary sensitivity analysis, reported beside the primary and never in place of it.
5. **Authorization:** The candidate calibration pass is authorized to proceed against the frozen candidate pool.

Owed before the measurement sweeps may begin:
- the contract check's four results (§2.5), including the gate verdict on returned precision;
- the realized per-stratum $n$ and the frozen corpus digest (§2.2);
- the analysis script's pinned commit (§9) **or** the Prove build's commit and declaration digest, whichever §9's addendum 2 resolves to;
- the pool-building session's Gate A and Gate B reports against [2026-09-22 Jev Dataset Spec](2026-09-22-jev-dataset-spec.md) §6, including the per-source licences, the personal-data and dedup counts, and the signed frozen-corpus digest (addendum 3).

---


**Addendum 5 — 2026-09-22, k replicates per item, and the corpus accepted as final.** Like addendum 4, this amendment edits no line of the pre-registered body: §1's freeze table still reads 900 items, three paired sweeps and a 6 MTok cap, and what supersedes each of those is here. Written before any measurement call and after nothing has been measured: the contract check (§2.5) and the candidate calibration pass are selection and gate work, not results, and no score from either shapes anything below. Taylor's ruling of 2026-09-22: k-replicate scores are a core part of Prove rather than a Jev-only feature, and they are specced as a generalisation of the paired replay module (Prove Paired Replay Specification §4.H, PR57–PR77), with pairs as the case $k = 2$.

**5.1 The corpus is final at 847 items.** The calibration pass filled $\mathcal{S}_{0.50}$ to 286, $\mathcal{S}_{0.60}$ to 261 and $\mathcal{S}_{0.90}$ to 300 before the declared candidate ranges were exhausted, the under-fill rule of §2.2 fired, and the realized corpus is frozen as `data/corpus_jev_realized_847.json`, `sha256 68ec1e88…`, committed at `f559587`. **That corpus is accepted as final**; the §13 fallback (300 at the 0.50 stratum, 100 at the others) does not fire, and no item is added, swapped or re-calibrated. The three $n$ are unequal and that is harmless here for the reason §2.4 already gives: the cuts are never compared, so each stratum's precision stands on its own. Every $n$ below is the realized one. What moves with it: §2.3's precision table was computed at $n = 300$ and now applies exactly at cut 0.90, and slightly wider at 0.50 and 0.60 — the zero-flip one-sided 95% upper bound is $0.0099$ at $n = 300$, $0.0104$ at $n = 286$ and $0.0114$ at $n = 261$. **Outcome A is therefore still reachable at cut 0.90 and is not reachable at the other two cuts**, where the zero-flip bound sits above the reportable floor $\delta^{*} = 0.01$ and Outcome C fires instead. That is a consequence of the under-fill and it is stated here rather than discovered at analysis time.

**5.2 Each item is sent five times per sweep.** $k = 5$, so each sweep declares five arms of the identical request instead of two, and the study's three replicate sweeps send each item 15 times in all. The declaration's first two arms stay the **declared pair**: every statistic of §5.1–§5.4 — the $2 \times 2$, $\hat{\delta}_{\text{flip}}$, $\hat{\Delta}$, McNemar, the item-clustered interval and the outcome — is computed on those two arms and on no other, exactly as this document pre-registered them. The other three arms are read only by the k-metrics of §5.4 below. Nothing in §0–§13 changes meaning.

**Why five, and not three or seven.** Three constraints, in the order they bind.

*It must be odd.* A majority over an even number of calls needs a tie-break, and a tie-break is a second decision rule that nothing here declared. So the candidates inside Taylor's five-to-eight range are 5 and 7.

*What the extra calls buy, and what they do not.* The width of the item-clustered interval on a k-metric is set by the number of item clusters and the within-item correlation. It is **not** set by $k$. Computed on this design's realized $n$, at the smallest stratum ($n = 261$), under a declared scenario family in which a fraction of near-cut items answer at random on $\pi \in [0.30, 0.70]$ and the rest are perfectly stable, with the fraction fixed so that the $k = 2$ flip rate is $\delta$:

| | $\delta = 0.05$ | | $\delta = 0.15$ | | $\delta = 0.30$ | |
|---|---|---|---|---|---|---|
| $j$ | agree@$j$ | 95% width | agree@$j$ | 95% width | agree@$j$ | 95% width |
| 2 | 0.950 | 0.042 | 0.850 | 0.066 | 0.700 | 0.078 |
| 3 | 0.925 | 0.057 | 0.775 | 0.087 | 0.550 | 0.097 |
| 5 | 0.904 | 0.069 | 0.713 | 0.104 | 0.426 | 0.110 |
| 7 | 0.897 | 0.073 | 0.692 | 0.110 | 0.384 | 0.114 |

Read the middle column. Going from $j = 5$ to $j = 7$ moves agree@$j$ by **2.1 points** while the interval around it is **10.4 points wide**. The seventh call buys a difference this design cannot see. The same reading holds at the other two $\delta$, and the majority-vote metric is flatter still — its width moves from 0.064 at $j = 5$ to 0.062 at $j = 7$. Five sits where the curve has converged and seven pays 40% more tokens for a step inside the noise.

*What five is enough for.* The one thing that does improve monotonically in $k$ is discrimination: an item that answers at random passes agree@$j$ — all $j$ calls alike, by luck — with probability $2^{1-j}$. That is one in 16 at $j = 5$ and one in 64 at $j = 7$. Six per cent of coin-flip items looking perfectly stable is a real limit and it is stated in §7 below rather than removed by spending.

**Feasibility, at the measured latency.** The contract check (16 calls, `8344f74`) recorded a median latency of **0.338 s**. At the declared concurrency of 4 that is 11.8 calls/s, or 710 requests/minute against the documented 1,200/minute limit. A sweep is $847 \times 5 = 4{,}235$ calls and takes about **6.0 minutes**, inside the declared 20-minute window with more margin than the two-arm design had under §4.1's pessimistic 2-second assumption. Note what this does not promise: the contract check measured 16 calls and says nothing about the tail. At a 1-second median a sweep would run about 17.6 minutes and still fit; at 2 seconds it would run 35 minutes and §4.1's withdrawal rule would fire, the data standing and the claim withdrawn per sweep.

**5.3 The token cap, and the arithmetic that moves it.** All figures are the provider's own recorded `usage.input_tokens`, at $0.042 per MTok input.

| Line | Calls | Input tokens |
|---|---|---|
| Contract check (§2.5), executed | 16 | 6,522 |
| Calibration pass, executed | 4,500 | 1,723,267 |
| **Spent so far** | **4,516** | **1,729,789** |
| Measurement, 3 sweeps × 5 arms × 847 items | 12,705 | 4,865,357 |
| **Study total, projected** | **17,221** | **6,595,146** |

The mean is **382.95 input tokens per call**, measured over the 4,500 calibration calls on these same item states with this same question — not the 543 the pre-calibration estimate used. One sweep is 4,235 calls and **1,621,786** tokens. The projected total of **6.595 MTok is above the pre-registered 6 MTok cap of §6**, which was set for a two-arm design.

**The cap is raised to 7 MTok**, which is the smallest whole number with two properties worth having: the study as declared fits inside it with 404,854 tokens of margin (6.1%), and a **fourth** sweep does not — 6.595 + 1.622 = 8.217 MTok — so Prove's between-sweeps gate (`--cap-check`, PR51) exits non-zero on any unplanned extra sweep rather than on the planned third. The cap stays priced in tokens so it is exactly pre-registrable; at the current price the whole study is **$0.277**, of which $0.073 is already spent. This is the only number in this document that the k-replicate change moves, and it is **owed to Taylor as one yes/no** before the first measurement sweep.

**5.4 The two k-metrics, and what they are.** Both are computed per cut, on that cut's own stratum, and never across cuts (§2.4 is unchanged). Both use the primary action rule of addendum 4 — $\text{Action} = 1 \iff p > c$, ties at $p = c$ recorded and evaluating to 0 — with the weak inequality $p \ge c$ reported beside them as the same pre-declared sensitivity analysis, never in place of them. Both carry the item-clustered percentile bootstrap of §5.3, $B = 10{,}000$, seed `20260921`, with the design effect beside them.

1. **agree@$j$, for $j = 2 \dots 5$** — *does it give the same answer if you ask again.* For one item in one sweep, agree@$j$ is 1 when the first $j$ calls all take the same action and 0 otherwise. The observation is the item-sweep, the cluster is the item, and there are 3 observations per item. **agree@2 is $1 - \hat{\delta}_{\text{flip}}$ item by item**, not merely on average, so the new metric and the pre-registered one are the same number at $j = 2$ and the curve extends it.
2. **MS@$j$, for odd $j \in \{1, 3, 5\}$** — *how many calls to trust it.* Take the majority of an item's first $j$ calls in a sweep; MS@$j$ is the rate at which two different sweeps' majorities for the same item agree. The observation is the item-and-sweep-pair, the cluster is the item, and there are $\binom{3}{2} = 3$ observations per item. MS@1 is the single-call version and is **not** $1 - \hat{\delta}_{\text{flip}}$: the flip rate compares two arms inside one sweep, MS@1 compares two sweeps. They are different estimands and the note may not treat them as one.

**pass@1 versus pass@$k$ is declared out**, and the reason is not budget. Under a threshold rule the two branches are symmetric in consequence — acting wrongly and declining wrongly are both decisions — so "at least one of $k$ calls acted" privileges the act branch with no operational warrant here, and pass@1 is an arm's own action rate, on which §5.2 already refuses to place an interval.

**5.5 Cost framing, pre-declared.** These are the sentences the note is allowed to build, fixed now so that no framing is chosen after a number is seen. For each $j$, the note may report:

- **dollars per decision**: $j \times 382.95$ tokens $\times$ the run-time price. At the current $0.042/MTok that is 1.6¢ per 1,000 decisions at $j = 1$ and 8.0¢ per 1,000 at $j = 5$.
- **latency per decision**: $j \times$ the recorded per-call median, serial, and the same divided by the declared concurrency of 4. At the contract check's 0.338 s that is 1.7 s serial and 0.42 s amortised at $j = 5$.
- **"out of 10,000 near-cut decisions, $N$ decided differently"**, where $N = 10{,}000 \times (1 - \text{MS@}j)$, always with both endpoints of the same clustered interval and **always with the near-cut conditioning attached in the same sentence**. It is a rate for items chosen to sit beside a cut and it is not a rate for production traffic; §7.4 is the standing withdrawal and this is where it would most easily be forgotten.

The shape of the claim, stated before the numbers exist: a table with one row per $j$, its price, its latency and its $N$ with bounds — so a reader can see what a call costs and what it buys, and can stop where the buying stops. No row is a recommendation and the note recommends no $j$.

**5.6 What this addendum does not change.** The cuts, the strata, the salts, the three windows, the pair assertion of §4.4 (now over five arms instead of two, with the same exemption list and the same zero-retry rule), the estimands of §5.1, the cluster unit, the bootstrap and its seed, the reportable floor, the outcome table and the three pre-written outcome sentences of §8, the withdrawals of §7, the article constraints of §10 and the out-of-scope list of §11. Cross-cut comparison stays forbidden and now extends to the k-metrics.

**5.7 What it adds to the withdrawals.** Three limits, in §7's register:
- **agree@5 cannot see a coin flip.** An item that answers at random passes agree@5 six times in a hundred. The metric bounds instability from below and the note says so.
- **A replicate set is all five calls or none.** If any of an item's five calls in a sweep errors, that item-sweep is excluded whole; it is not analysed at four. So the k-metrics are computed on the subset of item-sweeps where all five calls returned, and the exclusion count is reported per cut beside them.
- **Five calls in one sweep are five calls inside one window.** They are minutes apart, not days, and they inherit every caching, routing and batching withdrawal §7 already makes. A provider-side cache hit would make them agree by construction, so every agreement rate here is an **upper** bound on the agreement of an uncached replay, exactly as §7.5 makes the flip rate a lower bound.

**5.8 Owed before the measurement sweeps.** Addendum 4's list stands, minus the realized-$n$ and corpus-digest item, which §5.1 discharges. Added by this addendum: **the token cap of 7 MTok, one yes/no**; and the three retrofits of Prove Paired Replay Specification §10.5, of which R3 — a declared `gt`/`ge` comparison on the cut — is the one this study needs, because addendum 4 ruled $p > c$ and the module as built compares $p \ge c$. Until R3 is ruled, this study cannot be run through Prove under its own action rule.


**Addendum 6 — 2026-09-22, resolution of Addendum 2: analysis in Prove, declaration and harness freeze.** Addendum 2 is resolved: the pair assertion, contingency tables, item-clustered intervals, outcome resolution, window analysis, cost accounting, and k-replicate metrics are computed and produced directly by Prove (`proofload diff`, `proofload report`, `proofload paired`, and `proofload report --paired`), not by an analysis script. The four rows in §9 attributed to an external analysis script are produced as Prove's standard artifacts (`pair_assertion.json`, `contingency_by_cut.json`, `intervals_by_cut.json`, `windows.json`, `cost.json`, and `replicates_by_cut.json`). Pinned and frozen before the first measurement call:
- **Prove commit:** `7fb719630d3740ff914781aeddf0774bc9c72a28` (`7fb7196`, merging PR #2 / PR-3, phases 1–3 into `origin/main`).
- **Harness module digest:** `jev_harness.py` (`sha256 1fa5453b02d29767fd7dee33562cc5a3bfce0adc3e863da9edc836ddf445b9f2`), implementing POST `/v1/systemone` with `model = "jev-1.13.0"` pinned, question type `noul`, zero retries, and recording whole request/response bodies under the `"none"` capture cap.
- **Corpus digest:** `corpus_jev_realized_847.json` (`sha256 68ec1e881660dd4967aa058c91ab15a305c7422017caca3bc3ed9d4eed995dcf`, 847 items, frozen at `f559587`).
- **Sweep declarations:**
  - Sweep S1 (`jev_decl_s1.toml`): `sha256 f6710f71aee851793cd708a04b52054c780fa2642249d6faaf5fd34ec8b6b3cd` (Salt 1: `9f4a1c62d08e5b37`, arms `S1-a`, `S1-b`, `S1-3`, `S1-4`, `S1-5`).
  - Sweep S2 (`jev_decl_s2.toml`): `sha256 7d1a18b6cdc99674cb37529d9bac7ca7f036b1cee002455433b751ef7e1f9386` (Salt 2: `4c71e89b2a0f3d65`, arms `S2-a`, `S2-b`, `S2-3`, `S2-4`, `S2-5`).
  - Sweep S3 (`jev_decl_s3.toml`): `sha256 3cb60ba4daf0d5dc7ed06de1c1a39d052f5ec436f7306e4606c9eb59422f69c0` (Salt 3: `d82e05b1f63a94c7`, arms `S3-a`, `S3-b`, `S3-3`, `S3-4`, `S3-5`).
  - Multi-sweep study declaration (`jev_decl_study.toml`): `sha256 5ae001c1638120fbe4b362f9eab17bef9f394406834e80a66d161d84e0c3178f`.
- **Declared concurrency:** 4.
- **Window rule of §4.1:** The realized elapsed span of each sweep (first request of Arm A to last request of Arm 5) is measured and reported per sweep. If a sweep's span exceeds the declared 20-minute window (1,200 s), the 20-minute claim is withdrawn for that sweep and the actual span reported; the data stand, the description changes. The per-pair replay gap distribution is reported per cut as min, median, and max. Retries are set to zero.


**Addendum 7 — 2026-09-23, one declared pair restored at cut 0.60: an eligibility bug in Prove, not a change to the design.** Like addenda 4 to 6, this amendment edits no line of the pre-registered body. No call was made, no row was added or removed, and every number below was computed again by Prove from the stored runs in `data/store/`.

*The bug.* Addendum 5.2 computes every pair statistic on the declared pair, arms a and b. Addendum 5.7 excludes a replicate set whole **from the k-metrics** when any of its five calls errors. Prove at the pinned commit `7fb7196` excluded such a set from the pair analysis as well, because its pair assertion kept a set only when all five calls were eligible. The independent recompute (`recompute.py`) found the gap.

*The one affected pair.* Across the three sweeps and three cuts there is exactly one errored call. In S1 at cut 0.60, item `3a638a32ae3e2a381d32178fb4b1006111534bbbcc1571513572d9f019d54da9`, the fifth call returned HTTP 529. Its declared pair returned `0.62` and `0.64`, both acting under $p > c$: a concordant 1, not a flip. The replicate set stays excluded from the k-metrics exactly as 5.7 requires.

*The corrected cut 0.60 figures (primary rule $p > c$).*

| | As first reported | Corrected |
|---|---|---|
| Eligible pairs | 782 (261 × 3 − 1) | **783 (261 × 3)** |
| Pooled 2×2 $n_{11}/n_{10}/n_{01}/n_{00}$ | 234 / 62 / 83 / 403 | **235 / 62 / 83 / 403** |
| S1 2×2, $n$ | 80 / 19 / 29 / 132, 260 | **81 / 19 / 29 / 132, 261** |
| S1 action rates A, A′ | 38.08%, 41.92% | **38.31%, 42.15%** |
| S1 flip rate, exact 95% | 18.46% [13.94%, 23.72%] | **18.39% [13.88%, 23.63%]** |
| S1 net swing | +3.85% | **+3.83%** |
| Pooled action rates A, A′ | 37.85%, 40.54% | **37.93%, 40.61%** |
| Flips, $\hat{\delta}_{\text{flip}}$, item-clustered 95% | 145, 18.54% [15.45%, 21.74%] | **145, 18.52% [15.45%, 21.71%]** |
| Net swing $\hat{\Delta}$, clustered 95% | +2.69% [−0.26%, +5.63%] | **+2.68% [−0.26%, +5.62%]** |
| ICC, design effect | 0.1627, 1.325 | **0.1635, 1.327** |
| Ineligible declared pairs | 1 | **0** |
| Outcome | B | **B** |

- **Unchanged:** the flip count, all three McNemar arm-order checks ($p$ = 0.193, 0.461, 0.576), the tie counts (72 and 60), and every k-metric (`agree@j`, `MS@j`, their intervals and the cost framing).
- **Unchanged elsewhere:** cuts 0.50 and 0.90, and the token and dollar accounting.
- **Windows:** two figures move with the restored pair. S1's latency median is now over 4,232 calls rather than 4,230, and the 0.60 median replay gap is 56.2556 s rather than 56.2563 s. Every realized span and window claim is unchanged.
- **§8 outcome sentence for 0.60:** the counts now read "37.9% and 40.6% action rates while 145 of 783 actions flipped".

*The fix.* Retrofit test `0efdf45`, the ruled retrofit of ten frozen replicates rows `2b61478`, fix `94c1f15` and timestamp guard `88b39aa`, on branch `fix-pair-exclusion` of `poisson-labs/prove` over `7fb7196`. The declared pair of a set broken only past it is judged on arms a and b alone.

*The regeneration.*
- **Outputs:** `data/paired/` and `report-study-v2/`, generated by `94c1f15` from the stored runs with the same commands and the same interpreter that produced `paired/` and `report-study/`. Those originals are kept untouched beside them.
- **Recompute check:** the recompute's comparison against `paired-v2/` reads "every number matches", on its stated contract of exact counts and intervals to $10^{-12}$.
- **At zero tolerance**, the only remaining differences are these:
  - Four McNemar $p$ that the recompute stores to 12 decimals.
  - Eight per-sweep exact-binomial bounds at cuts 0.50, 0.60 and 0.90, which differ from the recompute in the 16th or 17th significant digit. They come from the recompute's newer scipy (1.17.1 against 1.16.3) and are the same in the original `paired/`. The same build under the recompute's scipy matches it bit for bit apart from the four stored McNemar values. Evidence: `pair exclusion audit`.

**No new data was collected and no pre-registered outcome changed.** All three cuts remain Outcome B.

---

## 13. CLOSED — the one ruling, answered

**Question, as asked.** Raise the corpus to **300 items per cut** (900 items, 5,400 measurement calls) instead of 100 per cut — yes or no?

**Ruled 2026-09-21: yes.** Filed as §12 addendum 1 and written through §0, §1, §2.2, §2.3, §4.1, §5 and §7.6. Nothing else in the design moved.

**Why it was asked.** The 2026-09-21 ruling fixed the *structure*: stratified, one stratum per cut, each calibrated to its own band, everything reported per cut. That structure is unchanged by the answer. What the power work in §2.3 showed is that a per-cut $n$ of 100 could not carry two of the things this spec promises:
- a zero-flip result at $n = 100$ has a 95% upper bound of $0.0295$, which does not rule out the reportable floor $\delta^{*} = 0.01$, so **Outcome A was unreachable at 100 per cut** — the best available result was Outcome C;
- McNemar's exact test at $n = 100$ needs a flip rate of $0.080$ even when every flip runs the same way, so it was powered only against gross one-directional drift.

**What the answer bought.** The zero-flip upper bound is $0.0099$, below $\delta^{*}$, so Outcome A is reachable. McNemar's minimum detectable rate falls from 8 points to 3 at $\psi = 1.0$ — and stays worthless against a symmetric flip process at any $n$, which is why it is the arm-order check and not the test (§2.3).

**What it cost, corrected.** Three times the calls: 5,400 measurement calls plus a larger calibration pass, a small fraction of the 6 MTok cap and cents rather than dollars at any plausible price. The real cost is the candidate pool — three times as many items have to calibrate into narrow bands. **The window is not a cost:** §13 as asked said "at 1,800 calls per arm", which was arithmetic on the wrong unit. It is 900 calls per arm and 1,800 per sweep, and at the already-declared concurrency of 4 with a 2-second median that is about 15 minutes, inside the declared 20-minute window (§4.1). No longer window and no higher concurrency is needed.

**The fallback, still standing.** If the candidate pool cannot supply 900 near-cut items, the fallback is 300 per cut at the 0.50 stratum only and 100 at the other two, with §2.4's ban on cross-cut comparison making the unequal $n$ harmless. If it fires it is filed as its own §12 addendum, before any measurement call.

## 14. Change log

**2026-09-21, review before freeze.** The spec was reviewed against the standard of the 45/44 note and corrected. Taylor's stratification ruling was written in. Changes, in order of consequence:

1. **Stratified corpus written in (§0, §1, §2.2).** 100 items per cut, each calibrated to its own band, no joint mid-mass corpus, every statistic and outcome sentence per cut. Fill order and the short-stratum rule declared so stratum membership is not a judgement call at fill time.
2. **Cross-cut comparison forbidden (§2.4).** A consequence of stratification: the three cuts have disjoint item sets, so any difference between their flip rates conflates cut position with item identity. The note may not order the cuts or present them as a trend.
3. **Power redone under the alternative (§2.3).** The previous section argued under $H_0$ with a single-arm Wilson example. Replaced with McNemar exact power at $n = 100$ over $(\delta, \psi)$, the $n_d \ge 6$ floor, and the minimum detectable rates. Stated plainly: 100 per cut cannot detect a flip rate worth reporting with McNemar, and the $N$ that would is named. Added the point the previous version missed — McNemar tests lopsidedness, not prevalence, and has no power against the symmetric flip process this design expects — and demoted it to the arm-order drift check.
4. **Cluster unit chosen and justified (§5.3).** The item, 100 clusters per cut. Salt rejected (three clusters is not a cluster bootstrap), item-within-salt rejected (that is the observation, and using it is the binomial assumption the design violates). Method named: percentile cluster bootstrap, $B = 10{,}000$, seed `20260921`, following `repro_r1_agreement.py`. Every interval moved onto a **paired** quantity, and §5.2 added to say why no interval goes on an arm's rate. Added the degenerate-at-zero fallback, the design effect, and the note that per-sweep intervals are not clustered.
5. **Near-cut conditioning made explicit (§0, §7.4, §8).** It is in the scope section, in the withdrawals and in all three outcome sentences. The note cannot be read as Jev's overall flip rate.
6. **Cost de-priced (§6).** The fixed $/MTok figure removed — it was a second-hand docs number in the first place. Cost is `usage.input_tokens` × the provider price at run time, and the receipt records the price used. Hard stop restated as a token cap so it is exactly pre-registrable.
7. **Duplicate removed.** The vault-root copy of this spec was deleted; the `posts/` copy is canonical. The wikilinks that pointed at the ambiguous name now resolve here.
8. **Salt semantics corrected (§4.2).** The claim that a salt "governs request scheduling and order in Prove" is false, read first-hand in `executor.py`: `run_salt` feeds `derive_seed` only, ordering is salt-independent, and the Jev request body has no seed field, so nothing the salt touches reaches Jev. The salt's real function — making pairing assertable, since `mcnemar_bh` refuses on mismatched salt or seed — is stated instead. The three sweeps are relabelled as replications separated in time, and §5.4 now says their spread is between-window variation on a fixed item set, correlated because the items are shared.
9. **Window resolved (§4.1).** Three windows, one per sweep, not one for all three. Call arithmetic stated: 600 calls per sweep, 1,800 total, with the cuts not multiplying the count. Feasible against the documented 1,200 req/min limit but not against an unobserved serial latency, so concurrency is declared at 4 and added to the pair assertion. Straddling pairs: no pair is ever dropped on a timing criterion; the realized span is reported and the 20-minute claim withdrawn per sweep if it is exceeded; the per-pair replay gap is reported, because "a replay" has no meaning without it.
10. **Pair assertion widened (§4.4).** Was three checks; the request can differ in more ways than three. Now the whole canonicalised request body plus endpoint and headers, with a closed exemption list, and the model pin asserted rather than assumed. Added harness and environment identity, response eligibility, and a zero-retry rule — the previous design would have let a retried call become a third draw and a best-of.
11. **Withdrawals completed (§7).** Added: near-cut selection; provider-side caching, which makes the measured rate a lower bound; arm order confounded with elapsed time, with the interleaving alternative recorded as considered and declined; what the version pin does not guarantee; cross-cut comparison; window length; no calibration claim without labels; and the first-hand MCA re-read as a gate on publication rather than a footnote.
12. **Artifact table made true (§9).** `pair_assertion.json` and `contingency_table.json` were named as standard Prove outputs and are not — `proofload` carries no cluster bootstrap, and `mcnemar_bh` is per-cell with BH across cells, which at one replicate per item is vacuous. The per-cut tables, intervals and timing are now attributed to one declared analysis script, pinned by path and commit, exactly as the 45/44 note's clustered interval was.
13. **Contract check added as a gate (§2.5).** Four unobserved API facts, three of which can invalidate the design. The one that matters most: if `noul` returns $p$ at two decimals or coarser, items selected within $\pm 0.05$ of a cut will sit *on* the cut and the study measures quantization. Gated, with the tie rule and the no-rounding comparison declared in §3.
14. **A third outcome added (§8).** Outcome C, "too few flips to tell", with an explicit decision table on the interval against $\delta^{*} = 0.01$. Needed because at $n = 100$ a zero-flip result cannot support Outcome A, and writing it anyway would be the strongest claim in the note resting on the weakest part of the design.
15. **Kept exactly as written:** §10 article constraints and §11 out-of-scope items, verbatim.

**2026-09-21, later — the per-cut $n$ ruled, and the analysis moved into Prove.** Two changes, both filed as §12 addenda rather than as silent edits. Items 1, 3, 4 and 14 above are kept as the history of the review that *asked* the question, and where they say "100 items per cut" or "100 clusters per cut" they describe what that review wrote, not what this document now specifies.

16. **The corpus is 300 per cut (§13 closed, addendum 1).** $N = 900$ as three disjoint strata. §2.3's McNemar power table, minimum detectable rates and exact-interval precision table are recomputed at $n = 300$; the $n = 100$ figures are kept only as the comparison the ruling was made on. §4.1's call arithmetic is restated — 900 calls per arm, 1,800 per sweep, 5,400 across the study — and the window shown to hold at the already-declared concurrency of 4, correcting §13's own "1,800 calls per arm". Outcome A moves from unreachable to reachable; Outcome C stays for every case the interval does not resolve. Pooled $n$ is now "300 items × 3 sweeps" and never 900.

17. **The pair assertion and the paired analysis are being built into Prove (§9, addendum 2).** Specced as Prove Paired Replay Specification, with this document as its acceptance case: the module has to produce every artifact §9's table names, plus `cost.json`, with no script beside it, and it reproduces the 45/44 note's published numbers as its golden test. §9 now states both cases — script, or Prove — and requires the choice to be filed before the measurement sweeps, not made at analysis time. The reason is the one the 45/44 note already exposed twice: a number a lab note credits to Prove should be a number Prove computed.
