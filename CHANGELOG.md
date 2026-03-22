# CHANGELOG

すべての注記は Keep a Changelog の慣例に従います。  
このファイルはコードベース（初期バージョン）から推測して作成した変更履歴です。

## [Unreleased]

- 今後の予定 / 未実装事項（コード内コメントや設計書参照に基づく予告）
  - ポジション管理におけるトレーリングストップ（peak_price の追跡）と時間決済（保有 60 営業日超過）の実装。
  - features / strategy の入力に対する追加のデータ品質チェック・例外ハンドリング強化。
  - AI スコア周りの詳細なモデル連携およびスコア正規化ロジックの拡張。
  - バックテストの並列化・パフォーマンス最適化（大規模データセット対応）。
  - エンドツーエンドでの monitoring / execution 層の統合（Slack 通知・実運用発注連携等）。

---

## [0.1.0] - 2026-03-22

初回リリース（コードベースから推測）。主要な追加点・設計方針は以下の通り。

### Added
- 基本パッケージ構成
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開 API 指定）。
- 設定・環境読み込み機能（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）から .env / .env.local を自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - OS 環境変数を保護するための上書き制御（.env.local が .env を上書きするが、既存の OS 環境変数は保護）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の必須設定取得（未設定時は ValueError を送出）。
  - KABUSYS_ENV と LOG_LEVEL の値チェック（有効な列挙値のみ許容）。
- 戦略（strategy）モジュール
  - feature_engineering.build_features
    - research の生ファクター（モメンタム / ボラティリティ / バリュー）を取得しマージ、ユニバースフィルタ（最低株価・平均売買代金）適用。
    - 指標の Z スコア正規化（指定列）および ±3 でのクリッピング。
    - DuckDB 上の features テーブルへ日付単位で置換（BEGIN/COMMIT + バルク挿入）して冪等性を確保。
  - signal_generator.generate_signals
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算して final_score を算出。
    - デフォルト重みと閾値（threshold=0.60）を用意。ユーザー提供の weights を検証・補完・再スケール。
    - Bear レジーム検出（AI の regime_score の平均が負の場合）による BUY 抑制。
    - エグジット判定（stop_loss: -8% など）による SELL シグナル生成。保有ポジションの評価は positions テーブルを参照。
    - signals テーブルへ日付単位で置換して書き込み（冪等処理）。
- Research（研究）用ユーティリティ（kabusys.research）
  - factor_research モジュール
    - calc_momentum / calc_volatility / calc_value を提供。prices_daily, raw_financials を用いた SQL ベースのファクター計算。
    - 移動平均・ATR・出来高比率・PER などを計算し、データ不足時は None を返す設計。
  - feature_exploration モジュール
    - calc_forward_returns（複数ホライズンでの将来リターン算出）、calc_ic（Spearman ランク相関による IC）、factor_summary（基本統計量）、rank（同順位は平均ランク）を提供。
    - 外部ライブラリ非依存（標準ライブラリのみで実装）。
  - 研究向けの zscore_normalize は kabusys.data.stats から利用可能（エクスポート済み）。
- バックテストフレームワーク（kabusys.backtest）
  - simulator: PortfolioSimulator（擬似約定、手数料・スリッページモデル、SELL 先行・BUY 後処理、マーク・トゥ・マーケット、トレード記録保存）。
  - metrics: calc_metrics / BacktestMetrics（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）。
  - engine: run_backtest（本番 DB から必要テーブルをインメモリ DuckDB にコピーして日次シミュレーションを実行するワークフロー）。
    - データコピーは date 範囲でフィルタ、market_calendar は全件コピー。コピー失敗は警告ログでスキップ。
    - 日次ループ: 約定（前日シグナルを当日の始値で実行）→ positions 書き戻し → 時価評価記録 → generate_signals 実行 → ポジションサイジング → 次日に備える。
    - ポジションサイジングでは 1 銘柄あたりの最大ポジション比率（max_position_pct）を考慮。
- DB スキーマ依存上の明記（コード内で参照されるテーブル）
  - prices_daily, raw_financials, features, ai_scores, positions, signals, market_calendar, market_regime 等。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Removed
- （新規リリースのため該当なし）

### Security
- （新規リリースのため該当なし）

---

## 既知の制限・注意点（implementation notes）
- 一部機能は意図的に未実装・将来実装予定
  - トレーリングストップ（peak_price）および時間決済（保有 60 営業日超過）はコメントで未実装と明記されている。
- データ欠損時の扱い
  - features に存在しない保有銘柄は final_score = 0.0 として SELL 判定候補にされる（ロギングあり）。
  - 価格欠損時は SELL 判定の判定自体をスキップして誤クローズを防ぐ処理があるが、バックテスト上の挙動に注意が必要。
- .env 自動読み込みはプロジェクトルートの検出に依存する（.git もしくは pyproject.toml）。配布後の挙動に注意。
- DuckDB に依存した実装であるため、必須テーブルとカラムの存在が前提。テーブル定義の不一致・欠損は実行時例外や警告の原因となる。
- バックテストのデータコピーは try/except で失敗したテーブルをスキップするため、部分的にデータが欠ける可能性がある（警告ログで通知）。
- weights 引数や env 値のバリデーションがあり、不正値はスキップまたは例外となる（generate_signals、Settings）。

---

この CHANGELOG はコードベースの実装内容および内包コメントから推測して作成しています。リリースノートとして公開する際は、実際のコミット履歴やリリース日、責任者などの実データで更新してください。