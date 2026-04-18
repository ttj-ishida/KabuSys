CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

[Unreleased]
------------

- 開発中。次のリリースに向けた小変更やバグ修正をここに追記予定。

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース。日本株自動売買システム "KabuSys" の基礎機能を実装。
- 環境・設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートの .env および .env.local、OS 環境変数を保護して処理）。
  - 強力な .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応）。
  - Settings クラスを導入し、環境変数の取得・検証を統一（必須項目チェック、列挙型検証、パスの Path 型返却など）。
  - config_setup: 対話式ウィザードで .env を生成/更新する CLI を追加。
  - validate_config: .env と config/*.yaml の起動前検証 CLI を追加（--strict オプションで警告を失敗扱いに可能）。
- 実行/監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合に専用の paper DB を使用し、MockBroker を利用することで本番 DB と完全分離。
  - run_monitoring: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用。
  - 停止フラグ（data/stop_requested.flag）および実行 PID 管理（data/execution.pid / data/execution.pid）で安全停止に対応。
- 実行系コンポーネントの骨子
  - ExecutionEngine の依存コンポーネントを組み立てるロジック（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）の組み立て処理を実装。
  - RiskConfig によるデフォルト設定（max_position_pct 等）を導入し、初期利用可能現金を broker.get_available_cash() で取得して利用。
- ロギング・プロセス制御ユーティリティ
  - logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保管）をルートロガーに統一的に設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority: Windows / POSIX(Linux, macOS, FreeBSD) を吸収したプロセス優先度設定ユーティリティ（high/normal/low）および CPU affinity 設定関数を追加。アクセス権限不足などは警告により安全にフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（score ソート）、等金額/スコア重み計算を実装。スコア全ゼロ時のフォールバック警告あり。
  - portfolio.risk_adjustment: セクター集中度チェック（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知のレジームでのフォールバック挙動を定義。
  - portfolio.position_sizing: risk_based / equal / score の割付ロジックを実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）超過時のスケーリング、cost_buffer を考慮した保守的見積り、残差に基づく追加配分などを実装。
- リサーチ
  - research.factor_research: DuckDB 接続を受け取ってモメンタム等のファクターを計算する骨子を追加（モジュール設計、定数、calc_momentum のインターフェース記述）。DuckDB の prices_daily / raw_financials テーブルを前提とした設計。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し、閾値（稼働率 99% 等）に基づき PASS/FAIL 判定を出力。コマンドライン引数で期間指定・DB パス指定が可能。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として公開。

Changed
- N/A（初版のため変更履歴なし）

Fixed
- N/A（初版のため修正履歴なし）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 実装上の注意
- .env の自動ロードは既定で有効。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等で利用）。
- .env 読み込み時、OS 環境変数は保護される（.env.local の override を行う際も保護対象を尊重）。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のみ許容。無効値は ValueError を発生させる。
- ロギングは stdout を使用（stderr ではない）ため、Task Scheduler / cron 等でのリダイレクト運用を想定。
- run_monitoring は MONITOR_POLL_INTERVAL に負の値や 0 が設定されている場合はデフォルト（60 秒）にフォールバックして安全化。
- run_execution は paper_trading モード時に paper DB を使用するため、本番 DB とは分離された検証が可能。

今後の予定（例）
- research.factor_research のファクター実装完了（calc_momentum 等の完全実装）。
- ExecutionEngine / OrderManager 等の統合テストと BrokerClient の本実装（kabuステーション接続部分）。
- より詳細な運用ドキュメントとデプロイ手順の追記。

参考
- パッケージバージョン: 0.1.0
- 生成日: 2026-04-18 (コードベースから推測して作成)