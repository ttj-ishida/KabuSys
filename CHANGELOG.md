# Changelog

すべての変更は「Keep a Changelog」準拠で記載しています。  
セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-22
初回リリース。本リポジトリの基礎機能を実装しました。主に日本株自動売買システム（バックテスト／研究／シグナル生成／設定管理）に必要なコアコンポーネントを含みます。

### Added
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring を __all__ に設定）。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 設定管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数の自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して自動ロード（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - POSIX 風の .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープに対応）。
  - OS 環境変数を保護する protected オプションを導入（.env.local で OS 環境変数を上書きしないよう配慮）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなどをプロパティで取得。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL 等の許容値チェック）と必須変数取得時の明示的エラーを実装。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research で算出した生ファクターを統合・正規化して features テーブルへ UPSERT（日付単位の置換）する機能を実装。
    - ユニバースフィルタ（最低株価 / 20日平均売買代金）を実装。
    - Zスコア正規化・±3 クリップを実装（外れ値対策）。
    - DuckDB トランザクションを用いた原子性のある置換処理（BEGIN/COMMIT/ROLLBACK）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算するユーティリティを実装。
    - 重みの取り扱い（デフォルト重み、ユーザ重みの検証・補完・再スケール）を実装。
    - Bear レジーム検知（ai_scores の regime_score 平均が負なら BUY 抑制）を実装。
    - エグジット条件（ストップロス、スコア低下）に基づく SELL 生成を実装。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）を実装。
    - 欠損データに対する安全装置（存在しない features の銘柄は score=0、AI スコア欠損は中立補完など）を実装。

- 研究モジュール（kabusys.research）
  - ファクター計算（research.factor_research）
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を DuckDB SQL で計算。
    - calc_volatility: 20日 ATR / atr_pct / 20日平均売買代金 / volume_ratio を計算。true_range の NULL 伝播を考慮した実装。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - いずれも prices_daily / raw_financials のみを参照（外部 API にはアクセスしない設計）。
  - 特徴量探索（research.feature_exploration）
    - calc_forward_returns: 指定日から複数ホライズン先までの将来リターンを一括クエリで取得（ホライズン検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（同順位の平均ランク対応）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank ユーティリティ: 同順位は平均ランクとするランク化を実装。
  - research パッケージの公開 API を整備（calc_momentum/calc_volatility/calc_value/zscore_normalize/etc. をエクスポート）。

- データ・スキーマ連携（参照実装を想定）
  - DuckDB を前提とした各種関数で prices_daily, features, ai_scores, positions, raw_financials, market_calendar 等のテーブルを操作・参照する実装。

- バックテスト（kabusys.backtest）
  - engine.run_backtest: 本番 DB からインメモリ DuckDB へ必要データをコピーし、日次ループでシミュレーションを実行するバックテストエンジンを実装。
    - コピー対象テーブルの範囲指定コピー（start_date - 300日 から end_date まで）により本番データの汚染を防止。
    - market_calendar 全件コピーの実装。
    - signals/positions の読み書き、open/close 価格取得ユーティリティを実装。
    - ポジションサイジング（max_position_pct に基づく割当）処理の呼び出し準備を実装（コードの続きで割当適用想定）。
  - ポートフォリオシミュレータ（backtest.simulator）
    - PortfolioSimulator: cash, positions, cost_basis を管理し、約定（simulate）と時価評価を実装。
    - execute_orders: SELL を先、BUY を後に処理。SELL は全量クローズ、BUY は alloc に基づく購入と再計算による手数料考慮の株数調整を実施。
    - スリッページ・手数料モデルを実装（engine の既定値と整合）。
    - mark_to_market による DailySnapshot 記録。
    - TradeRecord / DailySnapshot のデータクラス定義。
  - バックテストメトリクス（backtest.metrics）
    - calc_metrics と BacktestMetrics データクラスを実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）。
    - 各内部計算関数（_calc_cagr, _calc_sharpe, _calc_max_drawdown, _calc_win_rate, _calc_payoff_ratio）を実装。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Known limitations / Notes
- エグジット条件でトレーリングストップや時間決済（保有日数ベース）は未実装。positions テーブルに peak_price / entry_date 等の情報が必要（将来実装予定）。
- generate_signals は AI スコアが未登録の場合、news コンポーネントを中立（0.5）で補完する設計。
- .env パーサは多くの一般的なケースに対応するが、極めて複雑なシェル展開はサポートしない。
- 一部処理は対象テーブル・カラムの存在を前提とする（schema/init の実装が必要）。
- 外部依存（pandas 等）を敢えて使わず標準ライブラリ／DuckDB SQL ベースで実装しているため、大規模データでのパフォーマンスチューニングは今後の課題。

### Security
- 環境変数の必須チェックで未設定時に明示的なエラーを発生させることで運用ミスを検出しやすくしています。

---

今後のリリースでは下記のような拡張を予定しています（予定項目）
- execution 層（kabu API）との統合実装（実際の発注・アカウント管理）
- モデル学習／AI スコア生成パイプラインの統合
- positions テーブルの拡張（entry_date / peak_price 等）と高度なエグジット戦略（トレーリング等）
- 単体テスト・CI 設定およびドキュメント強化

(注) 本 CHANGELOG は提供されたソースコードから機能を推測して作成しています。実際の意図や設計方針と差分がある場合があります。