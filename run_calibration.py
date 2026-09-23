#!/usr/bin/env python3
"""
run_calibration.py — Candidate Pool Calibration Pass Runner for Jev Paired-Replay Study

Executes the candidate calibration pass against POST https://api.typesafe.ai/v1/systemone
using model jev-1.13.0 in accordance with:
- posts/2026-09-22 Jev Dataset Spec.md §5 & §6
- posts/2026-09-21 Jev Prove Study Spec.md Addendum 4

Constraints:
- Fixed hash ordering: walks eligible_candidates.json in (range, request_hash) order
- Concurrency: 4 worker threads (matching study spec §4.1 declared concurrency)
- No retries (Gate B9): 0 retries on any error
- Per-source cap: 120 items per stratum per source
- Half-open disjoint bands: [0.45, 0.55) -> S(0.50), [0.55, 0.65) -> S(0.60), [0.85, 0.95] -> S(0.90)
- Decimals evaluated with Decimal for exact lattice comparison
- Hard stops: all 3 strata full; 4,500 calls; 2,444,000 input tokens; spend >= $1.00
- NEVER prints, logs, or stores TYPESAFE_API_KEY
"""

import base64
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POOL_DIR = (
    os.path.join(SCRIPT_DIR, "data", "pool")
    if os.path.exists(os.path.join(SCRIPT_DIR, "data", "pool"))
    else os.path.join(SCRIPT_DIR, "pool")
)
URL = "https://api.typesafe.ai/v1/systemone"

PRICE_PER_MTOK_IN = 0.042
SPEND_LIMIT = 1.00
CALIBRATION_IN_TOK_LIMIT = 2_444_000
CONCURRENCY = 4

STRATA_CONFIG = {
    "0.50": {"low": Decimal("0.45"), "high": Decimal("0.55"), "closed_right": False},
    "0.60": {"low": Decimal("0.55"), "high": Decimal("0.65"), "closed_right": False},
    "0.90": {"low": Decimal("0.85"), "high": Decimal("0.95"), "closed_right": True},
}


def determine_band(p_dec):
    if p_dec is None:
        return None
    for stratum, cfg in STRATA_CONFIG.items():
        if cfg["closed_right"]:
            if cfg["low"] <= p_dec <= cfg["high"]:
                return stratum
        else:
            if cfg["low"] <= p_dec < cfg["high"]:
                return stratum
    return None


def execute_call(item, api_key):
    req_bytes = base64.b64decode(item["canonical_b64"])
    req_hash = hashlib.sha256(req_bytes).hexdigest()
    assert req_hash == item["request_hash"], "Integrity check failed: request_hash mismatch!"

    req = urllib.request.Request(
        URL,
        data=req_bytes,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    http_status = None
    error_msg = None
    raw_resp = b""

    # Gate B9: Retries are strictly zero
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            http_status = resp.status
            raw_resp = resp.read()
    except urllib.error.HTTPError as e:
        http_status = e.code
        raw_resp = e.read()
        error_msg = str(e)
    except Exception as e:
        error_msg = str(e)

    dt = time.perf_counter() - t0
    resp_time_iso = datetime.now(UTC).isoformat()
    resp_hash = hashlib.sha256(raw_resp).hexdigest() if raw_resp else None

    p_raw = None
    p_dec = None
    in_tok = 0
    out_tok = 0

    if raw_resp:
        try:
            resp_json = json.loads(raw_resp.decode("utf-8"))
            answers = resp_json.get("answers", {})
            q_ans = answers.get("q", {})
            if "noul" in q_ans:
                p_val = q_ans["noul"]
                raw_str = raw_resp.decode("utf-8")
                m = re.search(r'"noul"\s*:\s*([0-9\.]+)', raw_str)
                if m:
                    p_raw = m.group(1)
                else:
                    p_raw = str(p_val)
                p_dec = Decimal(p_raw)
            usage = resp_json.get("usage", {})
            in_tok = usage.get("input_tokens", 0)
            out_tok = usage.get("output_tokens", 0)
        except Exception as e:
            error_msg = f"Parse error: {e}"

    return {
        "item": item,
        "request_hash": req_hash,
        "http_status": http_status,
        "error": error_msg,
        "timestamp": resp_time_iso,
        "latency_s": round(dt, 4),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "p_raw": p_raw,
        "p_dec": p_dec,
        "response_sha256": resp_hash,
        "raw_response_bytes_b64": base64.b64encode(raw_resp).decode("ascii") if raw_resp else None,
    }


def run_calibration():
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        sys.exit("BLOCKED: TYPESAFE_API_KEY is not set in environment.")

    candidates_path = os.path.join(POOL_DIR, "eligible_candidates.json")
    with open(candidates_path, encoding="utf-8") as f:
        candidates = json.load(f)

    # Verify pool integrity
    digests_path = os.path.join(POOL_DIR, "DIGESTS.txt")
    with open(digests_path, encoding="utf-8") as f:
        for line in f:
            if "eligible_candidates.json" in line:
                expected_hash = line.strip().split()[0]
                with open(candidates_path, "rb") as cf:
                    actual_hash = hashlib.sha256(cf.read()).hexdigest()
                assert actual_hash == expected_hash, (
                    f"Integrity check failed: {actual_hash} != {expected_hash}"
                )

    print(f"Loaded {len(candidates)} candidates from frozen pool.")

    # Partition by declared range
    range1_items = [c for c in candidates if c.get("range") == 1]
    range2_items = [c for c in candidates if c.get("range") == 2]
    range3_items = [c for c in candidates if c.get("range") == 3]

    print(
        f"Declared ranges: Range 1 = {len(range1_items)}, Range 2 = {len(range2_items)}, Range 3 = {len(range3_items)}"
    )

    stratum_counts = {"0.50": 0, "0.60": 0, "0.90": 0}
    source_counts = {
        "0.50": {"S1": 0, "S2": 0, "S3": 0},
        "0.60": {"S1": 0, "S2": 0, "S3": 0},
        "0.90": {"S1": 0, "S2": 0, "S3": 0},
    }
    ties_at_cut = {"0.50": 0, "0.60": 0, "0.90": 0}
    p_distributions = {"0.50": {}, "0.60": {}, "0.90": {}}

    manifest_records = []
    corpus_items = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_calls_made = 0
    call_errors = []

    def is_all_strata_full():
        return all(stratum_counts[s] == 300 for s in ["0.50", "0.60", "0.90"])

    def process_range(range_items, range_num):
        nonlocal total_input_tokens, total_output_tokens, total_calls_made

        print()
        print("=" * 60)
        print(
            f"Executing Range {range_num} ({len(range_items)} candidates, concurrency={CONCURRENCY})..."
        )
        print("=" * 60)

        range_results = [None] * len(range_items)
        lock = threading.Lock()
        completed_count = 0
        t_start = time.perf_counter()

        def worker(idx, item):
            nonlocal completed_count
            res = execute_call(item, api_key)
            range_results[idx] = res
            with lock:
                completed_count += 1
                if completed_count % 100 == 0 or completed_count == len(range_items):
                    elapsed = time.perf_counter() - t_start
                    rps = completed_count / elapsed if elapsed > 0 else 0
                    print(
                        f"  [Range {range_num}] {completed_count:4d}/{len(range_items)} calls completed ({rps:.1f} req/s, {elapsed:.1f}s elapsed)"
                    )

        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = [executor.submit(worker, i, item) for i, item in enumerate(range_items)]
            concurrent.futures.wait(futures)

        print(
            f"Range {range_num} finished in {time.perf_counter() - t_start:.2f}s. Placing items in global hash order..."
        )

        for _idx, res in enumerate(range_results):
            total_calls_made += 1
            in_tok = res["input_tokens"]
            out_tok = res["output_tokens"]
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            if res["error"]:
                call_errors.append({"call_index": total_calls_made, "error": res["error"]})

            p_dec = res["p_dec"]
            p_raw = res["p_raw"]
            source = res["item"]["source_id"]
            band = determine_band(p_dec)

            stratum_assigned = None
            fill_idx = None

            if band is not None:
                if stratum_counts[band] < 300 and source_counts[band][source] < 120:
                    stratum_assigned = band
                    fill_idx = stratum_counts[band]
                    stratum_counts[band] += 1
                    source_counts[band][source] += 1

                    cut_dec = Decimal(band)
                    if p_dec == cut_dec:
                        ties_at_cut[band] += 1

                    p_distributions[band][p_raw] = p_distributions[band].get(p_raw, 0) + 1

                    corpus_entry = {
                        "stratum": band,
                        "cut": float(band),
                        "fill_index": fill_idx,
                        "request_hash": res["request_hash"],
                        "source_id": source,
                        "source_row_id": res["item"]["source_row_id"],
                        "list_id": res["item"]["list_id"],
                        "range": range_num,
                        "p_raw": p_raw,
                        "p_cal": float(p_dec),
                        "canonical_b64": res["item"]["canonical_b64"],
                        "state": res["item"]["state"],
                        "question_instructions": res["item"]["question_instructions"],
                    }
                    corpus_items.append(corpus_entry)

            manifest_record = {
                "call_index": total_calls_made,
                "order_index": res["item"]["order_index"],
                "range": range_num,
                "source_id": source,
                "source_row_id": res["item"]["source_row_id"],
                "request_hash": res["request_hash"],
                "timestamp": res["timestamp"],
                "latency_s": res["latency_s"],
                "http_status": res["http_status"],
                "error": res["error"],
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "p_raw": p_raw,
                "p_cal": float(p_dec) if p_dec is not None else None,
                "stratum_assigned": stratum_assigned,
                "fill_index": fill_idx,
                "response_sha256": res["response_sha256"],
                "raw_response_bytes_b64": res["raw_response_bytes_b64"],
            }
            manifest_records.append(manifest_record)

            spend = total_input_tokens * (PRICE_PER_MTOK_IN / 1_000_000)
            if spend >= SPEND_LIMIT:
                print(f"STOP: Spend limit reached (${spend:.4f} >= ${SPEND_LIMIT})!")
                return True

            if total_input_tokens >= CALIBRATION_IN_TOK_LIMIT:
                print(
                    f"STOP: Token ceiling reached ({total_input_tokens} >= {CALIBRATION_IN_TOK_LIMIT})!"
                )
                return True

        spend = total_input_tokens * (PRICE_PER_MTOK_IN / 1_000_000)
        print()
        print(f"Status after Range {range_num}:")
        print(
            f"  Calls: {total_calls_made}, Input Tokens: {total_input_tokens:,}, Spend: ${spend:.5f}"
        )
        for s in ["0.50", "0.60", "0.90"]:
            print(
                f"  Stratum {s:4s}: {stratum_counts[s]:3d}/300 (S1: {source_counts[s]['S1']}, S2: {source_counts[s]['S2']}, S3: {source_counts[s]['S3']}, ties: {ties_at_cut[s]})"
            )

        return is_all_strata_full()

    # Step 3: Range 1
    done = process_range(range1_items, 1)

    # Step 3: Range 2 if needed
    if not done and not is_all_strata_full():
        spend = total_input_tokens * (PRICE_PER_MTOK_IN / 1_000_000)
        if spend < SPEND_LIMIT and total_input_tokens < CALIBRATION_IN_TOK_LIMIT:
            done = process_range(range2_items, 2)

    # Step 3: Range 3 if needed
    if not done and not is_all_strata_full():
        spend = total_input_tokens * (PRICE_PER_MTOK_IN / 1_000_000)
        if spend < SPEND_LIMIT and total_input_tokens < CALIBRATION_IN_TOK_LIMIT:
            done = process_range(range3_items, 3)

    spend = total_input_tokens * (PRICE_PER_MTOK_IN / 1_000_000)
    print()
    print("=" * 60)
    print("CALIBRATION PASS COMPLETE")
    print("=" * 60)
    print(f"Total calls: {total_calls_made}")
    print(f"Total input tokens: {total_input_tokens:,}")
    print(f"Total output tokens: {total_output_tokens:,}")
    print(f"Total spend: ${spend:.6f}")
    print(f"Total errors: {len(call_errors)}")

    corpus_items.sort(key=lambda x: (x["stratum"], x["fill_index"]))

    manifest_path = os.path.join(SCRIPT_DIR, "manifest_calibration.jsonl")
    with open(manifest_path, "w", encoding="utf-8") as f:
        for rec in manifest_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Saved manifest: {manifest_path} ({len(manifest_records)} records)")

    corpus_fname = (
        "corpus_jev_900.json"
        if len(corpus_items) == 900
        else f"corpus_jev_realized_{len(corpus_items)}.json"
    )
    corpus_path = os.path.join(SCRIPT_DIR, corpus_fname)
    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(corpus_items, f, indent=2, ensure_ascii=False)
    corpus_hash = hashlib.sha256(open(corpus_path, "rb").read()).hexdigest()
    print(f"Saved corpus: {corpus_path} ({len(corpus_items)} items, SHA256: {corpus_hash})")

    summary = {
        "total_calls": total_calls_made,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_spend_usd": round(spend, 6),
        "total_errors": len(call_errors),
        "errors": call_errors,
        "all_strata_full": is_all_strata_full(),
        "stratum_counts": stratum_counts,
        "source_counts_3x3": source_counts,
        "ties_at_cut": ties_at_cut,
        "p_distributions": p_distributions,
        "corpus_file": corpus_fname,
        "corpus_sha256": corpus_hash,
        "corpus_count": len(corpus_items),
        "under_fill": {
            s: 300 - stratum_counts[s] for s in ["0.50", "0.60", "0.90"] if stratum_counts[s] < 300
        },
    }
    summary_path = os.path.join(SCRIPT_DIR, "calibration_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary: {summary_path}")


if __name__ == "__main__":
    run_calibration()
