# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

変更履歴は主にコードベースの内容から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-20

### Added
- 全体
  - 初期公開バージョン（__version__ = 0.1.0）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動的にプロジェクトルートを探索するユーティリティを追加（config 自動 .env ロードに使用）。
- 起動スクリプト / 実行制御
  - run_execution.py: 実際の注文実行を担当する ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動ロジックを実装。
    - 停止フラグ (data/stop_requested.flag) の検知およびエンジン停止ロジック、実行時 PID ファイル管理（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを集計。
    - 停止フラグ検知でループを終了する仕組みを実装。
- 設定 / CLI
  - config.py: 環境変数ラッパー Settings を追加。多くの設定（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視しきい値 / 環境種別など）をプロパティとして提供。
    - env 値の検証（development, paper_trading, live）と LOG_LEVEL の検証を実装。
    - PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH などペーパートレード向けの設定をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による .env 自動ロード無効化に対応。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（.env の読み書き、秘密値のマスク表示、保存確認など）。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在チェック、live 環境向けのガード等）。
- ロギング / プロセス制御
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、ログディレクトリ: logs/、デフォルト 30 日保持）をルートロガーに設定。
    - 環境変数 LOG_LEVEL / LOG_DIR、引数による上書きに対応。既存ハンドラの二重設定を防止。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）向けに差分を吸収。set_process_priority("high"/"normal"/"low")、set_cpu_affinity(N) を提供。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップ。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: 候補選定と重み計算（select_candidates、calc_equal_weights、calc_score_weights）を追加。
  - portfolio/risk_adjustment.py: セクター上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
    - セクター不明("unknown") の扱い、レジームに応じた乗数（bull/neutral/bear）などを実装。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケーリング、cost_buffer の考慮など）。
  - portfolio/__init__.py: 上記関数をパッケージ外に公開。
- 分析 / リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity の設計に準拠）。
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを参照してファクターを計算する方針を記載。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。
    - SQLite DB（PAPER_TRADING_SQLITE_PATH または --db）から集計して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを出力。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を行う。
    - --from / --to オプションで期間指定が可能。
- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を利用して監視用テーブルの存在を保証（冪等に初期化）。

### Changed
- 環境変数読み込み挙動
  - .env の自動読み込み順序を明文化: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護される（上書きされない）。
  - .env パーサーで export プレフィックス、シングル/ダブルクォート（エスケープ対応）、行内コメントの扱いをサポート。
- ログ出力
  - 標準エラーではなく標準出力（stdout）へ StreamHandler を出すように統一（タスクスケジューラや cron での一括リダイレクト容易化）。
- 起動時のプロセス優先度設定を各起動スクリプトの冒頭で実行（set_process_priority("high")）。

### Fixed
- .env ファイル読み込みでファイル IO エラー時に警告を出して安全に続行するよう改善。
- ログディレクトリ作成に失敗した場合でもコンソールログのみで継続するフォールバックを追加。

### Notes / Known limitations
- research/factor_research.py は設計方針と多くの定義を含むが、関数実装（ファイルの一部）が続く設計になっているため、追加実装・テストが必要な箇所が残る可能性があります（コードベースの一部が切れているように見えます）。詳細は該当ファイルを参照してください。
- position_sizing の lot_size 現状は全銘柄共通の想定。将来的に銘柄別単元をサポートする拡張が想定されている（TODO コメントあり）。
- apply_sector_cap の価格欠損時の扱いに注意（price が 0.0 の場合、エクスポージャーが過少見積もられるリスクがあることをコメントで言及）。
- process_priority や set_cpu_affinity は権限やプラットフォーム依存で失敗する可能性がある。失敗時は警告が出てスキップされる。

---

以上が本リリースでコードベースから推測できる主要な変更点です。必要ならば項目ごとに行や関数を参照した具体的なコード抜粋や追加で想定されるドキュメントを作成します。どの項目を詳細化しますか？