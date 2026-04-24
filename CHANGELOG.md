CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
セマンティックバージョニングを採用します。

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-24
-------------------

初回公開リリース。日本株自動売買フレームワーク "KabuSys" の基礎機能を実装しました。

Added
- 実行エントリスクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading の場合はペーパートレード用に MockBroker を利用し、paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）に記録するように実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルで検知。
- 設定管理/ウィザード/検証
  - config.py: 環境変数/.env 読み込みロジックと Settings クラスを実装。自動でプロジェクトルートの .env / .env.local を読み込み（OS 環境変数は保護）、KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を実装（秘密値のマスク表示、デフォルト/選択肢サポート）。
  - validate_config.py: .env と config/*.yaml の整合性チェック CLI を実装。--strict モードで警告を FAIL として扱う。
- ポートフォリオ構築モジュール（純関数）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順）、等金額配分、スコア加重配分を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数決定、単元株丸め、aggregate cap スケーリング、手数料・スリッページ見積り（cost_buffer）を実装。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 全スクリプト共通のログ設定ユーティリティを実装。stdout へ出力する StreamHandler と、日次ローテーション（30 日保持）のファイルハンドラをルートロガーに設定。LOG_DIR / LOG_LEVEL の環境変数に対応。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。psutil を利用し失敗時は警告を出してスキップ。
- 監視/DB 初期化
  - monitoring 関連の初期化呼び出し（init_monitoring_db）を各起動スクリプトに導入し、監視用テーブルの冪等な作成を保証。
  - 起動時に高優先度でプロセスを設定する処理を追加（set_process_priority("high") を最初に呼ぶ）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を解析し、稼働率・注文成功率・送信率・レイテンシ等の指標から PASS/FAIL を判定するレポートジェネレータを実装。閾値はソース内で定義（稼働率 >=99%、P95 <=200ms など）。--from/--to/--db オプション対応。
- リサーチ（骨格）
  - research/factor_research.py: モメンタム等ファクター計算の骨組みを実装（DuckDB 接続を受ける設計）。（ファイル末尾で実装途中の箇所が存在）

Changed
- ロギング設計
  - ログを stdout に出す理由を明記（Task Scheduler/cron などでの一元化を想定）。既定のログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続する挙動に。
- .env パーサの堅牢化
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの取り扱いなどに対応したパーサを実装。
  - .env の読み込み順序: OS 環境 > .env.local（上書き） > .env（既存変数は上書きしない）。OS 環境変数は protected として上書き不可。

Fixed
- 起動/停止制御
  - run_execution/run_monitoring のループ内で data/stop_requested.flag を監視し、安全にシャットダウンするロジックを実装。
  - run_execution は既に停止フラグが立っている場合は起動を行わず終了するように。

Security
- 秘密情報の扱い
  - config_setup の対話では secret フラグのものをマスク表示。README 等へ .env を絶対にコミットしないよう注意喚起を出力。

Notes / Potential breaking behavior
- 監視 DB の扱い
  - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（いわゆる「本番」monitoring DB）を使用する実装になっています。意図しない DB への書き込みを避けたい場合は設定（SQLITE_PATH）を明示的に切り替えてください。
- Paper Trading の分離
  - run_execution は paper_trading 環境時に専用の PAPER_TRADING_SQLITE_PATH を使用するため本番 DB と完全に分離されます（デフォルト: data/paper_trading.db）。
- 未完成箇所
  - research/factor_research.py の末尾が途中で切れている（実装継続が必要）。このモジュールの完全な利用には追加実装を行ってください。

Acknowledgments
- 本リリースは内部設計文書（PortfolioConstruction.md / StrategyModel.md 等）に沿って実装されています。各関数・モジュールはドキュメントに準拠するよう設計されています。

----------------------------------------------------------------------------- 

将来的なリリースでは以下の点を改善予定です（例）:
- research モジュールの完全実装（ファクター計算の最終化）
- テストカバレッジの追加（ユニットテスト・統合テスト）
- 銘柄ごとの単元株数対応（lot_size を銘柄マスタから取得する拡張）
- 実行エンジン/監視のより詳細なメトリクス収集とアラート設定

（以上）