CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初期リリース "KabuSys"（バージョン 0.1.0）。
  - パッケージルート: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - 公開モジュール群を __all__ に定義: data, strategy, execution, monitoring。

- 環境・設定管理モジュール（src/kabusys/config.py）
  - .env/.env.local ファイルおよび実際の OS 環境変数から設定を読み込む自動ロードを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（配布後も正しく動作）。
  - .env パーサ実装: export 構文、シングル/ダブルクォート内のエスケープ、インラインコメントルール等に対応。
  - 環境変数取得ユーティリティ _require と Settings クラスを提供。
    - 必須項目（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH。
    - バリデーション: KABUSYS_ENV（"development","paper_trading","live" のみ）、LOG_LEVEL（"DEBUG"〜"CRITICAL"）を検証。
    - Settings インスタンスを settings として公開。

- 戦略関連（src/kabusys/strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - build_features(conn, target_date): research で算出した raw ファクターを取り込み、ユニバースフィルタ・Z スコア正規化（zscore_normalize を使用）・±3 でのクリッピングを行い、features テーブルへ冪等的に書き込み。
    - ユニバースフィルタ: 最低株価（300 円）・20日平均売買代金（5 億円）を適用。
    - トランザクションを用いた日付単位の置換（DELETE + bulk INSERT）で原子性を確保。ROLLBACK の失敗は警告ログ出力。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ冪等的に書き込み。
    - スコア計算:
      - コンポーネント: momentum, value, volatility, liquidity, news（AI スコア）。
      - momentum 等は Z スコアをシグモイド変換して合算。欠損コンポーネントは中立 0.5 で補完。
      - 重みはデフォルト値（momentum:0.40 等）を用い、ユーザ指定 weights は検証・再スケーリングして適用。
    - Bear レジーム検知: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数閾値あり）。
    - SELL 判定（エグジット）:
      - ストップロス: 終値 / avg_price - 1 < -8%（最優先）。
      - スコア低下: final_score が閾値未満。
      - 一部未実装のエグジット（トレーリングストップ、時間決済）はコード中に注記あり。
    - signals テーブルへ日付単位の置換で原子性を確保。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev を計算（ウィンドウ不足時は None）。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の計算は high/low/prev_close の NULL を厳密に扱う。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER/ROE を計算（EPS が 0/NULL の場合は PER を None に）。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 指定ホライズンの将来リターンを一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算、サンプル不足時は None。
    - factor_summary(records, columns): count/mean/std/min/max/median を返す統計サマリー。
    - rank(values): 同順位は平均ランクとするランク付け実装（丸めで ties の検出漏れを防止）。
  - research パッケージは zscore_normalize と主要関数を公開。

- データ統計ユーティリティ（参照）
  - build_features 等で使用する zscore_normalize を data.stats から利用（実装ファイルはこの差分に含まれず参照のみ）。

- バックテストフレームワーク（src/kabusys/backtest）
  - シミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator: メモリ内での擬似約定・ポートフォリオ管理を実装。
      - execute_orders: SELL を先に処理、BUY は全額配分に基づき約定（部分利確・部分損切りは未対応）。
      - スリッページ・手数料モデルを適用（entry/exit に対する slippage_rate、commission_rate）。
      - 平均取得単価（cost_basis）の管理、TradeRecord の記録（BUY/SELL）。
      - mark_to_market: 終値で評価し DailySnapshot を記録。終値欠損時は 0 として警告ログを出力。
    - TradeRecord / DailySnapshot の dataclass 定義。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - calc_metrics(history, trades) が BacktestMetrics を返す。
    - 計算項目: CAGR, Sharpe Ratio（無リスク金利=0, 年次化: sqrt(252)）, Max Drawdown, Win Rate, Payoff Ratio, total_trades。
  - エンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20): 本番 DB からインメモリ DuckDB に必要データをコピーし、日次ループで generate_signals を用いたシミュレーションを実行して結果を返す（BacktestResult）。
    - _build_backtest_conn: データの部分コピー（date 範囲フィルタ）と market_calendar 全件コピーによりバックテスト用の in-memory 接続を構築。エラー時は警告ログでスキップする設計。
    - 日次ループの流れ:
      1. 前日シグナルを当日始値で約定（simulator.execute_orders）
      2. positions テーブルへ simulator の保有を書き戻し（generate_signals の SELL 判定のため）
      3. 終値で時価評価（simulator.mark_to_market）
      4. generate_signals を呼び出して当日シグナルを生成
      5. signal を読み取りポジションサイジングを行う（買付上限: max_position_pct 等）

Changed
- N/A（初回リリースのため過去からの変更点はなし）。

Fixed
- N/A（初回リリース）。

Notes / Known limitations
- signal_generator のエグジットロジックにはトレーリングストップや保有期間に基づく時間決済が未実装（コード内で明記）。
- features の一部カラム（per など）は正規化対象外（逆数変換等の扱いはコメントで言及）。
- 外部依存を排し、DuckDB へ SQL を発行する設計。pandas 等には依存しない実装方針。
- .env パーサは一般的なケースを想定しているが、特殊な .env フォーマットは想定外の挙動となる可能性あり。
- run_backtest は本番 DB を読み取り専用で使用し、in-memory にデータコピーして実行することで本番テーブルの汚染を避ける設計。ただし大規模データのコピーに伴うコストがある。

公開 API（主なもの）
- kabusys.settings (Settings インスタンス)
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=None, weights=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- kabusys.backtest.DailySnapshot, TradeRecord, BacktestMetrics

開発者向けメモ
- トランザクション処理時のエラーハンドリングは ROLLBACK の失敗を警告にとどめ、例外を再送出する方針。
- env 自動ロードはプロジェクトルートが特定できない場合にスキップされるため、パッケージを配布後も安全に動作する。
- 設定に関する例外は ValueError を利用して早期に誤設定を検出する設計。

-- End of changelog --