# Changelog

すべての注目すべき変更を記録します。  
このファイルは "Keep a Changelog" の形式に準拠します。

- リリース日付はリポジトリのスナップショットから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージ情報は src/kabusys/__init__.py にて定義（__version__ = "0.1.0"）。

- 実行用スクリプト / ランナーを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。プロセス優先度設定、SQLite / DuckDB 接続、PID/停止フラグ管理を実装。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して実行。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と優雅な停止処理を実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する仕様（監視データは環境に依存しない運用を想定）。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了処理を実装。

- 設定関連ユーティリティを追加
  - config.py
    - .env の自動読み込み機構（.env, .env.local）をプロジェクトルート検出に基づき実装。OS 環境変数を保護する仕組みを備える。
    - .env のパースロジックを実装（コメント、クォート、エスケープ、export プレフィックス対応）。
    - Settings クラスを提供し、環境変数から各種設定（DB パス、API トークン、環境区分、監視閾値など）を安全に取得できるインターフェースを定義。値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加（項目、説明、デフォルト、シークレット入力、保存確認を実装）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DBパスや config ファイルの存在チェック、live 環境向けの追加ガード等を実装。--strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート・候補選択（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックする。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap、および市場レジームに応じた投下資金乗数を返す calc_regime_multiplier を実装。未知レジームや unknown セクターのフォールバック挙動を定義。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap、cost_buffer（手数料・スリッページ見積）を考慮したスケーリング、残差処理によるロット追加配分などの細かな制約を実装。

- ユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーの一括設定ユーティリティを追加。コンソール出力は stdout を使用、TimedRotatingFileHandler による日次ローテーション（デフォルト logs/<app_name>.log、30 日保持）を実装。既存ハンドラのクリア、ログレベル/ログディレクトリの解決順（引数 > 環境変数 > デフォルト）に対応。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するヘルパを実装。Windows と POSIX の差異を吸収し、権限不足時は警告を出してフォールバックする。

- モニタリング DB 初期化共通化
  - monitoring.monitoring_db.init_monitoring_db を通じて monitoring 用テーブルの初期化処理を保証（冪等）。

- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py
    - ペーパートレードの SQLite データから検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出。閾値判定による PASS/FAIL を表示。
    - 日付フィルタ（--from/--to）、DB パス指定（--db / 環境変数）に対応。

- 研究用ファクター計算モジュール（研究用・未完の実装スケルトン）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター算出方針、定数、calc_momentum 関数の雛形を追加（DuckDB の prices_daily / raw_financials テーブル参照を前提）。
    - 本モジュールは DuckDB を用いたデータ処理設計を示す。

### Changed
- なし（初期リリースのため多くは追加のみ）。

### Fixed
- なし（初期リリース）。

### Notes / Usage highlights
- 環境変数とデフォルト:
  - KABUSYS_ENV: development | paper_trading | live（厳密チェックあり）。
  - SQLITE_PATH, DUCKDB_PATH 等はデフォルトを持ち、.env で上書き可能。
  - PAPER_TRADING_SQLITE_PATH を用いてペーパートレード用 DB を明示的に指定可能。
  - MONITOR_POLL_INTERVAL（秒）で監視ポーリング間隔を上書き可能。無効値は警告後にデフォルト(60s)にフォールバック。
  - PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかでなければ ValueError。
  - KILL_FLAG_CLEAR_ON_START は本番での危険性を考慮してデフォルト 0（クリアしない）を推奨。

- ログ:
  - setup_logging は stdout へ出力するため、cron / システム起動ログとの相性を考慮して使用可能。
  - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続する。

- セキュリティ/安全策:
  - validate_config により起動前に必須設定・本番モードのガード（LINE 通知設定の確認や kill-flag 自動クリアの警告）を実行可能。
  - run_execution/run_monitoring は stop flag / pid ファイル等で優雅な停止をサポート。

### Breaking Changes
- なし（初期リリース）。

### Known limitations / TODO
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map の導入を想定）。
- apply_sector_cap の価格欠損時（price_map が 0.0 など）の扱いは未改善（TODO コメントあり）。
- research/factor_research は一部未完（calc_momentum 等の完全実装が継続課題）。
- 実際の ExecutionEngine / BrokerClient 実装の詳細はこのスナップショットからは不明（BrokerFactory を介して依存注入する設計）。

---

オプション: 追加のファイル差分や特定モジュールの変更点を詳述したい場合は、対象ファイルを指定してください。