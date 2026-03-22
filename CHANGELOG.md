# CHANGELOG

すべての重要な変更をこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に準拠しています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しています。以下はコードベース（src/kabusys）から推測した主要な追加・仕様・制約です。

### 追加（Added）
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン情報と公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルート検出：.git または pyproject.toml）。
  - .env パーサーを実装（コメント・export 形式・シングル/ダブルクォート・バックスラッシュエスケープ対応）。
  - .env の読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 環境変数の必須取得ヘルパー _require と Settings クラスを実装。J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルなどのプロパティを提供。
  - env 値と log level の妥当性検証を実装（不正値で ValueError を送出）。
- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールの生ファクター（momentum/volatility/value）を取り込み、ユニバースフィルタ（株価・平均売買代金）を適用して正規化（Zスコア）・クリップ（±3）し、features テーブルへ日付単位で UPSERT。
    - DuckDB を用いたデータ参照（prices_daily / raw_financials）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出。
    - Bear レジーム判定（AI の regime_score 平均が負）による BUY 抑制。
    - BUY（閾値デフォルト 0.60）と保有ポジションのエグジット条件（ストップロス・スコア低下）に基づく SELL を生成。
    - weights の検証・補完・リスケール処理を実装。
    - signals テーブルへ日付単位置換（トランザクションで原子性確保）。
- Research（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1/3/6M, MA200 乖離）、Volatility（20日 ATR, atr_pct, avg_turnover, volume_ratio）、Value（PER, ROE）を DuckDB クエリで実装。
    - データ不足時の None 処理やウィンドウ行数チェックを適切に処理。
  - 特徴量探索（feature_exploration）
    - 将来リターンの計算（calc_forward_returns: LEAD を使用して複数ホライズンを一括計算）。
    - IC（Spearman の ρ）計算（rank 関数を含む）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - 研究用ユーティリティの公開（zscore_normalize を含む）。
- バックテスト（kabusys.backtest）
  - シミュレータ（simulator.PortfolioSimulator）
    - 擬似約定（BUY/SELL 両方）、スリッページ・手数料モデル、平均取得単価管理、日次時価評価（mark_to_market）、TradeRecord / DailySnapshot の定義。
    - BUY は資金に応じて株数を再計算、SELL は保有全量クローズ。始値欠損時のログ出力とスキップ処理。
  - メトリクス（metrics.calc_metrics）
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算。
  - バックテストエンジン（engine.run_backtest）
    - 本番 DB からインメモリ DuckDB へデータコピー（_build_backtest_conn）し、日次ループでシミュレーションを実行。
    - positions の書き戻し、シグナル生成（generate_signals）呼び出し、ポジションサイジング処理等を実装。
    - market_calendar のコピーと取り扱い、日付範囲のフィルタリング（prices_daily, features, ai_scores, market_regime）。
- 外部依存に関する設計方針
  - 主要ロジックは外部 API（発注 API／本番口座）へ依存しない設計。DuckDB と標準ライブラリ中心で実装。

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### 既知の制約・未実装（Notes / Known issues）
- エグジット条件の一部未実装（コメントに明記）
  - トレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date が必要。
- Value ファクター: PBR や配当利回りは現バージョンでは未実装。
- signals の AI ニューススコア未登録時は中立 0.5 で補完する仕様（欠損補完の方針が明示）。
- .env パーサーは多くのケースに対応しているが、極端なフォーマットや非 UTF-8 ファイルで警告を出す実装（読み込み失敗時に warnings.warn）。
- 一部処理は DuckDB 固有の SQL を利用（ROW_NUMBER 等）。別 DB へ移植する際は注意が必要。
- バックテスト用データコピーでは失敗テーブルをスキップし警告ログを出すため、コピー漏れが起きる可能性がある（設計上の許容）。

### セキュリティ（Security）
- 環境変数の扱い: OS 環境変数を protected として .env による上書きを防止する仕組みを導入。
- パスワードやトークンは Settings を通して必須取得とし、未設定時には ValueError で明示的に失敗させる。

### 互換性（Compatibility / Breaking Changes）
- 初版リリースのため後方互換性に関する既知の破壊的変更はなし。

---

今後の予定（推測）
- エグジットルール拡張（トレーリングストップ、時間決済の実装）
- 追加ファクター（PBR、配当利回り）やより高度なポジションサイジング
- execution 層（kabuAPI を用いた実際の発注機能）と monitoring 層の実装・統合
- テストカバレッジ拡充と CI の整備

（この CHANGELOG はソース内の docstring／コメントと実装から推測して作成しています。実際のリリースノート作成時は開発履歴・コミットログに基づいて精査してください。）