# scripts/run_paper_trading_verification.py
"""Paper Trading 検証進捗レポート（Issue #398）。

W1_08 シグナル・注文フロー 4週間検証の合否を確認する。
DuckDB（signals / signal_queue）と SQLite（paper_trading.db / orders）を参照する。

Usage:
    python scripts/run_paper_trading_verification.py --start-date 2026-06-16
    python scripts/run_paper_trading_verification.py --start-date 2026-06-16 --end-date 2026-07-14
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="paper_trading_verification", capture_stdio=False)
logger = logging.getLogger(__name__)

# ---- 判断基準 ---------------------------------------------------------------
_MIN_TRADING_DAYS = 20  # 最低実施期間（約4週間）
_MIN_BUY_SIGNALS = 10  # 最低シグナル発生数
_MAX_ERROR_RATE = 0.0  # 最大注文エラー率
_MAX_SLIPPAGE_PCT = 0.003  # 最大スリッページ乖離（±0.3%）


@dataclass
class VerificationResult:
    period_start: str
    period_end: str
    n_trading_days: int
    n_buy_signals: int
    n_orders_total: int
    n_orders_filled: int
    n_orders_rejected: int
    error_rate: float  # rejected / total
    slippage_mean_pct: float | None  # 平均スリッページ（基準価格比）
    slippage_max_pct: float | None  # 最大スリッページ
    pass_trading_days: bool
    pass_buy_signals: bool
    pass_error_rate: bool
    pass_slippage: bool

    @property
    def all_pass(self) -> bool:
        return (
            self.pass_trading_days
            and self.pass_buy_signals
            and self.pass_error_rate
            and self.pass_slippage
        )


def _collect_signal_stats(
    conn: duckdb.DuckDBPyConnection,
    start: date,
    end: date,
) -> tuple[int, int]:
    """期間中の trading days 数と BUY シグナル数を返す。"""
    try:
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT date) AS trading_days, COUNT(*) AS buy_signals
            FROM signals
            WHERE date >= ? AND date <= ? AND side = 'buy'
            """,
            [start, end],
        ).fetchone()
        if row:
            return int(row[0]), int(row[1])
    except Exception:
        logger.warning("signals テーブルの取得に失敗しました", exc_info=True)
    return 0, 0


def _collect_signal_queue_prices(
    conn: duckdb.DuckDBPyConnection,
    start: date,
    end: date,
) -> dict[str, float]:
    """signal_id → 基準価格 のマップを返す（BUY のみ）。"""
    result: dict[str, float] = {}
    try:
        rows = conn.execute(
            """
            SELECT signal_id, price
            FROM signal_queue
            WHERE date >= ? AND date <= ? AND side = 'buy' AND price IS NOT NULL AND price > 0
            """,
            [start, end],
        ).fetchall()
        result = {r[0]: float(r[1]) for r in rows}
    except Exception:
        logger.warning("signal_queue テーブルの取得に失敗しました", exc_info=True)
    return result


def _collect_order_stats(
    sqlite_path: Path,
    signal_ids: set[str],
) -> tuple[int, int, int, dict[str, float]]:
    """SQLite paper_trading.db から注文統計を取得する。

    Returns:
        (total, filled, rejected, {signal_id: avg_fill_price})
    """
    total = filled = rejected = 0
    fill_prices: dict[str, float] = {}
    if not sqlite_path.exists():
        logger.warning("paper_trading.db が見つかりません: %s", sqlite_path)
        return total, filled, rejected, fill_prices

    try:
        with sqlite3.connect(str(sqlite_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT signal_id, state, avg_fill_price FROM orders").fetchall()
    except Exception:
        logger.warning("paper_trading.db の読み込みに失敗しました", exc_info=True)
        return total, filled, rejected, fill_prices

    for row in rows:
        sid = row["signal_id"]
        if sid not in signal_ids:
            continue
        total += 1
        state = row["state"]
        if state in ("filled", "closed", "partial"):
            filled += 1
            afp = row["avg_fill_price"]
            if afp is not None:
                fill_prices[sid] = float(afp)
        elif state == "rejected":
            rejected += 1

    return total, filled, rejected, fill_prices


def run_verification(start: date, end: date, settings: Settings) -> VerificationResult:
    """検証結果を計算して返す。"""
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        n_days, n_buy = _collect_signal_stats(conn, start, end)
        ref_prices = _collect_signal_queue_prices(conn, start, end)
    finally:
        conn.close()

    signal_ids = set(ref_prices.keys())
    total, filled, rejected, fill_prices = _collect_order_stats(
        settings.paper_sqlite_path, signal_ids
    )

    error_rate = rejected / total if total > 0 else 0.0

    # スリッページ計算
    slippage_vals: list[float] = []
    for sid, fill_price in fill_prices.items():
        ref = ref_prices.get(sid)
        if ref and ref > 0:
            slippage_vals.append(abs(fill_price - ref) / ref)

    slippage_mean = sum(slippage_vals) / len(slippage_vals) if slippage_vals else None
    slippage_max = max(slippage_vals) if slippage_vals else None

    return VerificationResult(
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        n_trading_days=n_days,
        n_buy_signals=n_buy,
        n_orders_total=total,
        n_orders_filled=filled,
        n_orders_rejected=rejected,
        error_rate=error_rate,
        slippage_mean_pct=slippage_mean,
        slippage_max_pct=slippage_max,
        pass_trading_days=n_days >= _MIN_TRADING_DAYS,
        pass_buy_signals=n_buy >= _MIN_BUY_SIGNALS,
        pass_error_rate=error_rate <= _MAX_ERROR_RATE,
        pass_slippage=slippage_max is None or slippage_max <= _MAX_SLIPPAGE_PCT,
    )


def format_report(r: VerificationResult) -> str:
    def ok(passed: bool) -> str:
        return "PASS" if passed else "FAIL"

    def pct(v: float | None, digits: int = 3) -> str:
        return f"{v * 100:.{digits}f}%" if v is not None else "N/A (データなし)"

    sep = "=" * 62
    lines = [
        sep,
        "  [Paper Trading Verification] Issue #398 — W1_08",
        f"  期間: {r.period_start} 〜 {r.period_end}",
        sep,
        "",
        "【シグナル生成】",
        f"  取引日数:         {r.n_trading_days:>4} 日  (基準: >={_MIN_TRADING_DAYS} 日)  [{ok(r.pass_trading_days)}]",
        f"  BUY シグナル数:   {r.n_buy_signals:>4} 件  (基準: >={_MIN_BUY_SIGNALS} 件)   [{ok(r.pass_buy_signals)}]",
        "",
        "【注文フロー】",
        f"  総注文数:         {r.n_orders_total:>4} 件",
        f"  約定数:           {r.n_orders_filled:>4} 件",
        f"  拒否数:           {r.n_orders_rejected:>4} 件",
        f"  エラー率:         {pct(r.error_rate, 1):>10}  (基準: {_MAX_ERROR_RATE:.0%})  [{ok(r.pass_error_rate)}]",
        "",
        "【スリッページ】",
        f"  平均スリッページ: {pct(r.slippage_mean_pct):>10}",
        f"  最大スリッページ: {pct(r.slippage_max_pct):>10}  (基準: <=+/-{_MAX_SLIPPAGE_PCT * 100:.1f}%)  [{ok(r.pass_slippage)}]",
        "",
        sep,
        f"  総合判定: {'[ PASS — 本番投入可 ]' if r.all_pass else '[ FAIL — 継続検証 ]'}",
        sep,
    ]
    return "\n".join(lines)


def save_report(r: VerificationResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"paper_verification_{ts}.json"
    out_path.write_text(
        json.dumps(asdict(r), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper Trading 検証進捗レポートを生成する（Issue #398）。"
    )
    parser.add_argument(
        "--start-date",
        required=True,
        metavar="DATE",
        help="検証開始日 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        metavar="DATE",
        help="検証終了日 (YYYY-MM-DD、省略時は今日)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="レポート JSON の保存先（省略時: artifacts/paper_trading_verification）",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    try:
        start = date.fromisoformat(args.start_date)
    except ValueError:
        print(f"ERROR: --start-date の形式が不正です: {args.start_date}")
        sys.exit(1)

    end = date.today()
    if args.end_date:
        try:
            end = date.fromisoformat(args.end_date)
        except ValueError:
            print(f"ERROR: --end-date の形式が不正です: {args.end_date}")
            sys.exit(1)

    if end < start:
        print(f"ERROR: end-date ({end}) が start-date ({start}) より前です。")
        sys.exit(1)

    settings = Settings()
    result = run_verification(start, end, settings)

    print(format_report(result))

    out_dir = (
        Path(args.output_dir) if args.output_dir else Path("artifacts/paper_trading_verification")
    )
    saved = save_report(result, out_dir)
    print(f"\nレポート保存: {saved}")

    if not result.all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
