# Changelog

すべての重要な変更は Keeping a Changelog の方針に従って記載します。  
このファイルは人間に読みやすく、かつリリース履歴の追跡がしやすいことを目的としています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

※ このリポジトリのバージョンはパッケージメタデータ (src/kabusys/__init__.py) に合わせて v0.1.0 としています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-18

### Added
- 初期リリースとして以下の主要コンポーネントを追加。
  - 設定管理
    - Settings クラスおよび settings シングルトンで環境変数を一元管理（src/kabusys/config.py）。
    - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml で判定）。
    - .env ファイルのパース改善（export プレフィックス・クォート・インラインコメントを考慮）。
  - 設定ユーティリティ/CLI
    - 対話式環境設定ウィザード: `python -m kabusys.config_setup` による .env の初期作成/更新機能（src/kabusys/config_setup.py）。
    - 設定検証ツール: `python -m kabusys.validate_config` による起動前検証（必須環境変数やファイルパス、YAML 構文などをチェック）（src/kabusys/validate_config.py）。
  - 実行系 / 監視起動スクリプト
    - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
      - ブローカークライアントのファクトリを介した生成、各種依存コンポーネント（OrderRepository、OrderManager、RiskManager、Reconciler）を組み立て実行。
      - 停止フラグ（data/stop_requested.flag）および実行 PID 管理（data/execution.pid）の取り扱い。
    - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を参照して監視テーブルを初期化。
  - Paper Trading 検証ツール
    - `python -m kabusys.tools.paper_verification_report` による Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシなど）および期間フィルタ指定オプション（src/kabusys/tools/paper_verification_report.py）。
  - ポートフォリオ構築ロジック（純粋関数群）
    - 候補選定: select_candidates（スコア順・タイブレーク処理）
    - 重み付け: calc_equal_weights / calc_score_weights（スコア全0 のフォールバックロジック含む）
    - リスク調整: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに基づく乗数）
    - 取引数量決定: calc_position_sizes（risk_based / equal / score の各配分方式、単元丸め、aggregate cap スケーリング等）
  - ロギング / プロセス制御ユーティリティ
    - 統一ロギングセットアップ: setup_logging（コンソール stdout と日次ローテートファイルハンドラの追加、ログディレクトリ作成の安全処理）（src/kabusys/utils/logging_setup.py）。
    - プロセス優先度・CPU affinity 設定ユーティリティ: set_process_priority, set_cpu_affinity（Windows / POSIX を吸収）（src/kabusys/utils/process_priority.py）。
  - 研究用ファクター計算スケルトン
    - momentum 等のファクター計算用モジュール骨子（DuckDB 接続を想定）（src/kabusys/research/factor_research.py）。

### Changed
- アーキテクチャ/運用面の決定
  - データベース接続
    - duckdb を分析用 DB として採用（Settings.duckdb_path）。
    - 監視用 monitoring DB（SQLite）と paper_trading 用 SQLite を明確に分離（Settings.sqlite_path / Settings.paper_sqlite_path）。
  - 実行/監視プロセスは起動直後にプロセス優先度を "high" に設定することで重要処理の安定性を改善（set_process_priority を使用）。
  - ログの出力先を stdout に一本化して Task Scheduler / cron 等からのリダイレクト運用を想定。
- .env 読み込みの優先順位を明記
  - OS 環境変数 > .env.local > .env の順で読み込み。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 設定バリデーション
  - validate_config が PyYAML の有無を許容し、未インストール時には YAML 検証をスキップして警告を出す。

### Fixed
- .env パーサの改善により以下の問題を回避:
  - export プレフィックスを含む行の正しい処理。
  - クォート文字内のバックスラッシュエスケープと閉じクォート探索の対応。
  - クォートなし値のインラインコメント認識（'#' の前がスペース/タブの場合のみコメントとして扱う）。
- logging_setup でログディレクトリ作成に失敗した際にハンドラ二重追加やプロセス停止に繋がらないよう堅牢化（ファイルハンドラ作成失敗時にコンソール出力のみで継続）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（環境変数にシークレットを扱う設計であるため、.env を絶対に Git にコミットしない旨を config_setup のヘッダに明記）

---

付録（運用メモ）
- 起動例
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 主な環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - PAPER_FILL_MODE（paper_trading 時のフォールバック: instant / partial / never / reject）
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH / LOG_LEVEL / LOG_DIR 等
- 本番運用注意点
  - KABUSYS_ENV=live の場合は LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を厳重に確認してください（validate_config にて警告を出します）。
  - .env にシークレットを保持するため、リポジトリへのコミットおよび公開場所への保存を厳禁としてください。

---

参考: パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に対応しています。