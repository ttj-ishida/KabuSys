# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-20
初回公開リリース。日本株自動売買システム KabuSys のコア機能群を提供します。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 環境設定 & ロード
  - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - .env ファイルの柔軟なパーサーを実装（export 形式、クォート付き値、インラインコメントの取り扱い）。
  - 環境変数の自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを追加し、J-Quants / kabu API、DB パス、Paper Trading 設定、監視しきい値、実行環境判定（development/paper_trading/live）などをプロパティ経由で取得可能に。

- 環境設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を作成・更新するツール。
  - 主要設定項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LOG_LEVEL / Kill Switch 等）をサポート。
  - 既存 .env 読み取り・表示・秘密項目のマスク等を実装。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前に .env や config/*.yaml の検証を行う。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在とパースチェック（PyYAML がない場合は警告）を実施。
  - `--strict` オプションで警告を失敗扱いにできる。

- 実行/監視起動スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ完全分離して記録。
    - broker クライアントファクトリ（BrokerClientFactory）を利用。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全停止。
    - PID ファイル管理（data/execution.pid）対応。
  - `run_monitoring.py`
    - システム監視ループ起動スクリプト。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録（init_monitoring_db を実行してテーブル存在を保証）。
    - stop フラグ検知でループ終了、check_once() 実行中に例外が起きた場合はログ出力して次回ポーリングへ継続。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ログ設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - `kabusys.utils.process_priority`
    - クロスプラットフォーム（Windows/Linux/その他 POSIX）でのプロセス優先度設定を提供（`set_process_priority`）。
    - CPU Affinity 固定用 `set_cpu_affinity` を追加。
    - psutil で権限不足や未サポート関数を検出した場合は警告ログを出してスキップする堅牢化を実装。

- データベース統合
  - DuckDB と SQLite 接続を両方利用する設計を導入（分析用 DuckDB、監視/発注記録用 SQLite）。
  - 監視 DB 初期化ユーティリティ `init_monitoring_db` を呼び出すフローを追加。

- ポートフォリオ構築ライブラリ（純関数）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（スコア降順 + タイブレーク）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックし警告ログを出力。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する `apply_sector_cap`（既存保有のセクター暴露を計算し、閾値以上のセクターの新規候補を除外）。
    - 市場レジームに応じた投入資金乗数 `calc_regime_multiplier`（bull/neutral/bear にマッピング、未知レジームは警告の上フォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数を計算する `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 損切り率・リスク率に基づく risk-based 計算、単元株（lot_size）丸め、1株あたり上限、aggregate cap（利用可能現金を超える場合のスケールダウン）や余りの配分ロジックを実装。
    - cost_buffer を用いた手数料・スリッページの保守的見積りに対応。

- 研究用ファクター計算
  - `kabusys.research.factor_research`
    - Momentum / MA200 / ATR 等のファクター計算を行う構成。DuckDB を利用して prices_daily / raw_financials を参照する方針と実装の骨格を実装（モメンタム計算関数など）。（calc_momentum は実装途中の章あり）

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading の検証レポートを生成する CLI。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、P95 レイテンシ等を集計して PASS/FAIL 判定（閾値はファイル内定義）。
    - 日付フィルタオプション（--from / --to）および DB パス指定（--db / 環境変数）をサポート。
    - DB が存在しない / テーブルがない場合に柔軟に N/A を表示する堅牢化。

### Changed
- .env 読み込みの優先度と上書きルールを明確化
  - OS 環境変数 > .env.local > .env の順で読み込む。既存 OS 環境変数は protected として上書きを防止。
- ログレベル解決の順序を明示（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。
- ログハンドラの設定時に既存ハンドラを一度閉じてから削除することで二重出力を防止。
- run_execution / run_monitoring の起動フローでプロセス優先度設定を最初に行うように統一。

### Fixed
- 設定ファイル読み込み失敗時のハンドリングを改善
  - .env 読み込み失敗で警告を出す（warnings.warn）ようにして起動失敗を防止。
- process_priority でサポート外 OS・権限不足の際に例外で落ちないよう例外処理を追加。
- run_monitoring のポーリングループで check_once() が例外を出してもループを続行するようにして監視の継続性を確保。
- run_execution が停止フラグ検出時に安全に ExecutionEngine を停止してスレッド終了を待機する処理を追加。

### Security
- .env の生成スクリプトで「.env を絶対に Git にコミットしない」旨を明記（README 相当の注意喚起を .env コメント内に記載）。

### Notes / Known limitations
- research.factor_research の一部関数は実装途中の箇所あり（実稼働前に完全実装・テスト推奨）。
- position_sizing の将来的拡張点: 銘柄別 lot_size を導入し、stocks マスタから単元情報を読み取る設計に拡張予定（TODO コメントあり）。
- apply_sector_cap は price が欠損（0.0）の場合にエクスポージャーの過少見積りが発生する可能性があるため、将来フォールバック価格の導入を検討。
- 実行ユーザの権限や OS によってはプロセス優先度/affinity の設定がスキップされる。ログで確認可能。

---

この CHANGELOG は提供されたソースコードの構造・コメント・実装から推測して作成しています。追加の履歴分割（マイナー/パッチ等）やリリース日付の変更が必要な場合はご指示ください。