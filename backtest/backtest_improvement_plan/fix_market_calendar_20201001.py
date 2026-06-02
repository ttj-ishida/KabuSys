"""2020-10-01 market_calendar 修正スクリプト

東証システム障害（2020-10-01 全日取引停止）で prices_daily にデータが存在しないが
market_calendar では is_trading_day=True のままのため、バックテストがポジション時価を
0 と評価し擬似 MaxDD（T4: 95%、T5: 52%）が発生していた。

is_trading_day=False に変更してバックテストがその日をスキップするよう修正する。
"""

from __future__ import annotations

import sys
from pathlib import Path


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "strategy_config.yaml").exists():
            return candidate
    raise FileNotFoundError("config/strategy_config.yaml が見つかりません")


REPO_ROOT = _find_repo_root()
ENV_PATH = REPO_ROOT / ".env"
TARGET_DATE = "2020-10-01"


def _load_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        result[key.strip()] = val
    return result


def _get_db_path() -> Path:
    env = _load_env(ENV_PATH)
    db_path = Path(env.get("DUCKDB_PATH", "data/kabusys.duckdb"))
    if not db_path.is_absolute():
        db_path = REPO_ROOT / db_path
    return db_path


def main() -> None:
    import duckdb

    db_path = _get_db_path()
    if not db_path.exists():
        sys.exit(f"[ERROR] DuckDB が見つかりません: {db_path}")

    con = duckdb.connect(str(db_path))

    row = con.execute(
        "SELECT date, is_trading_day FROM market_calendar WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()

    if row is None:
        print(f"[WARN] {TARGET_DATE} は market_calendar に存在しません。何もしません。")
        con.close()
        return

    print(f"修正前: date={row[0]}  is_trading_day={row[1]}")

    if not row[1]:
        print(f"[INFO] {TARGET_DATE} は既に is_trading_day=False です。変更不要。")
        con.close()
        return

    con.execute(
        "UPDATE market_calendar SET is_trading_day = false WHERE date = ?",
        [TARGET_DATE],
    )

    after = con.execute(
        "SELECT date, is_trading_day FROM market_calendar WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    print(f"修正後: date={after[0]}  is_trading_day={after[1]}")

    cnt_sep30 = con.execute(
        "SELECT COUNT(*) FROM prices_daily WHERE date = '2020-09-30'"
    ).fetchone()[0]
    cnt_oct01 = con.execute(
        "SELECT COUNT(*) FROM prices_daily WHERE date = '2020-10-01'"
    ).fetchone()[0]
    print(
        f"prices_daily: 2020-09-30={cnt_sep30} 銘柄, 2020-10-01={cnt_oct01} 銘柄（欠損確認）"
    )

    con.close()
    print("[DONE] market_calendar の修正が完了しました。")


if __name__ == "__main__":
    main()
