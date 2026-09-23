# Pinned Candidate Sources for Jev Study Pool

Three public datasets, each corresponding to an evaluated workflow on evals.typesafe.ai. Pinned before any Jev call.

| Field | Source S1 | Source S2 | Source S3 |
|---|---|---|---|
| **source_id** | `S1` | `S2` | `S3` |
| **repo** | `PolyAI/banking77` | `clinc/clinc_oos` (config `plus`) | `nvidia/HelpSteer2` |
| **workflow** | Customer Service (Support Triage) | Customer Service (Scope Gating) | Agent Trace Observability (Output Review) |
| **revision** | `90d4e2ee5521c04fc1488f065b8b083658768c57` | `155b9c710419136e17307b80d0a13e68cd46b4ec` | `990b2711a36180dd19d9c94b8627844866f8982a` |
| **licence** | **CC BY 4.0** | **CC BY 3.0** | **CC BY 4.0** |
| **licence URL** | https://huggingface.co/datasets/PolyAI/banking77 | https://huggingface.co/datasets/clinc/clinc_oos | https://huggingface.co/datasets/nvidia/HelpSteer2 |
| **date read** | 2026-09-22 | 2026-09-22 | 2026-09-22 |
| **citation** | Casanueva et al. 2020, arXiv:2003.04807 | Larson et al., EMNLP-IJCNLP 2019 | Wang et al., arXiv:2406.08673, arXiv:2410.01257 |
| **raw_rows** | 13,083 (10,003 train / 3,080 test) | 23,850 (15,250 train / 3,100 val / 5,500 test) | 21,362 (20,324 train / 1,038 val) |

## Downloaded Files and SHA256 Digests

### S1: Banking77 (`PolyAI/banking77` @ `90d4e2ee5521c04fc1488f065b8b083658768c57`)
- `train.csv` (839,073 bytes): `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`
- `test.csv` (239,961 bytes): `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d`

### S2: CLINC150 (`clinc/clinc_oos` config `plus` @ `155b9c710419136e17307b80d0a13e68cd46b4ec`)
- `train-00000-of-00001.parquet` (312,246 bytes): `30188119cf9f86fc9db27e1c22442d091cb5cb0913c9496f945fe11e7a02a28f`
- `test-00000-of-00001.parquet` (136,155 bytes): `3e60e45b25bf86543aa5df8ba4fcc674114164e6184f0197690648c2908d0102`
- `validation-00000-of-00001.parquet` (77,358 bytes): `fbd545b46c611c4a7ba4b48cae6c7f09bb5b59f33ff56206ad1cd366c85cdfaa`

### S3: HelpSteer2 (`nvidia/HelpSteer2` @ `990b2711a36180dd19d9c94b8627844866f8982a`)
- `train.jsonl.gz` (11,043,995 bytes): `c0d7e91d738d42e8a08070db26c4c09a9c7631308e1f0fd380ff43d130c9f713`
- `validation.jsonl.gz` (581,399 bytes): `610eeb5289494d613c4c0f70aade2df8df0b499f3a24e76d232f74e6909d010a`
