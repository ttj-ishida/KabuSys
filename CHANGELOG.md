# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベース（バージョン 0.1.0）から推測できる主要な変更点・機能追加・挙動を日本語でまとめたものです。

※ バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]

（現在なし）

## [0.1.0] - YYYY-MM-DD
初回リリース（コードベースから推測した機能セット）

### Added
- 実行エントリポイントを多数追加 / 整備
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境に応じてブローカークライアントを切替え（KABUSYS_ENV=paper_trading で MockBrokerClient を使用）し、paper_trading 環境では専用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視プロセスの PID 管理、停止フラグ（data/stop_requested.flag）検知に対応。
  - run_intraday_monitor.py: ザラ場中監視 CLI。単発実行 / 監視モード（--watch）に対応し、実行中のプロセス・キルスイッチ・ドローダウン・注文エラー等のステータスを CLI に整形表示する。
  - run_pre_market_report.py, run_market_close_report.py, run_performance_report.py, run_position_reconciliation_report.py, run_signal_queue_report.py:
    - 各種レポート生成用の CLI を追加。共通で --save（アーティファクト保存）, --json（JSON 出力）, --date 指定などをサポート。
  - tools/paper_verification_report.py: ペーパートレーディング用検証レポート生成スクリプトを追加（稼働率、注文成功率、送信率、P95 レイテンシ等を算出）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数や config/*.yaml の存在・パース検証、KABUSYS_ENV による本番用ガード（警告）等を実施。--strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py: 対話式の .env 初期作成/更新ウィザードを追加。シークレット項目はマスクして入力を促し、.env ファイルへ書き出す機能を提供。

- 設定 / 環境変数管理
  - config.py: Settings クラスを導入し、アプリケーション設定を環境変数から取得するラッパーを追加。各種プロパティ（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境判定フラグ等）を提供。
  - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動的に読み込み。OS 環境変数は保護され、.env.local での上書きが可能。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できる。
  - .env パーサを強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント（クォート無しの値で直前にスペースがある場合のみ）などを考慮して安全にパースする実装を導入。

- モニタリング / PID 管理 / Kill Switch
  - run_monitoring.py / run_execution.py / run_pre_market_report.py などで PID ファイル（data/*.pid）や停止フラグ（data/stop_requested.flag）を利用する慣習を導入。プロセス起動時に優先度を "high" に設定するユーティリティを使用。
  - 設定に kill_flag_clear_on_start（KILL_FLAG_CLEAR_ON_START）を導入し、起動時に Kill Flag を自動クリアする挙動を制御可能（本番環境ではデフォルト 0 を推奨）。

- Risk / Execution
  - run_execution.py: risk_config.yaml の読み込みと検証を実装。パラメータの型/範囲チェック（0 < 比率 <= 1、閾値は 1 以上 等）を行い、不正な設定はエラーにする。起動時にブローカーから現金・保有ポジションを取得して初期総資産を計算、これを RiskConfig に渡して RiskManager を初期化する。
  - ExecutionEngine 起動前にリコンシリエーションを行い、Execution Startup Summary（CLI 出力および artifacts に保存）を生成する試みを行う（生成に失敗しても起動は継続）。

- データベース / DuckDB
  - 多くのコマンドが DuckDB（デフォルト data/kabusys.duckdb）を読み取り専用で使用。レポート系は read_only モードで接続。
  - monitoring 用の SQLite（デフォルト data/monitoring.db）は監視テーブル初期化（init_monitoring_db）を起動時に実行して存在を保証する。

- CLI UX
  - 多くの実行ファイルで exit コードを意味付け（OK/警告/ブロック等）して、スケジューラや監視に連携しやすくしている。
  - レポートの --save 時、JSON 出力と混在させないために保存先メッセージを stderr に出す配慮を行っている箇所あり。

- ユーティリティ
  - Paper Verification の P95 計算、数値フォーマットヘルパー、日付フィルタ生成等を実装。
  - .env の読み書き・ウィザード用ヘルパーを追加。

### Changed
- 主要コンポーネントがプロセス優先度を明示的に "high" に設定するようになった（起動直後に set_process_priority("high") を呼ぶ）。
- monitor（SystemMonitor）は常に本番用 sqlite_path を使用する旨を明記（監視は環境にかかわらず本番 DB を参照する設計）。

### Fixed
- MONITOR_POLL_INTERVAL のパースにおいて 0 以下や不正値を検出した際にデフォルト値へフォールバックしログで警告する動作を追加。time.sleep に渡す不正値で例外が発生するのを防止。
- .env パース周りでのクォート内のエスケープやインラインコメントの誤認識を改善（より現実的な .env ファイルに対応）。

### Documentation / UX
- 各 CLI モジュールに使用方法・例（ヘルプテキスト）を追加し、--date / --json / --save / --watch 等の説明を整備。
- config_setup.py のウィザードでシークレットはマスク表示、書き込み時にヘッダコメントで注意喚起（.env を Git にコミットしない旨）を埋め込む。

### Internal
- Settings クラスに以下のプロパティを実装（読みやすさと型安全の向上）:
  - jquants_refresh_token, jquants_bulk_api_key, kabu_api_password, kabu_api_base_url, kabu_trade_password
  - line_channel_access_token, line_user_id
  - duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - env, log_level, is_live, is_paper, is_dev

### Security
- シークレット系の取り扱い（.env ウィザード時のマスク表示や既存値の取り扱い）を配慮。

## Notes / 補足
- valid 値や挙動は実装から推測したものであり、実際の運用では config/*.yaml や環境変数の設定に注意してください（validate_config.py を用いた事前検証を推奨）。
- 一部 CLI は外部ライブラリ（PyYAML、duckdb 等）に依存しており、未インストール時の挙動は validate_config.py 等で考慮されています（YAML 未インストール時は YAML 検証がスキップされ警告を出す）。
- 実行ファイルはスクリプト形式のため、systemd 等のプロセスマネージャからの運用を想定した PID / stop-flag の仕組みが取り入れられています。

---
行単位の微細な修正や未公開の変更はここにすべて記載されているわけではありません。必要であれば各ファイルの実装箇所に基づき詳細な変更点を追加で作成します。