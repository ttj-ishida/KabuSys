# CHANGELOG

すべての notable な変更点を Keep a Changelog の形式で記録します。  
リリースの方針や記載ルールは https://keepachangelog.com/ja/ を参照してください。

なお、以下の内容はソースコードから推測して作成したものであり、実際の変更履歴と差異がある場合があります。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。

### Added
- 基本パッケージの追加（kabusys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 設定・環境変数管理機能
  - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序、OS 環境変数保護（protected）対応。
    - カスタムパーサーで export 形式、クォートやエスケープ、インラインコメントを扱えるように実装。
    - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視・システム設定等をプロパティで取得可能。
    - 環境変数のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - デフォルト値・選択肢表示、シークレット項目のマスク、保存確認を実装。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml（存在する場合）の事前検証を実行。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL チェック、DB パス親ディレクトリチェック、
      本番環境向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）を実装。
    - --strict オプションで警告も失敗扱いにできる。
- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト（プロセス優先度設定、DB 接続、Broker クライアント生成、依存コンポーネント組立て、スレッドベースの実行ループ、停止フラグ / PID ファイル処理）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き、既定 60 秒）。
    - 監視は環境にかかわらず production sqlite_path を参照する実装になっている点に注意。
    - 停止フラグ（data/stop_requested.flag）検知時にループを終了する。
- ログ設定ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを提供。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
- プロセス優先度 / CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアにピン止めする set_cpu_affinity を提供。
    - psutil の権限エラーや未対応 OS の場合は安全にスキップして警告ログを出力。
- ポートフォリオ構築・資金配分ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順・タイブレーク）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合はフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有時価を基にセクターをブロック、"unknown" セクターは除外しない仕様）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes（allocation_method: "risk_based"/"equal"/"score"、単元株丸め、max position・aggregate cap・cost_buffer を考慮）。
    - available_cash に対するスケールダウンと残差処理（lot_size 単位での調整）。
  - src/kabusys/portfolio/__init__.py にて API をエクスポート。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - paper_trading の SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から集計レポートを生成。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計・判定し PASS/FAIL を出力。
    - コマンドライン引数 --from / --to / --db をサポート。
- 研究用ファクター計算（骨組み）
  - src/kabusys/research/factor_research.py
    - Momentum 等のファクター計算に関する定数と設計方針を実装（DuckDB 接続を想定）。※ファイルの途中までが含まれており、以降の詳細実装は継続の余地あり。
- DuckDB / SQLite 連携
  - 起動スクリプトやツールが duckdb および sqlite3 接続を作成して使用する実装。
  - 監視 DB 初期化用の init_monitoring_db が参照される（実装ファイルは別途存在）。

### Changed
- －（初回リリースのため履歴上の変更は無し）

### Fixed
- －（初回リリースのため修正履歴は無し）

### Security
- 環境変数の .env は絶対に Git にコミットしない旨を config_setup のヘッダに明示。

### Notes / Operational details
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書き可能。無効な値（非整数や 0 以下）の場合はデフォルト 60 秒にフォールバックし、警告を出力する。
- run_execution は paper_trading モード時に paper DB を使い、本番 DB と完全に分離するよう設計されている。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力される。LOG_DIR 環境変数で変更可能。
- process_priority.set_process_priority("high") を起動直後に呼び出しているため、権限不足等で設定できない場合は警告が出るが起動自体は継続される。

---

将来的なリリースでは、monitoring_db や SystemMonitor / ExecutionEngine 等の詳細な変更点（バグ修正、パラメータ追加、最適化など）を個別に記載してください。