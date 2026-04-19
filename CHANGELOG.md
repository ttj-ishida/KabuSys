# Changelog

すべての変更は Keep a Changelog に準拠して記載しています。  
当リポジトリの初期リリース相当の変更点を、コードベースの内容から推測してまとめています。

## [Unreleased]

### Added
- ドキュメント化されている CLI / 起動スクリプトを追加
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 専用 SQLite DB を使用するよう分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポートし、停止フラグファイル（data/stop_requested.flag）検出で安全に終了。
  - kabusys.tools.paper_verification_report: ペーパートレード用検証レポート生成スクリプト（期間指定・DB 指定オプション有り）。

- 設定周りのユーティリティを追加
  - config.py: 環境変数 / .env の自動読み込み、.env パース（シングル/ダブルクォート、export プレフィックス、コメント処理対応）、Settings クラス（各種設定プロパティ、値検証）を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザード。シークレットのマスク表示、既存値の再利用、.env ファイル書き出し機能を提供。
  - validate_config.py: 起動前チェック用 CLI。必須環境変数や config/*.yaml、パスの存在チェック、KABUSYS_ENV による追加ガードチェック、--strict オプションにより警告を失敗扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）を追加
  - portfolio.portfolio_builder: 候補選定（スコア降順）、等金額配分、スコア重み配分（スコア全て 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment: セクター集中上限の適用（既存保有を考慮して候補を除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、aggregate cap（利用可能現金超過時のスケーリング）やコストバッファの考慮を実装。
  - portfolio パッケージのエクスポートを統一。

- 研究/ファクター計算の基盤追加（途中実装を含む）
  - research.factor_research: DuckDB 接続を受け取り、モメンタム・MA200 乖離・ATR 等のファクター算出方針と定数を定義（prices_daily / raw_financials を参照する設計）。

- ユーティリティ追加
  - utils.logging_setup: ルートロガーの統一セットアップ。stdout ストリームハンドラと日次ローテートのファイルハンドラを設定し、ログディレクトリ作成失敗時はファイル出力をスキップする堅牢化。
  - utils.process_priority: プラットフォーム差（Windows / POSIX）を吸収したプロセス優先度設定および CPU affinity 設定ユーティリティ。権限不足・未対応環境は警告でフォールバック。

- 監視データベース初期化のためのモジュール参照（init_monitoring_db）を各起動スクリプトで呼び出し、監視テーブル存在を保証するように。

### Changed
- .env 自動読み込みのポリシーを導入
  - プロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を自動ロード（OS 環境変数を保護しつつ .env.local は上書き可能）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- DB の取り扱いを明確化
  - Monitoring は環境にかかわらず本番 sqlite_path（data/monitoring.db）を使用する方針で起動スクリプトに反映。
  - Execution は paper_trading モード時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。

- ログ設定のデフォルトや挙動明確化
  - ログレベル解決順（引数 > 環境変数 > デフォルト）、ログディレクトリ解決順（引数 > 環境変数 > デフォルト）を仕様化。既存ハンドラは上書き防止のため一旦クリアする。

### Fixed / Hardened
- 設定値パース時の堅牢性向上
  - .env の各種書式（quoted values、エスケープ、inline コメント、export プレフィックス）に対応。
  - Settings クラスで不正な列挙値（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を検出して明確な例外を投げるように。
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトにフォールバックし、警告ログを出力するように。

- 起動スクリプトの安全な終了処理
  - 停止フラグファイル検知による安全停止処理を実装（run_execution/run_monitoring）。KeyboardInterrupt ハンドリングと DB コネクション確実クローズ。

- process_priority / cpu_affinity 周りで権限や未実装 API に対して警告ログでフォールバックするようにし、クラッシュを避けるように強化。

- validate_config による事前チェックで PyYAML 未導入時には YAML 検証をスキップして警告を出すように（起動時の不要な失敗回避）。

---

## [0.1.0] - 2026-04-19

初期公開リリース（コードベースの現状を反映）。

### Added
- 上記 Unreleased に記載した主要機能を初版としてリリース:
  - 起動スクリプト（run_execution, run_monitoring）
  - 設定管理（config, config_setup, validate_config）
  - ポートフォリオ構築（portfolio パッケージ）
  - ログ・プロセスユーティリティ（utils.logging_setup, utils.process_priority）
  - Paper Trading 検証レポートツール（tools.paper_verification_report）
  - 研究用ファクター計算基盤（research.factor_research; 計算ロジックの実装は継続予定）

### Changed
- 初期実装段階の API とファイルレイアウトを確立。各コンポーネントは将来的な拡張・分割を想定して設計。

### Fixed
- 起動時/実行時の堅牢性を中心に多くの入力検証とフォールバック処理を実装（上記参照）。

---

注:
- 本 CHANGELOG はコードベースの内容からの推測に基づいています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、特定ファイルや機能ごとに詳細な項目（変更理由、既知の制限、今後の課題など）を追加できます。