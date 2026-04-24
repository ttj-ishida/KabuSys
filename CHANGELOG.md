CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に従います。

フォーマット:
  - 変更はカテゴリ別に整理（Added, Changed, Fixed, Removed, Security 等）
  - 日付は YYYY-MM-DD 形式

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 基本アーキテクチャと実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と完全に分離する（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト: 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定管理
  - config.py: 環境変数と .env ファイルの自動読み込み、.env パーサ（クォートやエスケープ、コメント処理対応）、必須/オプション設定の取り扱い、環境フラグ（development / paper_trading / live）や各種パス / 閾値のプロパティを実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（項目定義、既存 .env 読み込み、保存処理、秘密値マスク表示など）。
  - validate_config.py: 起動前の設定検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の整合性、DB パスの親ディレクトリ確認、config/*.yaml の存在/パース検証（PyYAML があれば内容検証を実施）。--strict フラグで警告を FAIL 扱いにできる。

- 実行・監視の安全機構
  - stop/kill フラグ、PID ファイル経由での停止管理を両スクリプトに導入（data/stop_requested.flag、data/execution.pid 等）。
  - run_execution は起動前に停止フラグを検知すると起動をスキップし、稼働中にフラグを検知したらエンジン停止を試みる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを実装。コンソール (stdout) と TimedRotatingFileHandler（日次ローテーション・30 日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL で挙動をカスタマイズ可能。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。アクセス権限や未対応 OS に対しては安全にスキップし警告を出す。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル候補選定（スコア降順）と等重・スコア加重の重み計算を追加。全スコア 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加（未知レジームはフォールバックして 1.0 を返す）。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot_size）丸め、per-position 上限・aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer による保守的見積もり、端数配分ロジックを実装。

- 解析/検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出。閾値（稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）に基づき PASS/FAIL を判定。コマンドライン引数で期間（--from/--to）や DB パス（--db）を指定可能。

- 研究用ファクター計算（骨格）
  - research/factor_research.py: DuckDB 接続を受け取りモメンタム等のファクターを計算するための関数群の骨格を追加（モメンタム等の定義と定数を含む）。（実装途中の箇所あり）

Changed
- パッケージバージョンを初期リリースとして設定
  - __init__.py に __version__ = "0.1.0" を追加。

Fixed
- 環境変数/パラメータの堅牢性向上
  - run_monitoring: MONITOR_POLL_INTERVAL の値を検証し、0 以下や不正な値はデフォルト（60 秒）へフォールバックして警告を出す。
  - config.py: PAPER_FILL_MODE の受け入れ値を検証し、不正な値は ValueError を送出する（早期検出）。
  - logging_setup: ログディレクトリ作成やファイルハンドラ生成失敗時に例外を致命的扱いせず、コンソール出力のみで継続するフォールバックを実装。
  - process_priority: 各 OS や権限不足時に安全にスキップしてログに警告を出す実装。

Security
- .env の取り扱い上の注意喚起を config_setup のヘッダに明記（.env を絶対に Git にコミットしない旨）。

Notes / Implementation details
- データベース
  - DuckDB は分析用（duckdb_path）、SQLite は監視・履歴用（sqlite_path / paper_sqlite_path）として使い分け。
  - run_monitoring は監視用 DB（sqlite_path）を環境にかかわらず本番用パスとして使う仕様（監視データは本番 DB を利用する想定）。
  - run_execution は paper_trading 環境時に専用 SQLite を使用して本番環境と完全に分離する。

- 設定自動ロード
  - config.py はプロジェクトルートを .git または pyproject.toml で探し、存在すれば .env/.env.local を自動でロード（OS 環境変数を保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- CLI
  - config_setup.py と validate_config.py はモジュール実行（python -m kabusys.config_setup / kabusys.validate_config）でウィザード・検証を行える。

- ドキュメント参照
  - portfolio や strategy に関する設計メモ（PortfolioConstruction.md, StrategyModel.md など）への参照がコード内に記載されている。

Acknowledgements
- 本リリースはコードベースから推測した機能・意図に基づいて作成しています。将来的な変更や実際の運用環境に合わせて .env の設定、DB パス、ログ設定、プロセス優先度などを調整してください。

---