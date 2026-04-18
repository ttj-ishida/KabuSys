# Changelog

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠の形式で記載しています。  
このファイルはコードベースの内容から推測して作成した初期リリースの変更履歴です。

全般的な注意
- バージョン番号はパッケージ定義 (src/kabusys/__init__.py の __version__) に基づきます。
- 環境変数やデフォルトパス、動作ポリシーはソースコードのコメント・実装を参照して記載しています。

Unreleased
---------
- （なし）

0.1.0 - 2026-04-18
-----------------
Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: src/kabusys/__init__.py (__version__ = "0.1.0")
- 実行・監視用スクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）および MockBrokerClient を使用し、本番 DB と完全分離する動作をサポート。
    - 停止制御: プロジェクトルート/data/stop_requested.flag を検知してエンジン停止。起動時に STOP フラグが立っている場合は起動を行わない。
    - 実行中の PID を data/execution.pid に記録する想定（pid_file の取り扱い）。
    - デフォルトでプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を呼び出し）。
    - DuckDB（分析用）接続を使用。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用（monitoring 用 DB 初期化を行う）。
    - 停止制御: パッケージルート/data/stop_requested.flag を検知してループを終了。
    - プロセス優先度を "high" に設定して起動。
- 設定管理・ユーティリティを追加。
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を起点に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD で抑制可能。
    - .env/.env.local の読み込みルール（OS 環境変数優先、.env.local は上書き）。
    - 複雑な行パース対応: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理など。
    - 各種設定プロパティを提供: DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)、API トークン、PID/kill flag パス、監視閾値、環境 (KABUSYS_ENV)、ログレベル など。入力検証を実施（例: KABUSYS_ENV の有効値チェック、PAPER_FILL_MODE の有効値制約）。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI。
    - J-Quants / kabu API 等の必須項目、ログ/DB パス、Kill Switch の初期設定などを支援。
  - src/kabusys/validate_config.py
    - 起動前設定検証 CLI。
    - 必須環境変数の存在チェック、KABUSYS_ENV のバリデーション、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードチェックなどを実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティを追加。
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティ。
    - ログレベル、ログディレクトリの解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみにフォールバック。
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定・CPU affinity 設定ユーティリティ。
    - Windows と POSIX（Linux/Mac/FreeBSD）向けに nice / priority を設定し、失敗時は警告でフォールバック。
- 実行コンポーネント（実装の呼び出し点）を追加（参照のみ、詳細実装は別モジュール）。
  - src/kabusys/execution/* への参照（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）
  - ExecutionEngine の起動時設定: target_date デフォルトは date.today()、RiskManager にデフォルト RiskConfig を提供（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- ポートフォリオ構築・リスク・ポジションサイジングに関する純粋関数群を追加（DB 非依存、メモリ内計算）。
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights)。スコアが全て 0 の場合は等配分にフォールバック（警告）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクターキャップ適用 (apply_sector_cap): 既存保有のセクター比率が閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジームマルチプライヤ (calc_regime_multiplier): "bull"/"neutral"/"bear" に応じた乗数を返す（未知値は 1.0 でフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジック（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer（手数料・スリッページ見積）を考慮したスケーリング処理を実装。
    - 利用可能現金を超える場合のスケールダウンと残余キャッシュによる端数配分の処理を行う。
- リサーチ / ファクター計算の土台を追加（DuckDB 接続前提）。
  - src/kabusys/research/factor_research.py（モメンタム等のファクター計算を実装する設計。prices_daily / raw_financials テーブル参照、Zスコア正規化は別モジュール想定）。
- Paper Trading 向け検証レポートツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - SQLite（デフォルト data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH / --db で上書き可）から各種統計を集計して人間向けレポートを出力。
    - 出力指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、平均/最大/P95 レイテンシなど。
    - 判定基準（PASS/FAIL）を定義（例: 稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 レイテンシ <= 200 ms）。
- 監視データベース初期化ユーティリティ参照。
  - src/kabusys/monitoring/monitoring_db.py を起動スクリプトから呼び出し（init_monitoring_db）。

Changed
- （初期リリースのためなし）

Fixed
- （初期リリースのためなし）

Deprecated
- （初期リリースのためなし）

Removed
- （初期リリースのためなし）

Security
- 環境変数ファイル (.env) に関する注意を config_setup のヘッダに記載（.env を絶対に Git にコミットしない旨）。
- 機密項目は対話ウィザードでマスクして表示（config_setup）。

ドキュメント / 備考
- 各 CLI スクリプトは __main__ エントリポイントを提供しており、単体で実行可能。
- monitor / execution の停止制御はプロジェクトルート/data/stop_requested.flag を使用する運用想定。
- logging_setup は stdout 出力を優先（Task Scheduler/cron 等で stdout/stderr をリダイレクトする運用を考慮）。
- 一部の機能（ExecutionEngine、BrokerClientFactory、SystemMonitor 等）はこの差分に含まれる呼び出しインタフェースに基づき参照されており、別ファイルでの実装が前提。

今後の改善候補（コード中コメントより推測）
- position_sizing: 銘柄ごとの lot_size をサポートするため stocks マスタから lot_map を受ける方式への拡張。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価など）を導入して露出計算の信頼性を向上。
- config._find_project_root の補完ロジック強化や .env のより厳密なパース互換性の追加。
- factor_research の完実装（ファクター計算の SQL / 出力形式の完成）。

--- 

（注）本 CHANGELOG は提供されたソースコードの実装内容・コメント・ファイル構成から推測して作成したものであり、実際のリリースノートと完全に一致しない可能性があります。必要に応じて日付、細部の用語、追加の変更点を反映して更新してください。