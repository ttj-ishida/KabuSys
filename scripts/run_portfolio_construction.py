# scripts/run_portfolio_construction.py
"""Night batch: ポートフォリオ構築 (portfolio_construction_job)。

Task Scheduler から 21:00 に起動される。
signals テーブルから当日の BUY シグナルを読み込み、
ポートフォリオ構築を行って signal_queue と portfolio_targets に書き込む。

環境変数:
    PORTFOLIO_VALUE: 総資産額（円）。デフォルト: 10,000,000
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.portfolio.portfolio_builder import calc_score_weights, select_candidates
from kabusys.portfolio.position_sizing import calc_position_sizes

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_DEFAULT_PORTFOLIO_VALUE = 10_000_000  # 1000万円
_MAX_UTILIZATION = 0.70


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    target_date = date.today()

    portfolio_value = float(
        os.environ.get("PORTFOLIO_VALUE", str(_DEFAULT_PORTFOLIO_VALUE))
    )
    available_cash = portfolio_value * _MAX_UTILIZATION

    try:
        # 1. 当日の BUY シグナルを取得
        cur = conn.execute(
            "SELECT code, side, score, signal_rank FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        )
        rows = cur.fetchall()
        buy_signals = [
            dict(zip([d[0] for d in cur.description], row)) for row in rows
        ]

        if not buy_signals:
            logger.info("本日の BUY シグナルが 0 件です。signal_queue を更新しません。")
            return

        # 2. 銘柄選定・重み計算（メモリ内）
        candidates = select_candidates(buy_signals)
        if not candidates:
            logger.info("銘柄選定結果が 0 件です。signal_queue を更新しません。")
            return

        weights = calc_score_weights(candidates)
        if not weights:
            logger.info("重み計算結果が 0 件です。signal_queue を更新しません。")
            return

        # 3. 最新終値を取得（直近の prices_daily から）
        codes = [c["code"] for c in candidates]
        code_params = ",".join(["?"] * len(codes))
        price_cur = conn.execute(
            f"""
            SELECT p.code, p.close
            FROM prices_daily p
            INNER JOIN (
                SELECT code, MAX(date) AS max_date
                FROM prices_daily
                WHERE code IN ({code_params})
                GROUP BY code
            ) latest ON p.code = latest.code AND p.date = latest.max_date
            """,
            codes,
        )
        open_prices = {r[0]: float(r[1]) for r in price_cur.fetchall() if r[1] is not None}

        # 4. 現在のポジション取得
        pos_cur = conn.execute(
            "SELECT code, size FROM positions WHERE code IN (" + code_params + ")",
            codes,
        )
        current_positions = {r[0]: int(r[1]) for r in pos_cur.fetchall()}

        # 5. ポジションサイズ計算
        sizes = calc_position_sizes(
            weights=weights,
            candidates=candidates,
            portfolio_value=portfolio_value,
            available_cash=available_cash,
            current_positions=current_positions,
            open_prices=open_prices,
        )

        # 6. portfolio_targets / signal_queue をトランザクション内で更新
        conn.execute("BEGIN")
        try:
            conn.execute(
                "DELETE FROM portfolio_targets WHERE date = ?", [target_date]
            )
            for code, weight in weights.items():
                size = sizes.get(code, 0)
                conn.execute(
                    "INSERT INTO portfolio_targets (date, code, target_weight, target_size) VALUES (?,?,?,?)",
                    [target_date, code, weight, size],
                )

            # 7. signal_queue を更新（当日の pending シグナルをクリアして再挿入）
            conn.execute(
                "DELETE FROM signal_queue WHERE date = ? AND status = 'pending'",
                [target_date],
            )
            inserted = 0
            for code, shares in sizes.items():
                if shares <= 0:
                    continue
                price = open_prices.get(code)
                if price is None:
                    logger.warning("価格不明のため銘柄 %s をスキップします。", code)
                    continue
                conn.execute(
                    """INSERT INTO signal_queue
                       (signal_id, date, code, side, size, order_type, price, status)
                       VALUES (?, ?, ?, 'buy', ?, 'market', ?, 'pending')""",
                    [str(uuid.uuid4()), target_date, code, shares, price],
                )
                inserted += 1

            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        logger.info(
            "ポートフォリオ構築完了: %d 銘柄を signal_queue に挿入 (date=%s)",
            inserted,
            target_date,
        )

    except Exception:
        logger.exception("ポートフォリオ構築が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
