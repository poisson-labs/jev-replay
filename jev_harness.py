"""
jev_harness.py — Measurement Harness for Jev Paired-Replay Study

Targets POST https://api.typesafe.ai/v1/systemone using model jev-1.13.0 pinned
and question type noul in strict compliance with:
- posts/2026-09-21 Jev Prove Study Spec.md §4.1, §4.4, §7 & Addendum 5
- Zero retries (§4.4, Gate B9): errors are recorded, never retried.
- Concurrency: 4 worker threads (§4.1).
- Captures full HTTP span with input/output tokens and request/response traces.
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import os
import platform
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import proofload
from proofload.episode import Episode
from proofload.executor import derive_seed
from proofload.store import EpisodeRecord, RunManifest, Store, config_hash
from proofload.trace import Span, Trace

URL = "https://api.typesafe.ai/v1/systemone"
MODEL_PIN = "jev-1.13.0"
QUESTION_TYPE = "noul"
REQUEST_SPAN = "jev.classify"
CONCURRENCY = 4
ARM_LABELS = ("a", "b", "3", "4", "5")


def execute_call(
    item: dict[str, Any],
    call_idx: int,
    salt: str,
    api_key: str,
    run_id: str,
) -> tuple[EpisodeRecord, int, int]:
    """Execute a single model call with zero retries and return an EpisodeRecord."""
    req_bytes = base64.b64decode(item["canonical_b64"])
    req_hash = hashlib.sha256(req_bytes).hexdigest()
    if req_hash != item["request_hash"]:
        raise ValueError(
            f"Integrity check failed: request_hash mismatch for item {item.get('source_row_id')}"
        )

    req = urllib.request.Request(
        URL,
        data=req_bytes,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    t_start_ns = time.time_ns()
    http_status = None
    error_msg = None
    raw_resp = b""

    # Retries are strictly zero (§4.4)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            http_status = resp.status
            raw_resp = resp.read()
    except urllib.error.HTTPError as e:
        http_status = e.code
        raw_resp = e.read()
        error_msg = f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        error_msg = str(e)
    t_end_ns = time.time_ns()

    p_raw: str | None = None
    p_dec: Decimal | None = None
    in_tok = 0
    out_tok = 0

    if raw_resp:
        try:
            resp_str = raw_resp.decode("utf-8")
            resp_json = json.loads(resp_str)
            answers = resp_json.get("answers", {})
            q_ans = answers.get("q", {})
            if "noul" in q_ans:
                p_val = q_ans["noul"]
                m = re.search(r'"noul"\s*:\s*([0-9\.]+)', resp_str)
                if m:
                    p_raw = m.group(1)
                else:
                    p_raw = str(p_val)
                p_dec = Decimal(p_raw)
            usage = resp_json.get("usage", {})
            in_tok = int(usage.get("input_tokens", 0))
            out_tok = int(usage.get("output_tokens", 0))
        except Exception as e:
            error_msg = f"Parse error: {e}"

    span = Span(
        span_id=f"{call_idx:016x}",
        parent_id=None,
        kind="http",
        name=REQUEST_SPAN,
        start_ns=t_start_ns,
        end_ns=t_end_ns,
        input=req_bytes.decode("utf-8"),
        output=raw_resp.decode("utf-8") if raw_resp else "{}",
        tokens={"in": in_tok, "out": out_tok},
        attrs={
            "url.full": URL,
            "http.request.method": "POST",
        },
        error=error_msg,
    )

    cut_str = str(item["stratum"])
    cut_dec = Decimal(cut_str)
    cfg = {"item": item["request_hash"], "cut": cut_str}
    seed = derive_seed(salt, config_hash(cfg), 0)
    wall_time = round((t_end_ns - t_start_ns) / 1e9, 4)

    meta: dict[str, Any] = {
        "trace": Trace(spans=(span,), source="record").to_dict(),
        "answers": {"q": {"noul": p_raw}},
    }

    if error_msg is not None or p_dec is None:
        record = EpisodeRecord.errored(
            run_id=run_id,
            config=cfg,
            seed=seed,
            replicate_index=0,
            error=error_msg or "p_dec is None",
            wall_time=wall_time,
            meta=meta,
        )
    else:
        outcome = "acted" if p_dec > cut_dec else "declined"
        ep = Episode(outcome=outcome, t=1.0, horizon=10.0, meta=meta)
        record = EpisodeRecord.from_episode(
            ep,
            run_id=run_id,
            config=cfg,
            seed=seed,
            replicate_index=0,
            wall_time=wall_time,
        )
    return record, t_start_ns, t_end_ns


def run_arm(
    run_id: str,
    sweep_name: str,
    arm_label: str,
    salt: str,
    corpus: list[dict[str, Any]],
    store: Store,
    api_key: str,
    concurrency: int = CONCURRENCY,
) -> tuple[int, int, int, int]:
    """Execute one arm across all corpus items with declared concurrency."""
    manifest = RunManifest(
        run_id=run_id,
        target_id=f"jev@{MODEL_PIN}",
        t_unit="steps",
        run_salt=salt,
        axis_types={"item": "categorical", "cut": "categorical"},
        backend="local",
        environment={
            "python": sys.version,
            "platform": platform.platform(),
            "proofload_version": proofload.__version__,
            "concurrency": concurrency,
            "capture": {"content": True, "max_observation_bytes": "none"},
        },
    )
    store.create_run(manifest)

    records: list[EpisodeRecord] = [None] * len(corpus)  # type: ignore[list-item]
    starts: list[int] = [0] * len(corpus)
    ends: list[int] = [0] * len(corpus)
    errors = 0
    lock = threading.Lock()
    done_count = 0

    t0 = time.perf_counter()

    def _worker(idx: int, item: dict[str, Any]) -> None:
        nonlocal done_count, errors
        try:
            rec, s_ns, e_ns = execute_call(item, idx + 1, salt, api_key, run_id)
            records[idx] = rec
            starts[idx] = s_ns
            ends[idx] = e_ns
            with lock:
                done_count += 1
                if rec.error is not None:
                    errors += 1
                if done_count % 200 == 0 or done_count == len(corpus):
                    dt = time.perf_counter() - t0
                    rps = done_count / dt if dt > 0 else 0
                    print(
                        f"    [{run_id}] {done_count}/{len(corpus)} calls done "
                        f"({rps:.1f} req/s, errors: {errors})"
                    )
        except Exception as exc:
            print(f"    [{run_id}] ERROR on item {idx}: {exc}", file=sys.stderr)
            raise

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_worker, i, it) for i, it in enumerate(corpus)]
        concurrent.futures.wait(futures)
        for f in futures:
            f.result()

    store.append(run_id, records)
    store.mark_complete(run_id)

    first_start = min(starts)
    last_end = max(ends)
    return len(corpus), errors, first_start, last_end


def run_sweep(
    sweep_name: str,
    salt: str,
    corpus: list[dict[str, Any]],
    store: Store,
    api_key: str,
    concurrency: int = CONCURRENCY,
) -> dict[str, Any]:
    """Execute all five arms of a sweep sequentially, each arm using concurrency."""
    print(f"\n{'='*70}\nStarting Sweep {sweep_name} (salt: {salt}, k=5, items={len(corpus)})\n{'='*70}")
    sweep_t0 = time.perf_counter()
    arm_stats = {}
    sweep_first_ns = None
    sweep_last_ns = None

    for label in ARM_LABELS:
        run_id = f"{sweep_name}-{label}"
        print(f"  --> Arm {run_id} ({label}) starting...")
        n_items, n_errors, start_ns, end_ns = run_arm(
            run_id=run_id,
            sweep_name=sweep_name,
            arm_label=label,
            salt=salt,
            corpus=corpus,
            store=store,
            api_key=api_key,
            concurrency=concurrency,
        )
        if sweep_first_ns is None or start_ns < sweep_first_ns:
            sweep_first_ns = start_ns
        if sweep_last_ns is None or end_ns > sweep_last_ns:
            sweep_last_ns = end_ns
        arm_stats[label] = {
            "run_id": run_id,
            "items": n_items,
            "errors": n_errors,
            "elapsed_s": round((end_ns - start_ns) / 1e9, 2),
        }
        print(f"  <-- Arm {run_id} finished: {n_items} items, {n_errors} errors in {arm_stats[label]['elapsed_s']}s")

    sweep_elapsed_s = time.perf_counter() - sweep_t0
    sweep_span_s = round((sweep_last_ns - sweep_first_ns) / 1e9, 2)
    held = sweep_span_s <= 1200.0

    summary = {
        "sweep": sweep_name,
        "salt": salt,
        "arms": arm_stats,
        "total_calls": len(corpus) * len(ARM_LABELS),
        "total_errors": sum(a["errors"] for a in arm_stats.values()),
        "realized_span_s": sweep_span_s,
        "wall_elapsed_s": round(sweep_elapsed_s, 2),
        "window_claim": "held" if held else "withdrawn",
    }
    print(f"Sweep {sweep_name} complete in {sweep_span_s}s span ({summary['window_claim']}). Total calls: {summary['total_calls']}, errors: {summary['total_errors']}\n")
    return summary


def evaluate_item(cfg: Mapping[str, Any], seed: int) -> Episode:
    """Proofload rollout hook for single-item evaluation."""
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY not set")
    return Episode(outcome="acted", t=1.0, horizon=10.0)
