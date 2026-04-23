# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」準拠です。

注意: この CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のコミット履歴とは異なる場合があります。

## [Unreleased]

- 一部モジュール（例: research/factor_research の実装途中）や追加検証が残っています。今後のリリースで完成・改善予定。

---

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 環境設定・読み込み
  - .env と .env.local を自動読み込みする仕組み（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（src/kabusys/config.py）。
  - .env の堅牢なパース実装（コメント、引用符、export 構文の扱いを考慮）を実装（src/kabusys/config.py）。
  - Settings クラスでアプリ設定を統一的に取得可能。主要プロパティ:
    - J-Quants / kabuステーション / LINE 関連（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID` 等）
    - DB パス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`）
    - 環境区分（`KABUSYS_ENV` → `development`, `paper_trading`, `live`）
    - 監視／kill フラグ・PID ファイル関連（`PID_FILE_PATH`, `KILL_FLAG_PATH`, `KILL_FLAG_CLEAR_ON_START`）
    - 監視閾値（`CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT`）
    - Paper Trading 用の `PAPER_FILL_MODE`（入力値検証あり）

- 環境設定ウィザード
  - 対話式 CLI で .env を生成・更新する `config_setup`（python -m kabusys.config_setup）。主要設定項目のプロンプトと .env ファイル書き出し機能を提供（src/kabusys/config_setup.py）。

- 設定検証ツール
  - 起動前の設定検証 CLI `validate_config`（python -m kabusys.validate_config）。
  - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML が利用可能な場合）パース検証、KABUSYS_ENV=live 時の追加ガード等を実施。
  - `--strict` モードで警告を失敗扱いにできる（exit code 1）（src/kabusys/validate_config.py）。

- 実行系（Execution）
  - ExecutionEngine 起動スクリプト `run_execution` を追加（src/kabusys/run_execution.py）。
    - プロセス優先度を高く設定（utils/process_priority）。
    - `KABUSYS_ENV=paper_trading` の場合、ブローカーは Mock を利用し、Paper Trading 用 DB（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と完全分離。
    - 監視用テーブルの初期化（init_monitoring_db）を実行（冪等）。
    - BrokerClientFactory を使ったブローカー生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ監視（data/stop_requested.flag）。
    - 実行中に PID を data/execution.pid に保存する想定（設定経由で pid_file 指定可能）。

- 監視系（Monitoring）
  - SystemMonitor ポーリングループ起動スクリプト `run_monitoring` を追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用（設計上の注意点として明示）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - DB 初期化（init_monitoring_db）と duckdb 接続を行う。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング初期化ユーティリティ `setup_logging` を実装（src/kabusys/utils/logging_setup.py）。
    - コンソール出力は stdout、ファイルは日次ローテーション（TimedRotatingFileHandler）で 30 日保持。
    - ログレベル・ログディレクトリは引数・環境変数・デフォルトの順で解決。ログディレクトリ作成に失敗した場合はファイル出力をスキップ。
  - プロセス優先度・CPU affinity 設定ユーティリティ `set_process_priority` / `set_cpu_affinity` を実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収する実装。アクセス権限不足等は警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、signal_rank でタイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合のフォールバック）。
  - セクター上限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率に応じて候補を除外）、calc_regime_multiplier（bull/neutral/bear のマッピングとフォールバック）。
  - 株数決定・資金配分ロジック（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。lot_size 単位丸め、max_position_pct や aggregate cap、cost_buffer を考慮したスケールダウンロジックを実装。
  - 上記関数群を package export（src/kabusys/portfolio/__init__.py）。

- Paper Trading 検証レポートツール
  - `tools/paper_verification_report.py` を追加。Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト data/paper_trading.db）から指標を集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を行う（しきい値はソース内定義）（src/kabusys/tools/paper_verification_report.py）。
  - CLI で期間指定（--from / --to）および --db による DB パス指定が可能。

- Research（ファクター計算）
  - ファクター計算基盤を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity を想定して実装する方針と初期的な定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（一部実装は途上）。

- DB 初期化フック
  - 監視テーブルの初期化呼び出し（init_monitoring_db）の導入により、監視テーブルが存在することを保証（冪等）。

### Changed
- 初回リリースにつき変更履歴はありません（新規追加中心）。

### Fixed
- 初回リリースにつき既知のバグ修正履歴はありません。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境ファイル生成時に .env を明示的に Git にコミットしない旨を注意書き（config_setup の出力）。
- シークレット項目はウィザード出力でマスク表示。

### Notes / Migration & Usage
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- Paper Trading 実行時は本番 SQLite を使用しないため、本番データと分離される（run_execution が環境に応じて専用 DB を選択）。
- 監視ループは MONITOR_POLL_INTERVAL（秒）で制御可能。不正値は警告の上で 60 秒にフォールバック。
- 本番運用時は KABUSYS_ENV を慎重に設定（validate_config による事前チェック推奨）。KABUSYS_ENV=live の場合、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値に注意する警告が出る。
- process priority / cpu affinity の設定は OS と権限に依存。権限不足の場合は警告でスキップされる。

---

（今後）
- research/factor_research の完全実装（Momentum 等の詳細クエリ・計算）。
- 追加テスト、型アノテーションの整備、コンポーネント間の統合テスト。
- CLI のエントリポイント整備（setup.py / pyproject の console_scripts など）およびドキュメント拡充。