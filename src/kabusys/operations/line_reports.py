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
        lines.append("銘柄一覧:")
        for s in shown:
            side = s["side"].upper()
            size = s.get("target_size")
            size_str = f" {size}株" if size is not None else ""
            lines.append(f"  {s['code']} {side}{size_str}")
        if len(signals) > max_signals:
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
) -> str:
    """portfolio_construction 完了後の夜通知メッセージを生成する。"""
    lines = [
        f"【KabuSys 夜】{report_date}",
        f"翌日シグナル: {inserted} 件",
        f"当日リターン: {_fmt_rate(daily_return)}",
    ]
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
