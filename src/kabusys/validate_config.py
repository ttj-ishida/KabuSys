# src/kabusys/validate_config.py
"""設定検証 CLI。

.env および config/*.yaml の設定不備を起動前に検出する。

使い方:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_DIR = _PROJECT_ROOT / "config"

# ---------------------------------------------------------------------------
# 結果収集
# ---------------------------------------------------------------------------

_errors: list[str] = []
_warnings: list[str] = []
_infos: list[str] = []


def _error(msg: str) -> None:
    _errors.append(msg)


def _warn(msg: str) -> None:
    _warnings.append(msg)


def _info(msg: str) -> None:
    _infos.append(msg)


# ---------------------------------------------------------------------------
# 検証ロジック
# ---------------------------------------------------------------------------

_REQUIRED_ENV_VARS = [
    "JQUANTS_REFRESH_TOKEN",
    "KABU_API_PASSWORD",
]

_OPTIONAL_ENV_VARS = [
    "KABUSYS_ENV",
    "DUCKDB_PATH",
    "SQLITE_PATH",
    "LOG_LEVEL",
    "KABU_API_BASE_URL",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_USER_ID",
    "ENABLE_YAHOONEWS",
]

_VALID_KABUSYS_ENVS = frozenset({"development", "paper_trading", "live"})
_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

_CONFIG_FILES = [
    "system_config.yaml",
    "data_config.yaml",
    "strategy_config.yaml",
    "risk_config.yaml",
    "execution_config.yaml",
    "monitoring_config.yaml",
]


def _check_required_env_vars() -> None:
    for var in _REQUIRED_ENV_VARS:
        val = os.environ.get(var, "")
        if not val:
            _error(f"必須環境変数が未設定です: {var}")
        elif val.endswith("_here") or val == "your_value":
            _warn(f"環境変数 {var} がプレースホルダ値のままです。")
        else:
            _info(f"環境変数 {var}: 設定済み")


def _check_kabusys_env() -> None:
    env = os.environ.get("KABUSYS_ENV", "development").lower()
    if env not in _VALID_KABUSYS_ENVS:
        _error(
            f"KABUSYS_ENV の値が不正です: '{env}'. "
            f"有効な値: {sorted(_VALID_KABUSYS_ENVS)}"
        )
    elif env == "live":
        _warn(
            "KABUSYS_ENV=live が設定されています。"
            "本番環境です。すべての設定を慎重に確認してください。"
        )
    else:
        _info(f"KABUSYS_ENV: {env}")


def _check_log_level() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if level not in _VALID_LOG_LEVELS:
        _warn(
            f"LOG_LEVEL の値が不正です: '{level}'. "
            f"有効な値: {sorted(_VALID_LOG_LEVELS)}"
        )
    else:
        _info(f"LOG_LEVEL: {level}")


def _check_path(var: str, default: str, label: str) -> None:
    raw = os.environ.get(var, default)
    path = Path(raw).expanduser()
    parent = path.parent
    if not parent.exists():
        _warn(
            f"{label} の親ディレクトリが存在しません: {parent}"
            " (起動時に自動作成される場合あり)"
        )
    else:
        _info(f"{label}: {path} (親ディレクトリ存在)")


def _check_db_paths() -> None:
    _check_path("DUCKDB_PATH", "data/kabusys.duckdb", "DUCKDB_PATH")
    _check_path("SQLITE_PATH", "data/monitoring.db", "SQLITE_PATH")


_KNOWN_RISK_KEYS = frozenset(
    {
        "max_position_pct",
        "max_utilization",
        "max_drawdown",
        "rate_limit_per_sec",
        "circuit_breaker_errors",
        "circuit_breaker_window_sec",
    }
)


def _parse_ratio(key: str, val: object) -> float:
    """(0, 1] の比率を厳格にパースする。bool は拒否する。"""
    if isinstance(val, bool):
        raise TypeError(f"risk.{key} に bool 値は使用できません（{val!r}）。")
    return float(val)  # type: ignore[arg-type]


def _parse_positive_int(key: str, val: object) -> int:
    """1 以上の整数を厳格にパースする。bool は拒否、小数は拒否する。"""
    if isinstance(val, bool):
        raise TypeError(f"risk.{key} に bool 値は使用できません（{val!r}）。")
    if isinstance(val, float):
        if not val.is_integer():
            raise TypeError(
                f"risk.{key} に小数値は使用できません（{val!r}）。整数で設定してください。"
            )
        return int(val)
    return int(val)  # type: ignore[arg-type]


def _check_risk_config_content(data: object) -> None:
    """risk_config.yaml のセマンティック検証。

    _load_risk_config() と同じルールを事前検証として適用する。
    エラー・警告は _error / _warn に追記する（例外は送出しない）。
    """
    if not isinstance(data, dict):
        _error("risk_config.yaml のトップレベルが dict ではありません。")
        return
    r = data.get("risk")
    if not isinstance(r, dict):
        _error("risk_config.yaml に 'risk' セクションがありません。")
        return

    # 未知キーの警告
    for k in r:
        if k not in _KNOWN_RISK_KEYS:
            _warn(f"risk_config.yaml: 未知のキー 'risk.{k}' が含まれています。")

    # 必須キーの存在確認
    missing = [k for k in _KNOWN_RISK_KEYS if k not in r]
    for k in sorted(missing):
        _error(f"risk_config.yaml: 必須キー 'risk.{k}' がありません。")
    if missing:
        return  # 値検証は必須キーが揃っていることが前提

    # 値域チェック（_load_risk_config と同一ルール）
    try:
        max_position_pct = _parse_ratio("max_position_pct", r["max_position_pct"])
        max_utilization = _parse_ratio("max_utilization", r["max_utilization"])
        max_drawdown = _parse_ratio("max_drawdown", r["max_drawdown"])
        rate_limit_per_sec = _parse_positive_int(
            "rate_limit_per_sec", r["rate_limit_per_sec"]
        )
        circuit_breaker_errors = _parse_positive_int(
            "circuit_breaker_errors", r["circuit_breaker_errors"]
        )
        circuit_breaker_window_sec = _parse_positive_int(
            "circuit_breaker_window_sec", r["circuit_breaker_window_sec"]
        )
    except (ValueError, TypeError) as exc:
        _error(f"risk_config.yaml: 数値変換に失敗しました: {exc}")
        return

    for name, val in (
        ("max_position_pct", max_position_pct),
        ("max_utilization", max_utilization),
        ("max_drawdown", max_drawdown),
    ):
        if not (0 < val <= 1):
            _error(
                f"risk_config.yaml: risk.{name} は (0, 1] の範囲で設定してください"
                f"（現在値: {val}）"
            )

    if max_position_pct > max_utilization:
        _error(
            f"risk_config.yaml: risk.max_position_pct({max_position_pct}) は"
            f" risk.max_utilization({max_utilization}) 以下にしてください。"
        )

    for name, val in (
        ("rate_limit_per_sec", rate_limit_per_sec),
        ("circuit_breaker_errors", circuit_breaker_errors),
        ("circuit_breaker_window_sec", circuit_breaker_window_sec),
    ):
        if val < 1:
            _error(
                f"risk_config.yaml: risk.{name} は 1 以上で設定してください"
                f"（現在値: {val}）"
            )


def _check_config_yaml_files() -> None:
    """config/*.yaml の存在・構文確認。risk_config.yaml はセマンティック検証も行う。"""
    try:
        import yaml  # type: ignore[import]

        _yaml_available = True
    except ImportError:
        _yaml_available = False
        _warn(
            "PyYAML がインストールされていません。YAML ファイルの内容検証をスキップします。"
        )

    for filename in _CONFIG_FILES:
        path = _CONFIG_DIR / filename
        if not path.exists():
            _warn(
                f"config/{filename} が見つかりません。"
                " python scripts/generate_config.py で生成できます。"
            )
        elif _yaml_available:
            try:
                import yaml  # type: ignore[import]

                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                _info(f"config/{filename}: syntax OK")
                if filename == "risk_config.yaml":
                    _check_risk_config_content(data)
            except Exception as e:
                _error(f"config/{filename} のパースに失敗しました: {e}")


def _check_live_guards() -> None:
    """KABUSYS_ENV=live 時の追加チェック。"""
    env = os.environ.get("KABUSYS_ENV", "development").lower()
    if env != "live":
        return

    # LINE 通知の設定確認
    if not os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""):
        _warn(
            "本番環境で LINE_CHANNEL_ACCESS_TOKEN が未設定です。アラートが届きません。"
        )
    if not os.environ.get("LINE_USER_ID", ""):
        _warn("本番環境で LINE_USER_ID が未設定です。アラートが届きません。")

    # kill_flag_clear_on_start が 1 だと危険
    if os.environ.get("KILL_FLAG_CLEAR_ON_START", "0") == "1":
        _warn(
            "本番環境で KILL_FLAG_CLEAR_ON_START=1 が設定されています。"
            " Kill Switch が自動クリアされます。0 を推奨します。"
        )


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def validate() -> tuple[list[str], list[str], list[str]]:
    """検証を実行し、(errors, warnings, infos) を返す。"""
    _errors.clear()
    _warnings.clear()
    _infos.clear()

    _check_required_env_vars()
    _check_kabusys_env()
    _check_log_level()
    _check_db_paths()
    _check_config_yaml_files()
    _check_live_guards()

    return list(_errors), list(_warnings), list(_infos)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="KabuSys 設定を検証する")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="警告も FAIL として扱い exit(1) で終了する",
    )
    args = parser.parse_args(argv)

    errors, warnings, infos = validate()

    for msg in infos:
        print(f"  INFO    {msg}")
    for msg in warnings:
        print(f"  WARNING {msg}")
    for msg in errors:
        print(f"  ERROR   {msg}")

    if errors:
        print(f"\n[FAIL] エラー {len(errors)} 件 / 警告 {len(warnings)} 件")
        return 1
    if warnings and args.strict:
        print(f"\n[FAIL] 警告 {len(warnings)} 件（--strict モード）")
        return 1
    if warnings:
        print(f"\n[OK] エラーなし / 警告 {len(warnings)} 件")
    else:
        print("\n[OK] すべての検証に合格しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
