# Changelog

すべての重要な変更をここに記録します。本チェンジログは「Keep a Changelog」仕様に準拠します。

なお、本ファイルはソースコード内容から機能追加・設計上の振る舞い・既知の制約を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買フレームワークの核となるモジュール群を提供します。

### Added
- パッケージの基本情報
  - kabusys パッケージの初期バージョンを導入（__version__ = "0.1.0"）。
  - パッケージ公開 API：data, strategy, execution, monitoring を __all__ に定義。

- 環境設定（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト用途）。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応を含む）。
  - protected 機能により OS 環境変数を .env で上書きしない仕組みを提供。
  - Settings クラスを実装し、主要設定値をプロパティ経由で取得：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live 検証）
    - LOG_LEVEL（DEBUG/INFO/... 検証）
    - is_live / is_paper / is_dev ヘルパー

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定と配分：
    - select_candidates: スコア降順で上位 N 銘柄を選択（score / signal_rank によるタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（総スコアが 0 の場合は等金額にフォールバック）。
  - リスク調整：
    - apply_sector_cap: セクター別の既存エクスポージャーを計算し、セクター集中が最大比率（既定 30%）を超える場合に新規候補を除外。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告ログ）。
  - ポジションサイズ決定：
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。lot_size、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap 処理を実装。スケールダウン時の再配分で端数処理（lot 単位）と残差配分ロジックを持つ。
    - risk_based 方式では risk_pct と stop_loss_pct を用いた株数算出を実装。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research の生ファクター（calc_momentum / calc_volatility / calc_value）を統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - Z スコア正規化（指定カラム）、±3 クリップ、features テーブルへの日付単位 UPSERT（トランザクションで原子性保証）。
    - DuckDB を使用した SQL ベースの価格取得とバルク挿入。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - final_score を重み付け合成（デフォルト重みを実装）し、閾値（デフォルト 0.60）で BUY シグナルを生成。
    - Bear レジーム検知時は BUY シグナルを抑制（ai_scores の regime_score 平均が負かつサンプル数閾値以上）。
    - エグジット判定（STOP-LOSS およびスコア低下）を実装し SELL シグナルを生成。
    - signals テーブルへの日付単位の置換（トランザクションで原子性保証）。
    - 衝突回避や不正な weight 入力の検証ロジックを搭載（不正値はスキップ、合計が 1.0 に正規化）。

- リサーチ（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。各関数は欠損時の None 処理やウィンドウカウント条件を考慮。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。外部依存を持たず標準ライブラリ中心で実装。

- バックテスト（kabusys.backtest）
  - metrics.calc_metrics と内部メトリクス実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
  - simulator.PortfolioSimulator: 擬似約定処理とポートフォリオ状態管理を実装。DailySnapshot / TradeRecord のデータモデルを定義。
    - execute_orders: SELL を先行処理、BUY を後処理するポリシー。スリッページ・手数料モデルのパラメータ化（slippage_rate, commission_rate）。SELL は全量クローズの想定。

- ロギング・エラーハンドリング
  - 各モジュールで適切に logger を使用し、重要なフォールバックや警告（例: .env 読み込み失敗、価格欠損、weights の不正値、DB トランザクションの ROLLBACK 失敗）を出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known limitations
- signal_generator:
  - Bear レジームの扱いは保守的で、ai_scores が未登録またはサンプル不足の場合は Bear と見做さない。
  - SELL の判定条件のうち「トレーリングストップ」「時間決済（60 営業日超）」は未実装（positions テーブルに peak_price / entry_date が必要）。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）だとエクスポージャーが過少評価され、ブロックが外れる可能性がある（将来的にフォールバック価格の検討を注記）。
- position_sizing:
  - 単元株数 lot_size は現状グローバル共通（将来的に銘柄別対応を想定）。
  - cost_buffer を用いた保守的見積りは導入済みだが、手数料・スリッページの実運用調整は要検証。
- feature_engineering:
  - 正規化対象のカラムや閾値（例: _MIN_PRICE, _MIN_TURNOVER, _ZSCORE_CLIP）は現状固定値。運用での調整が想定される。
- 環境変数パーサ:
  - 一部の .env 書式（複雑な改行含む値など）や特殊ケースは未試験。読み込み失敗時は warnings.warn で通知。

### Security
- 現時点で特筆すべきセキュリティ修正はなし。ただし環境変数に機密情報を格納する設計のため、運用時の権限管理・シークレット管理は適切に行ってください。

## 破壊的変更 (Breaking Changes)
- 本初版のため、過去互換性に関する破壊的変更は無し。

---

参照:
- 各モジュールの実装には PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md などの設計ドキュメントに基づく旨のコメントが含まれています。運用・拡張の際はそれら設計資料を参照してください。