# Dataset and Run Artifacts

This directory contains the dataset artifacts, frozen candidate pool, and raw measurement run data for the Jev paired-replay study.

## Source Datasets

The study corpus is drawn from three public natural-language benchmarks, chosen to evaluate distinct automated classification workflows on `jev-1.13.0`. Each upstream source was pinned to a specific Git revision prior to calibration or measurement.

### 1. Banking77 (Source S1)
- **Workflow:** Customer Service (Support Triage)
- **Repository:** [`PolyAI/banking77`](https://huggingface.co/datasets/PolyAI/banking77)
- **Pinned Revision:** `90d4e2ee5521c04fc1488f065b8b083658768c57`
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Citation:** Casanueva et al., *Efficient Intent Detection with Dual Sentence Encoders*, arXiv:2003.04807 (2020)
- **Evaluated Files:**
  - `train.csv` (SHA256: `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`)
  - `test.csv` (SHA256: `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d`)

### 2. CLINC150 (Source S2)
- **Workflow:** Customer Service (Scope Gating)
- **Repository:** [`clinc/clinc_oos`](https://huggingface.co/datasets/clinc/clinc_oos) (config `plus`)
- **Pinned Revision:** `155b9c710419136e17307b80d0a13e68cd46b4ec`
- **Licence:** Creative Commons Attribution 3.0 Unported (CC BY 3.0)
- **Citation:** Larson et al., *An Evaluation Dataset for Intent Classification and Out-of-Scope Prediction*, EMNLP-IJCNLP (2019)
- **Evaluated Files:**
  - `train-00000-of-00001.parquet` (SHA256: `30188119cf9f86fc9db27e1c22442d091cb5cb0913c9496f945fe11e7a02a28f`)
  - `test-00000-of-00001.parquet` (SHA256: `3e60e45b25bf86543aa5df8ba4fcc674114164e6184f0197690648c2908d0102`)
  - `validation-00000-of-00001.parquet` (SHA256: `fbd545b46c611c4a7ba4b48cae6c7f09bb5b59f33ff56206ad1cd366c85cdfaa`)

### 3. HelpSteer2 (Source S3)
- **Workflow:** Agent Trace Observability (Output Review)
- **Repository:** [`nvidia/HelpSteer2`](https://huggingface.co/datasets/nvidia/HelpSteer2)
- **Pinned Revision:** `990b2711a36180dd19d9c94b8627844866f8982a`
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Citation:** Wang et al., *HelpSteer2: Open-source dataset for training top-performing reward models*, arXiv:2406.08673 (2024)
- **Evaluated Files:**
  - `train.jsonl.gz` (SHA256: `c0d7e91d738d42e8a08070db26c4c09a9c7631308e1f0fd380ff43d130c9f713`)
  - `validation.jsonl.gz` (SHA256: `610eeb5289494d613c4c0f70aade2df8df0b499f3a24e76d232f74e6909d010a`)

## Realized Corpus (`corpus_jev_realized_847.json`)

The candidate pool was constructed by `data/pool/generate_pool.py` applying language filtering, length capping (1,500 characters), deduplication, PII pattern screening, and per-source candidate caps. Stratum calibration (`run_calibration.py`) identified items whose assessed score fell within target half-open threshold bands (`[0.45, 0.55)`, `[0.55, 0.65)`, `[0.85, 0.95]`).

The realized corpus is frozen at 847 items:
- **Cut 0.50:** 286 items
- **Cut 0.60:** 261 items
- **Cut 0.90:** 300 items
- **File:** `corpus_jev_realized_847.json`
- **SHA256:** `68ec1e881660dd4967aa058c91ab15a305c7422017caca3bc3ed9d4eed995dcf`

## Stored Measurement Runs (`store/`)

Contains 15 complete run directories spanning three experimental sweeps (`S1`, `S2`, `S3`) with 5 arms each:
- Declared pair: Arms `a` and `b`
- Additional k-replicate arms: Arms `3`, `4`, `5`
Totaling 12,705 calls recorded across 15 Apache Parquet episode files, each accompanied by its immutable run manifest. All calls were recorded under zero retries and full span telemetry.

## Paired Analysis (`paired/`)

Carries the corrected paired replay artifacts produced under the pair-eligibility fix:
- `pair_assertion.json`: Verification of request identity, run salts, row seeds, and arm eligibility.
- `contingency_by_cut.json`: 2x2 contingency tables and McNemar tests per sweep and pooled across sweeps.
- `intervals_by_cut.json`: Clustered bootstrap intervals, design effects, and outcome determinations.
- `replicates_by_cut.json`: k-replicate agreement metrics (`agree@j`, `MS@j`).
- `windows.json`: Measured elapsed spans for all 20-minute execution windows.
- `cost.json`: Token and call accounting.
