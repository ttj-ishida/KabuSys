# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはソースコードの内容から推測して作成されています — 実際のコミット履歴ではなく、現行実装で導入されている機能・仕様・既知の制約をまとめたものです。

※ バージョンは src/kabusys/__init__.py の __version__ (0.1.0) を基準にしています。

全般的な注意
- 日付は本書作成日 (2026-04-18) を使用しています。
- 「追加」「変更」「修正」はコードから推測した範囲で記載しています。
- 実装上の既知制約や TODO（コード内コメントを元に推測）も最後に記載しています。

---------------------------------------------------------------------
Unreleased
---------------------------------------------------------------------
- なし

---------------------------------------------------------------------
[0.1.0] - 2026-04-18
---------------------------------------------------------------------
Added
- 基本アプリケーション構成を実装
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
- 環境設定管理
  - .env 自動読み込み機能（プロジェクトルートの .env/.env.local を読み込み、OS 環境変数を保護）
  - 高度な .env パーサ:
    - export KEY=val 形式対応、クォート（シングル/ダブル）やバックスラッシュエスケープを考慮
    - インラインコメントの扱い（クォート有無での振る舞い差分）
  - Settings クラス: 環境変数からの各種設定取得ロジック（デフォルト値、バリデーション付き）
    - DB パス（DUCKDB_PATH, SQLITE_PATH）、KABUSYS_ENV（development/paper_trading/live）、
      PAPER_FILL_MODE（instant/partial/never/reject のバリデーション）など
- 設定ユーティリティ CLI
  - config_setup: 対話式ウィザードで .env を作成/更新する機能を追加
    - 秘匿値はマスク表示、確認プロンプト、ファイルへの書き出しロジックを実装
  - validate_config: .env と config/*.yaml の簡易検証 CLI を追加
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック
    - PyYAML があれば config/*.yaml のパース検証を実行
    - KABUSYS_ENV=live の際の追加ガード（LINE 設定や Kill Switch 設定の警告）
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db をデフォルト）を使い本番 DB と分離
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBrokerClient を想定）
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動（スレッド実行）
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル指定
    - RiskManager の初期設定値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）がデフォルトで導入
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒、0/負値はデフォルトへフォールバックし警告）
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視 DB を共通化）
    - 停止フラグでループ終了、check_once() 実行時の例外はログ出力して次ポーリングへフォールバック
- ログ・プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定
    - LOG_LEVEL / LOG_DIR の解決順、ログディレクトリ作成失敗時の graceful fallback 実装
  - utils.process_priority:
    - set_process_priority(level) による Windows / POSIX の優先度設定ラッパー（psutil 利用）
    - set_cpu_affinity(cpu_count) による CPU affinity 設定（利用可能コア数未満のときの扱い、例外ハンドリング）
    - 例外・権限不足時は警告を出してスキップ
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順、同点は signal_rank 昇順でタイブレーク
    - calc_equal_weights, calc_score_weights（スコア合計が 0 の場合に等配分へフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャを計算し、最大セクタ割合を越えるセクターの新規候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: market regime に応じた投下比率（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 へフォールバック）
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）
    - lot_size（単元）に合わせた丸め処理、per-position 上限・aggregate cap（利用可能現金に合わせたスケールダウン）実装
    - cost_buffer を考慮した保守的見積り、スケールダウン時の fractional remainder による追加配分ロジック
- 解析・検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用の検証レポート生成スクリプトを追加
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計して PASS/FAIL 判定を出力
    - CLI 引数で日付範囲（--from/--to）・DB パス（--db）を指定可能
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
    - 各種閾値はソース内に定義（稼働率 >=99%、fill_rate >=90% 等）
- データ分析（研究）モジュール（着手）
  - research.factor_research: モメンタム等ファクター計算モジュールの骨組みを実装（DuckDB 接続受け取り、momentum 指標の計算設計が始まっている）

Changed
- ルートロギングを統一的に初期化する仕組みを追加し、起動スクリプトから必ず呼び出すように設計（setup_logging）
- 実行スクリプト起動時にプロセス優先度を最初に設定する設計へ（set_process_priority("high")）

Fixed
- なし（初期リリースとしての実装）

Deprecated
- なし

Removed
- なし

Security
- 環境変数の必須値は Settings._require で厳格にチェックするため、未設定時は ValueError を送出して起動を抑止する

---------------------------------------------------------------------
既知の制約・TODO（コードコメントから推測）
---------------------------------------------------------------------
- research.factor_research.calc_momentum の実装は途中で切れており未完成（関数末尾が途中で終わっている）。ファクター計算はまだ完全実装されていない可能性あり。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が 0.0 の場合にエクスポージャを過少見積りしてしまう旨の TODO がある（フォールバック価格の導入検討が必要）。
- position_sizing:
  - 将来的に銘柄別の lot_size をサポートする旨の TODO（現状は全銘柄共通の単元サイズを想定）。
- run_monitoring / run_execution:
  - 外部依存（duckdb, sqlite3, BrokerClientFactory, ExecutionEngine, SystemMonitor 等）の実装が別モジュールに分かれているため、本 CHANGELOG はそれらの内部挙動を完全にカバーしていない。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップするが、外部環境（CI/コンテナ等）では追加のロギング設定が必要となる場合あり。
- process_priority の設定は権限やプラットフォームによって失敗することがあり、その場合は警告でスキップされる（想定どおりの動作だが、期待どおり動作しない環境があり得る）。

---------------------------------------------------------------------
参考（実行コマンド例）
---------------------------------------------------------------------
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---------------------------------------------------------------------
付記
---------------------------------------------------------------------
この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートやコミット履歴がある場合はそちらを優先してください。必要であれば、各モジュール（ExecutionEngine / SystemMonitor / BrokerClientFactory 等）の詳細な変更点を個別に推測して追記できます。