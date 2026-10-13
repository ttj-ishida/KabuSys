"""手動注文候補レポート（#412）のデータ収集。

ユーザーが証券画面で手動注文するための判断材料（BUY/SELL 候補・上限・見送り条件）を
DuckDB から読み取り専用で集める。発注はしない。kabu API / Execution Engine に依存しない。

- evening: 夜間バッチ直後（21:10）。signal_date は通常 report_date 当日。
- morning: 寄り前（08:05）。signal_date は通常 report_date の前営業日。
  休場日・停止フラグ・DD 停止・シグナル欠落時は BUY 候補をすべて見送り候補に移す。
- シグナル生成後に手動約定があった銘柄の BUY は個別に見送り候補に移す。

Look-ahead 防止: すべてのクエリは date <= report_date（価格は <= signal_date）に限定する。
フォーマッタ・保存関数は manual_order_report_format.py。
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import duckdb

from kabusys.data.calendar_management import is_trading_day, prev_trading_day
from kabusys.operations.manual_order_report_checks import (
    HOLDINGS_CHANGED_REASON,
    SafeReader,
    as_date,
    buy_price_bounds,
    check_dd_stop,
    holdings_changed_codes,
    load_gap_thresholds,
)
from kabusys.operations.manual_trades import calc_manual_portfolio_value, manual_position_qty_map
from kabusys.operations.pre_market_collector import check_data_freshness, check_stop_flag
from kabusys.portfolio.position_sizing import calc_position_sizes

logger = logging.getLogger(__name__)

PHASES = ("evening", "morning")

# calc_position_sizes の既定 1 銘柄上限（総資産比）に追従する
MAX_POSITION_PCT: float = float(
    inspect.signature(calc_position_sizes).parameters["max_position_pct"].default
)

STATUS_OK = "OK"
STATUS_WARN = "WARN"
STATUS_BUY_SKIPPED = "BUY_SKIPPED"


@dataclass
class BuyCandidate:
    code: str
    name: str
    size: int  # 追加で買う株数（signal_queue.size）
    ref_price: float | None
    amount: float | None
    score: float | None
    rank: int | None
    held_qty: int  # シグナル日時点の自動保有 (+ 手動保有: MANUAL_TRADING_ENABLED 時)
    add_on: bool
    buy_max_price: int | None  # この価格以下なら買付可（上限）
    buy_min_price: int | None  # この価格以上なら買付可（下限）
    skip_reason: str | None = None  # 見送り理由（見送り候補のみ）


@dataclass
class SellCandidate:
    code: str
    name: str
    manual: bool
    manual_qty: int | None
    reason: str | None
    auto_qty: int


@dataclass
class ManualOrderReport:
    phase: str
    report_date: date
    generated_at: datetime
    signal_date: date | None
    gap_up_threshold: float
    gap_down_threshold: float
    manual_trading_enabled: bool
    portfolio_value: float
    available_cash: float | None
    max_position_pct: float
    max_position_amount: float
    buy_candidates: list[BuyCandidate] = field(default_factory=list)
    skipped_buys: list[BuyCandidate] = field(default_factory=list)
    buy_skip_reasons: list[str] = field(default_factory=list)
    sell_candidates: list[SellCandidate] = field(default_factory=list)
    # morning のみ（evening は None）。dd_stop=None は「不明」
    data_freshness_ok: bool | None = None
    stop_flag: bool | None = None
    dd_stop: bool | None = None
    dd_stop_since: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def total_buy_amount(self) -> float:
        return float(sum(b.amount or 0.0 for b in self.buy_candidates))

    @property
    def utilization(self) -> float | None:
        if self.portfolio_value <= 0:
            return None
        return self.total_buy_amount / self.portfolio_value

    @property
    def status(self) -> str:
        if self.buy_skip_reasons:
            return STATUS_BUY_SKIPPED
        if self.warnings:
            return STATUS_WARN
        return STATUS_OK


def _latest_signal_date(rd: SafeReader, report_date: date) -> date | None:
    dates: list[date] = []
    for table in ("signal_queue", "signals"):
        rows = rd.fetch(table, f"SELECT MAX(date) FROM {table} WHERE date <= ?", [report_date])
        d = as_date(rows[0][0]) if rows else None
        if d is not None:
            dates.append(d)
    return max(dates) if dates else None


def _auto_positions(rd: SafeReader, report_date: date) -> dict[str, int]:
    rows = rd.fetch(
        "positions",
        """
        SELECT code, position_size FROM positions
        WHERE date = (SELECT MAX(date) FROM positions WHERE date <= ?)
        """,
        [report_date],
    )
    return {r[0]: int(r[1]) for r in rows if r[1] is not None}


def _stock_names(rd: SafeReader) -> dict[str, str]:
    rows = rd.fetch("stocks", "SELECT code, name FROM stocks")
    return {r[0]: r[1] for r in rows if r[1]}


def _latest_closes(rd: SafeReader, codes: list[str], as_of: date) -> dict[str, float]:
    if not codes:
        return {}
    params = ",".join(["?"] * len(codes))
    rows = rd.fetch(
        "prices_daily",
        f"""
        SELECT p.code, p.close FROM prices_daily p
        JOIN (
            SELECT code, MAX(date) AS d FROM prices_daily
            WHERE code IN ({params}) AND date <= ? GROUP BY code
        ) l ON p.code = l.code AND p.date = l.d
        """,
        [*codes, as_of],
    )
    return {r[0]: float(r[1]) for r in rows if r[1] is not None}


def _collect_buys(
    rd: SafeReader,
    signal_date: date,
    names: dict[str, str],
    held: dict[str, int],
    gaps: tuple[float, float],
) -> list[BuyCandidate]:
    rows = rd.fetch(
        "signal_queue",
        """
        SELECT code, CAST(size AS BIGINT), price, created_at FROM signal_queue
        WHERE date = ? AND side = 'buy' AND status = 'pending'
        """,
        [signal_date],
    )
    if not rows:
        return []
    scores = {
        r[0]: (r[1], r[2])
        for r in rd.fetch(
            "signals",
            "SELECT code, score, signal_rank FROM signals WHERE date = ? AND side = 'buy'",
            [signal_date],
        )
    }
    closes = _latest_closes(rd, [r[0] for r in rows if r[2] is None], signal_date)
    changed = holdings_changed_codes(rd.conn, signal_date, {r[0]: r[3] for r in rows})
    out: list[BuyCandidate] = []
    for code, size, price, _created in rows:
        ref = float(price) if price is not None else closes.get(code)
        score, rank = scores.get(code, (None, None))
        qty = held.get(code, 0)
        upper, lower = buy_price_bounds(ref, gaps)
        out.append(
            BuyCandidate(
                code=code,
                name=names.get(code, code),
                size=int(size),
                ref_price=ref,
                amount=ref * int(size) if ref is not None else None,
                score=float(score) if score is not None else None,
                rank=int(rank) if rank is not None else None,
                held_qty=qty,
                add_on=qty > 0,
                buy_max_price=upper,
                buy_min_price=lower,
                skip_reason=HOLDINGS_CHANGED_REASON if code in changed else None,
            )
        )
    out.sort(key=lambda b: (b.rank is None, b.rank or 0, b.code))
    return out


def _collect_sells(
    rd: SafeReader, signal_date: date, names: dict[str, str], auto: dict[str, int]
) -> list[SellCandidate]:
    if rd.has_table("manual_action_queue"):
        sql = """
            SELECT s.code, m.qty, m.reason, m.action_id IS NOT NULL
            FROM signals s
            LEFT JOIN manual_action_queue m
              ON m.date = s.date AND m.code = s.code AND m.action = 'sell_candidate'
            WHERE s.date = ? AND s.side = 'sell'
            ORDER BY s.code
        """
    else:
        rd.warn("テーブル manual_action_queue がないため手動保有の売却情報を省略しました")
        sql = """
            SELECT code, NULL, NULL, FALSE FROM signals
            WHERE date = ? AND side = 'sell' ORDER BY code
        """
    return [
        SellCandidate(
            code=r[0],
            name=names.get(r[0], r[0]),
            manual=bool(r[3]),
            manual_qty=int(r[1]) if r[1] is not None else None,
            reason=r[2],
            auto_qty=auto.get(r[0], 0),
        )
        for r in rd.fetch("signals", sql, [signal_date])
    ]


def _skip_all_buys(rd: SafeReader, report: ManualOrderReport, reasons: list[str]) -> None:
    """全 BUY 候補を見送りに移す。BUY が 0 件でも理由は警告・見送り理由として残す。"""
    if not reasons:
        return
    for reason in reasons:
        rd.warn(reason)
        if reason not in report.buy_skip_reasons:
            report.buy_skip_reasons.append(reason)
    joined = " / ".join(reasons)
    for b in report.buy_candidates:
        b.skip_reason = joined if b.skip_reason is None else f"{b.skip_reason} / {joined}"
    report.skipped_buys = report.skipped_buys + report.buy_candidates
    report.buy_candidates = []


def _apply_morning_checks(
    rd: SafeReader,
    report: ManualOrderReport,
    stop_flag_path: Path | None,
    sqlite_path: Path | None,
) -> None:
    conn, report_date = rd.conn, report.report_date
    try:
        report.data_freshness_ok = check_data_freshness(conn, report_date)
    except duckdb.CatalogException:
        rd.warn("テーブル prices_daily がないため空として扱いました")
        report.data_freshness_ok = False
    if not report.data_freshness_ok:
        rd.warn("価格データ（prices_daily）が古いか、ありません")

    report.stop_flag = check_stop_flag(stop_flag_path) if stop_flag_path is not None else False
    report.dd_stop, report.dd_stop_since = check_dd_stop(sqlite_path)
    if report.dd_stop is None:
        rd.warn("DD 停止状態を確認できません（監視 SQLite を読めないため不明）")

    reasons: list[str] = []
    if not is_trading_day(conn, report_date):
        reasons.append("本日は休場日です")
    if report.stop_flag:
        reasons.append("停止フラグ（data/stop_requested.flag）があります")
    if report.dd_stop:
        reasons.append(f"DD 停止中です（{report.dd_stop_since} から）")
    expected = prev_trading_day(conn, report_date)
    if report.signal_date is not None and report.signal_date < expected:
        rd.warn(
            f"シグナルが古い可能性があります（シグナル日 {report.signal_date}、"
            f"期待値 {expected} 以降）。夜間バッチの欠落を確認してください"
        )
        reasons.append(f"シグナル日 {report.signal_date} が前営業日 {expected} より古い")
    _skip_all_buys(rd, report, reasons)


def _warn_missing_queue(rd: SafeReader, signal_date: date, has_buys: bool) -> None:
    """signals に BUY があるのに signal_queue に pending BUY がない場合に警告する。"""
    if has_buys:
        return
    rows = rd.fetch(
        "signals",
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'buy'",
        [signal_date],
    )
    n = int(rows[0][0]) if rows and rows[0][0] else 0
    if n > 0:
        rd.warn(
            f"signals に {signal_date} の BUY が {n} 件ありますが、signal_queue に pending の "
            "BUY がありません（portfolio_construction の失敗の可能性）"
        )


def collect_manual_order_report(
    conn: duckdb.DuckDBPyConnection,
    *,
    phase: str,
    report_date: date,
    manual_trading_enabled: bool,
    initial_cash: float,
    portfolio_value: float,
    stop_flag_path: Path | None = None,
    sqlite_path: Path | None = None,
    gap_thresholds: tuple[float, float] | None = None,
    now: datetime | None = None,
) -> ManualOrderReport:
    """手動注文候補レポートを収集する（DuckDB は読み取りのみ）。"""
    if phase not in PHASES:
        raise ValueError(f"phase は {PHASES} のいずれか: {phase!r}")
    warnings: list[str] = []
    rd = SafeReader(conn, warnings)
    gaps = gap_thresholds if gap_thresholds is not None else load_gap_thresholds()
    now = now or datetime.now()

    available_cash: float | None = None
    if manual_trading_enabled:
        portfolio_value, available_cash = calc_manual_portfolio_value(
            conn, initial_cash, as_of=report_date
        )

    report = ManualOrderReport(
        phase=phase,
        report_date=report_date,
        generated_at=now,
        signal_date=_latest_signal_date(rd, report_date),
        gap_up_threshold=gaps[0],
        gap_down_threshold=gaps[1],
        manual_trading_enabled=manual_trading_enabled,
        portfolio_value=float(portfolio_value),
        available_cash=available_cash,
        max_position_pct=MAX_POSITION_PCT,
        max_position_amount=float(portfolio_value) * MAX_POSITION_PCT,
        warnings=warnings,
    )
    if report_date < now.date():
        rd.warn(
            f"過去日（{report_date}）のレポートです。停止フラグ・DD 停止・資金などは"
            "実行時点の状態を反映しています"
        )

    if report.signal_date is None:
        rd.warn(f"{report_date} 以前のシグナルがありません")
    else:
        sig = report.signal_date
        names = _stock_names(rd)
        # 保有は sizing と同じ前提（シグナル日時点・手動分は MANUAL_TRADING_ENABLED 時のみ）
        held = _auto_positions(rd, sig)
        if manual_trading_enabled:
            for code, qty in manual_position_qty_map(conn, as_of=sig).items():
                held[code] = held.get(code, 0) + qty
        buys = _collect_buys(rd, sig, names, held, gaps)
        report.buy_candidates = [b for b in buys if b.skip_reason is None]
        report.skipped_buys = [b for b in buys if b.skip_reason is not None]
        if report.skipped_buys:
            rd.warn(f"{HOLDINGS_CHANGED_REASON}: " + ", ".join(b.code for b in report.skipped_buys))
        report.sell_candidates = _collect_sells(rd, sig, names, _auto_positions(rd, report_date))
        _warn_missing_queue(rd, sig, bool(buys))
        missing_price = [b.code for b in buys if b.ref_price is None]
        if missing_price:
            rd.warn(f"参考価格を取得できない BUY 候補があります: {', '.join(missing_price)}")
        if phase == "evening" and sig != report_date:
            _skip_all_buys(
                rd,
                report,
                [f"本日（{report_date}）のシグナルがありません。シグナル日 {sig} は古い"],
            )

    if phase == "morning":
        _apply_morning_checks(rd, report, stop_flag_path, sqlite_path)
    return report
