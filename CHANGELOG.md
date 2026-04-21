# Changelog

すべての変更は Keep a Changelog の規約に準拠して記載しています。  
リリース日付はコードベースから推測した最新変更日を使用しています。

## [0.1.0] - 2026-04-21

### 追加（Added）
- 基本アプリケーション初期実装を追加。
  - パッケージメタ情報: kabusys.__version = "0.1.0"。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する実装。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検出時の安全停止処理と PID ファイル管理。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する実装（監視データは本番 DB）。
    - 停止フラグ検知・例外捕捉・正常終了処理を実装。
- 設定管理
  - config.Settings クラスを追加（環境変数から各種設定を取得）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、API トークン、KABUSYS_ENV、LOG_LEVEL、各種閾値（CPU/MEM/DISK）などをプロパティ経由でアクセス可能。
    - `is_live` / `is_paper` / `is_dev` 等のヘルパーを提供。
    - PAPER_FILL_MODE（`instant`|`partial`|`never`|`reject`）を検証するプロパティを実装。
- .env 自動読み込み機能
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動読み込み。
  - OS 環境変数を保護する仕組み（上書き禁止）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env の行パーサーは `export KEY=val`、クォート、エスケープ、インラインコメント等に対応。
- 設定ウィザード CLI
  - config_setup: 対話式ウィザードで .env を生成・更新するツールを追加。
  - 複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE トークン等）に対応。シークレット入力のマスク表示、既存 .env 読み込み、保存確認を実装。
- 設定検証 CLI
  - validate_config: .env と config/*.yaml の基本検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの存在チェック（親ディレクトリ）など。
    - PyYAML が無い場合は YAML の内容検証をスキップして警告。
    - `--strict` オプションで警告を FAIL 扱いにする機能。
- ロギングユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせてルートロガーを構成。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログローテーションは 30 日分保持。
    - LOG_DIR / LOG_LEVEL の優先順位解決を実装。
- プロセス優先度・CPU 固定ユーティリティ
  - utils.process_priority.set_process_priority / set_cpu_affinity を追加。
    - Windows/Linux/macOS を吸収する実装（psutil ベース）。アクセス権限不足等は警告してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で銘柄選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合はフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限の実装（売却予定銘柄を除外可能）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear/フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の割付方式に基づく株数決定、単元株丸め、Aggregate cap スケーリング、cost_buffer の考慮等を実装。
- Paper Trading 検証ツール
  - tools.paper_verification_report: paper_trading の SQLite DB から各種指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポート出力する CLI を追加。
    - デフォルト閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）で PASS/FAIL 判定を行う。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）に対応。
- リサーチモジュール（下書き）
  - research.factor_research: DuckDB 接続を受けてモメンタム／ボラティリティ等のファクターを計算するための骨格を追加（prices_daily / raw_financials を参照する設計。関数群の実装は一部未完：モメンタム計算の開始位置に切れ目あり）。

### 変更（Changed）
- なし（初回リリースのため履歴は主に追加）。

### 修正（Fixed）
- なし（初回リリース。ただし各モジュールで入力検証・例外処理、ファイル作成失敗時のフォールバック等の堅牢化は行われている）。

### 破壊的変更（Breaking Changes）
- なし（初回公開）。ただし以下点は運用上の注意:
  - Monitoring は起動環境にかかわらずデフォルトで sqlite_path（本番用監視 DB）を使用するため、開発環境での監視データを本番 DB に混在させたくない場合は SQLITE_PATH を明示的に分けること。
  - 自動 .env 読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### ドキュメント / 補足（Notes）
- デフォルトのファイルパス:
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - PID / stop flag / kill flag: data/*.pid / data/stop_requested.flag / data/kill.flag
- 新規に導入された主な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START, KABUSYS_DISABLE_AUTO_ENV_LOAD, PAPER_TRADING_SQLITE_PATH
- CLI エントリポイント（モジュール実行可能）
  - python -m kabusys.run_execution など（各スクリプトは if __name__ == "__main__" を持つ）。
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

次回以降の変更提案（メモ）
- research.factor_research の完全実装（ファクター計算ロジックの完成）。
- position_sizing における銘柄別単元（lot_size）マスタ対応。
- apply_sector_cap の price フォールバック（前日終値や取得原価）対応。
- ログとメトリクスのさらに詳細な運用ドキュメント追加。