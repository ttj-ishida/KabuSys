# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠し、SemVer を採用します。

※リポジトリの現在のバージョン: 0.1.0

[Unreleased]

## [0.1.0] - 2026-04-18

Added
- 基本アプリケーション骨格を追加
  - パッケージ初期化: `kabusys.__version__ = "0.1.0"`
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず production 相当の `sqlite_path` を使用する設計。
    - 停止制御はプロジェクト直下の `data/stop_requested.flag` で行う。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB（`data/paper_trading.db`）を使用し、本番 DB と分離。
    - Broker クライアントのファクトリを利用して実行時に適切なクライアントを生成。
    - スレッドベースでエンジンを実行し、停止フラグ検出時に安全停止を行う。
    - PID ファイル管理 (`data/execution.pid`) に対応。
  - 起動時にプロセス優先度を "high" に設定するフローを組み込み（`set_process_priority` を呼び出し）。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。
    - 環境変数から各種設定をプロパティとして取得（J-Quants / kabu API / DB パス / 監視しきい値など）。
    - `KABUSYS_ENV` / `LOG_LEVEL` 等の値検証と便利な bool プロパティ（`is_live`, `is_paper`, `is_dev`）を提供。
    - Paper Trading 用の `paper_sqlite_path`、`paper_fill_mode` をサポート（`paper_fill_mode` は有効値チェックあり）。
  - 自動 .env ロード機能を追加
    - プロジェクトルート（`.git` または `pyproject.toml`）を基準に `.env` / `.env.local` を自動読み込み（OS 環境変数優先）。
    - 自動ロード無効化のための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- .env ファイルユーティリティ
  - 高機能な .env パーサを実装
    - `export KEY=val`、クォート（シングル/ダブル）内のバックスラッシュエスケープ、行末コメント処理などに対応。
    - 読み込み時の上書き制御（protected keys）をサポート。

- 設定支援 CLI
  - `kabusys.config_setup` ウィザードを追加
    - 対話式で `.env` を生成/更新可能。シークレット値はマスク表示。
    - 生成済み `.env` の書き込み機能を提供。
    - デフォルト値や選択肢を組み込んだ質問定義を搭載。
  - `kabusys.validate_config` 検証 CLI を追加
    - 必須環境変数、`KABUSYS_ENV`/`LOG_LEVEL` の妥当性、DB パス（親ディレクトリ存在）を検査。
    - `config/*.yaml` の存在・パースチェック（PyYAML がない場合はスキップして警告）。
    - `--strict` オプションで警告を失敗扱いにできる。
    - `live` 環境向けの追加ガード（LINE 通知設定や Kill Switch の設定警告）を実装。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を設定。
    - `LOG_LEVEL` / `LOG_DIR` 環境変数や引数による上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - `kabusys.utils.process_priority`
    - Windows / POSIX（Linux / macOS 等）でプロセス優先度を抽象的に設定（`high` / `normal` / `low`）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
    - アクセス権限不足などのエラーは警告にフォールバックする設計。

- Portfolio（銘柄選定・配分・資金配分）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（スコア降順、タイブレークロジック）`select_candidates`
    - 等金額配分 `calc_equal_weights`
    - スコア加重配分 `calc_score_weights`（全銘柄スコア 0 の場合は等配分にフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター比率が閾値超過時に候補を除外）
    - レジーム乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" マッピング、未知値は 1.0 でフォールバック）
  - `kabusys.portfolio.position_sizing`
    - 発注株数算出 `calc_position_sizes`
      - 複数の allocation_method（`risk_based`, `equal`, `score`）に対応
      - 単元株（lot_size）処理、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap のスケーリングと再配分ロジックを実装
      - price が欠損する銘柄はスキップ

- Paper Trading 向けの検証ツール
  - `kabusys.tools.paper_verification_report`
    - SQLite（paper_trading DB）から指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポートを標準出力に出力。
    - CLI: 日付範囲指定 `--from` / `--to`、DB パス上書き `--db` をサポート。
    - P95 計算、各種閾値による PASS/FAIL 判定を実装（閾値はファイル内の定数で調整可能）。
    - DB が存在しない場合やテーブルがない場合に適切にエラーメッセージ/フォールバックを出力。

- Research（ファクター計算）
  - `kabusys.research.factor_research`（骨格）
    - DuckDB を使った price/financials ベースのファクター計算の設計を追加（モメンタム・MA200・ATR 等の定数定義と関数群の骨組み）。

Changed
- （初版）多数のユーティリティ・CLI・ドメインロジックを一度に導入。運用上の注意点や挙動は各 docstring に記載。

Fixed
- N/A（初回リリースのため変更履歴としての修正は無し）

Security
- 環境変数ファイル (.env) は「絶対に Git にコミットしない」旨を config_setup のテンプレートに明記。

Notes / Operational
- 監視（run_monitoring）は MONITOR_POLL_INTERVAL を環境変数で指定可能。無効値（0 や非数）は警告されデフォルト 60 秒にフォールバックする。
- run_execution は paper_trading 環境で本番 DB に影響を与えないよう専用 DB を使用する設計。実運用前に `kabusys.validate_config` によるチェックを推奨。
- process_priority / cpu_affinity の変更は権限のない環境では失敗して警告にフォールバックするため、無権限コンテナ等でも安全に動作する。
- ログは標準出力（stdout）とファイル出力の両立を図っているため、cron/システムタスクからの起動時のリダイレクト運用に適している。

参考
- 主要エントリポイント:
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

[0.1.0]: https://example.com/kabusys/releases/tag/0.1.0