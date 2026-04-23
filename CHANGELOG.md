# Changelog

すべての注目すべき変更はここに記載します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-23

初回リリース。システム全体の起動スクリプト、設定管理、監視・実行基盤、ポートフォリオ構築・リスク調整・ポジション算出ロジック、ユーティリティ群、および Paper Trading 検証ツールを追加しました。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` によるフラグ検知で行う。
    - 監視は環境にかかわらず production 用の `sqlite_path` を使用する（監視 DB の一貫性確保）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用のペーパートレード用 DB を使い、本番 DB と分離（デフォルト: `data/paper_trading.db`）。
    - 起動前に `data/stop_requested.flag` を確認し、既に立っている場合は起動しない。
    - 実行中は停止フラグ検知で Engine.stop() を呼び出して安全終了する。PID ファイル管理あり（`data/execution.pid`）。

- 設定管理
  - config.py
    - 環境変数読み込み・管理を提供する `Settings` クラスを追加。
    - 自動 `.env` / `.env.local` ロード（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 各種既定値、パス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` など）およびバリデーション（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）を実装。
    - `settings` シングルトンを提供。
  - config_setup.py
    - 対話式ウィザードで `.env` の初期作成・更新を支援する CLI を追加。
    - 秘匿入力、選択肢、デフォルト表示、保存確認などを実装。
  - validate_config.py
    - `.env` と `config/*.yaml` の事前検証 CLI を追加。
    - 必須環境変数チェック、パス存在確認（親ディレクトリの有無）、YAML パースチェック（PyYAML 利用可時）、本番環境向けガード（LINE 通知や Kill スイッチ設定の警告）等を実装。
    - `--strict` モードで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定: `select_candidates`（スコア降順、タイブレーク処理含む）
    - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア全0 の場合は等分配にフォールバック）
  - portfolio/risk_adjustment.py
    - セクター集中制限: `apply_sector_cap`（既存ポジションのセクター比率を計算し、上限超過セクターの新規候補を除外）
    - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対する乗数を定義、未知レジームは警告の上 1.0 でフォールバック）
  - portfolio/position_sizing.py
    - 株数算出: `calc_position_sizes`
      - アロケーション方式: `"risk_based"`, `"equal"`, `"score"` をサポート
      - 単元株（lot_size）、手数料・スリッページ見積り（cost_buffer）、max_position_pct、max_utilization、aggregate cap によるスケーリング、端数処理（lot 単位）などを実装
      - 投下額が利用可能現金を超える場合の縮小ロジック（残差処理による追加配分）を実装

- 監視・実行用 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等処理）。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。root ロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト "INFO"。
    - ログディレクトリ解決順: 引数 > 環境変数 `LOG_DIR` > デフォルト "logs/"。ディレクトリ作成失敗時はファイル出力をスキップし標準出力へフォールバック。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows/Linux/macOS を吸収）。
    - `set_process_priority(level: "high"|"normal"|"low")` を実装（psutil を利用、例外時は警告でスキップ）。
    - `set_cpu_affinity(cpu_count: int | None)` を実装（指定が None の場合は変更しない）。

- 研究・ファクター計算（リサーチ）
  - research/factor_research.py
    - Momentum、Value、Volatility、Liquidity 等の計算を行うための骨格を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。
    - モメンタム関連定数と calc_momentum 関数の実装を開始（※ファイル末尾で実装が途中の箇所あり。今後の補完予定）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで DB を指定可能（デフォルト: `data/paper_trading.db`）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計。閾値による PASS/FAIL 判定を出力。
    - 日付フィルタ `--from` / `--to` による期間指定をサポート。

- パッケージ公開用
  - __init__.py でパッケージエクスポートの定義とバージョン管理を追加。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （現時点で特記すべきセキュリティ修正はありません）

---

注意事項 / 既知の制約
- research/factor_research.py の calc_momentum 等は実装の続きが必要な箇所が見られます（ファイル末尾で切れている）。リサーチ機能の完全稼働には追加実装が必要です。
- .env ファイルは機密情報を含むため、生成される `.env` を絶対にリポジトリにコミットしないでください（config_setup でも同旨の警告あり）。
- 監視プロセスは監視用 SQLite を常に production 用パスから開く設計です。運用時は SQLite パス周りの権限・バックアップ・整合性に注意してください。

--- 

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は開発履歴・コミットログを参照して追記・修正してください。）