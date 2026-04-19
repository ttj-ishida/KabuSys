CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に準拠して記載しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリースを追加。
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB/SQLite を利用したデータ層の統合を実装（設定でパスを指定可能）。
- 実行 / 監視
  - run_execution: ExecutionEngine 起動エントリポイントを追加。
    - 実行前にプロセス優先度を "high" に設定。
    - KABUSYS_ENV に応じて paper_trading 用に専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine のスレッド実行・停止処理を実装。
    - 起動・停止に data/stop_requested.flag、pid ファイル（data/execution.pid）を利用する制御を実装。
  - run_monitoring: SystemMonitor をポーリングする監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理 / ユーティリティ
  - config: 環境変数管理クラス Settings を実装。
    - .env 自動読み込み（.env.local を上書き）、OS 環境変数保護機能、プロジェクトルート検出ロジックを実装。
    - 設定プロパティ（J-Quants / kabu API / DB パス / paper trading 設定 / 監視閾値 / ログレベル等）を提供し、バリデーションを行う。
    - PAPER_FILL_MODE 等の列挙的設定に対する検証（不正値は例外）。
  - config_setup: 対話式 .env ウィザードを追加。
    - .env の読み込み・既存値の再利用、選択肢・シークレット入力対応、ファイル書き出し（テンプレートヘッダ付き）。
  - validate_config: 起動前検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML 利用可）や本番環境向けガードチェックを実装。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御
  - utils.logging_setup: 共通ロギング設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラのクリーンアップ、LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップしても継続可能。
  - utils.process_priority: プロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定を実装。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数算出ロジックを実装。
    - ロット単位（lot_size）、最大ポジション比率、最大利用率、cost_buffer（手数料・スリッページ見積）を考慮した aggregate cap（スケーリング）処理を実装。端数の再配分ロジックも実装。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮）で候補銘柄を除外する機能を追加。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に対する投下資金乗数を提供。未知レジームはフォールバック 1.0。
- 解析 / 研究
  - research.factor_research: DuckDB 接続を受け取り、momentum/value/volatility/liquidity 系ファクターを計算する設計を追加（関数インターフェースと定数群を実装。モメンタム計算関数の骨子あり）。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite を読み、system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計。
    - 定義された閾値に基づく PASS/FAIL 判定とレポート出力を実装。P95 は簡易パーセンタイル実装。
- 監視 DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視用テーブル存在を保証（冪等）。

Changed
- ロギングは stdout を標準出力に使用する設計に統一（cron 等からのリダイレクトを想定）。
- .env 自動読み込みの優先順位を明確化（OS 環境変数 > .env.local > .env）。プロジェクトルートが見つからない場合は自動読み込みをスキップ。
- process_priority 実装はプラットフォーム差分を吸収し、権限エラーを安全に無視するように変更（警告ログのみ）。

Fixed
- env ファイルパーサ: export プレフィックス、クォート文字列、エスケープシーケンス、インラインコメントの扱いに対応（より現実的な .env 解析）。
- 各種 DB パスの親ディレクトリが存在しない場合の警告出力（起動時自動作成される旨注記）。
- Paper Trade / Live の DB 分離を明示（paper_trading 環境は paper_sqlite_path を使用）。

Notes / Known limitations
- research.factor_research 内の一部関数は実装の骨子が含まれており、完全実装（データスキャン開始日の算出や SQL 統合）は今後の作業を想定。
- position_sizing の価格欠損時の挙動（price が 0 の場合の過少見積り）は TODO コメントとして明示。将来的にフォールバック価格の導入を検討。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML）に依存。これらがない環境では機能限定や警告出力で継続する設計だが、完全動作にはインストールが必要。

Authors
- KabuSys 開発チーム（コードベースの注釈・設計に基づき CHANGELOG を作成）

--- 

（この CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノートや履歴管理にはコミット履歴・リリースタグを参照してください。）