#!/usr/bin/env python3
"""Independent recompute of the Jev paired-replay headline numbers.

Reads the stored episode parquet rows under jev-measurement/store/.
Shares no code with proofload / Prove. Does not import proofload.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
STORE = (HERE / "data" / "store") if (HERE / "data" / "store").exists() else (HERE / "store")
PAIRED = (HERE / "data" / "paired") if (HERE / "data" / "paired").exists() else (HERE / "paired")

B = 10_000
SEED = 20260921
ALPHA = 0.05
FLOOR = Decimal("0.01")

SWEEPS = ("S1", "S2", "S3")
ARM_LABELS = ("a", "b", "3", "4", "5")
PAIR_ARMS = ("a", "b")
CUT_NAMES = ("0.50", "0.60", "0.90")
THRESHOLDS = {name: Decimal(name) for name in CUT_NAMES}

RUNS = {
    sweep: {arm: f"{sweep}-{arm}" for arm in ARM_LABELS} for sweep in SWEEPS
}

COUNT_TOL = 0  # exact
INTERVAL_TOL = Fraction(1, 10**12)  # stated: exact counts; intervals to 1e-12


def _parse_config(raw: str) -> tuple[str, str]:
    obj = json.loads(raw)
    return str(obj["cut"]), str(obj["item"])


def _parse_noul(meta_raw: str | None) -> Decimal | None:
    if not meta_raw:
        return None
    meta = json.loads(meta_raw)
    val = meta.get("answers", {}).get("q", {}).get("noul")
    if val is None or val == "":
        return None
    p = Decimal(str(val))
    if p < 0 or p > 1:
        return None
    return p


def _request_input(trace_obs_raw: str | None) -> str | None:
    if not trace_obs_raw:
        return None
    obs = json.loads(trace_obs_raw)
    for rec in obs.values():
        inp = rec.get("input")
        if inp:
            return inp
    return None


def load_store() -> dict:
    """rows[(run_id, item)] = record; also global inventories."""
    rows = {}
    file_hashes = {}
    run_ids_by_file = {}
    keys_seen = []
    request_by_run_item = {}
    errors = []

    for sweep in SWEEPS:
        for arm in ARM_LABELS:
            run_id = RUNS[sweep][arm]
            path = STORE / run_id / "episodes" / "part-00000.parquet"
            data = path.read_bytes()
            file_hashes[str(path)] = hashlib.sha256(data).hexdigest()
            table = pq.read_table(path)
            d = table.to_pydict()
            n = len(d["run_id"])
            run_ids = set(d["run_id"])
            run_ids_by_file[str(path)] = sorted(run_ids)
            for i in range(n):
                cut, item = _parse_config(d["config"][i])
                key = (d["run_id"][i], d["config_hash"][i], d["replicate_index"][i])
                keys_seen.append(key)
                rec = {
                    "run_id": d["run_id"][i],
                    "sweep": sweep,
                    "arm": arm,
                    "cut": cut,
                    "item": item,
                    "config_hash": d["config_hash"][i],
                    "replicate_index": d["replicate_index"][i],
                    "error": d["error"][i],
                    "noul": _parse_noul(d["meta"][i]),
                    "outcome": d["outcome"][i],
                }
                rows[(run_id, item)] = rec
                request_by_run_item[(run_id, item)] = _request_input(d["trace_obs"][i])
                if rec["error"]:
                    errors.append(rec)
    return {
        "rows": rows,
        "file_hashes": file_hashes,
        "run_ids_by_file": run_ids_by_file,
        "keys_seen": keys_seen,
        "request_by_run_item": request_by_run_item,
        "errors": errors,
    }


def action(p: Decimal, c: Decimal, rule: str) -> int:
    if rule == "gt":
        return 1 if p > c else 0
    if rule == "ge":
        return 1 if p >= c else 0
    raise ValueError(rule)


def is_tie(p: Decimal, c: Decimal) -> bool:
    return p == c


def mcnemar_p(n10: int, n01: int) -> Fraction:
    nd = n10 + n01
    if nd == 0:
        return Fraction(1)
    k = min(n10, n01)
    s = sum(math.comb(nd, i) for i in range(k + 1))
    # min(1, 2 * s / 2^nd) = min(1, s / 2^{nd-1})
    p = Fraction(s, 2 ** (nd - 1)) if nd >= 1 else Fraction(1)
    return min(Fraction(1), p)


def clopper_pearson(k: int, n: int, alpha: float = ALPHA) -> tuple[float, float]:
    """Two-sided exact (Clopper–Pearson) interval via the beta quantile."""
    from scipy.stats import beta

    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return lo, hi


def icc_oneway(clusters: list[list[float]]) -> tuple[float, float, float]:
    """One-way ANOVA ICC(1) and deff = 1 + (m_bar - 1) ρ. Unbalanced k0."""
    ys = [np.asarray(c, dtype=float) for c in clusters if c]
    G = len(ys)
    N = int(sum(len(c) for c in ys))
    if G < 2 or N <= G:
        return (float("nan"), float(N / G) if G else float("nan"), float("nan"))
    m_bar = N / G
    grand = float(np.concatenate(ys).mean())
    ssb = 0.0
    ssw = 0.0
    ns = []
    for c in ys:
        ni = len(c)
        ns.append(ni)
        mean_i = float(c.mean())
        ssb += ni * (mean_i - grand) ** 2
        ssw += float(np.sum((c - mean_i) ** 2))
    dfb = G - 1
    dfw = N - G
    msb = ssb / dfb
    msw = ssw / dfw if dfw else 0.0
    sum_n2 = float(sum(n * n for n in ns))
    k0 = (N - sum_n2 / N) / dfb
    denom = msb + (k0 - 1.0) * msw
    if denom == 0:
        rho = 0.0
    else:
        rho = (msb - msw) / denom
    deff = 1.0 + (m_bar - 1.0) * rho
    return rho, m_bar, deff


def cluster_bootstrap(clusters: list[list[float]], b: int = B, seed: int = SEED) -> tuple[float, float, float]:
    """Percentile cluster bootstrap: resample items, concat observations, mean."""
    ordered = [np.asarray(c, dtype=float) for c in clusters]
    G = len(ordered)
    rng = np.random.default_rng(seed)
    stats = np.empty(b, dtype=float)
    for i in range(b):
        idx = rng.integers(0, G, size=G)
        concat = np.concatenate([ordered[j] for j in idx])
        stats[i] = float(concat.mean()) if concat.size else float("nan")
    lo, hi = np.percentile(stats, [2.5, 97.5])
    point = float(np.concatenate(ordered).mean()) if G else float("nan")
    return point, float(lo), float(hi)


def majority(bits: list[int]) -> int:
    return 1 if sum(bits) * 2 > len(bits) else 0


def build_cells(store: dict) -> dict:
    """cells[cut][item][sweep] = {arm: rec}."""
    cells = {cut: defaultdict(dict) for cut in CUT_NAMES}
    for (run_id, item), rec in store["rows"].items():
        cells[rec["cut"]].setdefault(item, {})
        cells[rec["cut"]][item][rec["sweep"]] = cells[rec["cut"]][item].get(rec["sweep"], {})
        cells[rec["cut"]][item][rec["sweep"]][rec["arm"]] = rec
    return cells


def pair_eligible(sweep_arms: dict) -> bool:
    for arm in PAIR_ARMS:
        rec = sweep_arms.get(arm)
        if rec is None or rec["error"] or rec["noul"] is None:
            return False
    return True


def k_eligible(sweep_arms: dict) -> bool:
    for arm in ARM_LABELS:
        rec = sweep_arms.get(arm)
        if rec is None or rec["error"] or rec["noul"] is None:
            return False
    return True


def analyse_cut(cut: str, items: dict, rule: str, pair_follows_k: bool = False) -> dict:
    c = THRESHOLDS[cut]
    # Pair analysis: a vs b whenever both returned, unless pair_follows_k
    # (Prove's behaviour: drop the item-sweep from the pair if any of five erred).
    per_sweep = {s: {"n11": 0, "n10": 0, "n01": 0, "n00": 0, "ties_a": 0, "ties_b": 0} for s in SWEEPS}
    flip_clusters = {}  # item -> list of 0/1
    swing_clusters = {}  # item -> list of -1/0/+1
    agree_clusters = {j: {} for j in range(2, 6)}
    ms_clusters = {j: {} for j in (1, 3, 5)}
    k_excluded = []
    pair_excluded_by_k_but_pair_ok = []
    ties_arm = {arm: 0 for arm in ARM_LABELS}

    item_ids = sorted(items)
    for item in item_ids:
        sweeps = items[item]
        flips = []
        swings = []
        agree_obs = {j: [] for j in range(2, 6)}
        majority_by_sweep = {j: {} for j in (1, 3, 5)}
        for sweep in SWEEPS:
            arms = sweeps.get(sweep, {})
            pe = pair_eligible(arms)
            ke = k_eligible(arms)
            if pair_follows_k:
                pe = pe and ke
            if pe:
                pa, pb = arms["a"]["noul"], arms["b"]["noul"]
                aa, ab = action(pa, c, rule), action(pb, c, rule)
                if aa == 1 and ab == 1:
                    per_sweep[sweep]["n11"] += 1
                elif aa == 1 and ab == 0:
                    per_sweep[sweep]["n10"] += 1
                elif aa == 0 and ab == 1:
                    per_sweep[sweep]["n01"] += 1
                else:
                    per_sweep[sweep]["n00"] += 1
                if is_tie(pa, c):
                    per_sweep[sweep]["ties_a"] += 1
                if is_tie(pb, c):
                    per_sweep[sweep]["ties_b"] += 1
                flips.append(1 if aa != ab else 0)
                swings.append(ab - aa)
            if ke:
                vals = [arms[a]["noul"] for a in ARM_LABELS]
                acts = [action(p, c, rule) for p in vals]
                for arm, p in zip(ARM_LABELS, vals):
                    if is_tie(p, c):
                        ties_arm[arm] += 1
                for j in range(2, 6):
                    prefix = acts[:j]
                    agree_obs[j].append(1 if len(set(prefix)) == 1 else 0)
                for j in (1, 3, 5):
                    majority_by_sweep[j][sweep] = majority(acts[:j])
            else:
                # record k exclusion
                cause_arm = None
                detail = None
                for arm in ARM_LABELS:
                    rec = arms.get(arm)
                    if rec is None or rec["error"] or rec["noul"] is None:
                        cause_arm = arm
                        detail = None if rec is None else rec["error"]
                        break
                k_excluded.append(
                    {
                        "sweep": sweep,
                        "item": item,
                        "arm": cause_arm,
                        "detail": detail,
                        "pair_ok": pe,
                    }
                )
                if pe:
                    pair_excluded_by_k_but_pair_ok.append(
                        {
                            "sweep": sweep,
                            "item": item,
                            "arm": cause_arm,
                            "detail": detail,
                            "noul_a": str(arms["a"]["noul"]),
                            "noul_b": str(arms["b"]["noul"]),
                            "act_a": action(arms["a"]["noul"], c, "gt"),
                            "act_b": action(arms["b"]["noul"], c, "gt"),
                        }
                    )
        if flips:
            flip_clusters[item] = flips
            swing_clusters[item] = swings
        for j in range(2, 6):
            if agree_obs[j]:
                agree_clusters[j][item] = agree_obs[j]
        for j in (1, 3, 5):
            present = [s for s in SWEEPS if s in majority_by_sweep[j]]
            obs = []
            for i, s1 in enumerate(present):
                for s2 in present[i + 1 :]:
                    obs.append(1 if majority_by_sweep[j][s1] == majority_by_sweep[j][s2] else 0)
            if obs:
                ms_clusters[j][item] = obs

    n_pairs = sum(sum(per_sweep[s][k] for k in ("n11", "n10", "n01", "n00")) for s in SWEEPS)
    n10 = sum(per_sweep[s]["n10"] for s in SWEEPS)
    n01 = sum(per_sweep[s]["n01"] for s in SWEEPS)
    n11 = sum(per_sweep[s]["n11"] for s in SWEEPS)
    n00 = sum(per_sweep[s]["n00"] for s in SWEEPS)
    d_flip = n10 + n01
    delta = n01 - n10
    flip_rate = Fraction(d_flip, n_pairs) if n_pairs else Fraction(0)
    net_swing = Fraction(delta, n_pairs) if n_pairs else Fraction(0)

    items_sorted = sorted(flip_clusters)
    flip_lists = [flip_clusters[i] for i in items_sorted]
    swing_lists = [swing_clusters[i] for i in items_sorted]
    n_flip_items = sum(1 for lst in flip_lists if any(lst))
    if n_flip_items < 5:
        # fallback not expected here; still compute bootstrap for comparison
        fr_hat, fr_lo, fr_hi = cluster_bootstrap(flip_lists)
        sw_hat, sw_lo, sw_hi = cluster_bootstrap(swing_lists)
        basis = "exact_upper_one_sided"
    else:
        fr_hat, fr_lo, fr_hi = cluster_bootstrap(flip_lists)
        sw_hat, sw_lo, sw_hi = cluster_bootstrap(swing_lists)
        basis = "cluster_bootstrap"

    rho, m_bar, deff = icc_oneway(flip_lists)

    if fr_lo == 0 and fr_hi < float(FLOOR):
        outcome = "A"
    elif fr_lo > 0:
        outcome = "B"
    else:
        outcome = "C"

    sweep_out = {}
    for s in SWEEPS:
        n = sum(per_sweep[s][k] for k in ("n11", "n10", "n01", "n00"))
        d = per_sweep[s]["n10"] + per_sweep[s]["n01"]
        p_mc = mcnemar_p(per_sweep[s]["n10"], per_sweep[s]["n01"])
        lo, hi = clopper_pearson(d, n)
        rate_a = Fraction(per_sweep[s]["n11"] + per_sweep[s]["n10"], n) if n else Fraction(0)
        rate_b = Fraction(per_sweep[s]["n11"] + per_sweep[s]["n01"], n) if n else Fraction(0)
        sweep_out[s] = {
            **per_sweep[s],
            "n": n,
            "flips": d,
            "flip_rate": Fraction(d, n) if n else Fraction(0),
            "flip_lo": lo,
            "flip_hi": hi,
            "net_swing": Fraction(per_sweep[s]["n01"] - per_sweep[s]["n10"], n) if n else Fraction(0),
            "rate_a": rate_a,
            "rate_b": rate_b,
            "mcnemar": p_mc,
            "can_reject": d >= 6,
        }

    k_out = {}
    for j in range(2, 6):
        ordered_items = sorted(agree_clusters[j])
        lists = [agree_clusters[j][i] for i in ordered_items]
        hat, lo, hi = cluster_bootstrap(lists)
        k_out[f"agree@{j}"] = {"estimate": hat, "lo": lo, "hi": hi, "n_obs": sum(len(x) for x in lists), "n_items": len(lists)}
    for j in (1, 3, 5):
        ordered_items = sorted(ms_clusters[j])
        lists = [ms_clusters[j][i] for i in ordered_items]
        hat, lo, hi = cluster_bootstrap(lists)
        k_out[f"MS@{j}"] = {"estimate": hat, "lo": lo, "hi": hi, "n_obs": sum(len(x) for x in lists), "n_items": len(lists)}

    return {
        "cut": cut,
        "rule": rule,
        "n_items": len(items),
        "n_pairs": n_pairs,
        "n11": n11,
        "n10": n10,
        "n01": n01,
        "n00": n00,
        "flips": d_flip,
        "flip_rate": flip_rate,
        "flip_hat": fr_hat,
        "flip_lo": fr_lo,
        "flip_hi": fr_hi,
        "net_swing": net_swing,
        "swing_hat": sw_hat,
        "swing_lo": sw_lo,
        "swing_hi": sw_hi,
        "basis": basis,
        "icc": rho,
        "m_bar": m_bar,
        "deff": deff,
        "outcome": outcome,
        "ties_pair": {
            "a": sum(per_sweep[s]["ties_a"] for s in SWEEPS),
            "b": sum(per_sweep[s]["ties_b"] for s in SWEEPS),
        },
        "ties_arm": ties_arm,
        "per_sweep": sweep_out,
        "k": k_out,
        "k_excluded": k_excluded,
        "pair_kept_despite_k_exclusion": pair_excluded_by_k_but_pair_ok,
        "n_flip_items": n_flip_items,
    }


def fnum(x) -> str:
    if isinstance(x, Fraction):
        return f"{x} = {float(x):.12f}"
    if isinstance(x, float):
        return f"{x:.12f}"
    return str(x)


def pct4(x) -> str:
    v = float(x) * 100
    return f"{v:.4f}%"


def load_prove():
    return {
        "contingency": json.loads((PAIRED / "contingency_by_cut.json").read_text()),
        "intervals": json.loads((PAIRED / "intervals_by_cut.json").read_text()),
        "replicates": json.loads((PAIRED / "replicates_by_cut.json").read_text()),
        "assertion": json.loads((PAIRED / "pair_assertion.json").read_text()),
    }


def close(a, b, tol=INTERVAL_TOL) -> bool:
    return abs(Fraction(str(a)) - Fraction(str(b))) <= tol if False else abs(float(a) - float(b)) <= float(tol)


def compare(results: dict, prove: dict) -> list[str]:
    mismatches = []
    cont = prove["contingency"]["cuts"]
    iv = prove["intervals"]["cuts"]
    rep = prove["replicates"]["cuts"]

    for cut in CUT_NAMES:
        ours = results[cut]["gt"]
        pc = cont[cut]
        pi = iv[cut]
        pr = rep[cut]

        def miss(msg):
            mismatches.append(f"{cut} gt: {msg}")

        # per-sweep 2x2
        for s in SWEEPS:
            o = ours["per_sweep"][s]
            p = pc["per_sweep"][s]
            pi_s = pi["per_sweep"][s]
            for k in ("n11", "n10", "n01", "n00", "n"):
                if o[k] != p[k]:
                    miss(f"{s} {k} ours={o[k]} prove={p[k]}")
            if abs(float(o["mcnemar"]) - float(p["arm_order_check"]["p"])) > 1e-9:
                miss(f"{s} McNemar ours={float(o['mcnemar']):.12f} prove={p['arm_order_check']['p']}")
            if o["ties_a"] != p["ties"]["a"] or o["ties_b"] != p["ties"]["b"]:
                miss(f"{s} ties ours=({o['ties_a']},{o['ties_b']}) prove=({p['ties']['a']},{p['ties']['b']})")
            if abs(float(o["rate_a"]) - pi_s["rate_a"]) > 1e-12:
                miss(f"{s} rate_a ours={float(o['rate_a'])} prove={pi_s['rate_a']}")
            if abs(float(o["rate_b"]) - pi_s["rate_b"]) > 1e-12:
                miss(f"{s} rate_b ours={float(o['rate_b'])} prove={pi_s['rate_b']}")
            if abs(float(o["flip_rate"]) - pi_s["flip_rate"]["estimate"]) > 1e-12:
                miss(f"{s} flip_rate ours={float(o['flip_rate'])} prove={pi_s['flip_rate']['estimate']}")
            if abs(o["flip_lo"] - pi_s["flip_rate"]["lo"]) > 1e-12:
                miss(f"{s} flip_lo ours={o['flip_lo']} prove={pi_s['flip_rate']['lo']}")
            if abs(o["flip_hi"] - pi_s["flip_rate"]["hi"]) > 1e-12:
                miss(f"{s} flip_hi ours={o['flip_hi']} prove={pi_s['flip_rate']['hi']}")
            if abs(float(o["net_swing"]) - pi_s["net_swing"]["estimate"]) > 1e-12:
                miss(f"{s} net_swing ours={float(o['net_swing'])} prove={pi_s['net_swing']['estimate']}")

        if ours["ties_pair"]["a"] != pc["ties"]["a"] or ours["ties_pair"]["b"] != pc["ties"]["b"]:
            miss(f"pooled ties ours={ours['ties_pair']} prove={pc['ties']}")

        if ours["n_pairs"] != (pi["n"]["items"] * pi["n"]["sweeps"] - (1 if cut == "0.60" else 0)) and ours["n_pairs"] != sum(
            pc["per_sweep"][s]["n"] for s in SWEEPS
        ):
            prove_n = sum(pc["per_sweep"][s]["n"] for s in SWEEPS)
            if ours["n_pairs"] != prove_n:
                miss(f"n_pairs ours={ours['n_pairs']} prove={prove_n}")

        prove_flips = sum(pc["per_sweep"][s]["n10"] + pc["per_sweep"][s]["n01"] for s in SWEEPS)
        if ours["flips"] != prove_flips:
            miss(f"flips ours={ours['flips']} prove={prove_flips}")

        if abs(ours["flip_hat"] - pi["flip_rate"]["estimate"]) > 1e-12:
            miss(f"flip_rate hat ours={ours['flip_hat']:.16f} prove={pi['flip_rate']['estimate']}")
        if abs(ours["flip_lo"] - pi["flip_rate"]["lo"]) > 1e-12:
            miss(f"flip_rate lo ours={ours['flip_lo']:.16f} prove={pi['flip_rate']['lo']}")
        if abs(ours["flip_hi"] - pi["flip_rate"]["hi"]) > 1e-12:
            miss(f"flip_rate hi ours={ours['flip_hi']:.16f} prove={pi['flip_rate']['hi']}")
        if abs(ours["swing_hat"] - pi["net_swing"]["estimate"]) > 1e-12:
            miss(f"net_swing hat ours={ours['swing_hat']:.16f} prove={pi['net_swing']['estimate']}")
        if abs(ours["swing_lo"] - pi["net_swing"]["lo"]) > 1e-12:
            miss(f"net_swing lo ours={ours['swing_lo']:.16f} prove={pi['net_swing']['lo']}")
        if abs(ours["swing_hi"] - pi["net_swing"]["hi"]) > 1e-12:
            miss(f"net_swing hi ours={ours['swing_hi']:.16f} prove={pi['net_swing']['hi']}")
        if ours["outcome"] != pi["outcome"]:
            miss(f"outcome ours={ours['outcome']} prove={pi['outcome']}")

        # k-metrics vs prove primary
        mapping = {
            "agree@2": pr["agree"]["primary"]["j2"],
            "agree@3": pr["agree"]["primary"]["j3"],
            "agree@4": pr["agree"]["primary"]["j4"],
            "agree@5": pr["agree"]["primary"]["j5"],
            "MS@1": pr["majority"]["primary"]["j1"],
            "MS@3": pr["majority"]["primary"]["j3"],
            "MS@5": pr["majority"]["primary"]["j5"],
        }
        for name, block in mapping.items():
            o = ours["k"][name]
            for key, pk in (("estimate", "estimate"), ("lo", "lo"), ("hi", "hi")):
                if abs(o[key] - block[pk]) > 1e-12:
                    miss(f"{name} {key} ours={o[key]:.16f} prove={block[pk]}")

        # sensitivity
        ours_ge = results[cut]["ge"]
        smap = {
            "agree@2": pr["agree"]["sensitivity"]["j2"],
            "agree@3": pr["agree"]["sensitivity"]["j3"],
            "agree@4": pr["agree"]["sensitivity"]["j4"],
            "agree@5": pr["agree"]["sensitivity"]["j5"],
            "MS@1": pr["majority"]["sensitivity"]["j1"],
            "MS@3": pr["majority"]["sensitivity"]["j3"],
            "MS@5": pr["majority"]["sensitivity"]["j5"],
        }
        for name, block in smap.items():
            o = ours_ge["k"][name]
            for key, pk in (("estimate", "estimate"), ("lo", "lo"), ("hi", "hi")):
                if abs(o[key] - block[pk]) > 1e-12:
                    miss(f"ge {name} {key} ours={o[key]:.16f} prove={block[pk]}")

    return mismatches


def strata_check(cells: dict, store: dict, prove: dict) -> dict:
    items = {cut: set(cells[cut]) for cut in CUT_NAMES}
    requests = {cut: set() for cut in CUT_NAMES}
    config_hashes = {cut: set() for cut in CUT_NAMES}
    row_ids = {cut: set() for cut in CUT_NAMES}
    for cut in CUT_NAMES:
        for item, sweeps in cells[cut].items():
            for sweep, arms in sweeps.items():
                for arm, rec in arms.items():
                    config_hashes[cut].add(rec["config_hash"])
                    row_ids[cut].add((rec["run_id"], rec["config_hash"], rec["replicate_index"]))
                    req = store["request_by_run_item"].get((rec["run_id"], rec["item"]))
                    if req:
                        requests[cut].add(hashlib.sha256(req.encode()).hexdigest())
    pairs = prove["assertion"]["pairs"]
    prove_items = {cut: set() for cut in CUT_NAMES}
    prove_req = {cut: set() for cut in CUT_NAMES}
    for p in pairs:
        prove_items[p["cut"]].add(p["cluster"])
        prove_req[p["cut"]].add(p["request_digest"])

    def inter(a, b):
        return sorted(a & b)

    return {
        "n_items": {c: len(items[c]) for c in CUT_NAMES},
        "item_overlap_50_60": inter(items["0.50"], items["0.60"]),
        "item_overlap_50_90": inter(items["0.50"], items["0.90"]),
        "item_overlap_60_90": inter(items["0.60"], items["0.90"]),
        "request_overlap_50_60": inter(requests["0.50"], requests["0.60"]),
        "config_hash_overlap_50_60": inter(config_hashes["0.50"], config_hashes["0.60"]),
        "row_overlap_50_60": [list(x) for x in inter(row_ids["0.50"], row_ids["0.60"])],
        "prove_item_overlap_50_60": inter(prove_items["0.50"], prove_items["0.60"]),
        "prove_request_overlap_50_60": inter(prove_req["0.50"], prove_req["0.60"]),
        "unique_parquet_hashes": len(set(store["file_hashes"].values())),
        "n_parquet_files": len(store["file_hashes"]),
        "duplicate_keys": len(store["keys_seen"]) - len(set(store["keys_seen"])),
        "run_ids_by_file": store["run_ids_by_file"],
        "n_requests": {c: len(requests[c]) for c in CUT_NAMES},
    }


def prove_dropped_pair_n(prove) -> dict:
    """Prove's pair n from contingency (drops k-ineligible replicate sets)."""
    out = {}
    for cut in CUT_NAMES:
        per = prove["contingency"]["cuts"][cut]["per_sweep"]
        out[cut] = {s: per[s]["n"] for s in SWEEPS}
        out[cut]["pooled"] = sum(per[s]["n"] for s in SWEEPS)
    return out


def main() -> int:
    if "proofload" in sys.modules:
        raise SystemExit("refusing to run with proofload imported")

    store = load_store()
    cells = build_cells(store)
    prove = load_prove()

    results = {}
    prove_like = {}
    for cut in CUT_NAMES:
        results[cut] = {
            "gt": analyse_cut(cut, cells[cut], "gt"),
            "ge": analyse_cut(cut, cells[cut], "ge"),
        }
        prove_like[cut] = {
            "gt": analyse_cut(cut, cells[cut], "gt", pair_follows_k=True),
            "ge": analyse_cut(cut, cells[cut], "ge", pair_follows_k=True),
        }

    mismatches = compare(results, prove)
    mismatches_prove_like = compare(prove_like, prove)
    strata = strata_check(cells, store, prove)
    prove_n = prove_dropped_pair_n(prove)

    lines = []
    w = lines.append
    w("JEV INDEPENDENT RECOMPUTE")
    w("source: data/store parquet rows")
    w("no proofload import; Decimal comparisons; Fraction counts")
    w(f"bootstrap B={B} seed={SEED} numpy.random.default_rng")
    w("")

    w("== stored errors ==")
    w(f"error rows: {len(store['errors'])}")
    for rec in store["errors"]:
        w(
            f"  {rec['run_id']} cut={rec['cut']} item={rec['item']} error={rec['error']!r} noul={rec['noul']}"
        )
    w("")

    w("== 782 at cut 0.60 ==")
    excl = results["0.60"]["gt"]["k_excluded"]
    kept = results["0.60"]["gt"]["pair_kept_despite_k_exclusion"]
    w(f"261 × 3 = 783 item-sweeps in the 0.60 stratum")
    w(f"k-metric exclusions (addendum 5.7, all five or none): {len(excl)}")
    for e in excl:
        w(f"  sweep={e['sweep']} item={e['item']} arm={e['arm']} detail={e['detail']!r} pair_ok={e['pair_ok']}")
    w("spec rule: addendum 5.7 excludes whole replicate sets only from the k-metrics")
    w("declared pair is arms a,b (addendum 5.2); §5.1–§5.4 pair stats use those two arms")
    w(f"Prove pair n by sweep: {prove_n['0.60']}")
    w(f"this recompute pair n (a,b eligible): {results['0.60']['gt']['n_pairs']}")
    if kept:
        w("Prove dropped the errored item-sweep from the pair analysis.")
        for k in kept:
            w(
                f"  included here: S1 item={k['item']} a={k['noul_a']} b={k['noul_b']} "
                f"gt act {k['act_a']}/{k['act_b']} (concordant act, not a flip)"
            )
    else:
        w("no pair-eligible item-sweep was k-excluded")
    w("")

    w("== per-cut primary (p > c) ==")
    for cut in CUT_NAMES:
        r = results[cut]["gt"]
        w(f"-- cut {cut} --")
        w(f"  items={r['n_items']} pairs={r['n_pairs']}  2x2 n11={r['n11']} n10={r['n10']} n01={r['n01']} n00={r['n00']}")
        w(f"  flips={r['flips']}  flip_rate {fnum(r['flip_rate'])}")
        w(f"  flip interval {r['flip_lo']:.12f} {r['flip_hi']:.12f}  ({pct4(r['flip_lo'])} to {pct4(r['flip_hi'])})")
        w(f"  net_swing {fnum(r['net_swing'])}  [{r['swing_lo']:.12f}, {r['swing_hi']:.12f}]")
        w(f"  outcome {r['outcome']}  icc={r['icc']:.12f} m_bar={r['m_bar']:.12f} deff={r['deff']:.12f}")
        w(f"  ties p=c  a={r['ties_pair']['a']} b={r['ties_pair']['b']}")
        for s in SWEEPS:
            o = r["per_sweep"][s]
            w(
                f"  {s} n={o['n']} 2x2 {o['n11']}/{o['n10']}/{o['n01']}/{o['n00']} "
                f"rates {float(o['rate_a']):.6f}/{float(o['rate_b']):.6f} "
                f"flips={o['flips']} McNemar={float(o['mcnemar']):.12f} can_reject={o['can_reject']}"
            )
        for name in ("agree@2", "agree@3", "agree@4", "agree@5", "MS@1", "MS@3", "MS@5"):
            k = r["k"][name]
            w(f"  {name} {k['estimate']:.12f} [{k['lo']:.12f}, {k['hi']:.12f}]")
        w("")

    w("== sensitivity (p >= c) ==")
    for cut in CUT_NAMES:
        r = results[cut]["ge"]
        w(
            f"  {cut} pairs={r['n_pairs']} 2x2 {r['n11']}/{r['n10']}/{r['n01']}/{r['n00']} "
            f"flips={r['flips']} flip_rate {fnum(r['flip_rate'])} [{r['flip_lo']:.12f}, {r['flip_hi']:.12f}] "
            f"net_swing {fnum(r['net_swing'])} [{r['swing_lo']:.12f}, {r['swing_hi']:.12f}] "
            f"outcome {r['outcome']} ties a={r['ties_pair']['a']} b={r['ties_pair']['b']}"
        )
        for s in SWEEPS:
            o = r["per_sweep"][s]
            w(
                f"    {s} n={o['n']} 2x2 {o['n11']}/{o['n10']}/{o['n01']}/{o['n00']} "
                f"flips={o['flips']} McNemar={float(o['mcnemar']):.12f}"
            )
    w("  Prove paired JSON carries no ge 2x2; comparison is primary (gt) only.")
    w("")

    w("== 0.50 vs 0.60 independence ==")
    w(f"  items n {strata['n_items']}")
    w(f"  item overlap 0.50∩0.60: {len(strata['item_overlap_50_60'])} {strata['item_overlap_50_60'][:3]}")
    w(f"  item overlap 0.50∩0.90: {len(strata['item_overlap_50_90'])}")
    w(f"  item overlap 0.60∩0.90: {len(strata['item_overlap_60_90'])}")
    w(f"  request-body overlap 0.50∩0.60: {len(strata['request_overlap_50_60'])}")
    w(f"  config_hash overlap 0.50∩0.60: {len(strata['config_hash_overlap_50_60'])}")
    w(f"  stored-row overlap 0.50∩0.60: {len(strata['row_overlap_50_60'])}")
    w(f"  prove cluster overlap 0.50∩0.60: {len(strata['prove_item_overlap_50_60'])}")
    w(f"  prove request_digest overlap 0.50∩0.60: {len(strata['prove_request_overlap_50_60'])}")
    w(f"  parquet files={strata['n_parquet_files']} unique hashes={strata['unique_parquet_hashes']} duplicate keys={strata['duplicate_keys']}")
    mislabel = []
    for path, rids in strata["run_ids_by_file"].items():
        expect = Path(path).parts[-3]
        if rids != [expect]:
            mislabel.append((path, rids, expect))
    w(f"  mislabelled run_id files: {mislabel or 'none'}")
    w("")

    w("== comparison with Prove paired/*.json (spec eligibility: pair if a,b returned) ==")
    if not mismatches:
        w("every number matches")
    else:
        w(f"{len(mismatches)} mismatches:")
        for m in mismatches:
            w(f"  {m}")
    w("")
    w("== comparison if pair also drops k-ineligible item-sweeps (Prove's eligibility) ==")
    if not mismatches_prove_like:
        w("every number matches")
    else:
        w(f"{len(mismatches_prove_like)} mismatches:")
        for m in mismatches_prove_like:
            w(f"  {m}")
    w("")

    w("== §7.11 ==")
    w("publication condition is TypeSafe terms, first-hand re-read, a gate on the note")
    w("recorded as owed to Taylor in Dispatch Decisions; this session adds nothing")
    w("")

    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    (HERE / "output.txt").write_text(text)
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
