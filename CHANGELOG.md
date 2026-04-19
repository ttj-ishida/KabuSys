# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ内の __version__ を基準にしています。

## [Unreleased]
- 今後のリリースに向けた軽微な改善やドキュメント追記を予定。

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム「KabuSys」の基本機能群を追加しました。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV に応じて実ブローカまたは MockBroker を選択し、専用の SQLite（Paper Trading 時は data/paper_trading.db）を使用することで本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理・補助ツール
  - config.py: 環境変数読み込み・Settings クラスを実装。.env / .env.local の自動読み込み、保護された OS 環境変数の扱い、各種設定値（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 関連設定など）を提供。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加（初期セットアップ支援）。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。--strict モードを提供。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティ（コンソール stdout と日次ローテーションファイル出力）。ログディレクトリが作れない場合のフォールバック処理あり。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定ユーティリティ。Windows/Linux/macOS 等の違いを吸収し、失敗時は警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの選定（スコア順位）と等金額・スコア加重の重み計算。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）・単元株丸め・aggregate cap のスケーリングロジックを実装。
  - portfolio/__init__.py: 上記機能をパッケージとして export。
- 研究用モジュール
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨子を追加（モメンタム等の計算方針を実装）。（注: ファイル末尾は実装途中の箇所あり）
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率・送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計し PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能。
- モニタリング DB 初期化
  - monitoring_db.init_monitoring_db 呼び出しを run_monitoring/run_execution 内で行い、監視テーブルの存在を保証（冪等性確保）。
- その他設計上の注記（ドキュメント・ログ出力等）
  - 起動時にプロセス優先度を "high" に設定するよう各起動スクリプトで実施（set_process_priority の呼び出し）。
  - PID ファイル（execution.pid）や停止フラグ（data/stop_requested.flag）の使用による安全停止機構を導入。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 頑健性向上
  - config._parse_env_line: .env パーサを強化。シングル/ダブルクォート内のバックスラッシュエスケープ処理、export プレフィックスやコメント扱いの改善を実装。
  - run_monitoring._get_poll_interval: 環境変数 MONITOR_POLL_INTERVAL の値検証を追加。不正値（0 以下や非整数）は警告を出してデフォルトにフォールバック。
  - utils/logging_setup.setup_logging: ログディレクトリ作成に失敗した際にファイルハンドラをスキップしてコンソール出力のみで継続する安全なフォールバックを追加。
  - utils/process_priority.set_process_priority / set_cpu_affinity: psutil を使った操作で AccessDenied 等が発生した場合に例外を握りつぶし警告ログで継続するようにし、起動失敗リスクを低減。
  - run_execution: エンジンのバックグラウンドスレッドを監視し、停止フラグ検知時にエンジン.stop() を呼び安全に停止する処理を追加。スレッド join のタイムアウト処理を追加。
  - paper_verification_report: P95 計算、日付フィルタの生成、DB が存在しない場合のわかりやすいエラーメッセージ等を実装。

### Removed
- （初回リリースのため該当なし）

### Security
- 機密情報取り扱い
  - config_setup と .env 処理において、J-Quants トークンや kabu API パスワードなどのシークレットは対話時にマスク表示とし、.env の Git コミット禁止を README 注記に明示するスタブを追加。

---

備考:
- run_monitoring は「監視用 DB」を常に settings.sqlite_path（本番用想定）で開く設計になっています。環境による DB 分離が必要な場合は設定（環境変数）を調整してください。
- research/factor_research.py はモジュールの骨子と設計方針を含む実装が追加されていますが、一部未完の箇所（ファイル末尾での実装途上）が見受けられます。今後のリリースで続きの実装・テストを予定しています。