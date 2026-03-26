# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このリポジトリの現在のパッケージバージョン: 0.1.0

## [Unreleased]
- （現在の差分はありません）

## [0.1.0] - 初回リリース
リリース日: 未設定

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - kabase のサブパッケージをエクスポート: data, strategy, execution, monitoring, portfolio, research, backtest 等の主要モジュール群を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から特定）。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラス実装（プロパティ経由で各種必須/任意設定を取得）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得する _require() 実装。
    - KABU_API_BASE_URL のデフォルト値、DUCKDB_PATH / SQLITE_PATH の既定パス、環境 (development/paper_trading/live) と LOG_LEVEL の検証ロジック。
    - is_live / is_paper / is_dev ヘルパー。

- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定・重み付け (portfolio_builder)
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank によるタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック、警告出力）。
  - リスク調整 (risk_adjustment)
    - apply_sector_cap: 既存保有のセクターエクスポージャーを計算し、指定比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは警告の上 1.0 にフォールバック）。
  - 位置サイズ決定 (position_sizing)
    - calc_position_sizes: allocation_method による発注株数計算を実装（"risk_based" / "equal" / "score" に対応）。
    - リスクベースでは risk_pct, stop_loss_pct 等を用いて目標株数を算出。
    - 単元（lot_size）で丸め、per-stock 上限（max_position_pct）と aggregate 上限（available_cash）を考慮したスケーリング。
    - cost_buffer を使った保守的コスト見積り、端数処理のための再配分ロジックを実装。

- 戦略（feature engineering / signal generation） (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュールからの生ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（±3 クリップ）を行い、features テーブルへ日付単位で冪等的に書き込む。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する実装。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算して final_score を算出。
    - デフォルト重みと閾値（default threshold=0.60）を実装。ユーザー指定 weights は検証・正規化される。
    - Bear レジーム検知時は BUY シグナルを抑制（ai_scores の regime_score を集計して判定）。
    - SELL シグナル生成ロジック（ストップロス / final_score の閾値未満）を実装。保有位置の価格欠損時には判定をスキップし警告を出力。
    - signals テーブルへの日付単位の置換（トランザクションで原子性確保）。
    - BUY と SELL の優先ルール（SELL 優先で BUY から除外）とランク再付与。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装（各ファクターの定義は StrategyModel.md に準拠）。
    - DuckDB を用いて prices_daily / raw_financials から必要指標を算出（MA200, ATR20, avg_turnover, per, roe 等）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括クエリで計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ。
  - zscore_normalize は data.stats から提供されるユーティリティとして利用。

- バックテスト（kabusys.backtest）
  - metrics.calc_metrics: DailySnapshot / TradeRecord から評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算する機能。
  - simulator.PortfolioSimulator:
    - メモリ内のポートフォリオ状態管理、BUY/SELL の擬似約定処理を実装。SELL を先に処理し、その後 BUY（資金確保目的）。
    - スリッページ（buy:+、sell:-）と手数料率を考慮した約定価格・手数料の計算、TradeRecord の記録機能。
    - DailySnapshot / TradeRecord のデータクラスを定義。

### Changed
- （初回リリースのため過去変更はなし）

### Fixed
- （初回リリースのため過去修正はなし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

---

注意・既知の制限・TODO
- 一部機能は意図的に未実装／将来の拡張予定としてコメントあり（例：position_sizing の銘柄別 lot_size 拡張、signal_generator のトレーリングストップや時間決済条件）。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる可能性がある旨をコメントで明記。将来的に前日終値等のフォールバック実装を検討。
- generate_signals の Bear 判定は ai_scores のサンプル数不足時は Bear とみなさない（誤判定防止）。
- DuckDB と特定テーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提とした設計。実行には該当スキーマとデータが必要。

この CHANGELOG はコードベースの現状から推測して作成しています。実際のリリース日や追加のリリースノートはプロジェクトのリリースワークフローに従って補完してください。