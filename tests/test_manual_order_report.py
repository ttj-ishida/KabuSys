"""手動注文候補レポート（#412）のテスト。"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
import pytest

from kabusys.data.schema import init_schema
from kabusys.operations.manual_order_report import collect_manual_order_report
from kabusys.operations.manual_order_report_format import (
    format_cli_summary,
    format_json,
    format_line_message,
    format_markdown,
    save_manual_order_report,
)
from kabusys.operations.manual_trades import ManualTradeInput, add_manual_trade

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

D_SIG = date(2026, 10, 13)  # 火曜
D_NEXT = date(2026, 10, 14)  # 水曜
GAPS = (0.05, -0.03)


def _seed(conn: duckdb.DuckDBPyConnection, sig_date: date = D_SIG) -> None:
    conn.execute(
        "INSERT INTO stocks (code, name) VALUES "
        "('7203','トヨタ自動車'),('6758','ソニーG'),('8306','三菱UFJ'),('4063','信越化学')"
    )
    conn.execute(
        "INSERT INTO signal_queue (signal_id, date, code, side, size, order_type, price, status) "
        "VALUES ('q1', ?, '7203', 'buy', 100, 'market', 3000, 'pending'),"
        "       ('q2', ?, '6758', 'buy', 200, 'market', NULL, 'pending'),"
        "       ('q3', ?, '9984', 'buy', 100, 'market', 9000, 'filled'),"
        "       ('q4', DATE '2026-10-01', '1301', 'buy', 100, 'market', 500, 'pending')",
        [sig_date, sig_date, sig_date],
    )
    conn.execute(
        "INSERT INTO signals (date, code, side, score, signal_rank) VALUES "
        "(?, '7203', 'buy', 0.8, 1), (?, '6758', 'buy', 0.7, 2),"
        "(?, '8306', 'sell', NULL, NULL), (?, '4063', 'sell', NULL, NULL)",
        [sig_date] * 4,
    )
    for d, code, close in [
        (date(2026, 10, 1), "6758", 2400),
        (sig_date, "6758", 2500),
        (sig_date, "8306", 1100),
    ]:
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, 1000)",
            [d, code, close, close, close, close],
        )
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES "
        "(?, '7203', 100, 2900), (?, '4063', 400, 5000)",
        [sig_date, sig_date],
    )
    conn.execute(
        "INSERT INTO manual_action_queue (action_id, date, code, action, qty, reason) "
        "VALUES ('a1', ?, '8306', 'sell_candidate', 300, 'stop_loss')",
        [sig_date],
    )
    add_manual_trade(conn, ManualTradeInput(date(2026, 10, 1), "6758", "buy", 50, 2400))
    add_manual_trade(conn, ManualTradeInput(date(2026, 10, 1), "8306", "buy", 300, 1000))


@pytest.fixture()
def conn():
    c = init_schema(":memory:")
    _seed(c)
    yield c
    c.close()


def _monitoring_db(tmp_path: Path, since: str | None = None) -> Path:
    db = tmp_path / "monitoring.db"
    sc = sqlite3.connect(db)
    sc.execute("CREATE TABLE dashboard (id INTEGER PRIMARY KEY, dd_stop_blocked_since TEXT)")
    sc.execute("INSERT INTO dashboard VALUES (1, ?)", [since])
    sc.commit()
    sc.close()
    return db


def _collect(c, phase="evening", report_date=D_SIG, **kw):
    params = dict(
        phase=phase,
        report_date=report_date,
        manual_trading_enabled=True,
        initial_cash=1_000_000,
        portfolio_value=10_000_000,
        gap_thresholds=GAPS,
    )
    params.update(kw)
    return collect_manual_order_report(c, **params)


# --- evening ---


def test_evening_buy_candidates(conn):
    # 未来日の終値（参照してはいけない）
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (DATE '2026-10-20', '6758', 9999, 9999, 9999, 9999, 1000)"
    )
    r = _collect(conn)
    assert r.signal_date == D_SIG
    codes = [b.code for b in r.buy_candidates]
    assert codes == ["7203", "6758"]  # 順位順・filled/他日付は除外
    toyota, sony = r.buy_candidates
    assert toyota.name == "トヨタ自動車"
    assert toyota.size == 100
    assert toyota.ref_price == 3000
    assert toyota.amount == 300_000
    assert toyota.score == pytest.approx(0.8)
    assert toyota.rank == 1
    assert toyota.held_qty == 100  # 自動保有
    assert toyota.add_on is True
    assert toyota.skip_upper == pytest.approx(3150)
    assert toyota.skip_lower == pytest.approx(2910)
    # 参考価格なし → signal_date 以前の最新終値（未来日 9999 は使わない）
    assert sony.ref_price == 2500
    assert sony.amount == 500_000
    assert sony.held_qty == 50  # 手動保有
    assert sony.add_on is True
    assert r.skipped_buys == []


def test_evening_sell_candidates(conn):
    r = _collect(conn)
    sells = {s.code: s for s in r.sell_candidates}
    assert set(sells) == {"8306", "4063"}
    assert sells["8306"].manual is True
    assert sells["8306"].manual_qty == 300
    assert sells["8306"].reason == "stop_loss"
    assert sells["8306"].name == "三菱UFJ"
    assert sells["4063"].manual is False
    assert sells["4063"].auto_qty == 400
    assert sells["4063"].reason is None


def test_evening_limits_and_utilization(conn):
    r = _collect(conn)
    # 現金 = 1,000,000 - 50*2400 - 300*1000 = 580,000
    assert r.available_cash == pytest.approx(580_000)
    # 時価 = 50*2500 + 300*1100 = 455,000
    assert r.portfolio_value == pytest.approx(1_035_000)
    assert r.max_position_amount == pytest.approx(103_500)
    assert r.total_buy_amount == pytest.approx(800_000)
    assert r.utilization == pytest.approx(800_000 / 1_035_000)


def test_non_manual_uses_settings_portfolio_value(conn):
    r = _collect(conn, manual_trading_enabled=False)
    assert r.portfolio_value == 10_000_000
    assert r.available_cash is None
    assert r.max_position_amount == pytest.approx(1_000_000)


def test_evening_warns_when_no_signal_today(conn):
    r = _collect(conn, report_date=D_NEXT)
    assert r.signal_date == D_SIG
    assert any("2026-10-13" in w for w in r.warnings)


# --- morning ---


def test_morning_picks_previous_trading_day(conn, tmp_path):
    r = _collect(conn, phase="morning", report_date=D_NEXT, stop_flag_path=tmp_path / "x.flag")
    assert r.signal_date == D_SIG
    assert [b.code for b in r.buy_candidates] == ["7203", "6758"]
    assert r.skipped_buys == []
    assert r.stop_flag is False
    assert r.data_freshness_ok is True


def test_morning_stale_signal_skips_all_buys(conn, tmp_path):
    # 10/15 の前営業日は 10/14。最新シグナルは 10/13 → 夜間バッチ欠落の疑い
    r2 = _collect(
        conn, phase="morning", report_date=date(2026, 10, 15), stop_flag_path=tmp_path / "x"
    )
    assert r2.signal_date == D_SIG
    assert r2.buy_candidates == []
    assert [b.code for b in r2.skipped_buys] == ["7203", "6758"]
    assert any("シグナル" in reason for reason in r2.buy_skip_reasons)
    assert any("古い" in w for w in r2.warnings)
    assert r2.status == "BUY_SKIPPED"
    # SELL は常に表示
    assert {s.code for s in r2.sell_candidates} == {"8306", "4063"}


def test_morning_stop_flag_skips_all_buys(conn, tmp_path):
    flag = tmp_path / "stop_requested.flag"
    flag.write_text("stop")
    r = _collect(conn, phase="morning", report_date=D_NEXT, stop_flag_path=flag)
    assert r.stop_flag is True
    assert r.buy_candidates == []
    assert len(r.skipped_buys) == 2
    assert any("停止フラグ" in reason for reason in r.buy_skip_reasons)
    assert r.status == "BUY_SKIPPED"
    assert len(r.sell_candidates) == 2


def test_morning_dd_stop_skips_buys(conn, tmp_path):
    db = _monitoring_db(tmp_path, "2026-10-10")
    r = _collect(conn, phase="morning", report_date=D_NEXT, sqlite_path=db)
    assert r.dd_stop is True
    assert r.buy_candidates == []
    assert any("DD" in reason for reason in r.buy_skip_reasons)


def test_morning_dd_unknown_when_sqlite_missing(conn, tmp_path):
    r = _collect(conn, phase="morning", report_date=D_NEXT, sqlite_path=tmp_path / "none.db")
    assert r.dd_stop is None
    assert len(r.buy_candidates) == 2  # 不明は警告のみ
    assert any("DD" in w for w in r.warnings)
    assert r.status == "WARN"


# --- テーブル欠落 ---


def test_missing_tables_read_only_file_db(tmp_path):
    path = tmp_path / "empty.duckdb"
    duckdb.connect(str(path)).close()
    ro = duckdb.connect(str(path), read_only=True)
    try:
        r = collect_manual_order_report(
            ro,
            phase="morning",
            report_date=D_NEXT,
            manual_trading_enabled=True,
            initial_cash=1_000_000,
            portfolio_value=10_000_000,
            gap_thresholds=GAPS,
            stop_flag_path=tmp_path / "x.flag",
            sqlite_path=tmp_path / "none.db",
        )
    finally:
        ro.close()
    assert r.signal_date is None
    assert r.buy_candidates == [] and r.sell_candidates == []
    assert any("signal_queue" in w for w in r.warnings)
    md = format_markdown(r)
    assert "候補なし" in md


def test_partial_tables_read_only(tmp_path):
    path = tmp_path / "partial.duckdb"
    c = duckdb.connect(str(path))
    c.execute(
        "CREATE TABLE signal_queue (signal_id VARCHAR, date DATE, code VARCHAR, side VARCHAR,"
        " size BIGINT, order_type VARCHAR, price DECIMAL(18,4), status VARCHAR)"
    )
    c.execute(
        "INSERT INTO signal_queue VALUES ('q', ?, '7203', 'buy', 100, 'market', 3000, 'pending')",
        [D_SIG],
    )
    c.close()
    ro = duckdb.connect(str(path), read_only=True)
    try:
        r = _collect(ro)
    finally:
        ro.close()
    assert [b.code for b in r.buy_candidates] == ["7203"]
    assert r.buy_candidates[0].name == "7203"  # stocks なし → コード
    assert r.buy_candidates[0].held_qty == 0
    assert any("signals" in w for w in r.warnings)


# --- フォーマット ---


def test_markdown_evening(conn):
    md = format_markdown(_collect(conn))
    assert "前日夜" in md
    assert "トヨタ自動車" in md
    assert "保有 100 株 → 目標 200 株（差分 100 株を買う）" in md
    assert "損切り" in md and "[手動保有]" in md
    assert "+5% 超" in md and "−3% 以下" in md
    assert "103,500" in md  # 1 銘柄上限


def test_markdown_morning_sections(conn, tmp_path):
    flag = tmp_path / "stop.flag"
    flag.write_text("x")
    md = format_markdown(_collect(conn, phase="morning", report_date=D_NEXT, stop_flag_path=flag))
    assert "当日朝" in md
    assert "今日注文すべき候補" in md
    assert "見送り候補" in md
    assert "停止フラグ" in md


def test_json_roundtrip(conn):
    data = json.loads(format_json(_collect(conn)))
    assert data["phase"] == "evening"
    assert data["report_date"] == "2026-10-13"
    assert data["signal_date"] == "2026-10-13"
    assert data["buy_candidates"][0]["code"] == "7203"
    assert data["sell_candidates"][0]["code"] in {"8306", "4063"}


def test_line_message_morning(conn, tmp_path):
    r = _collect(
        conn,
        phase="morning",
        report_date=D_NEXT,
        stop_flag_path=tmp_path / "x",
        sqlite_path=_monitoring_db(tmp_path),
    )
    assert r.dd_stop is False
    msg = format_line_message(r)
    assert "2026-10-14" in msg
    assert "ステータス: OK" in msg
    assert "BUY 2件" in msg
    assert "7203 トヨタ自動車  100株  300,000円 [買い増し]" in msg
    assert "SELL 2件" in msg
    assert "8306 三菱UFJ  300株 (損切り) [手動保有]" in msg
    assert "4063 信越化学  400株" in msg


def test_line_message_buy_skipped(conn, tmp_path):
    flag = tmp_path / "stop.flag"
    flag.write_text("x")
    msg = format_line_message(
        _collect(conn, phase="morning", report_date=D_NEXT, stop_flag_path=flag)
    )
    assert "ステータス: BUY 見送り" in msg
    assert "停止フラグ" in msg


def test_line_message_top10(conn, tmp_path):
    r = _collect(conn, phase="morning", report_date=D_NEXT, stop_flag_path=tmp_path / "x")
    r.buy_candidates = r.buy_candidates * 7  # 14 件
    msg = format_line_message(r)
    assert "BUY 14件" in msg
    assert "他 4 件" in msg


def test_cli_summary(conn):
    s = format_cli_summary(_collect(conn))
    assert "evening" in s or "前日夜" in s
    assert "BUY 2" in s


def test_save_paths(conn, tmp_path):
    r = _collect(conn)
    run_dir = save_manual_order_report(r, output_dir=tmp_path)
    assert run_dir == tmp_path / "2026-10-13"
    assert (run_dir / "evening.md").exists()
    assert (run_dir / "evening.json").exists()


def test_save_default_dir(conn, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = save_manual_order_report(_collect(conn))
    assert run_dir == Path("artifacts") / "manual_orders" / "2026-10-13"


# --- 共通ラベル ---


def test_sell_reason_labels_public():
    from kabusys.operations.line_reports import SELL_REASON_LABELS

    assert SELL_REASON_LABELS["stop_loss"] == "損切り"


# --- スケジューラ ---


def test_scheduler_has_manual_order_report_jobs():
    import run_scheduler

    jobs = {j.name: j for j in run_scheduler._build_job_schedule()}
    ev = jobs["manual_order_report_evening"]
    assert (ev.script, ev.args, ev.trigger_hour, ev.trigger_minute, ev.needs_exclusive_db) == (
        "run_manual_order_report.py",
        ["--phase", "evening"],
        21,
        10,
        True,
    )
    mo = jobs["manual_order_report_morning"]
    assert (mo.script, mo.args, mo.trigger_hour, mo.trigger_minute, mo.needs_exclusive_db) == (
        "run_manual_order_report.py",
        ["--phase", "morning"],
        8,
        5,
        False,
    )


def test_task_scheduler_ps1_registers_jobs():
    ps1 = (Path(__file__).resolve().parents[1] / "scripts" / "setup_task_scheduler.ps1").read_text(
        encoding="utf-8"
    )
    assert "--phase evening" in ps1 and '"21:10"' in ps1
    assert "--phase morning" in ps1 and '"08:05"' in ps1


# --- スクリプト ---


def _run_script(phase: str, report, tmp_path):
    import run_manual_order_report as mod

    notifier = MagicMock()
    with (
        patch.object(mod, "Settings") as ms,
        patch.object(mod, "duckdb") as mdb,
        patch.object(mod, "collect_manual_order_report", return_value=report) as mc,
        patch.object(mod, "save_manual_order_report", return_value=tmp_path) as msave,
        patch.object(mod, "build_notifier", return_value=notifier),
        patch.object(mod, "register_process", return_value=None),
        patch.object(mod, "log_run_start"),
        patch.object(mod, "log_run_end"),
    ):
        ms.return_value.duckdb_path = tmp_path / "x.duckdb"
        ms.return_value.sqlite_path = tmp_path / "m.db"
        mod.main(["--phase", phase, "--date", "2026-10-14"])
    return mdb, mc, msave, notifier


def test_script_morning_sends_line(conn, tmp_path):
    report = _collect(conn, phase="morning", report_date=D_NEXT, stop_flag_path=tmp_path / "x")
    mdb, mc, msave, notifier = _run_script("morning", report, tmp_path)
    mdb.connect.assert_called_once()
    assert mdb.connect.call_args.kwargs.get("read_only") is True
    assert mc.call_args.kwargs["phase"] == "morning"
    assert mc.call_args.kwargs["report_date"] == D_NEXT
    msave.assert_called_once()
    notifier.send.assert_called_once()


def test_script_evening_no_line(conn, tmp_path):
    report = _collect(conn)
    _, _, msave, notifier = _run_script("evening", report, tmp_path)
    msave.assert_called_once()
    notifier.send.assert_not_called()


def test_script_exits_1_on_error(tmp_path):
    import run_manual_order_report as mod

    with (
        patch.object(mod, "Settings"),
        patch.object(mod, "duckdb"),
        patch.object(mod, "collect_manual_order_report", side_effect=RuntimeError("boom")),
        patch.object(mod, "register_process", return_value=None),
        patch.object(mod, "log_run_start"),
        patch.object(mod, "log_run_end"),
    ):
        with pytest.raises(SystemExit) as exc:
            mod.main(["--phase", "evening"])
    assert exc.value.code == 1


def test_script_line_failure_ignored(conn, tmp_path):
    import run_manual_order_report as mod

    report = _collect(conn, phase="morning", report_date=D_NEXT, stop_flag_path=tmp_path / "x")
    with (
        patch.object(mod, "Settings"),
        patch.object(mod, "duckdb"),
        patch.object(mod, "collect_manual_order_report", return_value=report),
        patch.object(mod, "save_manual_order_report", return_value=tmp_path),
        patch.object(mod, "build_notifier", side_effect=RuntimeError("line down")),
        patch.object(mod, "register_process", return_value=None),
        patch.object(mod, "log_run_start"),
        patch.object(mod, "log_run_end"),
    ):
        mod.main(["--phase", "morning"])  # 例外・SystemExit なし
