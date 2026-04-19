# Changelog

すべての注目すべき変更はこのファイルに記録します。これは Keep a Changelog の形式に準拠しています。

新しいバージョンのリリースポリシー、互換性などに関する詳細はリポジトリの README を参照してください。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-19

最初の公開リリース。システム全体の基本コンポーネント、CLI ユーティリティ、ポートフォリオ構築ロジック、paper trading 検証ツール、監視/実行用起動スクリプト、設定管理を含む。

### Added
- 基本バージョン情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - Settings クラス（`kabusys.config`）を追加。環境変数と .env ファイル（.env, .env.local）を読み込み、各種設定値（DB パス、API トークン、閾値など）をプロパティとして提供。
  - 自動 .env 読み込み機能を導入（プロジェクトルートを .git / pyproject.toml から検出）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env ファイルのパースロジックを強化し、`export KEY=val`、クォート値、インラインコメント処理に対応。
  - 設定の検証（必須 env の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML ファイルの存在確認）を行う CLI (`kabusys.validate_config`) を追加。`--strict` オプションで警告も失敗扱いにできる。

- 設定ウィザード
  - 対話式の .env 作成/更新ウィザード（`kabusys.config_setup`）を追加。主要項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、ログレベル、Kill Switch 関連など）を対話的に作成できる。

- 起動スクリプト / ランタイム
  - 実行エンジン起動スクリプト `run_execution.py`（`python -m kabusys.run_execution`）を追加。環境に応じて paper_trading 用の MockBrokerClient を使用し、paper トレード時は `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）にデータを分離して記録。
  - 監視ループ起動スクリプト `run_monitoring.py`（`python -m kabusys.run_monitoring`）を追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用の sqlite_path を参照する実装。
  - 停止フラグファイル（data/stop_requested.flag）を用いた優雅な停止処理を実装（監視/実行ともに対応）。実行プロセス用の pid ファイルパス設定をサポート。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギングセットアップ（`kabusys.utils.logging_setup.setup_logging`）を追加。StreamHandler を stdout に出力し、TimedRotatingFileHandler による日次ローテーション（デフォルト logs/<app_name>.log、30 日保持）を実装。ログレベル・ログディレクトリの解決順を定義。
  - プロセス優先度・CPU affinity 設定ユーティリティ（`kabusys.utils.process_priority`）を追加。Windows / POSIX を吸収した API を提供し、起動時に `set_process_priority("high")` を呼ぶことで優先度を引き上げる設計（失敗時は警告でスキップ）。

- ポートフォリオ構築（純関数群）
  - 銘柄選定と重み計算（`kabusys.portfolio.portfolio_builder`）
    - select_candidates: BUY シグナルをスコア降順で選択
    - calc_equal_weights / calc_score_weights: 等額配分・スコア重み分配（スコア総和が 0 の場合は等分にフォールバック）
  - リスク調整（`kabusys.portfolio.risk_adjustment`）
    - apply_sector_cap: セクター集中上限（max_sector_pct）チェックと候補除外ロジック
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear、未知のレジームは警告とともに 1.0 をフォールバック）
  - ポジションサイジング（`kabusys.portfolio.position_sizing`）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく買付株数計算、lot_size 単位丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリング。

- Research / ファクター
  - factor_research モジュール（`kabusys.research.factor_research`）にモメンタム等を計算するための骨組みを追加。DuckDB 接続を受け prices_daily / raw_financials を参照してファクターを算出する設計（モメンタム計算の定数・仕様は実装済み、一部関数は継続実装が必要）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` 又は `--db`）のデータからシステム稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを集計し、PASS/FAIL 判定を行う。閾値はソース内部で定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

- 監視 DB 初期化
  - 監視用テーブルを初期化する `init_monitoring_db`（監視起動時に呼び出し、冪等で DB スキーマを保障）。

### Changed
- .env 読み込みの挙動
  - 自動ロードの優先順位を OS 環境 > .env.local > .env とし、既存 OS 環境変数は保護される（protected 機構）。
- ログ出力
  - コンソール出力は stdout を使用（cron 等からのリダイレクト想定）。ファイルハンドラの作成失敗時はコンソール出力のみで継続する設計に。
- 実行 / 監視プロセスの優先度
  - 起動スクリプトで最初にプロセス優先度を "high" に設定するよう変更（set_process_priority を各起動処理の最初に呼び出し）。

### Fixed / Improved
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いを改善。
- ポジションサイズ計算の堅牢性
  - lot_size 単位での丸め処理、available_cash 超過時のスケーリング（小数端数の扱いに対する再配分ロジック）を導入。
- risk_adjustment のフォールバック
  - 未知のレジーム文字列に対し警告を出して 1.0 を返すことで安全側へフォールバック。
- 監視ループの堅牢化
  - check_once() 呼び出し中に例外が発生しても監視ループを継続するよう例外をキャッチしてログ出力し次回ポーリングへ備える実装。

### Notes / その他
- 環境変数関連の主要キー
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 推奨/任意: KABUSYS_ENV (development/paper_trading/live), DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - Paper trading 固有: PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE（"instant" | "partial" | "never" | "reject"）
  - 監視関連: MONITOR_POLL_INTERVAL（秒; >=1。デフォルト 60）、KILL_FLAG_CLEAR_ON_START
- DuckDB/SQLite のデフォルトパス
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視）: data/monitoring.db
  - SQLite（paper_trading）: data/paper_trading.db

---

このリリースの変更点に関して不明点や追加で記載してほしい項目があればお知らせください。