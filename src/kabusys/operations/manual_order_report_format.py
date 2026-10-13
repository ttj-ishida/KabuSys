"""手動注文候補レポート（#412）のフォーマッタと保存関数。

すべて純粋関数（save_manual_order_report を除く）。送信は呼び出し元が行う。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from kabusys.operations.line_reports import SELL_REASON_LABELS
from kabusys.operations.manual_order_report import (
    STATUS_BUY_SKIPPED,
    STATUS_OK,
    BuyCandidate,
    ManualOrderReport,
    SellCandidate,
)

PHASE_LABELS = {"evening": "前日夜", "morning": "当日朝"}
STATUS_LABELS = {STATUS_OK: "OK", "WARN": "警告あり", STATUS_BUY_SKIPPED: "BUY 見送り"}
_DEFAULT_BASE = Path("artifacts") / "manual_orders"


def _yen(v: float | None) -> str:
    return "不明" if v is None else f"{v:,.0f} 円"


def _num(v: float | None) -> str:
    return "-" if v is None else f"{v:,.0f}"


def _pct(v: float | None, signed: bool = False) -> str:
    if v is None:
        return "-"
    return f"{v * 100:+.0f}%" if signed else f"{v * 100:.1f}%"


def gap_rule_text(report: ManualOrderReport) -> str:
    up = f"+{report.gap_up_threshold * 100:g}%"
    down = f"−{abs(report.gap_down_threshold) * 100:g}%"
    return f"寄り付きが前日終値比 {up} 超 / {down} 以下なら見送り"


def reason_label(reason: str | None) -> str:
    if not reason:
        return ""
    return SELL_REASON_LABELS.get(reason, reason)


def add_on_text(b: BuyCandidate) -> str:
    if not b.add_on:
        return "新規"
    return f"保有 {b.held_qty} 株 → 目標 {b.held_qty + b.size} 株（差分 {b.size} 株を買う）"


def sell_qty(s: SellCandidate) -> int | None:
    """表示用の売却株数。手動分があれば手動分、なければ自動保有分。"""
    if s.manual and s.manual_qty:
        return s.manual_qty
    return s.auto_qty or None


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


BUY_MAX_LABEL = "この価格以下なら買付可（上限）"
BUY_MIN_LABEL = "この価格以上なら買付可（下限）"


def _buy_table(buys: list[BuyCandidate], *, with_reason: bool = False) -> list[str]:
    if not buys:
        return ["候補なし", ""]
    header = (
        "| 順位 | コード | 銘柄名 | 株数 | 参考価格 | 想定金額 | スコア "
        f"| {BUY_MAX_LABEL} | {BUY_MIN_LABEL} | 備考 |"
    )
    sep = "|---:|---|---|---:|---:|---:|---:|---:|---:|---|"
    if with_reason:
        header += " 見送り理由 |"
        sep += "---|"
    lines = [header, sep]
    for b in buys:
        score = "-" if b.score is None else f"{b.score:.3f}"
        line = (
            f"| {b.rank if b.rank is not None else '-'} | {b.code} | {b.name} | {b.size:,} "
            f"| {_num(b.ref_price)} | {_num(b.amount)} | {score} "
            f"| {_num(b.buy_max_price)} | {_num(b.buy_min_price)} | {add_on_text(b)} |"
        )
        if with_reason:
            line += f" {b.skip_reason or '-'} |"
        lines.append(line)
    lines.append("")
    return lines


def _skipped_section(r: ManualOrderReport, heading: str) -> list[str]:
    if not r.skipped_buys and not r.buy_skip_reasons:
        return []
    lines = [f"{heading}（{len(r.skipped_buys)} 件）", ""]
    if r.buy_skip_reasons:
        lines += ["BUY 全件見送りの理由:", *[f"- {x}" for x in r.buy_skip_reasons], ""]
    return lines + _buy_table(r.skipped_buys, with_reason=True)


def _sell_table(sells: list[SellCandidate]) -> list[str]:
    if not sells:
        return ["候補なし", ""]
    lines = [
        "| コード | 銘柄名 | 売却株数 | 手動保有株数 | 自動保有株数 | 理由 | 区分 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for s in sells:
        kind = "[手動保有]" if s.manual else "自動"
        lines.append(
            f"| {s.code} | {s.name} | {_num(sell_qty(s))} | {_num(s.manual_qty)} "
            f"| {s.auto_qty:,} | {reason_label(s.reason) or '-'} | {kind} |"
        )
    lines.append("")
    return lines


def _ok_ng(v: bool | None, ok: str, ng: str) -> str:
    return "不明" if v is None else (ok if v else ng)


def format_markdown(report: ManualOrderReport) -> str:
    r = report
    lines = [
        f"# 手動注文候補レポート（{PHASE_LABELS[r.phase]}） {r.report_date.isoformat()}",
        "",
        f"- 生成日時: {r.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- シグナル日: {r.signal_date.isoformat() if r.signal_date else 'なし'}",
        f"- ステータス: {STATUS_LABELS[r.status]}",
        "- KabuSys は発注しません。証券画面で手動注文してください。",
        "",
        "## 資金・上限",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| 総資産 | {_yen(r.portfolio_value)}"
        + ("（手動運用）" if r.manual_trading_enabled else "（PORTFOLIO_VALUE）")
        + " |",
        f"| 利用可能現金 | {_yen(r.available_cash)} |",
        f"| 1 銘柄上限（総資産の {r.max_position_pct * 100:g}%） | {_yen(r.max_position_amount)} |",
        f"| 想定投下額（BUY 合計） | {_yen(r.total_buy_amount)} |",
        f"| 利用率（総資産比） | {_pct(r.utilization)} |",
        "",
    ]
    if r.phase == "morning":
        lines += [
            "## 当日朝チェック",
            "",
            "停止フラグ・DD 停止・データ鮮度は、レポートを実行した時点の状態です。",
            "",
            "| 項目 | 結果 |",
            "|---|---|",
            f"| データ鮮度 | {_ok_ng(r.data_freshness_ok, 'OK', 'NG（古い）')} |",
            f"| 停止フラグ | {_ok_ng(r.stop_flag, 'あり', 'なし')} |",
            f"| DD 停止 | {_ok_ng(r.dd_stop, f'停止中（{r.dd_stop_since} から）', 'なし')} |",
            "",
            "## 今日注文すべき候補",
            "",
            f"### BUY（{len(r.buy_candidates)} 件）",
            "",
            *_buy_table(r.buy_candidates),
            f"### SELL（{len(r.sell_candidates)} 件）",
            "",
            *_sell_table(r.sell_candidates),
        ]
        lines += _skipped_section(r, "## 見送り候補") or ["## 見送り候補（0 件）", "", "なし", ""]
    else:
        lines += [
            f"## BUY 候補（{len(r.buy_candidates)} 件）",
            "",
            *_buy_table(r.buy_candidates),
            f"## SELL 候補（{len(r.sell_candidates)} 件）",
            "",
            *_sell_table(r.sell_candidates),
            *_skipped_section(r, "## BUY 見送り候補"),
        ]
    lines += [
        "## 見送りルール",
        "",
        f"- {gap_rule_text(r)}",
        "- 寄り前の気配は取得できないため、ギャップ率は計算しません。"
        f"BUY 表の「{BUY_MAX_LABEL}」「{BUY_MIN_LABEL}」と寄り付き価格を見比べてください"
        "（円未満は切り捨て / 切り上げ済み）。",
        "",
        "## 警告",
        "",
    ]
    lines += [f"- {w}" for w in r.warnings] if r.warnings else ["なし"]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON / CLI / LINE
# ---------------------------------------------------------------------------


def _json_default(o: object) -> str:
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"not serializable: {type(o)!r}")


def format_json(report: ManualOrderReport) -> str:
    data = asdict(report)
    data.update(
        status=report.status,
        total_buy_amount=report.total_buy_amount,
        utilization=report.utilization,
        gap_rule=gap_rule_text(report),
    )
    return json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)


def format_cli_summary(report: ManualOrderReport) -> str:
    r = report
    lines = [
        f"手動注文候補レポート（{PHASE_LABELS[r.phase]}） {r.report_date.isoformat()}"
        f"  ステータス: {STATUS_LABELS[r.status]}",
        f"  シグナル日: {r.signal_date.isoformat() if r.signal_date else 'なし'}",
        f"  BUY {len(r.buy_candidates)} 件 / 見送り {len(r.skipped_buys)} 件"
        f" / SELL {len(r.sell_candidates)} 件",
        f"  想定投下額: {_yen(r.total_buy_amount)}（利用率 {_pct(r.utilization)}）",
    ]
    lines += [f"  [警告] {w}" for w in r.warnings]
    return "\n".join(lines)


def format_line_message(report: ManualOrderReport, *, max_buys: int = 10) -> str:
    r = report
    lines = [
        f"【KabuSys 手動注文 {PHASE_LABELS[r.phase]}】{r.report_date.isoformat()}",
        f"ステータス: {STATUS_LABELS[r.status]}",
        f"シグナル日: {r.signal_date.isoformat() if r.signal_date else 'なし'}",
        "───────────────",
        f"BUY {len(r.buy_candidates)}件" + (":" if r.buy_candidates else ""),
    ]
    for b in r.buy_candidates[:max_buys]:
        suffix = " [買い増し]" if b.add_on else ""
        amount = "金額不明" if b.amount is None else f"{b.amount:,.0f}円"
        lines.append(f"  {b.code} {b.name}  {b.size}株  {amount}{suffix}")
    if len(r.buy_candidates) > max_buys:
        lines.append(f"  … 他 {len(r.buy_candidates) - max_buys} 件")
    if r.skipped_buys or r.buy_skip_reasons:
        lines.append(f"BUY 見送り {len(r.skipped_buys)}件:")
        lines += [f"  ・{x}" for x in r.buy_skip_reasons]
        for b in r.skipped_buys:
            if b.skip_reason and b.skip_reason not in " / ".join(r.buy_skip_reasons):
                lines.append(f"  {b.code} {b.name}: {b.skip_reason}")
    lines.append(f"SELL {len(r.sell_candidates)}件" + (":" if r.sell_candidates else ""))
    for s in r.sell_candidates:
        line = f"  {s.code} {s.name}"
        qty = sell_qty(s)
        if qty:
            line += f"  {qty}株"
        if s.reason:
            line += f" ({reason_label(s.reason)})"
        if s.manual:
            line += " [手動保有]"
        lines.append(line)
    if r.warnings:
        lines.append("警告:")
        lines += [f"  ・{w}" for w in r.warnings]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_manual_order_report(
    report: ManualOrderReport, output_dir: Path | str | None = None
) -> Path:
    """artifacts/manual_orders/{report_date}/{phase}.md と {phase}.json に保存する。

    Returns:
        保存先ディレクトリ。
    """
    base = Path(output_dir) if output_dir else _DEFAULT_BASE
    run_dir = base / report.report_date.isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"{report.phase}.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / f"{report.phase}.json").write_text(format_json(report), encoding="utf-8")
    return run_dir
