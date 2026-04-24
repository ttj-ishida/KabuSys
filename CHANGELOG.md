CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" 準拠です。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-24
-------------------

Added
- 初回公開リリース。
- 実行・監視用ランチャー
  - run_execution.py：ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。起動時にプロセス優先度を "high" に設定し、停止フラグ・PID ファイルに対応。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番用 sqlite_path を使用する動作を明記。
- 設定管理
  - config.py：.env の自動ロード機能（プロジェクトルート検出）、環境変数の堅牢なパース、Settings クラスによるプロパティ型の設定取得を追加。各種設定（DB パス、PID/kill フラグパス、監視閾値、PAPER_FILL_MODE 等）を提供。
  - config_setup.py：対話式ウィザードで .env を初期作成／更新する CLI を追加（秘密値マスク、デフォルト提示、保存確認）。
  - validate_config.py：起動前チェック用 CLI。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML が存在する場合）などを検証。--strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder：買い候補選定（スコア順）、等金額／スコア重みの計算。
  - portfolio.risk_adjustment：セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing：各銘柄の発注数量算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング、手数料等を考慮した cost_buffer。
- ユーティリティ
  - utils/logging_setup.py：統一ログ設定ユーティリティ。console (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定、ログディレクトリ自動作成の試行。LOG_LEVEL, LOG_DIR, app_name による挙動制御。
  - utils/process_priority.py：psutil を用いたプロセス優先度（Windows/Linux/macOS 対応）および CPU affinity 設定ユーティリティ。
- DuckDB 統合
  - 起動スクリプト・各コンポーネントで DuckDB 接続を受け取る設計を採用（Settings.duckdb_path）。
- 監視・運用関連
  - 監視 DB 初期化（init_monitoring_db 呼び出し）を起動処理に組み込み、監視テーブルが存在することを保証。
  - 停止フラグ（data/stop_requested.flag 等）と PID ファイルを用いた安全な起動・終了制御。
- ツール
  - tools/paper_verification_report.py：Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。期間フィルタと --db オプション対応。P95 計算ロジックを実装。
- パッケージメタ
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

Changed
- run_monitoring の動作方針を明確化：Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データの一元化を意図）。
- run_execution における DB パス解決ロジック：is_paper 判定により paper_sqlite_path を優先して使用することでペーパートレードと本番の完全分離を実現。
- logging_setup のハンドラ設定を「既存ハンドラを一度クリアしてから再設定」する実装に変更（多重設定防止）。
- .env パーサの強化（config.py）
  - export プレフィックスの許容、クォート文字内のバックスラッシュエスケープ、インラインコメント処理などをサポートし、より実用的な .env 解析を実現。
  - OS 環境変数を保護する protected オプションを導入（自動ロード時の上書き制御）。
- position_sizing のスケーリング／端数処理を詳細化：aggregate cap 超過時のスケールダウン、lot_size 単位での再配分アルゴリズムを実装。

Fixed
- process_priority と CPU affinity 設定で Unsupported/アクセス権限エラーが発生した際に警告を出してスキップする堅牢化を追加。
- logging_setup：ログディレクトリの作成に失敗した場合でもコンソール出力のみで継続できるように改善。

Security
- .env の生成スクリプト（config_setup.py）で「.env を絶対に Git にコミットしないこと」を明示するヘッダを追加。

Notes / Usage
- 実行例:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルトのファイルパス（ログ・DB・PID 等）は Settings クラスのプロパティで確認・上書き可能です。

今後の TODO / 改良案（コード内にコメントあり）
- position_sizing: 銘柄ごとの lot_size をサポートする（stocks マスタからの取得など）。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバックロジック（前日終値や取得原価など）。
- momentum 計算モジュール（research/factor_research.py）の未完部分（ファイル末尾に計算ロジックの続きがあることを示唆）。

---