CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。
http://keepachangelog.com/ja/1.0.0/

注: このリポジトリのバージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 として記載しています。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-20
-------------------

Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するメインスクリプト。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 DB を使用する（data/paper_trading.db をデフォルト）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。停止は data/stop_requested.flag によるフラグ検知で行う。
- 設定管理・ウィザード・検証 CLI を追加
  - config.py: 環境変数読み込み／ラッパー（.env 自動読み込み、保護された OS 環境変数の扱い、値検証など）。
  - config_setup.py: .env の対話式ウィザード（初期作成・更新支援）。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict により警告もエラー扱い）。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）・等金額/スコア重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio/position_sizing.py: 発注株数決定ロジック（リスクベース／等分配／スコアベース）、単元株丸め、aggregate cap に基づくスケーリング等を実装。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
- 監視・実行で利用する DB 初期化呼び出しと DuckDB 接続サポート
  - 監視・実行起動時に monitoring テーブルを冪等に初期化するための呼び出しを組み込み（init_monitoring_db）。
- ユーティリティ
  - utils/logging_setup.py: 統一されたロギング設定（コンソール stdout と日次ローテーションファイルハンドラ）を提供。ログディレクトリの作成失敗時はファイル出力をフォールバックで無効化。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定、CPU affinity 設定ユーティリティを追加。アクセス権限不足等は警告にフォールバック。
- ツール類
  - tools/paper_verification_report.py: Paper Trading 用 SQLite のログを解析し、稼働率・注文成功率・レイテンシ等を集計して検証レポートを出力するスクリプト。期間指定（--from / --to）と DB パスの上書き (--db) に対応。
- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を用いたファクター計算モジュール（モメンタム、MA200 陽性/陰性などの計算方針を実装開始）。（ファイル途中までの実装が含まれる）

Changed
- （初回リリース）プロジェクト構成を整備し、各コンポーネントをモジュール化。起動スクリプトから共通ユーティリティを利用する設計に。

Fixed
- N/A（初回リリースのため既存不具合修正はなし）

Deprecated
- N/A

Removed
- N/A

Security
- 環境変数の取り扱いに注意喚起を明記（.env を絶対に Git にコミットしない旨を config_setup.py に記載）。

Notes / 重要な設計上のポイント
- .env 自動ロード
  - 起動時にプロジェクトルート（.git または pyproject.toml を起点）を探索して .env と .env.local を自動読み込みします。ただし OS 環境変数は保護され、.env.local は既存値の上書きに使用されます。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- Settings（config.py）の厳格なバリデーション
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等は有効値チェックを行い、不正な値は ValueError を投げます。起動前に validate_config.py による検証を推奨します。
- DB の分離
  - paper_trading モードでは paper 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 monitoring.db と明確に分離されます。
- ログとハンドラ
  - setup_logging() は既存ハンドラをクリアしてから再設定します。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- プロセス制御
  - 実行・監視スクリプトは起動時にプロセス優先度を "high" に設定しようとします。権限不足や未サポート OS の場合は警告にフォールバックします。
- 停止フラグ / PID
  - data/stop_requested.flag を監視して安全に停止します。ExecutionEngine は data/execution.pid を PID 管理に使用します。
- 依存ライブラリ
  - duckdb、psutil を実行時に利用します。validate_config は PyYAML の有無をチェックし、インストールされていない場合は YAML 検証をスキップします（警告）。

Usage（主なコマンド）
- 環境設定ウィザード（.env の初期作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine 起動（本番 / paper_trading に応じた挙動）
  - python -m kabusys.run_execution
- SystemMonitor 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を変更可能
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）

Migration / 注意点
- .env を環境に合わせて正しく設定すること（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD は必須）。
- KABUSYS_ENV の値は "development" | "paper_trading" | "live" のいずれかに限定されます。不正な値は起動時に例外になります。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかでなければなりません。
- ログディレクトリ作成やプロセス優先度設定に失敗しても動作は継続しますが、警告が出力されます。
- research/factor_research.py は作業途中の実装が含まれるため、利用時は内容を確認してください。

Authors
- KabuSys チーム（コードベースに含まれるモジュールの著者）

LICENSE
- リポジトリ内のライセンスファイルを参照してください。