CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-26
--------------------

Added
- パッケージ初期リリース。
- 基本モジュール群を実装:
  - kabusys.config
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース/タブ直前の # をコメント扱い）に対応。
    - OS 環境変数を protected として .env の上書きを制御。
    - settings オブジェクトを提供（J-Quants / kabu ステーション / Slack / DB パス / 実行環境 / ログレベルなどのプロパティ、妥当性チェックを含む）。
  - ポートフォリオ関連
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルを score 降順（同点は signal_rank 昇順）で上位 N 件を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
    - portfolio.risk_adjustment
      - apply_sector_cap: 既存保有のセクター比率に基づき、上限を超えるセクターの新規候補を除外（"unknown" セクターは適用除外）。sell_codes を受け取り当日売却予定銘柄をエクスポージャー計算から除外可能。
      - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0、警告ログあり）。
    - portfolio.position_sizing
      - calc_position_sizes: risk_based / equal / score の各 allocation_method を実装。lot_size（単元）で丸め、per-position 上限・aggregate cap、cost_buffer を考慮したスケーリングと端数配分ロジックを実装。
  - 戦略（strategy）
    - strategy.feature_engineering
      - build_features: research モジュールの生ファクター（momentum/volatility/value）からユニバースフィルタ（株価・流動性）を適用、Z スコア正規化・±3 クリップして features テーブルへ日付単位で冪等的に書き込み（トランザクション + バルク挿入、ロールバック対応）。
    - strategy.signal_generator
      - generate_signals: features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、シグモイド変換・欠損補完を行い final_score を算出。
      - Bear レジーム検知時は BUY シグナルを抑制。SELL（エグジット）判定ロジック（ストップロス、スコア低下）を実装し、SELL を優先して signals テーブルへ日付単位で冪等的に書き込み。
  - research
    - factor_research: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関、ties の平均ランク対応）、factor_summary（基本統計量）を実装。外部依存を持たない実装。
    - research パッケージから主要ユーティリティをエクスポート（zscore_normalize 等）。
  - backtest
    - backtest.metrics: バックテスト評価指標（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）計算を実装。
    - backtest.simulator: PortfolioSimulator（DailySnapshot / TradeRecord）を実装。SELL を先行処理し BUY を後で処理する実約定シミュレーション、スリッページ・手数料モデル（引数で指定）や lot_size 対応。ロギングを含む。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（.env が意図せずシステム変数を上書きしないように保護）。

Notes / Known limitations / TODO
- 一部設計上の注意・未実装事項をソースコメントで明示:
  - apply_sector_cap: price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性あり。将来的な価格フォールバックの検討が必要。
  - signal_generator: トレーリングストップや時間決済（保有日数ベース）の条件は未実装（positions テーブルに peak_price / entry_date が必要）。
  - position_sizing: lot_size を銘柄別に持たせる拡張（stocks マスタ）を将来的に想定。
  - feature_engineering/research: DuckDB 上のテーブル構成（prices_daily/raw_financials 等）に依存。実行前にスキーマとデータの整合性を確認すること。
  - 一部関数は入力データの不備（欠損やサンプル不足）に対して None やフォールバックを返す設計になっているため、上位レイヤーでのハンドリングが必要。
- テスト・エッジケース検証は今後継続して強化予定。

Authors
- 実装: kabusys チーム

References
- 各モジュール内に設計ドキュメントおよび参照セクション（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等）の言及あり。実運用前に該当ドキュメントを確認してください。