#!/usr/bin/env python3
"""
generate_pool.py — Candidate Pool Generator for the Jev Paired-Replay Study

Implements the candidate pool specification from posts/2026-09-22 Jev Dataset Spec.md:
- Ingests raw datasets: Banking77 (S1), CLINC150 plus (S2), HelpSteer2 (S3)
- Applies exclusions in §5.5 order (field presence, language py3langid >= 0.90, length [20, 1500], PII screen, exact dedup, near dedup)
- Builds canonical request bodies and request_hash values
- Partitions into 7 declared lists and verifies ceilings (Gate A7)
- Verifies template_id is null across all rows (Gate A10)
- Assigns candidates to Range 1 (2,700), Range 2 (1,200), Range 3 (600) -> 4,500 ceiling calls
- Outputs exclusions.json, eligible_candidates.json, dry_run_hashes.json, label_text.json, sibling_map.json, DIGESTS.txt
"""

import os
import sys
import json
import gzip
import csv
import re
import unicodedata
import hashlib
import time
import math
import base64
from collections import Counter, defaultdict
import pandas as pd
import py3langid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RAW_DIR = os.environ.get("RAW_DATASETS_DIR", os.path.join(SCRIPT_DIR, "raw_datasets"))

def get_raw_dir():
    if len(sys.argv) > 1:
        return sys.argv[1]
    if os.path.exists(DEFAULT_RAW_DIR):
        return DEFAULT_RAW_DIR
    raise FileNotFoundError(f"Raw datasets directory not found at {DEFAULT_RAW_DIR}")

# PII regex patterns and Luhn check
re_email = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
re_phone = re.compile(r"(?:\+?1[-. ]?)?\(?[2-9][0-9]{2}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}|\+[1-9]\d{1,14}")
re_iban = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
re_ssn = re.compile(r"\b(?!000|666|9\d{2})\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b")
re_street = re.compile(r"\b\d+\s+[A-Za-z0-9\., ]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\b", re.IGNORECASE)
re_user_url = re.compile(r"https?://[^\s/]+/(?:users?|profile|u|~|accounts?)/[^\s/]+", re.IGNORECASE)
re_handle = re.compile(r"(?<!\w)@[a-zA-Z0-9_]{2,30}\b")
re_api_key = re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|xoxb-[0-9A-Za-z-]{20,}|AIza[0-9A-Za-z-_]{35})\b")
re_base64 = re.compile(r"\b[A-Za-z0-9+/]{30,}={0,2}\b")

def luhn_check(s):
    for match in re.finditer(r"\b\d{13,19}\b", s):
        digits = [int(c) for c in match.group(0)]
        checksum = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            if i % 2 == 1:
                d = d * 2
                if d > 9:
                    d -= 9
            checksum += d
        if checksum % 10 == 0:
            return True
    return False

def check_pii(text):
    if re_email.search(text): return "email"
    if re_phone.search(text): return "phone"
    if re_iban.search(text): return "iban"
    if luhn_check(text): return "credit_card_luhn"
    if re_ssn.search(text): return "ssn"
    if re_street.search(text): return "street_address"
    if re_user_url.search(text): return "user_url"
    if re_handle.search(text): return "handle"
    if re_api_key.search(text): return "api_key"
    if re_base64.search(text): return "base64_run"
    return None

def norm(text):
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip().casefold()

def build_pool():
    raw_dir = get_raw_dir()
    print(f"Loading raw datasets from: {raw_dir}")

    # Set up py3langid identifier with normalized probabilities
    ident = py3langid.langid._get_identifier()
    ident._norm_probs = True

    # 1. Banking77 label mapping and sibling map
    b77_train_path = os.path.join(raw_dir, "banking77", "train.csv")
    b77_cats = set()
    with open(b77_train_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            b77_cats.add(r["category"])
    sorted_b77 = sorted(list(b77_cats))
    assert len(sorted_b77) == 77, f"Expected 77 categories, found {len(sorted_b77)}"

    label_text = {cat: cat.replace("_", " ") for cat in sorted_b77}
    sibling_map = {}
    for i in sorted_b77:
        toks_i = i.split("_")
        best_j = None
        best_len = -1
        for j in sorted_b77:
            if j == i: continue
            toks_j = j.split("_")
            l = 0
            while l < len(toks_i) and l < len(toks_j) and toks_i[l] == toks_j[l]:
                l += 1
            if l > best_len:
                best_len = l
                best_j = j
            elif l == best_len:
                if best_j is None or j < best_j:
                    best_j = j
        sibling_map[i] = best_j

    with open(os.path.join(SCRIPT_DIR, "label_text.json"), "w", encoding="utf-8") as f:
        json.dump(label_text, f, indent=2)
        f.write("\n")

    with open(os.path.join(SCRIPT_DIR, "sibling_map.json"), "w", encoding="utf-8") as f:
        json.dump(sibling_map, f, indent=2)
        f.write("\n")

    scope_para = "This assistant handles: banking, credit cards, kitchen and dining, home, auto and commute, travel, utility, work, small talk, and meta requests about the assistant itself."

    # Tracking exclusions
    raw_counts = {"S1": 0, "S2": 0, "S3": 0}
    missing_field = {"S1": 0, "S2": 0, "S3": 0}
    h0_dropped = {"S1": 0, "S2": 0, "S3": 0}
    lang_excluded = {"S1": 0, "S2": 0, "S3": 0}
    len_under = {"S1": 0, "S2": 0, "S3": 0}
    len_over = {"S1": 0, "S2": 0, "S3": 0}
    pii_by_pattern = defaultdict(lambda: {"S1": 0, "S2": 0, "S3": 0})

    candidates = []

    # Source S1: Banking77
    for split in ["train", "test"]:
        csv_path = os.path.join(raw_dir, "banking77", f"{split}.csv")
        with open(csv_path, "r", encoding="utf-8") as f:
            for i, r in enumerate(csv.DictReader(f)):
                raw_counts["S1"] += 1
                t = r.get("text", "")
                cat = r.get("category", "")
                row_id = f"{split}:{i}"
                if not t or not cat:
                    missing_field["S1"] += 1
                    continue
                l, c = ident.classify(t)
                if l != "en" or c < 0.90:
                    lang_excluded["S1"] += 1
                    continue
                if len(t) < 20:
                    len_under["S1"] += 1
                    continue
                if len(t) > 1500:
                    len_over["S1"] += 1
                    continue
                pii = check_pii(t)
                if pii:
                    pii_by_pattern[pii]["S1"] += 1
                    continue

                is_sib = int(hashlib.sha256(f"S1:{row_id}".encode()).hexdigest(), 16) % 2 == 0
                variant = "sibling" if is_sib else "gold"
                target_label = sibling_map[cat] if is_sib else cat
                lbl_txt = label_text[target_label]
                state = {"channel": "customer support chat", "message": t}
                q_text = f"Should this message be routed to the queue that handles {lbl_txt}?"
                body = {
                    "model": "jev-1.13.0",
                    "questions": {"q": {"type": "noul", "instructions": q_text}},
                    "state": state
                }
                can = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                h = hashlib.sha256(can).hexdigest()
                candidates.append({
                    "source_id": "S1",
                    "source_revision": "90d4e2ee5521c04fc1488f065b8b083658768c57",
                    "source_row_id": row_id,
                    "norm_text": norm(t),
                    "request_hash": h,
                    "canonical": can,
                    "gold_label": cat,
                    "variant": variant,
                    "list_id": "S1",
                    "template_id": None,
                    "question_id": "q",
                    "question_instructions": q_text,
                    "question_sha256": hashlib.sha256(q_text.encode("utf-8")).hexdigest(),
                    "state": state,
                    "state_sha256": hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
                })

    # Source S2: CLINC150 plus
    for split in ["train", "validation", "test"]:
        pq_path = os.path.join(raw_dir, "clinc_oos", f"{split}-00000-of-00001.parquet")
        df = pd.read_parquet(pq_path)
        for i, r in df.iterrows():
            raw_counts["S2"] += 1
            t = r.get("text", "")
            intent = r.get("intent")
            row_id = f"{split}:{i}"
            if not t or intent is None:
                missing_field["S2"] += 1
                continue
            l, c = ident.classify(t)
            if l != "en" or c < 0.90:
                lang_excluded["S2"] += 1
                continue
            if len(t) < 20:
                len_under["S2"] += 1
                continue
            if len(t) > 1500:
                len_over["S2"] += 1
                continue
            pii = check_pii(t)
            if pii:
                pii_by_pattern[pii]["S2"] += 1
                continue

            list_id = "S2_oos" if intent == 42 else "S2_in_scope"
            state = {"assistant_scope": scope_para, "utterance": t}
            q_text = "Is this utterance within the assistant's stated scope?"
            body = {
                "model": "jev-1.13.0",
                "questions": {"q": {"type": "noul", "instructions": q_text}},
                "state": state
            }
            can = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            h = hashlib.sha256(can).hexdigest()
            candidates.append({
                "source_id": "S2",
                "source_revision": "155b9c710419136e17307b80d0a13e68cd46b4ec",
                "source_row_id": row_id,
                "norm_text": norm(t),
                "request_hash": h,
                "canonical": can,
                "gold_label": "oos" if intent == 42 else "in_scope",
                "variant": None,
                "list_id": list_id,
                "template_id": None,
                "question_id": "q",
                "question_instructions": q_text,
                "question_sha256": hashlib.sha256(q_text.encode("utf-8")).hexdigest(),
                "state": state,
                "state_sha256": hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
            })

    # Source S3: HelpSteer2
    for split in ["train", "validation"]:
        gz_path = os.path.join(raw_dir, "helpsteer2", f"{split}.jsonl.gz")
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            for i, line in enumerate(f):
                raw_counts["S3"] += 1
                r = json.loads(line)
                h_score = r.get("helpfulness")
                if h_score == 0:
                    h0_dropped["S3"] += 1
                    continue
                if h_score is None:
                    missing_field["S3"] += 1
                    continue
                p = r.get("prompt", "")
                resp = r.get("response", "")
                if not p or not resp:
                    missing_field["S3"] += 1
                    continue
                t_comb = p + " " + resp
                l, c = ident.classify(t_comb)
                if l != "en" or c < 0.90:
                    lang_excluded["S3"] += 1
                    continue
                if len(t_comb) < 20:
                    len_under["S3"] += 1
                    continue
                if len(t_comb) > 1500:
                    len_over["S3"] += 1
                    continue
                pii = check_pii(t_comb)
                if pii:
                    pii_by_pattern[pii]["S3"] += 1
                    continue

                list_id = f"S3_h{h_score}"
                state = {"assistant_response": resp, "user_request": p}
                q_text = "Is this response ready to send to the user as it is?"
                body = {
                    "model": "jev-1.13.0",
                    "questions": {"q": {"type": "noul", "instructions": q_text}},
                    "state": state
                }
                can = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                req_h = hashlib.sha256(can).hexdigest()
                candidates.append({
                    "source_id": "S3",
                    "source_revision": "990b2711a36180dd19d9c94b8627844866f8982a",
                    "source_row_id": f"{split}:{i}",
                    "norm_text": norm(t_comb),
                    "request_hash": req_h,
                    "canonical": can,
                    "gold_label": h_score,
                    "variant": None,
                    "list_id": list_id,
                    "template_id": None,
                    "question_id": "q",
                    "question_instructions": q_text,
                    "question_sha256": hashlib.sha256(q_text.encode("utf-8")).hexdigest(),
                    "state": state,
                    "state_sha256": hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
                })

    # Step 5: Exact dedup
    exact_groups = defaultdict(list)
    for c in candidates:
        exact_groups[c["norm_text"]].append(c)

    exact_survivors = []
    dropped_exact_by_src = defaultdict(int)
    for k, group in exact_groups.items():
        sorted_group = sorted(group, key=lambda x: x["request_hash"])
        exact_survivors.append(sorted_group[0])
        for dropped in sorted_group[1:]:
            dropped_exact_by_src[dropped["source_id"]] += 1

    # Step 6: Prefix-filtering near-dedup (5-gram Jaccard >= 0.90)
    t0 = time.time()
    item_ngrams = []
    ngram_freq = Counter()
    for c in exact_survivors:
        nt = c["norm_text"]
        ngs = set(nt[i:i+5] for i in range(len(nt)-4))
        item_ngrams.append(ngs)
        ngram_freq.update(ngs)

    sorted_item_indices = sorted(range(len(exact_survivors)), key=lambda i: len(item_ngrams[i]))
    sorted_ngrams_per_item = {}
    for i in sorted_item_indices:
        sorted_ngrams_per_item[i] = sorted(list(item_ngrams[i]), key=lambda g: ngram_freq[g])

    inv_index = defaultdict(list)
    pairs = set()
    for idx in sorted_item_indices:
        ng_list = sorted_ngrams_per_item[idx]
        size_a = len(ng_list)
        if size_a == 0: continue
        prefix_len = size_a - math.ceil(0.90 * size_a) + 1
        prefix_tokens = ng_list[:prefix_len]
        candidates_seen = set()
        for tok in prefix_tokens:
            for prev_idx in inv_index[tok]:
                if prev_idx in candidates_seen: continue
                candidates_seen.add(prev_idx)
                size_b = len(item_ngrams[prev_idx])
                if size_b < 0.90 * size_a: continue
                inter = len(item_ngrams[idx] & item_ngrams[prev_idx])
                union_len = size_a + size_b - inter
                if union_len > 0 and inter / union_len >= 0.90:
                    pairs.add((min(idx, prev_idx), max(idx, prev_idx)))
            inv_index[tok].append(idx)

    parent = {}
    def find(i):
        if parent.setdefault(i, i) != i:
            parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        pi, pj = find(i), find(j)
        if pi != pj: parent[pi] = pj

    for i, j in pairs:
        union(i, j)

    clusters = defaultdict(list)
    for i in range(len(exact_survivors)):
        if i in parent:
            clusters[find(i)].append(i)

    clustered_indices = set()
    largest_cluster_size = 0
    dropped_near_by_src = defaultdict(int)
    near_survivors = []

    for root, members in clusters.items():
        if len(members) > largest_cluster_size:
            largest_cluster_size = len(members)
        sorted_m = sorted(members, key=lambda idx: exact_survivors[idx]["request_hash"])
        survivor_idx = sorted_m[0]
        clustered_indices.update(members)
        near_survivors.append(exact_survivors[survivor_idx])
        for dropped_idx in sorted_m[1:]:
            dropped_near_by_src[exact_survivors[dropped_idx]["source_id"]] += 1

    for i in range(len(exact_survivors)):
        if i not in clustered_indices:
            near_survivors.append(exact_survivors[i])

    # Record exclusions summary
    exclusions_record = {
        "raw_counts": raw_counts,
        "missing_field": missing_field,
        "helpfulness_0_dropped": h0_dropped,
        "language_excluded": lang_excluded,
        "length_under_20": len_under,
        "length_over_1500": len_over,
        "pii_removals": {
            pat: dict(pii_by_pattern[pat]) for pat in sorted(pii_by_pattern.keys())
        },
        "pii_totals": {src: sum(pii_by_pattern[p][src] for p in pii_by_pattern) for src in ["S1", "S2", "S3"]},
        "exact_dedup_dropped": dict(dropped_exact_by_src),
        "near_dedup": {
            "clusters_count": len(clusters),
            "largest_cluster_size": largest_cluster_size,
            "dropped_by_source": dict(dropped_near_by_src),
            "total_dropped": sum(dropped_near_by_src.values())
        },
        "final_eligible_count": len(near_survivors),
        "arithmetic_reconciliation": {
            src: {
                "raw": raw_counts[src],
                "excluded_pre_dedup": (
                    missing_field[src] + h0_dropped[src] + lang_excluded[src] +
                    len_under[src] + len_over[src] + sum(pii_by_pattern[p][src] for p in pii_by_pattern)
                ),
                "exact_dedup_dropped": dropped_exact_by_src[src],
                "near_dedup_dropped": dropped_near_by_src[src],
                "eligible": sum(1 for c in near_survivors if c["source_id"] == src)
            } for src in ["S1", "S2", "S3"]
        }
    }
    with open(os.path.join(SCRIPT_DIR, "exclusions.json"), "w", encoding="utf-8") as f:
        json.dump(exclusions_record, f, indent=2)
        f.write("\n")

    # Group by list
    by_list = defaultdict(list)
    for c in near_survivors:
        by_list[c["list_id"]].append(c)

    # Sort each list ascending by request_hash
    ordered_lists = {}
    dry_run_hashes = {}
    ceilings = {
        "S1": 1500,
        "S2_in_scope": 750,
        "S2_oos": 750,
        "S3_h1": 375,
        "S3_h2": 375,
        "S3_h3": 375,
        "S3_h4": 375
    }

    print("\n--- List Verification Against Ceilings (Gate A7) ---")
    for lid in sorted(ceilings.keys()):
        sorted_list = sorted(by_list[lid], key=lambda x: x["request_hash"])
        ordered_lists[lid] = sorted_list
        hashes = [x["request_hash"] for x in sorted_list]
        full_str = "\n".join(hashes) + "\n"
        list_sha256 = hashlib.sha256(full_str.encode("utf-8")).hexdigest()
        dry_run_hashes[lid] = {
            "count": len(hashes),
            "ceiling": ceilings[lid],
            "surplus": len(hashes) - ceilings[lid],
            "first_20": hashes[:20],
            "list_sha256": list_sha256
        }
        status = "PASSED" if len(hashes) >= ceilings[lid] else "FAILED"
        print(f"  {lid:15s}: realized={len(hashes):5d}, ceiling={ceilings[lid]:4d}, surplus={len(hashes)-ceilings[lid]:5d} [{status}]")
        assert len(hashes) >= ceilings[lid], f"List {lid} shortfall: {len(hashes)} < {ceilings[lid]}"

    with open(os.path.join(SCRIPT_DIR, "dry_run_hashes.json"), "w", encoding="utf-8") as f:
        json.dump(dry_run_hashes, f, indent=2)
        f.write("\n")

    # Slice into Range 1, Range 2, Range 3
    range_allocations = {
        1: {"S1": 900, "S2_in_scope": 450, "S2_oos": 450, "S3_h1": 225, "S3_h2": 225, "S3_h3": 225, "S3_h4": 225},
        2: {"S1": 400, "S2_in_scope": 200, "S2_oos": 200, "S3_h1": 100, "S3_h2": 100, "S3_h3": 100, "S3_h4": 100},
        3: {"S1": 200, "S2_in_scope": 100, "S2_oos": 100, "S3_h1": 50,  "S3_h2": 50,  "S3_h3": 50,  "S3_h4": 50}
    }

    # Offsets in each list
    list_offsets = {lid: 0 for lid in ceilings}
    final_candidates = []
    global_order_index = 0

    for r_num in [1, 2, 3]:
        alloc = range_allocations[r_num]
        range_items = []
        for lid, count in alloc.items():
            start = list_offsets[lid]
            end = start + count
            items = ordered_lists[lid][start:end]
            list_offsets[lid] = end
            for it in items:
                it_copy = dict(it)
                it_copy["range"] = r_num
                range_items.append(it_copy)
        
        # Sort range_items ascending by request_hash across all sources (§5.6 Step 3)
        sorted_range = sorted(range_items, key=lambda x: x["request_hash"])
        for it in sorted_range:
            it["order_index"] = global_order_index
            it["canonical_b64"] = base64.b64encode(it["canonical"]).decode("ascii")
            del it["canonical"]
            del it["norm_text"]
            final_candidates.append(it)
            global_order_index += 1

    assert len(final_candidates) == 4500, f"Expected 4,500 candidates, got {len(final_candidates)}"
    assert all(c["template_id"] is None for c in final_candidates), "Gate A10 failure: non-null template_id found!"

    print(f"\nFinal ceiling candidates built: {len(final_candidates)} items across 3 ranges.")
    print(f"  Range 1: 2700 items (indices 0..2699)")
    print(f"  Range 2: 1200 items (indices 2700..3899)")
    print(f"  Range 3:  600 items (indices 3900..4499)")

    cand_path = os.path.join(SCRIPT_DIR, "eligible_candidates.json")
    with open(cand_path, "w", encoding="utf-8") as f:
        json.dump(final_candidates, f, indent=2)
        f.write("\n")

    # Generate DIGESTS.txt for all files in pool/
    files_to_hash = [
        "SOURCES.md",
        "py3langid_version.txt",
        "scope_paragraph.txt",
        "band_definitions.json",
        "per_source_cap.json",
        "range_table.json",
        "under_fill_rule.md",
        "pii_patterns.json",
        "label_text.json",
        "sibling_map.json",
        "exclusions.json",
        "dry_run_hashes.json",
        "generate_pool.py",
        "eligible_candidates.json"
    ]
    digests_lines = []
    for fname in sorted(files_to_hash):
        fpath = os.path.join(SCRIPT_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            digests_lines.append(f"{h}  {fname}")

    digests_path = os.path.join(SCRIPT_DIR, "DIGESTS.txt")
    with open(digests_path, "w", encoding="utf-8") as f:
        f.write("\n".join(digests_lines) + "\n")

    print("\nDIGESTS.txt generated successfully:")
    for line in digests_lines:
        print(f"  {line}")

if __name__ == "__main__":
    build_pool()
