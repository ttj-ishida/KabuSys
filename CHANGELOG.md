CHANGELOG
=========
(このプロジェクトは "Keep a Changelog" の形式に準拠しています)

Unreleased
----------
- なし

[0.1.0] - 2026-04-19
--------------------
Added
- 基本アプリケーション構成を追加（初回リリース）。
  - パッケージバージョンを __version__ = "0.1.0" に設定。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、本番 DB と完全分離する実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立てを行い、ExecutionEngine.run_session をデーモンスレッドで実行。停止は data/stop_requested.flag による外部フラグで行える。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを追加（set_process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視処理は環境にかかわらず production の sqlite_path を利用する（監視 DB は常に本番パス）。
    - 停止フラグ（data/stop_requested.flag）の検知でループを終了。
- 設定管理
  - config.py
    - Settings クラスを追加し、環境変数から各種設定を取得するインターフェースを提供。
    - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。優先度は OS 環境変数 > .env.local > .env。
    - .env パース機能は export キーワード、クォート文字、インラインコメント（スペース/タブで始まる '#' のみ）などに対応。
    - 各種プロパティを実装（J-Quants トークン、kabu API、DuckDB/SQLite パス、Paper Trading 設定、監視閾値、環境判定ユーティリティ等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 設定ユーティリティ／CLI
  - config_setup.py
    - .env 作成・更新の対話式ウィザードを追加。既存 .env の読み込み、シークレットのマスク表示、確認後ファイル出力を行う。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス／config/*.yaml の存在と YAML パース、live 環境向けガード等）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定する共通ユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定を追加（Windows/Linux/macOS の nice/priority を考慮）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（アクセス権限がない場合は警告でスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分へフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）を実装。既存保有のセクター別時価に基づき上限を越えるセクターの新規候補を除外する。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull:1.0 / neutral:0.7 / bear:0.3）。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - position sizing（株数決定）ロジックを実装。allocation_method= "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファ（cost_buffer）を考慮したスケーリング、残差配分ロジックを実装。
- リサーチ
  - research/factor_research.py（ファクター計算モジュールを追加）。DuckDB を使い prices_daily/raw_financials を参照してモメンタム／Value／Volatility／Liquidity を計算する方針を実装（モジュールの一部がファイル末尾で未完）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH 環境変数（または --db オプション）で DB を指定。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する基準値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from/--to）に対応。
- 監視データベース初期化
  - monitoring_db.init_monitoring_db を run_* スクリプトから呼び出して、監視テーブルが存在することを保証（冪等処理）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues
- research/factor_research.py はファイル末尾が切れており、calc_momentum 等の一部実装が未完の可能性があります（リリース時点で補完が必要）。
- apply_sector_cap: price_map に欠損（0.0）がある場合、エクスポージャーが過少に見積もられる旨の TODO コメントがあり、将来的にフォールバック価格の導入が想定されています。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム制約で失敗する場合があり、その場合は警告を出してスキップする設計です。

How to use (簡易)
- .env はプロジェクトルートの .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 設定確認: python -m kabusys.validate_config [--strict]
- .env 作成: python -m kabusys.config_setup
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上