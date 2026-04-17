CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ内の __version__ (src/kabusys/__init__.py) に基づきます。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アプリケーションの初回リリース。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを作成。RiskManager、OrderManager、Reconciler、ExecutionEngine の組み立てと実行を行う。
    - 停止フラグ (data/stop_requested.flag) を監視し、検知時に安全にエンジンを停止する仕組みを備える。
    - 実行時の PID を data/execution.pid に記録する仕組み（Engine に渡される）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する（監視データは一元管理）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了する。

- 設定・ユーティリティ
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env／.env.local の読み込み順序（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複数の設定プロパティを提供（J-Quants、kabuAPI、LINE、データベースパス、監視閾値、環境種別など）。
    - PAPER_FILL_MODE の許容値チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の許容値チェック（development/paper_trading/live）。
  - config_setup.py
    - 対話式ウィザードで .env ファイルを新規作成／更新する CLI。
    - デフォルト値、シークレットマスク表示、選択肢サポート、保存確認を提供。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在/パース確認、本番向けガード等を検証。
    - --strict オプションで警告をエラー扱いにできる。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）を OS ごとに適切に設定するユーティリティ。
    - Windows の HIGH_PRIORITY_CLASS 等に対応し、POSIX（Linux/Mac/FreeBSD）では nice 値を設定。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能（未対応環境やアクセス権限不足時は警告でスキップ）。

- 監視関連
  - monitoring_db の初期化呼び出し（init_monitoring_db）を run_monitoring と run_execution の起動時に行う（冪等で監視テーブルを保証）。

- Paper Trading / ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を集計して検証レポートを生成する CLI。
    - 指標: 稼働率 (uptime)、注文成功率（填率）、送信率、P95 レイテンシなど。
    - デフォルト閾値を実装（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。期間指定 (--from/--to) と DB パス指定 (--db) をサポート。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 信号のランキング選択（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコア合計が 0 の場合は等配分にフォールバック（警告出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を提供（bull/neutral/bear をマップし、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出（risk_based / equal / score の allocation_method）。
    - 損切り率、リスク率、単元株（lot_size）、単銘柄上限 (max_position_pct)、投下上限 (max_utilization)、cost_buffer（手数料・スリッページ見積）に対応。
    - aggregate cap によるスケールダウンと、lot_size 単位での端数処理を安定的に配分するロジックを実装。

- リサーチ（DuckDB ベース）
  - research/factor_research.py
    - DuckDB 接続を使って prices_daily / raw_financials を参照するファクター計算群を実装（モメンタム、ボラティリティ等）。
    - calc_momentum, calc_volatility 等の定義（MA200, 1/3/6ヶ月リターン、ATR20、20日平均出来高 等）。
    - 大量データの集計処理を SQL + Python で行う設計。

Changed
- n/a（初回リリースのため変更はなし）。

Fixed
- n/a（初回リリースのため修正はなし）。

Security
- 環境変数ファイル (.env) は Git にコミットしない旨を config_setup のヘッダに明示。
- シークレット項目は config_setup の表示でマスク処理を行う。

Notes / Important details
- 監視データベース（monitoring）は run_monitoring が常に Settings.sqlite_path を参照するため、環境にかかわらず本番用パスが使われる点に注意してください（意図的な設計）。
- Paper Trading は本番 DB と分離され、settings.is_paper が True の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
- MONITOR_POLL_INTERVAL の不正値（0 や負値、整数でない文字列）はログ警告の上でデフォルト 60 秒にフォールバックします。
- config モジュールはプロジェクトルート検出に __file__ の親階層を使うため、配布後も CWD に依存せず動作することを意図しています。プロジェクトルートが見つからない場合は自動 .env ロードをスキップします。
- set_process_priority / set_cpu_affinity は権限不足や非対応プラットフォームで失敗する可能性があり、その場合はログ出力でスキップされます。
- position_sizing 等のアルゴリズムは現時点で単元株（lot_size）を全銘柄共通で想定しているため、将来的に銘柄別 lot_size を導入する余地があります（TODO コメントあり）。

Upgrade notes
- 初回リリースのため移行手順はありません。既存の環境で利用する場合は .env を作成し、validate_config でチェックしてください。

ライセンス、貢献方法等についてはリポジトリ内のドキュメントを参照してください。