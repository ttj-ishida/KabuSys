# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルはコードベースの現在の状態から推測して作成しています（実装済み機能・振る舞い・既知の制約を記載）。

全般的な注意
- 本リリースでは内部 API・実装の多くが初期実装されています。将来的に API や環境変数のデフォルトが変更される可能性があります。
- 環境依存の挙動（例: プロセス優先度設定やファイル書き込み）が実行環境によって一部スキップされることがあります。ログや警告に従ってください。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21

### Added
- プロジェクト初期版のコア機能を追加
  - パッケージメタ情報
    - `kabusys.__version__ = "0.1.0"`
  - 環境/設定管理
    - `kabusys.config.Settings`：環境変数からアプリ設定を取得するラッパーを実装。
      - KABUSYS_ENV（development / paper_trading / live）の検証。
      - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）および監視閾値（CPU/MEM/DISK）をプロパティで提供。
      - PAPER_FILL_MODE（paper trading の fill モード）を検証。
    - .env 自動読み込み機能
      - プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動ロード（既存 OS 環境変数は保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - `.env` のパースは引用符やエスケープ、inline コメントなどに対応。
  - 設定作成・検証 CLI
    - `kabusys.config_setup`：対話式ウィザードで `.env` を生成/更新する CLI を追加（秘密値のマスク表示、選択肢・デフォルト対応）。
    - `kabusys.validate_config`：起動前チェック用 CLI を追加。必須環境変数やファイル/ディレクトリの存在、YAML のパース（PyYAML があれば）や本番環境向けのガードチェックを実行。`--strict` オプションで警告を失敗扱いにできる。
  - 実行系（Engine / 実行ループ）
    - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と分離。
      - BrokerClientFactory を用いてブローカークライアントを生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとスレッドでの実行制御（停止フラグ検知による安全停止）を実装。
      - PID ファイルと停止フラグ（data/execution.pid / data/stop_requested.flag）を使用。
  - 監視系
    - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境に関わらず本番の `sqlite_path` を使用して監視テーブルを初期化（`init_monitoring_db`）。
      - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
      - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。
  - データアクセス・分析
    - DuckDB を利用した分析用接続 (`duckdb` を使用) を標準でサポート（各起動スクリプトが接続を生成して注入）。
  - ポートフォリオ構築関連（純粋関数群）
    - `kabusys.portfolio.portfolio_builder`
      - select_candidates：BUY シグナルをスコア降順で選択（タイブレーク: signal_rank）。
      - calc_equal_weights：等重配分。
      - calc_score_weights：スコア加重（全スコア 0 の場合は等重へフォールバック）。
    - `kabusys.portfolio.risk_adjustment`
      - apply_sector_cap：既存保有セクター割合が上限を超える場合、新規候補を除外するロジック（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未知レジームは警告のうえ 1.0 にフォールバック）。
    - `kabusys.portfolio.position_sizing`
      - calc_position_sizes：allocation_method（risk_based / equal / score）に基づき発注株数を算出。単元（lot_size）丸め、per-stock cap、aggregate cap のスケーリング処理、コストバッファ考慮、残余配分ロジックを実装。
      - risk_based の基本式、aggregate スケーリングの細かな処理、残差を用いた追加配分などを実装。
    - `kabusys.portfolio.__init__` で上記関数群をエクスポート。
  - ユーティリティ
    - `kabusys.utils.logging_setup`
      - 統一ロギング設定ユーティリティを追加。
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）のファイルハンドラをルートロガーに設定。LOG_DIR / LOG_LEVEL による上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップして警告出力。
    - `kabusys.utils.process_priority`
      - set_process_priority(level)：Windows / POSIX に対応した優先度（nice / Windows priority class）設定。失敗時は警告を出してスキップ。
      - set_cpu_affinity(cpu_count)：プロセスの CPU affinity を最初の N コアに固定（権限不足や非対応環境では警告）。
  - ツール
    - `kabusys.tools.paper_verification_report`
      - Paper Trading 用の検証レポート生成スクリプトを追加。
      - system_status / trade_logs / risk_logs から、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg / max / P95）等を計算してレポート出力。
      - デフォルト閾値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）に基づいて PASS/FAIL 判定を行う。
      - コマンドライン引数で期間指定（--from, --to）および DB パス（--db）を受け付ける。DB が存在しない場合はエラーメッセージを表示。
  - 監視 DB 初期化ヘルパー
    - `kabusys.monitoring.monitoring_db.init_monitoring_db` を起動側で呼んで冪等的に監視テーブルの存在を保証（監視・実行スクリプトで使用）。

### Changed
- 初期リリースのため該当なし（本バージョンでの実装内容はすべて新規追加として扱う）。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 該当なし。

### Deprecated
- 該当なし。

### Security
- 該当なし。

### Known issues / TODO（コード内コメントより）
- position_sizing:
  - 将来的に銘柄ごとの lot_size をマスタで扱うことを想定（現状は全銘柄共通の引数）。
- apply_sector_cap:
  - price_map に価格が欠損 (0.0) の場合、エクスポージャーが過小評価される可能性があり、注記として TODO が残されている（将来的には前日終値などのフォールバックを導入予定）。
- research/factor_research モジュールはファイル末尾が途中で切れている（実装継続の余地あり）。  
  （本 CHANGELOG は現状のファイル群に基づいて作成しているため、未実装部分は将来のリリースで補完予定）

### 使用上の重要な注意
- 監視（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数で間隔を指定可能。無効な値はデフォルト 60 秒にフォールバックします。
- run_monitoring は監視用 DB に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視は環境に依らず本番 sqlite_path を参照します（意図的な仕様）。
- 実行（run_execution）は KABUSYS_ENV=paper_trading のとき専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離します。
- 自動 .env 読み込みはプロジェクトルートが検出できない場合スキップされる点に注意してください。
- プロセス優先度・CPU affinity の設定は権限や OS に依存します。設定に失敗してもプロセスは継続しますが、警告が出力されます。

---

今後のリリースでは以下を予定（推測）
- factor_research の完全実装（ファクター計算ロジックの完成）
- テスト・CI の追加（ユニットテスト、integration tests）
- ドキュメント（API / 設定 / 運用手順書）の拡充
- 単元株情報のマスタ化と lot_size の銘柄別対応
- より厳密なエラーハンドリングと運用監視アラート整備

（以上）