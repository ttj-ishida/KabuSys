"""テスト用ダミーシグナル注入 CLI。

使用例:
    python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100
    python -m kabusys.tools.inject_dummy_signal --code 9984 --side SELL --date 2026-05-08
    python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from typing import Optional

import duckdb

logger = logging.getLogger(__name__)


class DuplicateSignalError(Exception):
    """同一 signal_id のレコードが既に存在するときに送出される。"""


def build_signal_id(target_date: date, code: str, side: str) -> str:
    """ダミーシグナルの一意な ID を生成する。

    形式: DUMMY_{YYYY-MM-DD}_{code}_{side}
    実行系が生成する {date}_{code}_{side} とプレフィックスで区別できる。
    """
    return f"DUMMY_{target_date.isoformat()}_{code}_{side}"


def resolve_target_date(
    conn: duckdb.DuckDBPyConnection,
    explicit_date: Optional[date],
    today: Optional[date] = None,
) -> date:
    """対象日を解決する。

    explicit_date が指定されればその値をそのまま返す。
    None の場合は today（省略時は date.today()）の翌営業日を返す。
    """
    if explicit_date is not None:
        return explicit_date

    from kabusys.data.calendar_management import next_trading_day

    base = today if today is not None else date.today()
    return next_trading_day(conn, base)


def inject_signal(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    code: str,
    side: str,
    qty: int = 100,
    force: bool = False,
) -> str:
    """signal_queue にダミーシグナルを INSERT する。

    Args:
        conn:        DuckDB 接続。
        target_date: シグナルの対象日。
        code:        銘柄コード（例: "7203"）。
        side:        売買区分（"buy" / "sell"、大文字も受け付ける）。
        qty:         注文数量（1 以上）。デフォルト 100。
        force:       True のとき既存レコードを上書きする。

    Returns:
        挿入または更新した signal_id。

    Raises:
        ValueError: side が buy/sell 以外、または qty が 1 未満の場合。
        DuplicateSignalError: force=False かつ同一 signal_id が既に存在する場合。
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError(f"side は 'buy' または 'sell' を指定してください: {side!r}")
    if qty <= 0:
        raise ValueError(f"qty は 1 以上の整数を指定してください: {qty}")

    signal_id = build_signal_id(target_date, code, side)

    conn.execute("BEGIN")
    try:
        existing = conn.execute(
            "SELECT 1 FROM signal_queue WHERE signal_id = ?", [signal_id]
        ).fetchone()

        if existing is not None:
            if not force:
                raise DuplicateSignalError(
                    f"signal_id={signal_id!r} は既に存在します。上書きするには --force を指定してください。"
                )
            conn.execute("DELETE FROM signal_queue WHERE signal_id = ?", [signal_id])

        conn.execute(
            """
            INSERT INTO signal_queue (signal_id, date, code, side, size, order_type, price, status)
            VALUES (?, ?, ?, ?, ?, 'market', NULL, 'pending')
            """,
            [signal_id, target_date, code, side, qty],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return signal_id


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="signal_queue にダミーシグナルを注入する開発ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
利用例:
  python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY
  python -m kabusys.tools.inject_dummy_signal --code 9984 --side SELL --qty 200 --date 2026-05-08
  python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --force
        """,
    )
    parser.add_argument("--code", required=True, help="銘柄コード（例: 7203）")
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        help="売買区分（BUY または SELL）",
    )
    parser.add_argument(
        "--qty",
        type=int,
        default=100,
        help="注文数量（デフォルト: 100）",
    )
    parser.add_argument(
        "--date",
        default=None,
        help=(
            "対象日 YYYY-MM-DD（省略時: 翌営業日）。"
            "注入後すぐに run_signal_queue_report で確認する場合は"
            " --date に同じ日付を指定すること"
            "（レポートのデフォルトは date.today()）。"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="既存の同一シグナルを上書きする",
    )
    args = parser.parse_args()

    explicit_date: Optional[date] = None
    if args.date:
        try:
            explicit_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error(
                "--date の形式が不正です（YYYY-MM-DD 形式で指定してください）: %s",
                args.date,
            )
            sys.exit(1)

    side = args.side.lower()

    from kabusys.config import settings
    from kabusys.data.schema import init_schema

    conn = init_schema(str(settings.duckdb_path))
    try:
        target_date = resolve_target_date(conn, explicit_date)
        signal_id = inject_signal(
            conn,
            target_date=target_date,
            code=args.code,
            side=side,
            qty=args.qty,
            force=args.force,
        )
    except DuplicateSignalError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    finally:
        conn.close()

    action = "上書き" if args.force else "注入"
    print(
        f"✓ ダミーシグナルを{action}しました\n"
        f"  signal_id : {signal_id}\n"
        f"  date      : {target_date}\n"
        f"  code      : {args.code}\n"
        f"  side      : {side}\n"
        f"  qty       : {args.qty}\n"
        f"  order_type: market\n"
        f"  status    : pending"
    )


if __name__ == "__main__":
    main()
