# -*- coding: utf-8 -*-
# Issue #388: U1_t4 walk-forward analysis -- 2021-2023 three-year consecutive loss
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ARTIFACTS = Path("C:/Projects/KabuSys/artifacts/backtest")
U_BASE = ARTIFACTS / "backtest_phase2_group_u/20260603_021339"
V_BASE = ARTIFACTS / "backtest_phase2_group_v/20260603_155545"
PATHS = {
    "U0_ref": U_BASE / "U0_ref/report",
    "U1_t4": U_BASE / "U1_t4/report",
    "V0_ref": V_BASE / "V0_ref/report",
    "V1_score": V_BASE / "V1_score/report",
}

TARGET_YEARS = [2021, 2022, 2023]
COMPARE_YEARS = list(range(2017, 2026))
BUCKET_ORDER = ["0-7d", "8-14d", "15-30d", "31-60d", "61d+"]


def get_report_dir(p: Path) -> Path:
    return next(p.iterdir())


def load_closed(scenario: str) -> list[dict]:
    rpt = get_report_dir(PATHS[scenario])
    raw = []
    with open(rpt / "trades.csv", newline="", encoding="utf-8") as f:
        raw = list(csv.DictReader(f))
    open_pos: dict[str, dict] = {}
    closed = []
    for t in sorted(raw, key=lambda x: x["date"]):
        code = t["code"]
        dt = datetime.strptime(t["date"], "%Y-%m-%d").date()
        price = float(t["price"])
        shares = float(t["shares"])
        pnl_raw = t.get("realized_pnl", "").strip()
        if t["side"] == "buy":
            open_pos[code] = {"entry_date": dt, "entry_price": price, "shares": shares}
        elif t["side"] == "sell" and code in open_pos:
            e = open_pos.pop(code)
            hold = (dt - e["entry_date"]).days
            pnl = float(pnl_raw) if pnl_raw else (price - e["entry_price"]) * shares
            closed.append(
                {
                    "code": code,
                    "entry_date": e["entry_date"],
                    "exit_date": dt,
                    "hold_days": hold,
                    "pnl": pnl,
                    "year": dt.year,
                    "month": dt.month,
                }
            )
    return closed


def bucket(d: int) -> str:
    if d <= 7:
        return "0-7d"
    if d <= 14:
        return "8-14d"
    if d <= 30:
        return "15-30d"
    if d <= 60:
        return "31-60d"
    return "61d+"


def annual_pnl(closed: list[dict]) -> dict[int, float]:
    r: dict[int, float] = defaultdict(float)
    for t in closed:
        r[t["year"]] += t["pnl"]
    return dict(r)


def monthly_pnl(closed: list[dict]) -> dict[tuple, float]:
    r: dict[tuple, float] = defaultdict(float)
    for t in closed:
        r[(t["year"], t["month"])] += t["pnl"]
    return dict(r)


def bucket_stats(closed: list[dict], years=None) -> dict:
    data = closed if years is None else [t for t in closed if t["year"] in years]
    stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0})
    for t in data:
        b = bucket(t["hold_days"])
        stats[b]["n"] += 1
        stats[b]["pnl"] += t["pnl"]
        if t["pnl"] > 0:
            stats[b]["wins"] += 1
    return dict(stats)


SEP = "=" * 72


def main():
    print(SEP)
    print("Issue #388: U1_t4 Walk-Forward Analysis (2021-2023 three-year loss)")
    print(SEP)

    closed: dict[str, list[dict]] = {}
    for sc in ["U0_ref", "U1_t4", "V0_ref", "V1_score"]:
        closed[sc] = load_closed(sc)
        print(f"  {sc}: {len(closed[sc])} closed positions")

    annual: dict[str, dict] = {sc: annual_pnl(closed[sc]) for sc in closed}
    mpnl: dict[str, dict] = {sc: monthly_pnl(closed[sc]) for sc in closed}

    # ── 1. Annual realized PnL comparison ───────────────────────────────────
    print(f"\n{SEP}")
    print("[ 1 ] Annual Realized PnL comparison (JPY)")
    print(SEP)
    print(
        f"{'Year':>4}  {'U0_ref':>12}  {'U1_t4':>12}  {'V0_ref':>12}  {'V1_score':>12}  {'U0-U1 diff':>12}"
    )
    print("-" * 72)
    for y in COMPARE_YEARS:
        u0 = annual["U0_ref"].get(y, 0)
        u1 = annual["U1_t4"].get(y, 0)
        v0 = annual["V0_ref"].get(y, 0)
        v1 = annual["V1_score"].get(y, 0)
        mark = "  <== TARGET" if y in TARGET_YEARS else ""
        print(
            f"{y:>4}  {u0:>+12,.0f}  {u1:>+12,.0f}  {v0:>+12,.0f}  {v1:>+12,.0f}  {u0 - u1:>+12,.0f}{mark}"
        )

    # ── 2. Monthly PnL: U0_ref vs U1_t4 (2021-2023) ─────────────────────────
    print(f"\n{SEP}")
    print("[ 2 ] Monthly Realized PnL -- U0_ref vs U1_t4 (2021-2023, JPY)")
    print(SEP)
    print(
        f"  {'Mth':>3}  {'U0/2021':>10}  {'U1/2021':>10}  {'diff':>9}  |  {'U0/2022':>10}  {'U1/2022':>10}  {'diff':>9}  |  {'U0/2023':>10}  {'U1/2023':>10}  {'diff':>9}"
    )
    print(f"  {'-' * 100}")
    for m in range(1, 13):
        row = f"  {m:>3}"
        for y in TARGET_YEARS:
            u0v = mpnl["U0_ref"].get((y, m), 0)
            u1v = mpnl["U1_t4"].get((y, m), 0)
            d = u0v - u1v
            mark = "*" if abs(d) > 30000 else " "
            row += f"  {u0v:>+10,.0f}  {u1v:>+10,.0f}  {d:>+8,.0f}{mark} |"
        print(row)

    # ── 3. Holding-period bucket breakdown (2021-2023) ───────────────────────
    print(f"\n{SEP}")
    print("[ 3 ] Holding-period bucket analysis (2021-2023)")
    print(SEP)
    for sc in ["U0_ref", "U1_t4", "V1_score"]:
        bkt = bucket_stats(closed[sc], TARGET_YEARS)
        total_pnl = sum(v["pnl"] for v in bkt.values())
        total_n = sum(v["n"] for v in bkt.values())
        print(f"\n  {sc}  (2021-2023 total PnL: {total_pnl:>+12,.0f} JPY / {total_n} trades)")
        print(f"  {'Bucket':12}  {'N':>5}  {'WinRate':>7}  {'Total PnL':>12}  {'Avg PnL':>10}")
        print(f"  {'-' * 56}")
        for b in BUCKET_ORDER:
            if b not in bkt:
                continue
            d = bkt[b]
            wr = d["wins"] / d["n"] * 100 if d["n"] else 0
            avg = d["pnl"] / d["n"] if d["n"] else 0
            print(f"  {b:12}  {d['n']:>5}  {wr:>6.1f}%  {d['pnl']:>+12,.0f}  {avg:>+10,.0f}")

    # ── 4. Full period vs 2021-2023 bucket compare (U1_t4) ──────────────────
    print(f"\n{SEP}")
    print("[ 4 ] U1_t4: Full-period vs 2021-2023 bucket comparison")
    print(SEP)
    bkt_all = bucket_stats(closed["U1_t4"])
    bkt_tgt = bucket_stats(closed["U1_t4"], TARGET_YEARS)
    print(f"  {'Bucket':12}  {'All PnL':>12}  {'21-23 PnL':>12}  {'All WR':>8}  {'21-23 WR':>9}")
    print(f"  {'-' * 62}")
    for b in BUCKET_ORDER:
        a = bkt_all.get(b, {"n": 0, "wins": 0, "pnl": 0.0})
        t = bkt_tgt.get(b, {"n": 0, "wins": 0, "pnl": 0.0})
        wr_a = a["wins"] / a["n"] * 100 if a["n"] else 0
        wr_t = t["wins"] / t["n"] * 100 if t["n"] else 0
        print(f"  {b:12}  {a['pnl']:>+12,.0f}  {t['pnl']:>+12,.0f}  {wr_a:>7.1f}%  {wr_t:>8.1f}%")

    # ── 5. Worst months for U1_t4 in 2021-2023 ──────────────────────────────
    print(f"\n{SEP}")
    print("[ 5 ] U1_t4: Worst 12 months in 2021-2023 (Realized PnL)")
    print(SEP)
    tgt_ym = [(y, m) for y in TARGET_YEARS for m in range(1, 13)]
    worst = sorted(tgt_ym, key=lambda ym: mpnl["U1_t4"].get(ym, 0))
    print(f"  {'YM':>7}  {'U1_t4':>12}  {'U0_ref':>12}  {'V1_score':>12}  {'U0-U1':>12}")
    print(f"  {'-' * 60}")
    for ym in worst[:12]:
        u0v = mpnl["U0_ref"].get(ym, 0)
        u1v = mpnl["U1_t4"].get(ym, 0)
        v1v = mpnl["V1_score"].get(ym, 0)
        mark = "  <<" if u1v < -50000 else ""
        print(
            f"  {ym[0]}/{ym[1]:02d}  {u1v:>+12,.0f}  {u0v:>+12,.0f}  {v1v:>+12,.0f}  {u0v - u1v:>+12,.0f}{mark}"
        )

    # ── 6. Walk-forward IS/OOS splits ────────────────────────────────────────
    print(f"\n{SEP}")
    print("[ 6 ] Walk-forward IS/OOS splits (U1_t4 annual PnL)")
    print(SEP)
    splits = [
        ("IS 2017-2020 / OOS 2021", range(2017, 2021), [2021]),
        ("IS 2017-2021 / OOS 2022", range(2017, 2022), [2022]),
        ("IS 2017-2022 / OOS 2023", range(2017, 2023), [2023]),
        ("IS 2017-2020 / OOS 2021-2023", range(2017, 2021), TARGET_YEARS),
        ("IS 2017-2023 / OOS 2024-2025", range(2017, 2024), [2024, 2025]),
    ]
    u1a = annual["U1_t4"]
    for label, is_yr, oos_yr in splits:
        is_pnl = sum(u1a.get(y, 0) for y in is_yr)
        oos_pnl = sum(u1a.get(y, 0) for y in oos_yr)
        oos_det = ", ".join(f"{y}:{u1a.get(y, 0):>+,.0f}" for y in oos_yr)
        verdict = "OK (positive)" if oos_pnl > 0 else "NG (negative)"
        print(f"\n  {label}")
        print(f"    IS  total: {is_pnl:>+12,.0f} JPY")
        print(f"    OOS total: {oos_pnl:>+12,.0f} JPY  [{oos_det}]  -> {verdict}")

    # ── 7. quality_score contribution (U0 vs U1 trade count & PnL) ──────────
    print(f"\n{SEP}")
    print("[ 7 ] Quality-score filter impact: U0_ref vs U1_t4 trade count")
    print(SEP)
    print(
        f"  {'Year':>4}  {'U0 trades':>10}  {'U1 trades':>10}  {'diff':>8}  {'U0 PnL':>12}  {'U1 PnL':>12}  {'diff':>12}"
    )
    print(f"  {'-' * 75}")
    u0_by_yr: dict[int, list] = defaultdict(list)
    u1_by_yr: dict[int, list] = defaultdict(list)
    for t in closed["U0_ref"]:
        u0_by_yr[t["year"]].append(t)
    for t in closed["U1_t4"]:
        u1_by_yr[t["year"]].append(t)
    for y in COMPARE_YEARS:
        u0n = len(u0_by_yr[y])
        u1n = len(u1_by_yr[y])
        u0pnl = sum(t["pnl"] for t in u0_by_yr[y])
        u1pnl = sum(t["pnl"] for t in u1_by_yr[y])
        mark = "  <=" if y in TARGET_YEARS else ""
        print(
            f"  {y:>4}  {u0n:>10}  {u1n:>10}  {u1n - u0n:>+8}  {u0pnl:>+12,.0f}  {u1pnl:>+12,.0f}  {u0pnl - u1pnl:>+12,.0f}{mark}"
        )

    # ── 8. V1_score vs V0_ref monthly diff in 2022-2023 ────────────────────
    print(f"\n{SEP}")
    print("[ 8 ] V1_score vs V0_ref monthly diff (2022-2023, reason for extra loss)")
    print(SEP)
    print(
        f"  {'YM':>7}  {'V0_ref':>12}  {'V1_score':>12}  {'diff V0-V1':>12}  {'hold_d diff (V1-V0 avg)':>24}"
    )
    print(f"  {'-' * 70}")

    def avg_hold(closed_data, year, month):
        trades = [t for t in closed_data if t["year"] == year and t["month"] == month]
        if not trades:
            return 0.0
        return sum(t["hold_days"] for t in trades) / len(trades)

    for y in [2022, 2023]:
        for m in range(1, 13):
            v0v = mpnl["V0_ref"].get((y, m), 0)
            v1v = mpnl["V1_score"].get((y, m), 0)
            diff = v0v - v1v
            if abs(diff) > 10000:
                ah0 = avg_hold(closed["V0_ref"], y, m)
                ah1 = avg_hold(closed["V1_score"], y, m)
                print(
                    f"  {y}/{m:02d}  {v0v:>+12,.0f}  {v1v:>+12,.0f}  {diff:>+12,.0f}  V0_avg={ah0:.1f}d  V1_avg={ah1:.1f}d"
                )

    print(f"\n{SEP}")
    print("Analysis complete.")
    print(SEP)


if __name__ == "__main__":
    main()
