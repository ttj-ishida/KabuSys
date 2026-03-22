CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

[Unreleased]

0.1.0 - 2026-03-22
------------------

### Added
- 全体
  - 初期リリース。パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - ロギングと入力データ欠損に対する冗長なチェック・警告出力を各モジュールで導入。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト用途）。
  - .env パーサーを強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォートのエスケープ処理対応
    - インラインコメント処理（クォート有無での挙動を考慮）
  - 読み込み時の上書き制御（override）と OS 環境変数を保護する protected 機能を実装。
  - Settings クラスを提供。主要な環境変数に対する取得メソッド（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、パス（DUCKDB_PATH, SQLITE_PATH）の Path 返却、KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値チェック）や is_live / is_paper / is_dev の便宜プロパティを実装。

- 研究モジュール（src/kabusys/research/*.py）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（価格との結合含む）。
    - SQL ベースで DuckDB の窓関数を活用し、営業日欠損や部分窓を考慮。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランクで処理）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位の平均ランク対応、丸め処理による ties 対応を実装。
  - 研究モジュールは外部 API に依存せず、DuckDB の prices_daily / raw_financials のみ参照する設計。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value を統合して features を構築。
    - ユニバースフィルタ（最低株価 _MIN_PRICE = 300 円、最低 20 日平均売買代金 _MIN_TURNOVER = 5e8 円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップして外れ値の影響を抑制。
    - 日付単位での置換（DELETE → bulk INSERT）をトランザクションで実行し、原子性と冪等性を確保。エラー時にロールバック処理とログ出力。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合し、各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントごとのスコア補完戦略（None を中立値 0.5 で補完）。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と、ユーザ渡し weights の検証・マージ・再スケーリング機能を実装（無効値は警告でスキップ）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数 >= _BEAR_MIN_SAMPLES の場合）により BUY シグナル抑制。
    - BUY 条件: final_score >= threshold（Bear の場合抑制）。
    - SELL 条件（_generate_sell_signals）:
      - ストップロス: 現在価格 / avg_price - 1 <= -0.08（-8%）で即 SELL。
      - スコア低下: final_score < threshold。
      - 価格欠損時の SELL 判定スキップや features にない保有銘柄の扱いについてのログと挙動を明示。
    - signals テーブルへの日付単位置換をトランザクションで行い、冪等性と原子性を保証。

- バックテスト（src/kabusys/backtest/*）
  - simulator:
    - PortfolioSimulator: メモリ内での資産管理、BUY/SELL 約定処理、スリッページと手数料モデルを実装。
    - execute_orders: SELL を先に処理、BUY は alloc（割当）に基づいて株数計算。手数料込みで再計算する資金不足対応。
    - mark_to_market: 終値で評価し DailySnapshot を記録。終値欠損は 0 として評価し警告ログ出力。
    - TradeRecord / DailySnapshot dataclass を提供。
  - metrics:
    - calc_metrics: history/trades から BacktestMetrics（CAGR、Sharpe、MaxDrawdown、WinRate、PayoffRatio、TotalTrades）を計算。
    - 内部で cagr/sharpe/max_drawdown/win_rate/payoff_ratio の実装を提供。
  - engine:
    - run_backtest(conn, start_date, end_date, initial_cash=..., slippage_rate=..., commission_rate=..., max_position_pct=...):
      - 本番 DuckDB からインメモリ DuckDB へ必要データをコピーする _build_backtest_conn を実装（signals/positions を汚さない設計）。
      - 日次ループで (1) 前日シグナル約定 → (2) positions 書き戻し → (3) mark_to_market → (4) generate_signals → (5) 発注リスト作成 → (6) 次日約定、の流れを実装。
      - _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals 等のヘルパーを提供。
      - init_schema(":memory:") 経由で初期スキーマを用意し、必要テーブルを日付範囲でコピー。
      - get_trading_days (kabusys.data.calendar_management) と連携して営業日ループを実行。

### Design / Implementation notes
- 多くの処理（research、strategy、backtest）は発注 API や本番口座に依存しないように設計されており、DuckDB のテーブル（prices_daily / raw_financials / features / ai_scores / positions / market_calendar 等）を入力として利用します。
- データ欠損や非数値（NaN/Inf）に対する防御コード（警告ログ、値補完、スキップ）を各所に実装。
- DB 書き込みは日付単位の置換（DELETE → INSERT）とトランザクションで原子性を担保。ロールバック失敗時には警告ログを出力。
- 外部ユーティリティ（例: kabusys.data.stats.zscore_normalize、kabusys.data.schema.init_schema、kabusys.data.calendar_management.get_trading_days）に依存する箇所あり。

### Known limitations / Todo
- 未実装の戦略機能:
  - トレーリングストップ（peak_price を用いた -10% トレーリング）および時間決済（保有 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date が必要。
  - PBR・配当利回り等のバリュー指標は未実装。
- AI スコアや ai_scores テーブルの存在が前提。登録がない場合は中立扱い（補完）するが運用上の注意が必要。
- 単体テスト・統合テストはこの差分からは提供されていない（テストスイートは別途必要）。
- 一部外部モジュール（data サブパッケージ等）の実装詳細は本差分に含まれていないため、実行環境での依存解決が必要。

Credits
-------
この CHANGELOG はコードベースの内容から生成された推測的ドキュメントです。実際のリリースノートとして公開する場合は、運用チームや開発チームでの確認を推奨します。