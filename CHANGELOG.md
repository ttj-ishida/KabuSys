# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
これらの変更点はソースコードの内容から推測して記載しています。

フォーマット: 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）にまとめています。

注意: パッケージのバージョンは src/kabusys/__init__.py の __version__ (= 0.1.0) に基づいています。

## [Unreleased]

### Added
- research モジュールの雛形 (factor_research.py) を追加。モメンタム等のファクター計算を行う設計を導入。
- calc_momentum 等の関数の骨組みを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。
- ローカル開発支援ツール:
  - config_setup: 対話式 .env 作成/更新ウィザードを追加。
  - validate_config: .env と config/*.yaml の起動前検証 CLI を追加。
  - tools/paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加（稼働率・注文成功率・レイテンシ等を判定）。
- 実行/監視用起動スクリプトを追加:
  - run_execution: ExecutionEngine を起動するエントリポイント（paper_trading と本番 DB の分離・停止フラグ対応）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能）。
- 設定管理:
  - Settings クラスを追加し、.env / 環境変数から設定を統一的に取得する仕組みを提供（デフォルト値や検証ロジックを含む）。
  - 自動 .env ロード機能を導入（プロジェクトルート検出に .git / pyproject.toml を利用）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサーを改良（export プレフィックス、クォート／エスケープ、インラインコメント等に対応）。
- ロギング/プロセスユーティリティ:
  - utils.logging_setup: stdout の StreamHandler と 日次ローテーションの TimedRotatingFileHandler を組み合わせた統一ログ設定を提供。ログディレクトリ作成失敗時はファイルハンドラを安全にスキップ。
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。呼び出し側は OS を意識せずに使用可能。
- ポートフォリオ構築ライブラリ:
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコアが全て 0 の場合は警告を出して等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、レジームに基づく乗数 (calc_regime_multiplier) を追加。未知レジームはフォールバック処理を行う。
  - portfolio.position_sizing: 単元株丸め、リスクベース／等配分／スコア配分に基づく株数決定ロジック、aggregate cap によるスケーリング（残余を考慮した lot 単位の再配分）を実装。
- Execution コンポーネントの組み立て点検用の stub/参照（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み合わせロジックを run_execution から起動）。

### Changed
- run_monitoring:
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様を明示（監視データは本番 DB を参照）。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能。無効値（0以下や非数）はデフォルト 60 秒にフォールバックし警告を出す。
  - 終了処理: data/stop_requested.flag を検知して graceful shutdown。
- run_execution:
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使い paper_trading DB に分離（本番 DB と完全分離）。
  - 起動前に停止フラグを確認し、既に立っている場合は起動しない。
  - エンジンはデーモンスレッドで動作し、停止フラグ検知時には engine.stop() を呼んで終了を試みる。
- Settings:
  - PAPER_FILL_MODE のバリデーションを実装（有効値: instant|partial|never|reject）。不正値は ValueError。
  - 環境名 KABUSYS_ENV のバリデーションと is_live/is_paper/is_dev のユーティリティを追加。
  - 各種閾値（CPU/MEM/DISK）やファイルパス関連のデフォルト値を整理。
- validate_config:
  - 必須・任意の環境変数チェック、設定ファイル存在チェック、PyYAML 未導入時のスキップ警告、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定未設定や Kill Switch の自動クリアなど）を実装。

### Fixed
- .env ファイル読み込み:
  - 読み込み失敗時に警告を出してスキップする堅牢化（ファイルアクセスエラー時に warnings.warn）。
  - _load_env_file の override/protected ロジックで OS の既存環境変数を保護して意図しない上書きを防止。

### Known issues / TODO
- research.factor_research.calc_momentum の実装が途中（ファイル末尾でコードが切れている痕跡があり、詳細実装が未完）。この関数および他のファクター計算ロジックは完成が必要。
- portfolio.risk_adjustment.apply_sector_cap にて price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的にフォールバック価格（前日終値等）を導入することを検討中。

---

## [0.1.0] - 2026-04-24

初回公開リリース。上記「Added / Changed / Fixed」に該当する主要機能を含むリリース。

### Added
- 基本的な自動売買フレームワークのコアコンポーネントを追加:
  - 実行エンジン起動スクリプト (run_execution)
  - 監視起動スクリプト (run_monitoring)
  - 設定管理 (config.Settings) と自動 .env ロード
  - 対話式 .env ウィザード (config_setup)
  - 設定検証 CLI (validate_config)
  - ロギング設定ユーティリティ (utils.logging_setup)
  - プロセス優先度 / CPU 固定ユーティリティ (utils.process_priority)
  - ポートフォリオ構築モジュール (portfolio)
  - Position sizing / risk adjustmentロジック
  - Paper Trading 用検証レポートツール (tools/paper_verification_report)
  - research モジュール骨組み
- 停止/キルフラグ管理（data/* フラグファイルを使用する慣習）を導入。

### Changed
- パッケージメタ情報: __version__ = "0.1.0"

### Fixed
- 初期実装段階での堅牢性向上（ログディレクトリ作成失敗時のフォールバック、.env 読み込みエラーの警告化等）。

### Notes
- デフォルト設定や環境変数名、ログの出力先（logs/）などは README / ドキュメントに従って適切に設定してください。
- 本リリースの一部機能（特にファクター計算）は引き続き実装・テストが必要です。

---

過去バージョンが存在する場合は、その履歴をここに追記してください。