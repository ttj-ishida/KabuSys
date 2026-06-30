"""line_reports.py — LINE 定期レポートのメッセージ文字列生成。

すべて純粋関数。送信は呼び出し元（run_execution.py 等）が行う。
"""

from __future__ import annotations


def _fmt_rate(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:+.1f}%"


def _fmt_yen(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.0f} 円"


def format_position_reconciliation_message(
    *,
    status: str,
    total_count: int,
    mismatch_count: int,
    positions: list[dict],
    report_date: str,
    max_mismatches: int = 10,
) -> str:
    """Position Reconciliation Report 完了時の LINE 通知メッセージを生成する。

    status は "CLEAN" / "DISCREPANCY" のいずれか。
    DISCREPANCY 時は差分銘柄の詳細を含め、緊急アラートとして送信する。
    """
    if status == "DISCREPANCY":
        header = f"【⚠️ KabuSys ポジション差分検出】{report_date}"
    else:
        header = f"【KabuSys Reconciliation】{report_date}"

    lines = [
        header,
        f"ステータス: {status}",
        f"差分あり: {mismatch_count} 件 / 全体: {total_count} 件",
    ]

    if status == "DISCREPANCY":
        mismatches = sorted(
            [p for p in positions if p.get("status") == "MISMATCH"],
            key=lambda p: p["code"],
        )
        if mismatches:
            shown = mismatches[:max_mismatches]
            lines.append("差分銘柄:")
            for p in shown:
                diff = p.get("diff", p["broker_qty"] - p["local_qty"])
                diff_str = f"+{diff}" if diff > 0 else str(diff)
                lines.append(
                    f"  {p['code']} ブローカー:{p['broker_qty']} / ローカル:{p['local_qty']} (差分:{diff_str})"
                )
            if len(mismatches) > max_mismatches:
                lines.append(f"  … 他 {len(mismatches) - max_mismatches} 件")

    return "\n".join(lines)


def format_signal_queue_message(
    *,
    status: str,
    buy_count: int,
    sell_count: int,
    signals: list[dict],
    report_date: str,
    max_signals: int = 10,
) -> str:
    """Signal Queue Report 完了時の LINE 通知メッセージを生成する。

    status は "READY" / "EMPTY" のいずれか。
    銘柄一覧は max_signals 件まで表示し、超過分は「他 N 件」と省略する。
    """
    lines = [
        f"【KabuSys Signal Queue】{report_date}",
        f"ステータス: {status}",
        f"BUY: {buy_count} 件 / SELL: {sell_count} 件",
    ]
    if signals:
        shown = signals[:max_signals]
        truncated = len(signals) > max_signals
        header = f"銘柄一覧（上位 {max_signals} 件）:" if truncated else "銘柄一覧:"
        lines.append(header)
        for s in shown:
            side = s["side"].upper()
            size = s.get("target_size")
            size_str = f" {size}株" if size is not None else ""
            lines.append(f"  {s['code']} {side}{size_str}")
        if truncated:
            lines.append(f"  … 他 {len(signals) - max_signals} 件")
    return "\n".join(lines)


def format_pre_market_message(
    *,
    status: str,
    warnings_count: int,
    pending_count: int,
    report_date: str,
) -> str:
    """Pre-Market Report 完了時の LINE 通知メッセージを生成する。

    status は "READY" / "READY_WITH_WARNINGS" / "BLOCKED" のいずれか。
    """
    lines = [
        f"【KabuSys Pre-Market】{report_date}",
        f"ステータス: {status}",
        f"警告件数: {warnings_count} 件",
        f"pending シグナル: {pending_count} 件",
    ]
    return "\n".join(lines)


def format_morning_message(
    *,
    status: str,
    orders_no_status: int,
    pending_count: int,
    report_date: str,
) -> str:
    """Execution 起動完了時の朝通知メッセージを生成する。"""
    lines = [
        f"【KabuSys 朝】{report_date}",
        f"ステータス: {status}",
        f"pending シグナル: {pending_count} 件",
    ]
    if orders_no_status > 0:
        lines.append(f"⚠ ステータス不明の注文: {orders_no_status} 件（要確認）")
    return "\n".join(lines)


def format_evening_message(
    *,
    inserted: int,
    report_date: str,
    daily_return: float | None = None,
    buy_signals: list[dict] | None = None,
    sell_signals: list[dict] | None = None,
    max_signals: int = 10,
) -> str:
    """portfolio_construction 完了後の夜通知メッセージを生成する。

    buy_signals=None のとき件数のみの旧フォーマット（後方互換）。
    buy_signals が list のとき BUY/SELL 詳細を展開する。
    """
    if buy_signals is not None:
        buy_count = len(buy_signals)
        sell_count = len(sell_signals) if sell_signals is not None else 0
        header_signal = f"翌日BUY: {buy_count}件 / SELL: {sell_count}件"
    else:
        header_signal = f"翌日シグナル: {inserted} 件"

    lines = [
        f"【KabuSys 夜】{report_date}",
        header_signal,
        f"当日リターン: {_fmt_rate(daily_return)}",
    ]

    has_details = (buy_signals is not None and len(buy_signals) > 0) or (
        sell_signals is not None and len(sell_signals) > 0
    )
    if has_details:
        lines.append("───────────────")

    if buy_signals:
        lines.append("BUY銘柄:")
        shown = buy_signals[:max_signals]
        for s in shown:
            lines.append(f"  {s['code']} {s['name']}  {s['size']}株")
        if len(buy_signals) > max_signals:
            lines.append(f"  … 他 {len(buy_signals) - max_signals} 件")

    if sell_signals:
        lines.append("SELL銘柄:")
        shown = sell_signals[:max_signals]
        for s in shown:
            lines.append(f"  {s['code']} {s['name']}")
        if len(sell_signals) > max_signals:
            lines.append(f"  … 他 {len(sell_signals) - max_signals} 件")

    return "\n".join(lines)


def _format_periodic_message(
    label: str,
    *,
    summary: dict[str, float | None],
    from_date: str,
    to_date: str,
) -> str:
    lines = [
        f"【KabuSys {label}】{from_date} 〜 {to_date}",
        f"累積リターン: {_fmt_rate(summary.get('cumulative_return'))}",
        f"最大ドローダウン: {_fmt_rate(summary.get('max_drawdown'))}",
        f"勝率: {_fmt_rate(summary.get('win_rate'))}",
        f"期末資産: {_fmt_yen(summary.get('equity_end'))}",
    ]
    return "\n".join(lines)


def format_weekly_message(
    *,
    summary: dict[str, float | None],
    from_date: str,
    to_date: str,
) -> str:
    """週次サマリ通知メッセージを生成する。"""
    return _format_periodic_message("週次", summary=summary, from_date=from_date, to_date=to_date)


def format_monthly_message(
    *,
    summary: dict[str, float | None],
    from_date: str,
    to_date: str,
) -> str:
    """月次サマリ通知メッセージを生成する。"""
    return _format_periodic_message("月次", summary=summary, from_date=from_date, to_date=to_date)
