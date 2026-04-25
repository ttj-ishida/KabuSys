CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

ルール:
- 変更はカテゴリ（Added, Changed, Fixed, Removed, Deprecated, Security）ごとに分けて記載します。
- 日付は YYYY-MM-DD 形式で記載します。

[Unreleased]
------------

（現状、未リリースの差分はありません）

[0.1.0] - 2026-04-25
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基礎実装を追加。
  - パッケージバージョンは __version__ = "0.1.0"。
- 設定・環境関連
  - Settings クラスを実装し、環境変数経由で各種設定を取得可能に。
    - J-Quants / kabuステーション / LINE API のトークンや URL、ログレベル、KABUSYS_ENV 等をプロパティで提供。
    - DB パス（DuckDB / SQLite）、paper_trading 用 SQLite パス、PID/kill フラグパス、各種閾値（CPU/MEM/DISK）をサポート。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）を実装。
    - env 値（development / paper_trading / live）の検証ロジックを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序（OS 環境変数を保護）に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env ファイルのパースは export KEY=val、クォート、エスケープ、インラインコメント等に対応。
- 設定操作用 CLI/ユーティリティ
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 関連、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env の読み込みと Enter キーで既存値再利用可能。
  - validate_config: 起動前チェック用 CLI を追加。必須環境変数やパス、config/*.yaml の存在とパース（PyYAML があれば内容検証）を実行。
    - --strict オプションで警告をエラー扱いにできる。
    - live 環境に関するガードチェック（LINE 設定や Kill Switch の設定警告等）を実装。
- 起動スクリプト / ランタイム
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - paper_trading 環境では MockBrokerClient を利用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine の起動と停止（stop flag / PID ファイル処理）を実装。
    - RiskManager のデフォルト設定を明記（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() を使用。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - こちらは環境に関わらず本番 sqlite_path を使用して監視テーブルを操作する設計。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告後にデフォルトフォールバック。
    - stop フラグファイル（data/stop_requested.flag）検知でループ終了、例外や KeyboardInterrupt のハンドリング、DB 接続のクローズを行う。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 重複ハンドラ防止（既存ハンドラをクリア）を実装。
  - utils.process_priority: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加。
    - Windows / POSIX の差分吸収（nice 値や priorityClass を適切に設定）。権限不足などは警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（同点時は signal_rank でブレーク）と上位抽出。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 同一セクター集中制限を実装（sell_codes を考慮して既存保有を除外して判定、"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: market レジームに応じた資金乗数（bull/neutral/bear）を提供し、不明レジームはフォールバックして 1.0 を返す。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method("risk_based","equal","score") に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）に対するスケーリング、cost_buffer による保守的見積り、残差の分配ロジックを実装。
- 分析・検証ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下件数、API レイテンシ（平均・最大・P95）等を集計してレポート出力。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - CLI オプション: --from / --to / --db。環境変数 PAPER_TRADING_SQLITE_PATH との連携。
- 研究用モジュール（骨組み）
  - research.factor_research: DuckDB を利用したファクター計算用モジュールの骨格を追加（モメンタム等の定数・計算方針を定義）。関数の実装が進行中（ファイル途中まで実装）。

Changed
- 初期リリースのため変更履歴はなし。

Fixed
- 初期リリースのため修正履歴はなし。

Notes / Known limitations
- run_monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計（監視 DB を別に持つ想定がある場合は注意）。
- .env 自動ロードはプロジェクトルートを .git または pyproject.toml から検出するため、配布後やインストール環境で検出できない場合は自動ロードがスキップされる。
- research.factor_research の実装は未完（ファイルが途中で終わっています）。完全なファクター計算は今後の実装予定。

Security
- 特記事項なし。

ライセンス・貢献
- 初期リリース。貢献・バグ報告や改善提案はリポジトリの Issue を利用してください。

-----