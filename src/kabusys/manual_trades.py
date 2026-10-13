"""Manual trade entry CLI.

Examples:
    python -m kabusys.manual_trades add --date 2026-09-18 --code 7203 --side BUY --qty 100 --price 2850 --apply
    python -m kabusys.manual_trades wizard
    python -m kabusys.manual_trades list --date 2026-09-18
"""

from __future__ import annotations

import argparse
from datetime import date
from typing import Sequence

import duckdb

from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.operations.manual_trades import (
    DuplicateManualTradeError,
    ManualTradeInput,
    add_manual_trade,
    delete_manual_trade,
    evaluate_manual_positions,
    list_manual_trades,
)


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("YYYY-MM-DD 形式で指定してください") from exc


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("整数を指定してください") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("1 以上を指定してください")
    return value


def _non_negative_float(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("数値を指定してください") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("0 以上を指定してください")
    return value


def _print_trade_preview(payload: ManualTradeInput) -> None:
    print("手動約定入力:")
    print(f"  date  : {payload.trade_date}")
    print(f"  code  : {payload.code}")
    print(f"  side  : {payload.side.lower()}")
    print(f"  qty   : {payload.qty}")
    print(f"  price : {payload.price:g}")
    print(f"  fees  : {payload.fees:g}")
    if payload.source_signal_id:
        print(f"  signal: {payload.source_signal_id}")
    if payload.note:
        print(f"  note  : {payload.note}")


def _make_payload(args: argparse.Namespace) -> ManualTradeInput:
    return ManualTradeInput(
        trade_date=args.date,
        code=args.code,
        side=args.side,
        qty=args.qty,
        price=args.price,
        fees=args.fees,
        source_signal_id=args.source_signal_id,
        note=args.note,
    )


def _add_from_args(conn: duckdb.DuckDBPyConnection, payload: ManualTradeInput, args) -> str:
    # --force は非推奨。--allow-duplicate と同義で、既存の約定は上書きしない。
    return add_manual_trade(
        conn,
        payload,
        allow_duplicate=args.allow_duplicate or args.force,
        allow_oversell=args.allow_oversell,
    )


def _cmd_add(args: argparse.Namespace) -> int:
    payload = _make_payload(args)
    _print_trade_preview(payload)
    if not args.apply:
        print("保存していません。保存するには --apply を付けて再実行してください。")
        return 0

    conn = init_schema(settings.duckdb_path)
    try:
        trade_id = _add_from_args(conn, payload, args)
    except (DuplicateManualTradeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        conn.close()

    print(f"✓ 手動約定を登録しました: {trade_id}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    conn = init_schema(settings.duckdb_path)
    try:
        rows = list_manual_trades(conn, trade_date=args.date)
    finally:
        conn.close()

    if not rows:
        print("手動約定はありません。")
        return 0

    print("trade_id | date | code | side | qty | price | fees | signal | note")
    for row in rows:
        print(
            " | ".join(
                [
                    row.trade_id,
                    row.trade_date.isoformat(),
                    row.code,
                    row.side,
                    str(row.qty),
                    f"{row.price:g}",
                    f"{row.fees:g}",
                    row.source_signal_id or "",
                    row.note or "",
                ]
            )
        )
    return 0


def _cmd_delete(args: argparse.Namespace) -> int:
    conn = init_schema(settings.duckdb_path)
    try:
        deleted = delete_manual_trade(conn, args.trade_id)
    finally:
        conn.close()

    if deleted:
        print(f"✓ 削除しました: {args.trade_id}")
    else:
        print(f"対象がありません: {args.trade_id}")
    return 0


def _cmd_positions(args: argparse.Namespace) -> int:
    conn = init_schema(settings.duckdb_path)
    try:
        rows = evaluate_manual_positions(conn, as_of=args.date)
    finally:
        conn.close()

    if not rows:
        print("手動保有ポジションはありません。")
        return 0

    print(
        "code | qty | avg_price | cost_basis | price_date | close_price | "
        "market_value | unrealized_pnl | unrealized_pnl_pct | realized_pnl | "
        "total_pnl | last_trade_date"
    )
    for row in rows:

        def value(item: float | None) -> str:
            return "" if item is None else f"{item:g}"

        print(
            " | ".join(
                [
                    row.code,
                    str(row.qty),
                    f"{row.avg_price:g}",
                    f"{row.cost_basis:g}",
                    row.price_date.isoformat() if row.price_date else "",
                    value(row.close_price),
                    value(row.market_value),
                    value(row.unrealized_pnl),
                    value(row.unrealized_pnl_pct),
                    f"{row.realized_pnl:g}",
                    value(row.total_pnl),
                    row.last_trade_date.isoformat(),
                ]
            )
        )
    return 0


def _prompt(label: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{label}{suffix}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    return ""


def _cmd_wizard(args: argparse.Namespace) -> int:
    target_date = _parse_date(_prompt("約定日 YYYY-MM-DD", default=date.today().isoformat()))
    code = _prompt("銘柄コード")
    side = _prompt("売買 BUY/SELL").lower()
    qty = _positive_int(_prompt("数量"))
    price = _non_negative_float(_prompt("約定単価"))
    fees = _non_negative_float(_prompt("手数料", default="0"))
    source_signal_id = _prompt("Signal ID（任意）", default="")
    note = _prompt("メモ（任意）", default="")

    payload = ManualTradeInput(
        trade_date=target_date,
        code=code,
        side=side,
        qty=qty,
        price=price,
        fees=fees,
        source_signal_id=source_signal_id or None,
        note=note or None,
    )
    _print_trade_preview(payload)
    if not args.apply:
        confirm = _prompt("保存しますか？ y/N", default="N").lower()
        if confirm != "y":
            print("保存していません。")
            return 0

    conn = init_schema(settings.duckdb_path)
    try:
        trade_id = _add_from_args(conn, payload, args)
    except (DuplicateManualTradeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        conn.close()

    print(f"✓ 手動約定を登録しました: {trade_id}")
    return 0


def _add_registration_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-duplicate", action="store_true", help="同一内容の約定をもう 1 件登録する"
    )
    parser.add_argument(
        "--allow-oversell", action="store_true", help="保有を超える売却の登録を許可する"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="[非推奨] --allow-duplicate と同じ（既存の約定は上書きしない）",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="手動約定をCLIから入力・確認する")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="手動約定を1件入力する")
    add.add_argument("--date", required=True, type=_parse_date, help="約定日 YYYY-MM-DD")
    add.add_argument("--code", required=True, help="銘柄コード")
    add.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    add.add_argument("--qty", required=True, type=_positive_int, help="約定数量")
    add.add_argument("--price", required=True, type=_non_negative_float, help="約定単価")
    add.add_argument("--fees", default=0.0, type=_non_negative_float, help="手数料")
    add.add_argument("--source-signal-id", default=None, help="対応する Signal Queue ID")
    add.add_argument("--note", default=None, help="メモ")
    add.add_argument("--apply", action="store_true", help="確認だけでなくDBへ保存する")
    _add_registration_flags(add)
    add.set_defaults(func=_cmd_add)

    listing = sub.add_parser("list", help="登録済み手動約定を表示する")
    listing.add_argument("--date", type=_parse_date, default=None, help="約定日で絞り込む")
    listing.set_defaults(func=_cmd_list)

    delete = sub.add_parser("delete", help="手動約定を trade_id で削除する")
    delete.add_argument("trade_id")
    delete.set_defaults(func=_cmd_delete)

    positions = sub.add_parser("positions", help="手動約定から現在の保有ポジションを表示する")
    positions.add_argument("--date", type=_parse_date, default=None, help="この日付時点で集計する")
    positions.set_defaults(func=_cmd_positions)

    wizard = sub.add_parser("wizard", help="対話式で手動約定を入力する")
    wizard.add_argument("--apply", action="store_true", help="最後の確認を省略して保存する")
    _add_registration_flags(wizard)
    wizard.set_defaults(func=_cmd_wizard)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
