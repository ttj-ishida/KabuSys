# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。

- リリース日付は ISO 形式（YYYY-MM-DD）で記載しています。
- 初版（0.1.0）はパッケージの主要機能群の実装を含みます。

## [Unreleased]

## [0.1.0] - 2026-03-22

### Added
- パッケージ基盤
  - kabusys パッケージの初回リリース。トップレベルの公開 API を __all__ で定義（data, strategy, execution, monitoring）。
  - バージョン番号を "0.1.0" として定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local の自動ロード機構を実装。プロジェクトルートを .git または pyproject.toml から探索して検出（CWD に依存しない）。
  - .env ファイルパーサ実装（export 形式、クォート文字列、エスケープ、インラインコメント等に対応）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テストでの無効化に利用）。
  - 設定アクセス用 Settings クラスを提供（プロパティ経由で環境変数を取得）。
  - 必須環境変数取得時の _require による明示的エラー発生（不足時は ValueError）。
  - 必須環境変数例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値・パス:
    - KABUSYS_ENV のデフォルトは "development"（有効値: development, paper_trading, live）
    - LOG_LEVEL のデフォルトは "INFO"（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - DUCKDB_PATH デフォルト "data/kabusys.duckdb"
    - SQLITE_PATH デフォルト "data/monitoring.db"
  - OS 環境変数を保護するための上書き制御（.env の override 処理で protected キーを除外）。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）の算出。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を算出（EPS が 0/欠損 の場合は None）。
    - SQL と DuckDB を用いた実装。prices_daily / raw_financials のみ参照。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン算出。ホライズン検証（1〜252 営業日）。
    - calc_ic: スピアマンのランク相関（IC）計算。有効レコードが 3 未満の場合は None。
    - factor_summary, rank: ファクターの統計サマリー、ランク変換ユーティリティ。
    - 外部ライブラリに依存せず、標準ライブラリ + DuckDB で実装する設計方針。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date): research モジュールの生ファクターを取得して統合・正規化し、features テーブルへ UPSERT（対象日を削除して再挿入する日付単位の置換で冪等を保証）。
  - ユニバースフィルタ:
    - 最低株価 _MIN_PRICE = 300 円
    - 20日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）
  - Z スコア正規化対象カラムを定義し、Z スコアを ±3 でクリップして外れ値の影響を抑制。
  - 処理は発注・execution 層に依存しない純粋な特徴量計算。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重み:
      - momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - final_score の BUY 閾値デフォルト _DEFAULT_THRESHOLD = 0.60
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合（サンプル数 >= _BEAR_MIN_SAMPLES）に BUY を抑制。
    - SELL（エグジット）判定:
      - ストップロス: 損益率 <= -8% (_STOP_LOSS_RATE = -0.08)
      - スコア低下: final_score が閾値未満
      - positions / prices 欠損時の安全なスキップ、ログ出力により誤判定や誤クローズを防止。
    - weights の入力検証（未知キー・非数値・負値等はスキップ）、合計が 1.0 でない場合は再スケールあるいはデフォルトにフォールバック。
    - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入で原子性を保証）。

- バックテストフレームワーク（kabusys.backtest）
  - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
    - 本番 DB から必要なテーブルを抽出してインメモリ DuckDB にコピーし（start_date - 300 日の範囲など）、generate_signals を用いて日次ループでシミュレーションを実行。
    - デフォルトのスリッページ・手数料・ポジション最大比率を設定。
    - _build_backtest_conn: date 範囲でのテーブルコピー、market_calendar 全件コピー、コピー失敗時の警告出力。
    - _fetch_open_prices / _fetch_close_prices、_read_day_signals、_write_positions などの補助関数を提供。
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator: メモリ内で cash, positions, cost_basis を管理し約定処理をシミュレート。
    - 約定処理の仕様:
      - SELL を先に処理 → BUY を後で処理（資金管理のため）
      - BUY: alloc に基づいて始値にスリッページを加味し購入株数を切り捨て。手数料を含めて現金不足なら株数を再計算。
      - SELL: 保有全量をクローズ（部分利確非対応）、スリッページ＆手数料反映、realized_pnl を計算して TradeRecord を作成。
      - mark_to_market: 終値で評価し DailySnapshot を記録。価格欠損時は 0 評価で WARNING を出す。
    - TradeRecord / DailySnapshot のデータクラスを提供。
  - メトリクス（kabusys.backtest.metrics）
    - calc_metrics(history, trades) により BacktestMetrics を生成（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 個別計算ロジック（年次化係数、シャープ比の算出、勝率・ペイオフ比の定義等）を実装。

- ロギング・堅牢性
  - 各処理で詳細なログ出力（info/debug/warning）を行うよう実装。トランザクション失敗時は ROLLBACK を試み、失敗時に警告を出す。
  - 欠損データや異常値に対する保険的動作（スキップ、None 扱い、中立値 0.5 で補完など）を多数導入し実運用での安定性を確保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱いに注意:
  - 必要なシークレットは環境変数から取得し、未設定時は明示的にエラーを返すことで安全性を確保。
  - .env の自動ロードはデフォルト有効だが、明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記:
- この CHANGELOG はコードベースから推測して作成した初版の変更履歴です。実際のリリースノートではリリース日や細かい注釈（既知の制限、マイグレーション手順、互換性など）を追加してください。