"""手動注文候補レポート（#412）のデータ収集。

ユーザーが証券画面で手動注文するための判断材料（BUY/SELL 候補・上限・見送り条件）を
DuckDB から読み取り専用で集める。発注はしない。kabu API / Execution Engine に依存しない。

- evening: 夜間バッチ直後（21:10）。signal_date は通常 report_date 当日。
- morning: 寄り前（08:05）。signal_date は通常 report_date の前営業日。
  停止フラグ・DD 停止・シグナル欠落時は BUY 候補をすべて見送り候補に移す。

Look-ahead 防止: すべてのクエリは date <= report_date（価格は <= signal_date）に限定する。
フォーマッタ・保存関数は manual_order_report_format.py。
"""

from __future__ import annotations

import inspect
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb

from kabusys.data.calendar_management import prev_trading_day
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
    held_qty: int  # 手動保有 + 自動保有
    add_on: bool
    skip_upper: float | None  # 寄り付きがこの価格を超えたら見送り
    skip_lower: float | None  # 寄り付きがこの価格以下なら見送り


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


class _Reader:
    """テーブル欠落（CatalogException）を空扱い + 警告にする読み取りヘルパー。"""

    def __init__(self, conn: duckdb.DuckDBPyConnection, warnings: list[str]) -> None:
        self.conn = conn
        self.warnings = warnings

    def warn(self, msg: str) -> None:
        if msg not in self.warnings:
            self.warnings.append(msg)

    def fetch(self, table: str, sql: str, params: list[Any] | None = None) -> list[tuple]:
        try:
            return self.conn.execute(sql, params or []).fetchall()
        except duckdb.CatalogException:
            self.warn(f"テーブル {table} がないため空として扱いました")
            return []

    def has_table(self, table: str) -> bool:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_name = ?",
            [table],
        ).fetchone()
        return bool(row and row[0])


def _as_date(v: object) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _latest_signal_date(rd: _Reader, report_date: date) -> date | None:
    dates: list[date] = []
    for table in ("signal_queue", "signals"):
        rows = rd.fetch(table, f"SELECT MAX(date) FROM {table} WHERE date <= ?", [report_date])
        d = _as_date(rows[0][0]) if rows else None
        if d is not None:
            dates.append(d)
    return max(dates) if dates else None


def _auto_positions(rd: _Reader, report_date: date) -> dict[str, int]:
    rows = rd.fetch(
        "positions",
        """
        SELECT code, position_size FROM positions
        WHERE date = (SELECT MAX(date) FROM positions WHERE date <= ?)
        """,
        [report_date],
    )
    return {r[0]: int(r[1]) for r in rows if r[1] is not None}


def _stock_names(rd: _Reader) -> dict[str, str]:
    rows = rd.fetch("stocks", "SELECT code, name FROM stocks")
    return {r[0]: r[1] for r in rows if r[1]}


def _latest_closes(rd: _Reader, codes: list[str], as_of: date) -> dict[str, float]:
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
    rd: _Reader,
    signal_date: date,
    names: dict[str, str],
    held: dict[str, int],
    gaps: tuple[float, float],
) -> list[BuyCandidate]:
    rows = rd.fetch(
        "signal_queue",
        """
        SELECT code, CAST(size AS BIGINT), price FROM signal_queue
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
    missing = [r[0] for r in rows if r[2] is None]
    closes = _latest_closes(rd, missing, signal_date)
    out: list[BuyCandidate] = []
    for code, size, price in rows:
        ref = float(price) if price is not None else closes.get(code)
        score, rank = scores.get(code, (None, None))
        qty = held.get(code, 0)
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
                skip_upper=ref * (1 + gaps[0]) if ref is not None else None,
                skip_lower=ref * (1 + gaps[1]) if ref is not None else None,
            )
        )
    out.sort(key=lambda b: (b.rank is None, b.rank or 0, b.code))
    return out


def _collect_sells(
    rd: _Reader, signal_date: date, names: dict[str, str], auto: dict[str, int]
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


def _check_dd_stop(sqlite_path: Path | None) -> tuple[bool | None, str | None]:
    """監視 SQLite の dashboard.dd_stop_blocked_since を読む。読めなければ (None, None)。"""
    if sqlite_path is None or not Path(sqlite_path).exists():
        return None, None
    try:
        sc = sqlite3.connect(f"file:{Path(sqlite_path).as_posix()}?mode=ro", uri=True)
        try:
            row = sc.execute("SELECT dd_stop_blocked_since FROM dashboard WHERE id = 1").fetchone()
        finally:
            sc.close()
    except Exception:
        logger.warning("DD 停止状態の取得に失敗しました: %s", sqlite_path, exc_info=True)
        return None, None
    since = row[0] if row else None
    return (since is not None and str(since).strip() != ""), since


def load_gap_thresholds() -> tuple[float, float]:
    """config/strategy_config.yaml の (gap_up_threshold, gap_down_threshold)。"""
    from kabusys.strategy.signal_generator import _load_strategy_config

    cfg = _load_strategy_config()
    return float(cfg["gap_up_threshold"]), float(cfg["gap_down_threshold"])


def _apply_morning_checks(
    rd: _Reader,
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
    report.dd_stop, report.dd_stop_since = _check_dd_stop(sqlite_path)
    if report.dd_stop is None:
        rd.warn("DD 停止状態を確認できません（監視 SQLite を読めないため不明）")

    reasons: list[str] = []
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
    if reasons and report.buy_candidates:
        report.skipped_buys = report.buy_candidates
        report.buy_candidates = []
        report.buy_skip_reasons = reasons


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
    rd = _Reader(conn, warnings)
    gaps = gap_thresholds if gap_thresholds is not None else load_gap_thresholds()

    available_cash: float | None = None
    if manual_trading_enabled:
        portfolio_value, available_cash = calc_manual_portfolio_value(
            conn, initial_cash, as_of=report_date
        )
    manual_qty = manual_position_qty_map(conn, as_of=report_date)
    auto_qty = _auto_positions(rd, report_date)
    held = dict(auto_qty)
    for code, qty in manual_qty.items():
        held[code] = held.get(code, 0) + qty

    report = ManualOrderReport(
        phase=phase,
        report_date=report_date,
        generated_at=now or datetime.now(),
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

    if report.signal_date is None:
        rd.warn(f"{report_date} 以前のシグナルがありません")
    else:
        names = _stock_names(rd)
        report.buy_candidates = _collect_buys(rd, report.signal_date, names, held, gaps)
        report.sell_candidates = _collect_sells(rd, report.signal_date, names, auto_qty)
        if phase == "evening" and report.signal_date != report_date:
            rd.warn(
                f"本日（{report_date}）のシグナルがありません。"
                f"最新の {report.signal_date} 分を表示しています"
            )
        missing_price = [b.code for b in report.buy_candidates if b.ref_price is None]
        if missing_price:
            rd.warn(f"参考価格を取得できない BUY 候補があります: {', '.join(missing_price)}")

    if phase == "morning":
        _apply_morning_checks(rd, report, stop_flag_path, sqlite_path)
    return report
