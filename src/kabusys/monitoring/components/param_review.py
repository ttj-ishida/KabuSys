"""param_review.py — AI 提案パラメータのレビュー・適用・バックテスト再実行・比較表示コンポーネント。"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import date
from pathlib import Path

import duckdb
import streamlit as st
import yaml

from kabusys.ai.config_manager import apply_params, backup_config, restore_backup

_logger = logging.getLogger(__name__)

_DISPLAY_NAMES: dict[str, str] = {
    "threshold": "threshold（BUY 閾値）",
    "stop_loss_rate": "stop_loss_rate（損切り率）",
    "trailing_stop_atr_mult": "trailing_stop_atr_mult（ATR 乗数）",
    "min_holding_days": "min_holding_days（最低保有日数）",
    "max_holding_days": "max_holding_days（最大保有日数）",
    "gap_up_threshold": "gap_up_threshold（ギャップアップ閾値）",
    "gap_down_threshold": "gap_down_threshold（ギャップダウン閾値）",
    "sector_boost": "sector_boost（セクターブースト）",
    "sector_quartile": "sector_quartile（セクター区切り）",
    "topix_drawdown_threshold": "topix_drawdown_threshold（TOPIX 下落閾値）",
    "topix_size_multiplier_bear": "topix_size_multiplier_bear（弱気相場サイズ係数）",
}


def _read_current_params(config_path: Path) -> dict:
    """strategy_config.yaml から現在の変更可能パラメータを読み取る。"""
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        _logger.warning("_read_current_params: config 読み取り失敗: %s", e)
        return {}

    result: dict = {}
    s = data.get("strategy", {}) or {}
    for key in (
        "threshold",
        "stop_loss_rate",
        "trailing_stop_atr_mult",
        "min_holding_days",
        "max_holding_days",
        "gap_up_threshold",
        "gap_down_threshold",
    ):
        if key in s:
            result[key] = s[key]
    if isinstance(s.get("weights"), dict):
        result["weights"] = s["weights"]

    sec = data.get("sector", {}) or {}
    if "boost" in sec:
        result["sector_boost"] = sec["boost"]
    if "quartile" in sec:
        result["sector_quartile"] = sec["quartile"]

    reg = data.get("regime", {}) or {}
    for key in ("topix_drawdown_threshold", "topix_size_multiplier_bear"):
        if key in reg:
            result[key] = reg[key]

    return result


def _load_default_dates(duckdb_path: Path) -> tuple[str | None, str | None]:
    """backtest_runs の最新行の start_date / end_date を文字列で返す。"""
    try:
        conn = duckdb.connect(str(duckdb_path), read_only=True)
        try:
            row = conn.execute(
                "SELECT start_date, end_date FROM backtest_runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None, None

    if row is None:
        return None, None
    return str(row[0]), str(row[1])


def _load_run_metrics(duckdb_path: Path, run_id: str) -> dict | None:
    """DuckDB から指定 run_id の指標 dict を返す。見つからない場合は None。"""
    try:
        conn = duckdb.connect(str(duckdb_path), read_only=True)
        try:
            row = conn.execute(
                "SELECT cagr, sharpe, max_drawdown, win_rate, total_trades"
                " FROM backtest_runs WHERE run_id = ?",
                [run_id],
            ).fetchone()
        finally:
            conn.close()
    except Exception as e:
        _logger.warning("_load_run_metrics: %s", e)
        return None

    if row is None:
        return None
    return {
        "cagr": row[0],
        "sharpe": row[1],
        "max_drawdown": row[2],
        "win_rate": row[3],
        "total_trades": row[4],
    }


def render_param_review(
    suggested_params: dict,
    config_path: Path,
    duckdb_path: Path,
    prev_run_id: str | None,
) -> None:
    """AI 提案パラメータのレビュー・適用・バックテスト再実行・比較表示 UI を描画する。

    Args:
        suggested_params: param_extractor.extract_params() が返した提案 dict。
        config_path:      strategy_config.yaml の Path。
        duckdb_path:      subprocess に渡す DuckDB ファイルパス。
        prev_run_id:      変更前の backtest_runs.run_id（比較用）。None の場合は比較なし。
    """
    applied = st.session_state.get("param_review_applied", False)

    if not suggested_params and not applied:
        return

    st.divider()
    st.subheader("📋 AI 提案パラメータ")

    if not applied:
        current = _read_current_params(config_path)
        rows = []
        for key, proposed in suggested_params.items():
            if key == "weights":
                for wk, wv in proposed.items():
                    curr_w = current.get("weights", {}).get(wk, "N/A")
                    rows.append(
                        {
                            "パラメータ": f"weights.{wk}",
                            "現在値": curr_w,
                            "提案値": wv,
                        }
                    )
            else:
                rows.append(
                    {
                        "パラメータ": _DISPLAY_NAMES.get(key, key),
                        "現在値": current.get(key, "N/A"),
                        "提案値": proposed,
                    }
                )
        if rows:
            st.dataframe(rows, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 適用する", key="param_review_apply"):
                try:
                    backup_path = backup_config(config_path)
                    apply_params(config_path, suggested_params)
                    st.session_state["param_review_applied"] = True
                    st.session_state["param_review_backup_path"] = str(backup_path)
                    st.session_state["param_review_prev_run_id"] = prev_run_id
                    st.rerun()
                except Exception as e:
                    st.error(f"適用に失敗しました: {e}")
        with col2:
            if st.button("❌ キャンセル", key="param_review_cancel"):
                st.session_state.pop("param_review_suggested", None)
                st.rerun()
        return

    # --- 適用済み: バックテスト実行フォーム ---
    st.success("✅ パラメータを適用しました。バックテストを再実行して効果を確認できます。")

    default_start, default_end = _load_default_dates(duckdb_path)

    start_val = (
        date.fromisoformat(default_start) if default_start else date(date.today().year - 2, 1, 1)
    )
    end_val = date.fromisoformat(default_end) if default_end else date.today()

    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input("開始日", value=start_val, key="param_review_start")
    with col_e:
        end_date = st.date_input("終了日", value=end_val, key="param_review_end")

    col_run, col_roll = st.columns(2)
    with col_run:
        if st.button("▶ バックテスト実行", key="param_review_run"):
            with st.status("バックテスト実行中...", expanded=True) as status:
                st.write(f"期間: {start_date} 〜 {end_date}")
                try:
                    proc = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "kabusys.backtest.run",
                            "--start",
                            start_date.isoformat(),
                            "--end",
                            end_date.isoformat(),
                            "--db",
                            str(duckdb_path),
                            "--output-format",
                            "json",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=600,
                    )
                except subprocess.TimeoutExpired:
                    status.update(label="❌ タイムアウト", state="error")
                    st.error(
                        "バックテストが600秒でタイムアウトしました。期間を短くするか、後で再試行してください。"
                    )
                    return
                if proc.returncode != 0:
                    status.update(label="❌ バックテスト失敗", state="error")
                    st.error(f"エラー:\n{proc.stderr}")
                    return
                try:
                    report_data = json.loads(proc.stdout)
                    new_run_id: str = report_data["meta"]["run_id"]
                except (json.JSONDecodeError, KeyError) as e:
                    status.update(label="❌ 結果の解析に失敗", state="error")
                    st.error(f"stdout パース失敗: {e}")
                    return
                status.update(label="✅ バックテスト完了", state="complete")
                st.session_state["param_review_new_run_id"] = new_run_id
            st.rerun()
            return

    with col_roll:
        backup_path_str: str = st.session_state.get("param_review_backup_path", "")
        if st.button("⏪ ロールバック", key="param_review_rollback"):
            if not backup_path_str:
                st.error("バックアップが見つかりません。手動で設定を確認してください。")
            else:
                try:
                    restore_backup(Path(backup_path_str), config_path)
                    for k in (
                        "param_review_applied",
                        "param_review_backup_path",
                        "param_review_prev_run_id",
                        "param_review_new_run_id",
                        "param_review_suggested",
                    ):
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"ロールバックに失敗しました: {e}")

    # --- 比較表示 ---
    new_run_id_state: str | None = st.session_state.get("param_review_new_run_id")
    prev_run_id_state: str | None = st.session_state.get("param_review_prev_run_id")
    if not new_run_id_state:
        return

    st.subheader("📊 変更前後の比較")
    new_m = _load_run_metrics(duckdb_path, new_run_id_state)
    prev_m = _load_run_metrics(duckdb_path, prev_run_id_state) if prev_run_id_state else None

    def _pct(v: float | None) -> str:
        return f"{v:+.2%}" if v is not None else "N/A"

    def _f(v: float | None, prec: int = 3) -> str:
        return f"{v:.{prec}f}" if v is not None else "N/A"

    metrics = [
        ("CAGR", "cagr", _pct, True, _pct),
        (
            "Sharpe Ratio",
            "sharpe",
            _f,
            True,
            lambda v: f"{v:+.2f}" if v is not None else "N/A",
        ),
        ("Max Drawdown", "max_drawdown", _pct, True, _pct),
        ("Win Rate", "win_rate", _pct, True, _pct),
        (
            "Total Trades",
            "total_trades",
            lambda v: str(int(v)) if v is not None else "N/A",
            False,
            None,
        ),
    ]

    h1, h2, h3, h4 = st.columns(4)
    h1.markdown("**指標**")
    h2.markdown("**変更前**")
    h3.markdown("**変更後**")
    h4.markdown("**差分**")

    for label, mk, fmt, show_diff, diff_fmt in metrics:
        nv = new_m.get(mk) if new_m else None
        pv = prev_m.get(mk) if prev_m else None
        c1, c2, c3, c4 = st.columns(4)
        c1.write(label)
        c2.write(fmt(pv))
        c3.write(fmt(nv))
        if show_diff and nv is not None and pv is not None and diff_fmt is not None:
            diff = nv - pv
            icon = "🟢" if diff > 0 else "🔴"
            c4.markdown(f"{icon} {diff_fmt(diff)}")
        else:
            c4.write("—")
