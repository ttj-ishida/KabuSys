# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」の仕様に準拠しています。  
注意: 以下の内容はコードベースから推測してまとめた変更履歴です。

## [Unreleased]

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite DB を使用し、MockBrokerClient を利用する設計になっている。停止フラグ（data/stop_requested.flag）や PID ファイルの扱いを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する（ドキュメント注記あり）。

- 環境設定関連の CLI を追加
  - config_setup.py: .env の初期作成・更新を対話式で行うウィザードを追加。各設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定など）を対話形式で入力・保存可能。
  - validate_config.py: .env および config/*.yaml の基本検証を行う CLI を追加。必須環境変数未設定や KABUSYS_ENV、LOG_LEVEL の妥当性チェック、DB パスや config ファイルの存在チェック、PyYAML が無い場合のスキップなどを実装。`--strict` オプションで警告を失敗扱いにできる。

- Paper Trading 検証レポート生成ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し、PASS/FAIL 判定付きのレポートを生成するユーティリティを追加。期間指定オプション（--from, --to）と DB パス上書きオプション（--db）をサポート。

- ポートフォリオ構築関連の純粋関数群を追加（DB参照なし）
  - portfolio/portfolio_builder.py: シグナル候補選定（select_candidates）、等配分ウェイト（calc_equal_weights）、スコア加重ウェイト（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数計算（calc_regime_multiplier）を実装。セクター未定義は "unknown" 扱いで上限適用除外。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score の各 allocation_method）、単元株（lot_size）での丸め、per-銘柄上限・aggregate cap のスケーリング処理、コストバッファの考慮を実装。

- 研究用ファクター計算モジュールを追加（部分実装）
  - research/factor_research.py: モメンタム等のファクター計算器を追加（設計方針・定数定義を含む）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モジュールは今後の拡張を想定（コード末尾で計算処理の実装が始まっている）。

- 共通ユーティリティを追加
  - utils/logging_setup.py: ルートロガーの初期化ユーティリティを追加。stdout 出力の StreamHandler と 日次ローテート（TimedRotatingFileHandler）を設定。LOG_LEVEL/LOG_DIR の解決、既存ハンドラのクリーンアップ、ファイルハンドラ作成失敗時のフォールバック処理などを実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity を固定する set_cpu_affinity を追加。psutil の例外をハンドルしてフォールバックする。

- 設定管理を強化
  - config.py: Settings クラスを導入。環境変数のアクセスラッパー（J-Quants、kabu API、DB パス、監視閾値、PID/kill flag パス等）とバリデーションを提供。PAPER_FILL_MODE の厳密チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、is_live / is_paper / is_dev の便利プロパティを追加。
  - 自動 .env ロード機能: プロジェクトルートを .git または pyproject.toml で検出し、.env（未設定のキーのみ）および .env.local（上書き）を読み込む仕組みを実装。OS 環境変数は protected として上書きされない。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーの強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの取り扱いなどを正しく処理するパーサーを実装。

- 監視 DB 初期化機能を呼び出すフックを整備
  - init_monitoring_db の呼び出しを run_monitoring/run_execution の起動処理に組み込み、監視用テーブルの存在を冪等に保証。

### Changed
- ロギングの既定動作を統一
  - setup_logging により、全起動スクリプトから一貫したログ出力（stdout + 日次ローテートファイル）を行うように変更。既存ハンドラを再設定して二重記録を防止する。

- 実行・監視プロセスの優先度を起動時に High に設定するように統一（set_process_priority を利用）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring で環境変数 MONITOR_POLL_INTERVAL をパースし、0 以下や非整数などの不正値は警告してデフォルト（60 秒）にフォールバックする処理を追加。

- .env 読み込み時の保護機能
  - OS 環境変数を上書きしないよう protected セットを導入し、.env.local 等の上書きでも不注意で重要な環境変数を書き換えないようにした。

### Security
- .env の取り扱いに関する注意喚起を CLI と生成ファイルに明記（.env を Git にコミットしないよう強調）。
- 必須環境変数未設定時に早期に検出する validate_config を追加し、起動前に設定ミスによる誤作動を防ぐ手段を提供。

### Docs
- 各スクリプト・モジュールの docstring に使い方や設計方針、注意点（例: run_monitoring が常に本番 sqlite_path を使うこと、PAPER_FILL_MODE の有効値など）を明記。

---

## [0.1.0] - 2026-04-18

初回リリース相当。上記の主要機能群を最初にまとめたリリース。

### Added
- コアライブラリとユーティリティ
  - Settings（環境変数ラッパー）、自動 .env ロード、.env パーサ
  - logging/setup_logging、process_priority（優先度/CPU affinity）
  - DuckDB / SQLite を利用する初期化フロー（init_monitoring_db 呼び出し）
- 実行/監視/検証ツール群
  - run_execution.py、run_monitoring.py、validate_config.py、config_setup.py
  - tools/paper_verification_report.py
- ポートフォリオ構築モジュール
  - portfolio_builder、risk_adjustment、position_sizing
- 研究用モジュール（factor_research の雛形）

### Fixed / Improved
- ログ出力の統一（日次ローテーション、stdout 使用、ログレベル解決）
- 環境設定の事前検証と対話式ウィザード追加
- Paper Trading と本番 DB の分離（paper_trading 用 DB パスをサポート）

---

今後の予定（想定）
- research/factor_research.py の各ファクター計算ロジックの完成
- ExecutionEngine 周り（実行ロジック、ブローカ抽象化）の詳細実装とテスト強化
- 単体テスト・統合テストの追加と CI 設定
- ドキュメントの拡充（運用手順・設定例・デプロイ手順）

もし特定の変更点を詳細に反映してほしい、あるいはリリース日やバージョン分けを別の方針で整備したい場合は指示してください。