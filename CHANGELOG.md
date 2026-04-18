# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に従っています。  

## [Unreleased]

（現在該当なし）

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基本機能をまとめて追加しました。

### Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - エントリスクリプト: `run_execution.py`, `run_monitoring.py`
- 設定・環境変数管理
  - `kabusys.config.Settings` クラスを導入し、アプリ設定をプロパティ経由で取得可能に。
  - 自動 .env ロード機能を実装（プロジェクトルートの `.env` / `.env.local` を読み込み）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化対応。
  - `.env` パーサーは `export KEY=...` 形式やクォートされた値、インラインコメント等に対応。
  - 重要な環境変数の取得は未設定時に明示的なエラーを出す `_require()` を実装。
- 設定ウィザード / 検証ツール
  - `kabusys.config_setup`：対話式ウィザードで .env を作成/更新する CLI を追加。シークレット入力のマスク表示やデフォルト値のサポート。
  - `kabusys.validate_config`：起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在と YAML パース（PyYAML がある場合）等をチェック。`--strict` オプションで警告を失敗扱いに可能。
- 実行/監視プロセス
  - `run_execution.py`
    - プロセス優先度を起動時に「high」に設定（`kabusys.utils.process_priority` を利用）。
    - `paper_trading` 環境では専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - Broker クライアント生成用の `BrokerClientFactory` を利用。
    - `ExecutionEngine` をスレッドで起動し、プロジェクトルートの `data/stop_requested.flag` による外部停止をサポート。PID ファイルの指定あり。
    - `RiskManager` のデフォルト `RiskConfig` を実装（max_position_pct 等の既定値を設定、初期ポートフォリオ値に broker.get_available_cash() を使用）。
    - `init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等）。
  - `run_monitoring.py`
    - 監視ポーリングループを実装。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の `sqlite_path`（監視 DB）を使用する設計。
    - 停止フラグ検知により安全にループを終了。
- ロギング / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を設定するユーティリティを追加。`LOG_DIR` / `LOG_LEVEL` / 引数による解決、ログディレクトリ作成失敗時のフォールバックあり。
  - `kabusys.utils.process_priority`
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。`set_cpu_affinity` によるコア固定機能も提供。権限不足や未実装環境では警告を出して安全にスキップ。
- ポートフォリオ構築ロジック（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`、等配分 `calc_equal_weights`、スコア重み `calc_score_weights` を実装。スコア全零時のフォールバックとログ警告あり。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中度制限 `apply_sector_cap`、市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を実装。未知のレジームはログ警告のうえフォールバック。
  - `kabusys.portfolio.position_sizing`
    - 株数決定ロジック `calc_position_sizes` を実装。`risk_based` / `equal` / `score` の配分方式をサポートし、単元（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、端数処理（残差順に lot 単位で追加配分）を実装。
- 解析 / 調査用
  - `kabusys.research.factor_research` を追加（ファクター群：Momentum / Value / Volatility / Liquidity 計算方針と定数を実装）。（注：ファイル末尾に一部未完成の箇所あり）
  - DuckDB を分析用に採用（`duckdb` 接続を受ける設計）。
- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（P95 含む）、リスク却下数などを集計・判定し、PASS/FAIL レポートを標準出力に表示。閾値はスクリプト内定義で変更可能。日付フィルタ `--from` / `--to` と `--db` 指定をサポート。

### Changed
- データベース関連の扱いを明確化
  - `run_execution` では `settings.is_paper` によって paper_trading 用 DB を選択して起動することで本番データと完全分離する設計。
  - `init_monitoring_db` を起動時に呼び出して監視用テーブルの初期化（存在チェック）を保証し、複数回呼び出しても安全（冪等）に。
- ログ出力の標準化
  - すべての起動スクリプトで `setup_logging(app_name=...)` を使用することでログ取得方法を統一。

### Fixed
- .env 読み込みの堅牢化
  - クォート処理やエスケープ、export プレフィックス、コメント扱いの細かなケースに対応。
  - OS 環境変数を保護する `protected` パラメータで `.env.local` からの上書きを制御。
- 実行中の停止や例外処理の強化
  - 監視ループおよびエンジン実行ループで停止フラグ・KeyboardInterrupt を検出して安全に終了する処理を追加。
  - 監視 `check_once()` 内での例外を捕捉して次のポーリングに影響しないようにログ出力して継続。

### Known limitations / Notes
- `kabusys.research.factor_research` の一部（ファイル末尾）は未完了のコード（実装途中）を含みます。利用時は実装の完成が必要です。
- `calc_position_sizes` などの一部ロジックは価格が欠損（0.0）の場合に現状の挙動で過少評価やスキップを行います。将来的にフォールバック価格（前日終値等）を導入する余地があります（コード内に TODO コメントあり）。
- ログファイル作成やプロセス優先度設定は権限や環境に依存し、失敗した場合はフォールバック動作（警告出力）になります。

---

（以降のリリースでは Unreleased に変更を記載し、バージョン切り分けを行ってください。）