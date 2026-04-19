# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: バージョンはパッケージ内の __version__ に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler 組立て、エンジンスレッド管理、停止フラグ検出を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - tools/paper_verification_report.py: ペーパートレード履歴を集計して検証レポートを生成する CLI を追加。期間指定 (--from/--to) と DB パス指定 (--db) をサポート。
- 設定 / 検証ツール
  - config.py: 環境変数 / .env の自動ロード機能を実装。プロジェクトルート検出（.git または pyproject.toml に基づく）、.env/.env.local の読み込みロジック、型・値チェック付き Settings クラスを提供。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 環境変数の取り扱い: PAPER_FILL_MODE（instant/partial/never/reject）、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、各種閾値などをプロパティで取得可能。
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新するユーティリティを追加（秘密値はマスク表示、選択肢/デフォルト対応）。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ確認、YAML パーサ（PyYAML があれば内容チェック）、本番環境用の追加警告などを実装。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: シグナル選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0時のフォールバックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバックしてログ警告。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算 (calc_position_sizes) を実装。
    - allocation_method は "risk_based", "equal", "score" をサポート。
    - lot_size 単位で丸め、1 銘柄上限・集計上限・コストバッファを考慮したスケーリングを実装。
- utils
  - utils/logging_setup.py: ルートロガーを統一的に設定するユーティリティを追加。コンソールは stdout、ファイルは日次ローテーション (TimedRotatingFileHandler)・30日保持。ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
  - utils/process_priority.py: Windows/Linux/macOS を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティを追加。権限不足時は警告を出してスキップ。
- research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム / MA200 乖離 / ATR / 出来高系などを想定した設計、関数インターフェースを含む）。（ファイル末尾に一部未完の実装開始あり）
- DB 初期化補助
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルの存在を保証する呼び出しを run_* スクリプトで実施。
- パッケージ初期情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- ロギング方針: 全スクリプトは setup_logging を呼び出すことで一貫したログ出力形式・ローテーションを共有。
- run_execution/run_monitoring: 起動直後に set_process_priority("high") を呼び、重要プロセスの優先度を高めるようにした（権限がない場合はログ警告で継続）。
- .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され、.env.local で上書き可能。

### Fixed / Robustness
- .env パーサを強化
  - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（未クォート時は '#' がスペース直前でコメントと判定）に対応。
  - 読み込み失敗時は警告を発生させつつ起動継続（テストや権限問題に耐性）。
- process_priority / cpu_affinity: 非対応 OS や権限不足時に例外を投げず警告でスキップするように変更し、クロスプラットフォームで安全に呼び出せるようにした。
- logging_setup: ログディレクトリ作成失敗やファイルハンドラ作成失敗時に fallback 動作（コンソール出力のみ）することでクラッシュを防止。
- run_monitoring: MONITOR_POLL_INTERVAL の値検証を追加し、0 以下や不正な文字列が指定された場合にデフォルトにフォールバックして警告を出すようにした。
- run_execution/run_monitoring: 停止フラグ (data/stop_requested.flag) を監視し、安全にシャットダウンする仕組みを実装。

### Notes / Known limitations
- research/factor_research.py はファイル末尾で実装が途中で切れている箇所があり、完全実装は今後のリリースで行う予定。
- position_sizing の価格欠損処理について注記あり（price が 0.0 の場合にエクスポージャーが過小見積もりされる可能性）。将来的にフォールバック価格を導入予定。
- apply_sector_cap は sector が "unknown" の銘柄に対してセクター上限を適用しない設計だが、必要に応じてポリシーを変更可能。
- config_setup.py のウィザードは対話式のため非対話環境では利用できない。自動化が必要な場合は .env を直接作成してください。

---

開発・運用に関する補足や、リリースノートに加えたい情報（例: リリース担当者、リリース手順、移行注意点等）があれば提供ください。必要に応じて CHANGELOG を更新します。