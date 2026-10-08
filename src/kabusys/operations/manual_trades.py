"""Manual trade entry service.

手動で発注・約定した取引を DuckDB に記録するための小さな業務ロジック。
CLI と将来の GUI はこのモジュールを共通利用する。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import duckdb

from kabusys.strategy.holdings import HeldPosition

logger = logging.getLogger(__name__)


class DuplicateManualTradeError(Exception):
    """同一 manual trade ID が既に存在するときに送出される。"""


@dataclass(frozen=True)
class ManualTradeInput:
    trade_date: date
    code: str
    side: str
    qty: int
    price: float
    fees: float = 0.0
    source_signal_id: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class ManualTrade:
    trade_id: str
    trade_date: date
    code: str
    side: str
    qty: int
    price: float
    fees: float
    source_signal_id: str | None
    note: str | None
    created_at: datetime


@dataclass(frozen=True)
class ManualPosition:
    code: str
    qty: int
    avg_price: float
    realized_pnl: float
    last_trade_date: date
    first_entry_date: date | None = None
    latest_entry_date: date | None = None


@dataclass(frozen=True)
class ManualPositionValuation:
    code: str
    qty: int
    avg_price: float
    cost_basis: float
    price_date: date | None
    close_price: float | None
    market_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None
    realized_pnl: float
    total_pnl: float | None
    last_trade_date: date


_MANUAL_TRADES_DDL = """
CREATE TABLE IF NOT EXISTS manual_trades (
    trade_id          VARCHAR       NOT NULL PRIMARY KEY,
    trade_date        DATE          NOT NULL,
    code              VARCHAR       NOT NULL,
    side              VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell')),
    qty               BIGINT        NOT NULL CHECK (qty > 0),
    price             DECIMAL(18,4) NOT NULL CHECK (price >= 0),
    fees              DECIMAL(18,4) NOT NULL DEFAULT 0 CHECK (fees >= 0),
    source_signal_id  VARCHAR,
    note              VARCHAR,
    created_at        TIMESTAMP     NOT NULL DEFAULT current_timestamp
)
"""


def ensure_manual_trade_schema(conn: duckdb.DuckDBPyConnection) -> None:
    try:
        conn.execute(_MANUAL_TRADES_DDL)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_manual_trades_date_code ON manual_trades(trade_date, code)"
        )
    except duckdb.Error as exc:
        msg = str(exc).lower()
        if "read-only" in msg or "read only" in msg:
            return
        raise


def build_manual_trade_id(trade_date: date, code: str, side: str) -> str:
    return f"MANUAL_{trade_date.isoformat()}_{code}_{side.lower()}"


def _normalize_input(payload: ManualTradeInput) -> ManualTradeInput:
    code = payload.code.strip()
    side = payload.side.strip().lower()
    if not code:
        raise ValueError("code は必須です")
    if side not in ("buy", "sell"):
        raise ValueError(f"side は buy/sell を指定してください: {payload.side!r}")
    if payload.qty <= 0:
        raise ValueError(f"qty は 1 以上を指定してください: {payload.qty}")
    if payload.price < 0:
        raise ValueError(f"price は 0 以上を指定してください: {payload.price}")
    if payload.fees < 0:
        raise ValueError(f"fees は 0 以上を指定してください: {payload.fees}")
    return ManualTradeInput(
        trade_date=payload.trade_date,
        code=code,
        side=side,
        qty=payload.qty,
        price=payload.price,
        fees=payload.fees,
        source_signal_id=payload.source_signal_id,
        note=payload.note,
    )


def add_manual_trade(
    conn: duckdb.DuckDBPyConnection,
    payload: ManualTradeInput,
    *,
    force: bool = False,
) -> str:
    ensure_manual_trade_schema(conn)
    normalized = _normalize_input(payload)
    trade_id = build_manual_trade_id(normalized.trade_date, normalized.code, normalized.side)

    conn.execute("BEGIN")
    try:
        existing = conn.execute(
            "SELECT 1 FROM manual_trades WHERE trade_id = ?", [trade_id]
        ).fetchone()
        if existing is not None:
            if not force:
                raise DuplicateManualTradeError(
                    f"trade_id={trade_id!r} は既に存在します。上書きするには --force を指定してください。"
                )
            conn.execute("DELETE FROM manual_trades WHERE trade_id = ?", [trade_id])

        conn.execute(
            """
            INSERT INTO manual_trades (
                trade_id, trade_date, code, side, qty, price, fees, source_signal_id, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trade_id,
                normalized.trade_date,
                normalized.code,
                normalized.side,
                normalized.qty,
                normalized.price,
                normalized.fees,
                normalized.source_signal_id,
                normalized.note,
            ],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return trade_id


def _row_to_manual_trade(row: tuple[Any, ...]) -> ManualTrade:
    return ManualTrade(
        trade_id=row[0],
        trade_date=row[1],
        code=row[2],
        side=row[3],
        qty=int(row[4]),
        price=float(row[5]),
        fees=float(row[6]),
        source_signal_id=row[7],
        note=row[8],
        created_at=row[9],
    )


def list_manual_trades(
    conn: duckdb.DuckDBPyConnection,
    *,
    trade_date: date | None = None,
) -> list[ManualTrade]:
    ensure_manual_trade_schema(conn)
    if trade_date is None:
        rows = conn.execute(
            """
            SELECT trade_id, trade_date, code, side, qty, price, fees,
                   source_signal_id, note, created_at
            FROM manual_trades
            ORDER BY trade_date DESC, created_at DESC, trade_id
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT trade_id, trade_date, code, side, qty, price, fees,
                   source_signal_id, note, created_at
            FROM manual_trades
            WHERE trade_date = ?
            ORDER BY created_at DESC, trade_id
            """,
            [trade_date],
        ).fetchall()
    return [_row_to_manual_trade(row) for row in rows]


def delete_manual_trade(conn: duckdb.DuckDBPyConnection, trade_id: str) -> int:
    ensure_manual_trade_schema(conn)
    existing = conn.execute("SELECT 1 FROM manual_trades WHERE trade_id = ?", [trade_id]).fetchone()
    if existing is None:
        return 0
    conn.execute("DELETE FROM manual_trades WHERE trade_id = ?", [trade_id])
    return 1


def calculate_manual_positions(
    conn: duckdb.DuckDBPyConnection,
    *,
    as_of: date | None = None,
) -> list[ManualPosition]:
    """manual_trades から現在の手動保有ポジションを計算する。

    BUY 手数料は取得原価に含め、SELL 手数料は実現損益から控除する。
    部分売却時は平均単価法で原価を取り崩す。
    """
    ensure_manual_trade_schema(conn)
    if as_of is None:
        rows = conn.execute(
            """
            SELECT trade_date, code, side, qty, price, fees
            FROM manual_trades
            ORDER BY trade_date, created_at, trade_id
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT trade_date, code, side, qty, price, fees
            FROM manual_trades
            WHERE trade_date <= ?
            ORDER BY trade_date, created_at, trade_id
            """,
            [as_of],
        ).fetchall()

    state: dict[str, dict[str, Any]] = {}
    for trade_date, code, side, qty, price, fees in rows:
        qty = int(qty)
        price = float(price)
        fees = float(fees)
        pos = state.setdefault(
            code,
            {
                "qty": 0,
                "cost": 0.0,
                "realized_pnl": 0.0,
                "last_trade_date": trade_date,
                "first_entry_date": None,
                "latest_entry_date": None,
            },
        )
        current_qty = int(pos["qty"])
        current_cost = float(pos["cost"])
        if side == "buy":
            if current_qty == 0:
                pos["first_entry_date"] = trade_date
            pos["latest_entry_date"] = trade_date
            pos["qty"] = current_qty + qty
            pos["cost"] = current_cost + (qty * price) + fees
        elif side == "sell":
            sell_qty = min(qty, current_qty)
            avg_cost = current_cost / current_qty if current_qty > 0 else 0.0
            released_cost = avg_cost * sell_qty
            pos["qty"] = current_qty - sell_qty
            pos["cost"] = max(0.0, current_cost - released_cost)
            pos["realized_pnl"] = (
                float(pos["realized_pnl"]) + (sell_qty * price) - released_cost - fees
            )
        pos["last_trade_date"] = trade_date

    positions: list[ManualPosition] = []
    for code, pos in state.items():
        qty = int(pos["qty"])
        if qty <= 0:
            continue
        cost = float(pos["cost"])
        positions.append(
            ManualPosition(
                code=code,
                qty=qty,
                avg_price=cost / qty,
                realized_pnl=float(pos["realized_pnl"]),
                last_trade_date=pos["last_trade_date"],
                first_entry_date=pos["first_entry_date"],
                latest_entry_date=pos["latest_entry_date"],
            )
        )
    return sorted(positions, key=lambda p: p.code)


def evaluate_manual_positions(
    conn: duckdb.DuckDBPyConnection,
    *,
    as_of: date | None = None,
) -> list[ManualPositionValuation]:
    """指定日以前の最新終値で手動保有ポジションを評価する。"""
    valuation_date = as_of or date.today()
    positions = calculate_manual_positions(conn, as_of=valuation_date)
    has_prices = bool(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = 'prices_daily'
            """
        ).fetchone()[0]
    )

    valuations: list[ManualPositionValuation] = []
    for position in positions:
        price_row = None
        if has_prices:
            price_row = conn.execute(
                """
                SELECT date, close
                FROM prices_daily
                WHERE code = ? AND date <= ?
                ORDER BY date DESC
                LIMIT 1
                """,
                [position.code, valuation_date],
            ).fetchone()

        cost_basis = position.qty * position.avg_price
        price_date = price_row[0] if price_row else None
        close_price = float(price_row[1]) if price_row else None
        market_value = position.qty * close_price if close_price is not None else None
        unrealized_pnl = market_value - cost_basis if market_value is not None else None
        unrealized_pnl_pct = (
            unrealized_pnl / cost_basis * 100
            if unrealized_pnl is not None and cost_basis > 0
            else None
        )
        total_pnl = position.realized_pnl + unrealized_pnl if unrealized_pnl is not None else None
        valuations.append(
            ManualPositionValuation(
                code=position.code,
                qty=position.qty,
                avg_price=position.avg_price,
                cost_basis=cost_basis,
                price_date=price_date,
                close_price=close_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                realized_pnl=position.realized_pnl,
                total_pnl=total_pnl,
                last_trade_date=position.last_trade_date,
            )
        )
    return valuations


def load_manual_held_positions(
    conn: duckdb.DuckDBPyConnection, target_date: date
) -> list[HeldPosition]:
    """target_date 時点の手動保有を SELL 判定用の HeldPosition に変換する。"""
    return [
        HeldPosition(
            code=p.code,
            qty=p.qty,
            avg_price=p.avg_price,
            first_entry_date=p.first_entry_date,
            latest_entry_date=p.latest_entry_date,
            source="manual",
        )
        for p in calculate_manual_positions(conn, as_of=target_date)
    ]


def manual_position_qty_map(conn: duckdb.DuckDBPyConnection, *, as_of: date) -> dict[str, int]:
    """as_of 時点の手動保有数量 {code: qty}。"""
    return {p.code: p.qty for p in calculate_manual_positions(conn, as_of=as_of)}


_ACTION_STATUSES = frozenset({"open", "done", "skipped"})
_MANUAL_SOURCES = frozenset({"manual", "mixed"})


def calc_manual_portfolio_value(
    conn: duckdb.DuckDBPyConnection,
    initial_cash: float,
    *,
    as_of: date,
) -> tuple[float, float]:
    """手動運用の (総資産, 利用可能現金) を返す。

    現金 = 元手 − Σ(BUY 約定額 + 手数料) + Σ(SELL 約定額 − 手数料)
    総資産 = 現金 + Σ(手動保有数量 × as_of 以前の最新終値)。終値なしは時価 0 として warning。
    """
    ensure_manual_trade_schema(conn)
    cash = float(initial_cash)
    rows = conn.execute(
        """
        SELECT side, SUM(qty * price), SUM(fees)
        FROM manual_trades
        WHERE trade_date <= ?
        GROUP BY side
        """,
        [as_of],
    ).fetchall()
    for side, amount, fees in rows:
        amount_f = float(amount or 0.0)
        fees_f = float(fees or 0.0)
        if side == "buy":
            cash -= amount_f + fees_f
        else:
            cash += amount_f - fees_f

    market_value = 0.0
    for valuation in evaluate_manual_positions(conn, as_of=as_of):
        if valuation.market_value is None:
            logger.warning(
                "手動保有 %s の終値がないため時価 0 として総資産を計算します as_of=%s",
                valuation.code,
                as_of,
            )
            continue
        market_value += valuation.market_value
    return max(cash + market_value, 0.0), max(cash, 0.0)


def merge_current_positions(
    current: dict[str, int], manual_qty: dict[str, int], codes: list[str]
) -> dict[str, int]:
    """BUY 候補 codes について、自動分の保有株数に手動保有数量を加算する。"""
    merged = dict(current)
    for code in codes:
        qty = manual_qty.get(code, 0)
        if qty > 0:
            merged[code] = merged.get(code, 0) + qty
    return merged


@dataclass(frozen=True)
class ManualAction:
    action_id: str
    date: date
    code: str
    action: str
    qty: int
    reason: str
    status: str
    created_at: datetime
    updated_at: datetime | None


def ensure_manual_action_schema(conn: duckdb.DuckDBPyConnection) -> None:
    from kabusys.data.schema import _MANUAL_ACTION_QUEUE

    try:
        conn.execute(_MANUAL_ACTION_QUEUE)
    except duckdb.Error as exc:
        msg = str(exc).lower()
        if "read-only" in msg or "read only" in msg:
            return
        raise


def build_action_id(target_date: date, code: str, action: str) -> str:
    return f"{target_date.isoformat()}_{code}_{action}"


def record_sell_candidates(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    sell_signals: list[dict[str, Any]],
) -> int:
    """手動保有（source=manual/mixed）の SELL を売却候補として記録する（冪等）。

    既存行は qty / reason のみ更新し、ユーザーが変更した status は保持する。
    発注は行わない。Execution Engine はこのテーブルを参照しない。
    """
    ensure_manual_action_schema(conn)
    recorded = 0
    for sig in sell_signals:
        if sig.get("source") not in _MANUAL_SOURCES:
            continue
        conn.execute(
            """
            INSERT INTO manual_action_queue (action_id, date, code, action, qty, reason)
            VALUES (?, ?, ?, 'sell_candidate', ?, ?)
            ON CONFLICT (action_id) DO UPDATE SET
                qty = excluded.qty,
                reason = excluded.reason,
                updated_at = now()
            """,
            [
                build_action_id(target_date, sig["code"], "sell_candidate"),
                target_date,
                sig["code"],
                int(sig["qty"]),
                str(sig["reason"]),
            ],
        )
        recorded += 1
    return recorded


def list_manual_actions(
    conn: duckdb.DuckDBPyConnection,
    *,
    target_date: date | None = None,
    status: str | None = None,
) -> list[ManualAction]:
    ensure_manual_action_schema(conn)
    where: list[str] = []
    params: list[Any] = []
    if target_date is not None:
        where.append("date = ?")
        params.append(target_date)
    if status is not None:
        where.append("status = ?")
        params.append(status)
    sql = (
        "SELECT action_id, date, code, action, qty, reason, status, created_at, updated_at "
        "FROM manual_action_queue"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, code"
    return [
        ManualAction(
            action_id=r[0],
            date=r[1],
            code=r[2],
            action=r[3],
            qty=int(r[4]),
            reason=r[5],
            status=r[6],
            created_at=r[7],
            updated_at=r[8],
        )
        for r in conn.execute(sql, params).fetchall()
    ]


def update_manual_action_status(
    conn: duckdb.DuckDBPyConnection, action_id: str, status: str
) -> int:
    if status not in _ACTION_STATUSES:
        raise ValueError(f"status は open/done/skipped を指定してください: {status!r}")
    ensure_manual_action_schema(conn)
    before = conn.execute(
        "SELECT COUNT(*) FROM manual_action_queue WHERE action_id = ?", [action_id]
    ).fetchone()[0]
    conn.execute(
        "UPDATE manual_action_queue SET status = ?, updated_at = current_timestamp "
        "WHERE action_id = ?",
        [status, action_id],
    )
    return int(before)


def run_manual_signal_step(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    *,
    enabled: bool,
    generate: Callable[..., int],
    **generate_kwargs: Any,
) -> tuple[int, int]:
    """generate_signals を手動保有込みで実行し、手動保有の SELL を売却候補として記録する。

    enabled=False のときは手動保有を渡さず、候補も記録しない（従来動作）。
    signals 書き込み後に候補記録が失敗した場合は例外を送出する（ジョブを失敗扱いにするため）。
    """
    manual_positions = load_manual_held_positions(conn, target_date) if enabled else None
    sell_out: list[dict[str, Any]] = []
    n = generate(
        conn,
        target_date,
        manual_positions=manual_positions,
        sell_signals_out=sell_out,
        **generate_kwargs,
    )
    recorded = record_sell_candidates(conn, target_date, sell_out) if enabled else 0
    return n, recorded
