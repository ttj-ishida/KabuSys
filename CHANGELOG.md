# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 本ドキュメントは提示されたソースコードの内容から推測して作成した初期リリース向けの変更履歴です。実際のコミット履歴ではありません。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-25

初回公開リリース。日本株自動売買システム「KabuSys」の基本機能群を提供します。以下の主要な機能・ユーティリティ・CLI を含みます。

### Added

- 基本パッケージ情報
  - パッケージバージョン: `__version__ = "0.1.0"`

- 設定管理
  - Settings クラス（kabusys.config）を実装。環境変数から設定を読み取り、各種設定プロパティを提供。
  - .env 自動読み込み機能を提供（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順と上書きルールを実装（OS環境変数を保護）。
  - 設定値のバリデーション：KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE などの妥当性チェック。

- 環境設定ウィザード CLI
  - kabusys.config_setup: 対話式の .env 作成/更新ウィザードを実装。
  - デフォルト項目やシークレット入力、既存値の読み込み・表示、.env ファイル書き込み機能を提供。

- 設定検証 CLI
  - kabusys.validate_config: .env と config/*.yaml の事前検証を行う CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、YAML ファイルの存在とパースチェック、KABUSYS_ENV=live 時の追加警告等。
  - --strict オプションで警告を失敗扱い（exit code 1）にできる。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用の専用 SQLite DB を使う（データは本番 DB と分離）。
    - プロセス優先度を高く設定（utils.process_priority を利用）。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理に対応。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てロジックを含む。
  - run_monitoring: SystemMonitor 起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（設計上の意図を明示）。
    - 停止フラグ検知、例外安全な check_once の呼び出しループを提供。

- 監視（monitoring）初期化
  - monitoring_db の初期化呼び出しを行い、監視テーブルが存在することを保証（冪等な初期化）。

- ロギングユーティリティ
  - kabusys.utils.logging_setup: StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーへ設定するユーティリティを実装。
  - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"）。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。

- プロセス優先度 / CPU affinity
  - kabusys.utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）を実装。
  - CPU affinity 設定の補助関数も実装。権限不足や未対応環境では警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルからスコア順に候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による配分（全スコア 0 の場合は等金額にフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を適用し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: 重み・候補・リスクパラメータに基づく銘柄毎の発注株数計算（risk_based / equal / score に対応）。
    - aggregate cap（総投資額が available_cash を超える場合のスケーリング）や単元株（lot_size）丸めロジックを実装。
    - cost_buffer による手数料・スリッページの保守的見積りを考慮。

- 研究/ファクター計算（基盤）
  - kabusys.research.factor_research: DuckDB 接続を受け prices_daily / raw_financials からモメンタム・ボラティリティ等のファクターを計算する設計を追加（関数インターフェースと定数群を実装）。※一部実装が途中（コードが切れている箇所あり）。

- Paper Trading 検証ツール
  - kabusys.tools.paper_verification_report: Paper Trading 用 SQLite データベースからシステム安定性、注文成功率、送信率、レイテンシ等を集計してレポート出力する CLI を追加。
    - P95 計算、閾値判定（稼働率、成功率、送信率、P95 レイテンシ）を行い PASS/FAIL を判定。
    - --from / --to / --db オプションをサポート。
    - デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）。

### Changed

- なし（初回公開）

### Fixed

- 環境変数の妥当性およびフォールバックを強化
  - MONITOR_POLL_INTERVAL: 整数で 1 以上でない場合はデフォルト（60 秒）にフォールバックして警告を出すように実装。
  - PAPER_FILL_MODE: 許容値以外は ValueError を発生させるバリデーションを追加。
  - set_process_priority/set_cpu_affinity: 権限不足や未対応 OS の際に例外を捕捉して警告し、プロセス継続を保証。

- ログ設定の堅牢化
  - ログディレクトリ作成に失敗した場合はファイルハンドラ作成をスキップして stdout のみで継続。既存ハンドラはクリアして重複設定を防止。

- DB 初期化の冪等性
  - Execution および Monitoring 起動時に監視用テーブルが存在することを保証する初期化処理を導入（init_monitoring_db を起動時に呼出し、存在確認/作成を行う）。

### Removed

- なし

### Known issues / TODO

- kabusys.research.factor_research の実装が途中（ソースが切れている部分があります）。ファクター計算の完全実装とテストが必要です。
- position_sizing: lot_size を銘柄別に扱う拡張（将来的な stocks マスタの導入）を TODO として記載。
- apply_sector_cap の価格欠損時（price が 0.0）の取り扱いについてコメントがある（将来的なフォールバック価格導入の検討）。
- ログディレクトリ作成失敗時は stdout へ直接警告を出す実装になっているが、より統一的なエラーハンドリングに改善の余地あり。

---

参考: 実行 / 確認に便利な CLI
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

環境変数の主要デフォルト:
- KABUSYS_ENV: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 60

以上。補足や別フォーマット（英語版やセクション分割など）をご希望の場合は指示してください。