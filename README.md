# Jev Paired-Replay Study

Replication artifacts and independent verification suite for the paired-replay reliability study of TypeSafe's Jev (`jev-1.13.0`).

Published research note: [https://poissonlabs.ai/research/jev-paired-replay](https://poissonlabs.ai/research/jev-paired-replay)

## What the Study Asks

When an automated pipeline deploys a decision model behind a fixed threshold $c$, taking an action if assessed probability $p > c$ and declining otherwise:

**Does an identical replay change the model's action at a threshold people ship?**

This study evaluates `jev-1.13.0` across three operational thresholds ($c \in \{0.50, 0.60, 0.90\}$) using 847 frozen evaluation items drawn from three public benchmark datasets ([Banking77](https://huggingface.co/datasets/PolyAI/banking77), [CLINC150](https://huggingface.co/datasets/clinc/clinc_oos), [HelpSteer2](https://huggingface.co/datasets/nvidia/HelpSteer2)). Each item was evaluated across three independent replicate sweeps (`S1`, `S2`, `S3`) of 5 arms each (arms `a` and `b` forming the pre-registered pair, plus arms `3`, `4`, `5` for k-replicate agreement), totaling 12,705 calls. All calls were issued with zero retries inside declared 20-minute operational windows.

## Headline Findings

All three thresholds resolved to **Outcome B** (flips detected with net swing covering zero). Reported in accordance with the pre-registered outcome sentences:

- **Threshold 0.50:** Two runs of the identical item set scored 38.81% and 40.56% action rates while 159 of 858 actions flipped at the shipped cut — on items picked to sit right beside that cut, so this is not a rate for ordinary traffic — and the flips nearly cancelled.
  - Flips: 159 / 858 (18.53%, 95% item-clustered interval [15.38%, 21.79%]).
  - Net swing: +1.75% (95% interval [-1.28%, +4.78%]).
  - Sweep McNemar checks: $p = 0.461$ (S1), $p = 0.419$ (S2), $p = 0.896$ (S3).

- **Threshold 0.60:** Two runs of the identical item set scored 37.93% and 40.61% action rates while 145 of 783 actions flipped at the shipped cut — on items picked to sit right beside that cut, so this is not a rate for ordinary traffic — and the flips nearly cancelled.
  - Flips: 145 / 783 (18.52%, 95% item-clustered interval [15.45%, 21.71%]).
  - Net swing: +2.68% (95% interval [-0.26%, +5.62%]).
  - Sweep McNemar checks: $p = 0.193$ (S1), $p = 0.461$ (S2), $p = 0.576$ (S3).

- **Threshold 0.90:** Two runs of the identical item set scored 54.78% and 54.56% action rates while 48 of 900 actions flipped at the shipped cut — on items picked to sit right beside that cut, so this is not a rate for ordinary traffic — and the flips nearly cancelled.
  - Flips: 48 / 900 (5.33%, 95% item-clustered interval [3.56%, 7.22%]).
  - Net swing: -0.22% (95% interval [-1.56%, +1.11%]).
  - Sweep McNemar checks: $p = 0.302$ (S1), $p = 0.629$ (S2), $p = 0.210$ (S3).

Every rate reported above is conditional on near-cut items ($[0.45, 0.55)$, $[0.55, 0.65)$, $[0.85, 0.95]$) and is expected to run higher than on general traffic, where the majority of inputs sit far from decision boundaries.

## How to Verify

An independent verification script is provided at `recompute.py`. It has zero dependencies on Poisson Prove, imports only `numpy`, `scipy`, and `pyarrow`, uses `Decimal` comparisons and `Fraction` counts, and reproduces every published table and clustered interval directly from the raw Parquet rows in `data/store/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "numpy>=2.0.0" "scipy>=1.14.0" "pyarrow>=17.0.0"

python3 recompute.py
```

The script runs the $B = 10{,}000$ cluster bootstrap (seed `20260921`), validates cross-stratum independence, reproduces the 145 of 783 flips at 0.60, and confirms exact agreement with the paired JSON outputs in `data/paired/`.

## How to Re-Run

Re-running the study against the live API requires your own TypeSafe API key (`TYPESAFE_API_KEY`) and Poisson Prove. Poisson Prove is currently pre-release and in testing, and is not yet public.

With the `proofload` CLI installed and your key exported:

```bash
export TYPESAFE_API_KEY="your-api-key"

# 1. Verify API contract and model pin
python3 contract_check.py

# 2. Execute sweep S1 across all 5 arms
proofload sweep jev_decl_s1.toml --target jev_harness:evaluate_item --salt 9f4a1c62d08e5b37

# 3. Execute sweep S2 across all 5 arms
proofload sweep jev_decl_s2.toml --target jev_harness:evaluate_item --salt 4c71e89b2a0f3d65

# 4. Execute sweep S3 across all 5 arms
proofload sweep jev_decl_s3.toml --target jev_harness:evaluate_item --salt d82e05b1f63a94c7

# 5. Compute paired replay analysis and generate report
proofload paired jev_decl_study.toml --out report/
```

## What It Cost

- **Total API calls:** 12,705 live calls (847 items $\times$ 5 arms $\times$ 3 sweeps).
- **Recorded token consumption:** 4,875,417 input tokens (~4.88 MTok), well within the pre-registered 7.0 MTok ceiling. Output tokens are not billed by the provider for structured classification endpoints.
- **Provider pricing:** Dollar amounts are not published on TypeSafe's public site and are omitted here.

## Repository Contents

| Path | Description |
|---|---|
| `recompute.py` | Standalone verification entry point reading `data/store/`. |
| `jev_harness.py` | Measurement harness calling `POST /v1/systemone` under concurrency 4. |
| `jev_decl_*.toml` | Declarations for sweeps S1, S2, S3, and pooled study. |
| `contract_check.py` | Pre-flight validation of model pinning and question type. |
| `run_calibration.py` | Stratum calibration runner generating `corpus_jev_realized_847.json`. |
| `data/corpus_jev_realized_847.json` | Frozen 847-item corpus (`sha256: 68ec1e88...`). |
| `data/pool/` | Candidate pool generator and frozen candidate tables. |
| `data/store/` | 15 Parquet episode directories containing all raw response records (5.2 MB). |
| `data/paired/` | Corrected paired replay JSON outputs (783 pairs at 0.60). |
| `report/` | Complete study report (`report.md`), receipt (`receipt.html`), and figures. |
| `docs/` | Pre-registration study spec, dataset spec, and repo hygiene standard. |

## Licence

Code and study artifacts are licensed under the MIT License; see [LICENSE](LICENSE). Upstream datasets are licensed under CC BY 4.0 (Banking77, HelpSteer2) and CC BY 3.0 (CLINC150); see [NOTICE](NOTICE) and [data/README.md](data/README.md).
