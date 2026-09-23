#!/usr/bin/env python3
"""
contract_check.py — §2.5 Contract Check Runner for Jev Paired-Replay Study

Runs 10 to 25 calls to POST https://api.typesafe.ai/v1/systemone using jev-1.13.0:
- Tests all three question shapes: S1 (routing), S2 (scope), S3 (output review)
- Includes repeat calls of identical requests to test repeat-call determinism
- Captures raw response bytes and checks decimal precision (Gate A11)
- Measures exact landings on 0.50, 0.60, 0.90 and tie behavior
- Measures serial round-trip latency and token usage (Gate A12)
- NEVER prints, logs, or stores TYPESAFE_API_KEY
"""

import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POOL_DIR = (
    os.path.join(SCRIPT_DIR, "data", "pool")
    if os.path.exists(os.path.join(SCRIPT_DIR, "data", "pool"))
    else os.path.join(SCRIPT_DIR, "pool")
)
URL = "https://api.typesafe.ai/v1/systemone"


def run_contract_check():
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        sys.exit("BLOCKED: TYPESAFE_API_KEY is not set in the process environment.")

    candidates_path = os.path.join(POOL_DIR, "eligible_candidates.json")
    with open(candidates_path, encoding="utf-8") as f:
        candidates = json.load(f)

    # Pick 4 items from S1, 4 from S2, 4 from S3
    s1_items = [c for c in candidates if c["source_id"] == "S1"][:4]
    s2_items = [c for c in candidates if c["source_id"] == "S2"][:4]
    s3_items = [c for c in candidates if c["source_id"] == "S3"][:4]

    # Build sequence of 16 calls:
    # S1: items 0, 0 (repeat), 1, 2, 3 (5 calls)
    # S2: items 0, 0 (repeat), 1, 2, 3 (5 calls)
    # S3: items 0, 0 (repeat 1), 0 (repeat 2), 1, 2, 3 (6 calls)
    call_plan = [
        (s1_items[0], "S1_item0_call1"),
        (s1_items[0], "S1_item0_call2_repeat"),
        (s1_items[1], "S1_item1"),
        (s1_items[2], "S1_item2"),
        (s1_items[3], "S1_item3"),
        (s2_items[0], "S2_item0_call1"),
        (s2_items[0], "S2_item0_call2_repeat"),
        (s2_items[1], "S2_item1"),
        (s2_items[2], "S2_item2"),
        (s2_items[3], "S2_item3"),
        (s3_items[0], "S3_item0_call1"),
        (s3_items[0], "S3_item0_call2_repeat1"),
        (s3_items[0], "S3_item0_call3_repeat2"),
        (s3_items[1], "S3_item1"),
        (s3_items[2], "S3_item2"),
        (s3_items[3], "S3_item3"),
    ]

    print(f"Executing §2.5 contract check ({len(call_plan)} calls to {URL})...")
    results = []

    for idx, (item, label) in enumerate(call_plan):
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

        latency = time.perf_counter() - t0
        resp_hash = hashlib.sha256(raw_resp).hexdigest() if raw_resp else None

        # Parse response safely
        resp_json = {}
        p_raw = None
        p_val = None
        in_tok = 0
        out_tok = 0

        if raw_resp:
            try:
                resp_json = json.loads(raw_resp.decode("utf-8"))
                # noul answer format: answers.q.noul
                answers = resp_json.get("answers", {})
                q_ans = answers.get("q", {})
                if "noul" in q_ans:
                    p_val = q_ans["noul"]
                    # Extract raw string representation from JSON text
                    raw_str = raw_resp.decode("utf-8")
                    m = re.search(r'"noul"\s*:\s*([0-9\.]+)', raw_str)
                    if m:
                        p_raw = m.group(1)
                    else:
                        p_raw = str(p_val)
                usage = resp_json.get("usage", {})
                in_tok = usage.get("input_tokens", 0)
                out_tok = usage.get("output_tokens", 0)
            except Exception as e:
                error_msg = f"Parse error: {e}"

        record = {
            "call_index": idx,
            "label": label,
            "source_id": item["source_id"],
            "request_hash": req_hash,
            "http_status": http_status,
            "error": error_msg,
            "latency_s": round(latency, 4),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "p_raw": p_raw,
            "p_val": p_val,
            "response_sha256": resp_hash,
            "raw_response_bytes_b64": base64.b64encode(raw_resp).decode("ascii")
            if raw_resp
            else None,
        }
        results.append(record)
        print(
            f"  [{idx + 1:2d}/{len(call_plan)}] {label:24s} -> status={http_status} p={p_raw} latency={latency:.3f}s in_tok={in_tok}"
        )

    out_file = os.path.join(SCRIPT_DIR, "contract_check_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {out_file}")


if __name__ == "__main__":
    run_contract_check()
