# Changelog

すべての変更は「Keep a Changelog」形式に従い、重大度の高い変更を分かりやすく分類しています。

リンクやリリースノートがなければ、ここでは主要な機能追加・仕様をコードベースから推測して記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース — KabuSys 基本モジュール群を追加。

### Added
- 実行エントリ／デーモン化系
  - run_execution.py を追加。ExecutionEngine を起動するスクリプトを提供。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の MockBrokerClient を利用し、データベースは分離された paper_trading.db を使用する。
    - 実行中の停止制御はプロジェクトルートの data/stop_requested.flag による。
    - エンジンの PID を data/execution.pid に書き出す仕組みをサポート。
    - スレッドで engine.run_session() を起動し、停止フラグ検知で安全に停止するループ実装。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する（監視データは本番DBを参照）。
    - 停止は data/stop_requested.flag により行う。
    - check_once() 実行時の例外は捕捉してログ出力し、次ポーリングへフォールバックする実装。

- 設定・環境管理
  - config.py を追加。.env の自動読み込み、環境変数のラッパー Settings クラスを提供。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む自動ローダを実装（テスト等で無効化可能な KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
    - .env 行パーサーは export 形式・クォート・インラインコメント・エスケープに対応。
    - Settings に各種プロパティを定義（J-Quants, kabuAPI, DB パス, PAPER_FILL_MODE の検証、閾値設定、PID/kill flag パス、環境判定ユーティリティ等）。
  - config_setup.py を追加。.env 作成用の対話式ウィザードを提供（.env の初期作成／更新）。
    - 入力補助、シークレットのマスク表示、保存確認、.env のテンプレート書き出し機能を実装。
  - validate_config.py を追加。起動前に .env と config/*.yaml の設定検証を行う CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML が利用可能なら）パース検証を行う。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）をルートロガーへ設定する共通ユーティリティ。
    - ログレベル・ログディレクトリ解決ルール（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作。
  - utils/process_priority.py を追加。Windows/Linux/Mac の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）設定と CPU affinity 固定機能を提供。
    - 利用可能でない場合は安全にフォールバックしてログ警告を出力する。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py を追加。シグナル選定と等金額・スコア加重の重み計算関数を実装（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py を追加。セクター集中制限の適用（apply_sector_cap）と市場レジームに基づく投入資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py を追加。発注株数算出ロジック（risk_based / equal / score 配分、単元丸め、aggregate cap スケーリング、cost_buffer 対応）を実装。
  - portfolio/__init__.py で上記 API をエクスポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計して検証レポートを出力する CLI。
    - システム稼働率（system_status）、注文成功率および送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（latency: avg/max/P95）を算出。
    - 判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義し、PASS/FAIL を判定。
    - --from / --to / --db オプションをサポート。

- データ分析基盤（断片）
  - research/factor_research.py を追加（ファクター計算モジュールの骨子）。
    - DuckDB 接続を受け prices_daily/raw_financials を参照して Momentum/Value/Volatility/Liquidity 等のファクターを計算する設計。モジュール内に定数・計算方針を定義（関数 calc_momentum の実装開始）。

- パッケージメタ
  - __init__.py にて package version を "0.1.0" に設定。

### Changed
- （初回リリースのため「変更」は特になし）

### Fixed
- （初回リリースのため「修正」は特になし）

### Notes / Operational details
- 環境変数一覧（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - LOG_LEVEL, LOG_DIR
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト: 60）
- 監視（monitoring）は設定に関わらず監視用 SQLite を「本番」パスで初期化・使用する設計になっている点に注意。
- run_execution の起動前に data/stop_requested.flag が立っている場合は起動をスキップする安全策を実装。
- process_priority の設定はプラットフォーム依存のため、権限不足や未対応環境では警告ログを出してスキップする。
- logging_setup は既存ハンドラをクリアしてから再設定するため、スクリプトから複数回呼んでも二重出力にならない。

### Security
- .env ファイルは生成ツール（config_setup.py）で注意喚起コメントを付与し、Git にコミットしない旨を明記。
- 環境変数にシークレットを含める設計であり、取り扱いに注意が必要。

---

今後の予定（推測）
- factor_research の完全実装（Momentum ほか各ファクターの計算ロジックの完成）。
- ExecutionEngine / BrokerClient の詳細実装とテスト、発注ロジック周りのカバレッジ強化。
- 単体テスト追加、CI ワークフロー、ドキュメント整備（API ドキュメント、運用手順）。