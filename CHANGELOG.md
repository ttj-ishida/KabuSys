# Changelog

すべての重要な変更履歴は Keep a Changelog 規約に従って記載しています。セマンティックバージョニングを採用しています。

全般的な注記:
- 本 CHANGELOG は、提示されたソースコードから読み取れる機能追加・設計意図・動作仕様を推測して作成しています。
- 実際のコミット履歴ではなく、コードベースの「初期リリース相当の変更点」をまとめたものです。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-25
初版リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行スクリプト / サービス起動
  - run_execution: ExecutionEngine 起動用エントリポイントを追加。
    - プロセス優先度を設定（`set_process_priority("high")`）。
    - 環境に応じて paper_trading 用 DB を分離（`PAPER_TRADING_SQLITE_PATH` / settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て・起動。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、実行用 PID ファイル management。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する旨の動作。
    - stop フラグ検出で監視ループを終了、例外・KeyboardInterrupt をハンドリングしてクリーンに接続を閉じる。
    - duckdb と sqlite の接続確立、監視 DB 初期化（init_monitoring_db）。

- 設定・環境管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数から各種設定値（J-Quants、kabu API、DB パス、監視閾値、KABUSYS_ENV 等）を取得するプロパティ群を提供。
    - 自動 .env 読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - PAPER_FILL_MODE の妥当性検査（instant/partial/never/reject）。
    - 環境の enum チェック（development / paper_trading / live）とログレベル検証。
  - settings インスタンスをモジュール化して簡易アクセスを提供。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env ファイルの初期作成・更新を行う CLI を追加。
    - 入力プロンプト・既存 .env 読み込み・シークレットマスク・選択肢サポート。
    - 生成される .env テンプレートと注意書き。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml 存在と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログ出力先・レベルの解決順（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使うことで cron 等のリダイレクト環境に配慮。
  - process_priority: クロスプラットフォームなプロセス優先度設定・CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS を吸収する実装。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を実装。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: シグナルのスコア降順ソートと上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック。既存保有を加味して新規候補をフィルタリング。unknown セクターは制限適用しない設計。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装（デフォルトフォールバックと警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定ロジック。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に応じたスケールダウン、cost_buffer を加味した保守的見積り、端数処理の再分配ロジック等を実装。

- 監視・実行のための DB/モニタ関連
  - init_monitoring_db 呼び出しを run_* スクリプトに組み込み、監視テーブルが存在することを保証（冪等）。
  - SystemMonitor / ExecutionEngine 等（参照されるが詳細実装は別モジュール）との連携を意図した起動フローを整備。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を抽出してレポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - 基準値（閾値）を定義し PASS/FAIL を判定する仕組みを提供。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）をサポート。
    - latency の P95 計算、存在しないテーブルへのフォールバック処理を備える。

- リサーチ / ファクター計算（下書き）
  - research/factor_research.py を追加（モメンタム等のファクター計算関数を実装予定）。
    - DuckDB を使った prices_daily/raw_financials 参照設計、モメンタム・MA・ATR 等の計算方針をドキュメント化。
    - ファイルは途中（トランケート）だが、設計方針と定数は定義済み。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

----------

注記・運用上のポイント（コードから推測）
- 環境分離:
  - Paper Trading は paper_trading 専用の SQLite を使用し、本番データと明確に分離される設計（安全対策）。
- Kill / Stop 制御:
  - data/stop_requested.flag や kill.flag 系を用いた外部停止フラグを監視して安全に停止する仕組みがある。
- ログとデバッグ:
  - ログ設定は全起動スクリプトで統一されており、ファイル出力が失敗してもコンソールログでフォールバックする堅牢性を持つ。
- 設定健全性:
  - validate_config により起動前に設定ミスを検知できる（YAML パースチェックは PyYAML の有無に依存）。
- 数値/丸め処理:
  - position_sizing の実装は lot_size（単元）丸めや aggregate スケーリング、端数再配分など実運用向けの配慮がなされている。

もし望まれるなら、以下を提供できます:
- 各モジュール／API（関数・クラス）ごとの詳細な「変更点→理由→影響範囲」ドキュメント
- 実運用時のチェックリスト（.env 作成・validate_config の使い方、ログ監視、停止フラグ運用など）
- CHANGELOG を Markdown ファイルとしてそのまま使える形で出力（ファイル化）